from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.conf import settings
from bms.admin_inlines.planned_payment.planned_payment import RefundPlannedPaymentToCollectInline,    RefundPlannedPaymentToPayInline
from bms.admin_inlines.actual_payment.actual_payment import ActualPaymentPaidByMemberInline,    ActualPaymentPaidToMemberInline
from bms.models import PlannedPayment
from bms.models.booking.booking import Booking, BookingRefundProxy
from bms.services import bookings as bookings_service


class BookingRefundProxyAdmin(admin.ModelAdmin):
    model = BookingRefundProxy
    inlines = [RefundPlannedPaymentToCollectInline, RefundPlannedPaymentToPayInline,
               ActualPaymentPaidByMemberInline, ActualPaymentPaidToMemberInline, ]
    readonly_fields = ['code', 'departure_at', 'type', 'buyer', 'currency', 'amount',
                       'amount_in_inr', 'booking_actions',
                       'booking_date', 'destination',
                       'nights_count',
                       'adults_count', 'children_count', 'document_status', 'proof', 'inclusions',
                       'description', ]

    list_display = ['id', 'code', 'type', 'category', 'destination', 'departure_at',
                    'nights_count', 'booking_date', 'created_by',
                    'currency',
                    'amount',
                    'created_at', 'created_by']

    fieldsets = (
        ('Booking info', {
            'fields': (('code'), ('type',),
                       ('buyer'), ('seller'),
                       ('booking_actions')
                       )}),
        ('Other Booking info', {
            'classes': ('grp-collapse grp-closed',),
            'fields': (
                ('currency'), ('amount'), ('departure_at',), ('amount_in_inr'), ('safe_id'),
                ('booking_date'), ('destination'), ('nights_count'), ('adults_count'),
                ('children_count'), ('inclusions'),)}),
    )

    def get_fieldsets(self, request, obj=None):
        if obj:
            if obj.booking_version_type == self.model.V2:
                return (
                    ('Booking info', {
                        'fields': (('code'), ('type',),
                                   ('buyer'), ('booking_actions')
                                   )}),
                    ('Other Booking info', {
                        'classes': ('grp-collapse grp-closed',),
                        'fields': (
                            ('currency'), ('amount'), ('departure_at',), ('amount_in_inr'), ('safe_id'),
                            ('booking_date'), ('destination_text'), ('destination'), ('nights_count'), ('adults_count'),
                            ('children_count'), ('inclusions'),)}),
                )
        return self.fieldsets

    def edit_booking(self, obj):
        return mark_safe("<a href='{}'>Edit Booking</a>".format(reverse('admin:trs_booking_change', args=[obj.id])))

    def booking_actions(self, obj):
        if not obj.status == Booking.CANCELLED:
            return mark_safe(
                "<ul><li>{}</li><li></li><li>{}</li><li></li></ul>".format(self.edit_booking(obj),
                                                                                      self.claim_link(obj)))

    def claim_link(self, obj):
        return mark_safe("<a href='{}' target='_booking'>Claim collection</a>".format(
            reverse('admin:accounts_bankrecord_changelist')))


    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(deleted=False).select_related('type', 'category', 'buyer', 'seller', 'currency',
                                                       'destination', 'created_by')

    def has_add_permission(self, request, obj=None):
        return False


    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        response = super(BookingRefundProxyAdmin, self).render_change_form(request, context, add, change, form_url, obj)
        response.context_data['title'] = "Booking Refund Page"
        return response

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=True)
        for instance in instances:
            if formset.model == PlannedPayment:
                if instance.bookings.booking_version_type == Booking.V2:
                    if instance.member.id == instance.bookings.buyer.id:
                        instance.member_currency = instance.bookings.collection_currency
                        instance.amount_in_collection_currency = bookings_service.calculate_amount_in_collection_currency_for_collection(
                            instance.bookings.collection_currency.id,
                            instance.member_currency.id, instance.bookings.created_at, instance.amount)
                    else:
                        seller_cost_components = bookings_service.get_seller_cost_components_by_booking_code(instance.bookings.code, seller_member__id=instance.member.id)
                        instance.member_currency = seller_cost_components.last().seller_currency
                        instance.amount_in_collection_currency = bookings_service.calculate_amount_in_collection_currency_for_payment(
                            instance.bookings.collection_currency.id, instance.amount, seller_cost_components)
            instance.save()

    def response_change(self, request, obj):
        if "_continue" not in request.POST:
            if obj.category.id == settings.CATEGORY_FLIGHT_ID:
                return redirect(reverse('admin:trs_bookingflightproxy_change', args=[obj.id]))
            return redirect(reverse('admin:trs_booking_change', args=[obj.id]))
        return super().response_change(request, obj)


admin.site.register(BookingRefundProxy, BookingRefundProxyAdmin)
