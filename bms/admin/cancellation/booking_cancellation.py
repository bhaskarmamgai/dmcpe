from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.conf import settings
from bms.admin_inlines.booking.booking_cancellation import BookingCancellationInline, \
    CancellationStatusHistoryReadOnlyInline
from bms.admin_inlines.planned_payment.planned_payment import CancellationPlannedPaymentCollectionInline, \
    CancellationPlannedPaymentScheduleInline
from bms.admin_inlines.actual_payment.actual_payment import ActualPaymentPaidByMemberInline, \
    ActualPaymentPaidToMemberInline
from bms.models.booking.booking import Booking, BookingCancellationProxy
from bms.models.booking.booking_log import BookingLog
from bms.models.planned_payment.planned_payment import PlannedPayment
from bms.models.cancellation.booking_cancellation import CancellationRequestType, CancellationRequest, \
    CancellationStatusHistory
from django.db.models import Q, OuterRef, Subquery


class BookingCancellationProxyAdmin(admin.ModelAdmin):
    model = BookingCancellationProxy
    inlines = [BookingCancellationInline, CancellationPlannedPaymentScheduleInline,
               CancellationPlannedPaymentCollectionInline,
               ActualPaymentPaidByMemberInline, ActualPaymentPaidToMemberInline, ]
    readonly_fields = ['code', 'departure_at', 'type', 'buyer', 'currency', 'amount',
                       'amount_in_inr', 'current_status', 'booking_actions',
                       'booking_date', 'destination',
                       'nights_count',
                       'adults_count', 'children_count', 'document_status', 'proof', 'inclusions',
                       'description', ]

    list_display = ['id', 'code', 'type', 'category', 'destination', 'departure_at',
                    'nights_count', 'booking_date', 'created_by',
                    'currency',
                    'amount',
                    'created_at', 'created_by']
    list_per_page = 5

    fieldsets = (
        ('Booking info', {
            'fields': (('code'), ('type',),
                       ('buyer'), ('seller'),
                       ('current_status'),
                       ('booking_actions')
                       )}),
        ('Other Booking info', {
            'classes': ('grp-collapse grp-closed',),
            'fields': (
                ('currency'), ('amount'), ('departure_at',), ('amount_in_inr'), ('safe_id'),
                ('booking_date'), ('destination'), ('nights_count'), ('adults_count'),
                ('children_count'), ('inclusions'),)}),
    )

    def edit_booking(self, obj):
        return mark_safe("<a href='{}'>Edit Booking</a>".format(reverse('admin:bms_booking_change', args=[obj.id])))

    def booking_actions(self, obj):
        if not obj.status == Booking.CANCELLED:
            return mark_safe(
                "<ul><li>{}</li><li></li><li>{}</li><li></li></ul>".format(self.edit_booking(obj),
                                                                           self.claim_link(obj)))

    def claim_link(self, obj):
        return mark_safe("<a href='{}' target='_booking'>Claim collection</a>".format(
            reverse('admin:accounts_bankrecord_changelist')))

    def current_status(self, obj):
        if obj.status == Booking.CANCELLATION_INITIATED:
            return mark_safe(
                "Cancellation Initiated<br />" +
                "<a href='{}'>Settle Cancellation</a><br>".format(
                    reverse('bms:booking_cancellation_cancellation_final_settlement', args=[obj.id])
                ) +
                "<a href='{}' class='proxy_booking_cancel_link'>Cancel Now</a>".format(
                    reverse('bms:booking_cancellation_cancel_booking', args=[obj.id]))
            )
        if obj.status == Booking.CANCELLATION_SETTLED:
            return mark_safe(
                "Cancellation Initiated<br /> " +
                "Cancellation Settled<br /> " +
                "<a href='{}' class='proxy_booking_cancel_link'>Cancel Now</a>".format(
                    reverse('bms:booking_cancellation_cancel_booking', args=[obj.id])))
        elif obj.status == Booking.CANCELLED:
            return mark_safe(
                "Cancellation Initiated<br /> " +
                "Cancellation Settled<br /> " +
                "Cancelled ")
        else:
            return obj.status

    def save_model(self, request, obj, form, change):
        if not obj.pk:

            obj.created_by = request.user
        else:
            if change:

                old_object = self.model.objects.get(id=obj.id)
                if obj.status == BookingCancellationProxy.CONFIRMED:
                    obj.status = BookingCancellationProxy.CANCELLATION_INITIATED

                for field in form.changed_data:
                    tl = BookingLog(bookings=obj, column_name=field, old_value=getattr(old_object, field),
                                    new_value=getattr(obj, field), done_by=request.user)
                    tl.save()
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        return qs.filter(deleted=False).select_related('type', 'category', 'buyer', 'seller', 'currency',
                                                       'destination', 'created_by',
                                                       'booking_summary')

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            if formset.model == PlannedPayment:
                if instance.member.id == instance.bookings.buyer.id:
                    instance.type = PlannedPayment.DUE_ON_MEMBER
                if instance.member.id == instance.bookings.seller.id:
                    instance.type = PlannedPayment.DUE_TO_MEMBER
            instance.save()
        formset.save_m2m()

    def get_model_perms(self, request):
        """
        #https://stackoverflow.com/questions/2431727/django-admin-hide-a-model
        Return empty perms dict thus hiding the model from admin index.
        """
        return {}

    def has_add_permission(self, request, obj=None):
        return False

    def response_change(self, request, obj):
        return redirect(reverse('admin:bms_bookingcancellationproxy_change', args=[obj.id]))

    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        response = super(BookingCancellationProxyAdmin, self).render_change_form(request, context, add, change,
                                                                                 form_url, obj)
        response.context_data['title'] = "Booking Cancellation Details"
        return response

    class Media:
        js = [
            '/static/js/bookings.js/',
        ]


class CancellationRequestTypeAdmin(admin.ModelAdmin):
    model = CancellationRequestType
    list_display = ['id', 'request_type', 'version', 'category', 'is_direct_cancellation', 'additional_remarks']
    list_filter = ['request_type', 'version', 'category']
    search_fields = ['request_type', 'category']
    list_per_page = 5

    def has_delete_permission(self, request, obj=None):
        return False


class CancellationRequestAdmin(admin.ModelAdmin):
    model = CancellationRequest
    list_per_page = 5
    fields = ['get_requests_count', 'status', 'get_document_url', 'request_type',
              'get_seller_booking_code_and_supplier_name', 'member_remarks', 'booking_link', 'get_booking_date',
              'get_booking_departure_date', 'created_by', 'get_cancellation_code', 'charges',
              'background_sync_with_provider_status', 'oc_status', 'assigned_to']
    readonly_fields = ['get_requests_count', 'request_type', 'member_remarks', 'booking_link', 'get_booking_date',
                       'get_booking_departure_date', 'get_booking_category',
                       'get_seller_booking_code_and_supplier_name',
                       'created_by', 'get_cancellation_code', 'get_document_url']
    list_display = ['id', 'request_type', 'member_remarks', 'get_seller_booking_code_and_supplier_name', 'booking_link',
                    'get_booking_date', 'service_request_status', 'status', 'get_booking_departure_date',
                    'get_booking_category',
                    'get_cancellation_code', 'created_at', 'created_by', 'updated_at']
    list_filter = ['request_type', 'booking', 'booking__category',
                   'booking__departure_at',
                   'booking__booking_date',
                   'status', 'service_request_status', 'created_by']

    search_fields = ['id', 'request_type__request_type', 'status', 'booking__code', 'cancellation_code',
                     'booking__booking_details__seller_booking_code']
    autocomplete_fields = ['booking']
    inlines = [CancellationStatusHistoryReadOnlyInline]

    def get_requests_count(self, obj):
        count = CancellationRequest.objects.filter(booking_id=obj.booking_id).count()
        return mark_safe("<a href='{}'>{}</a>".format(
            settings.ADMIN_SITE_DOMAIN + "/admin/bms/cancellationrequest/?booking__id__exact={}".format(obj.booking_id),
            count))

    def booking_link(self, obj):
        return mark_safe(
                "<a href='{}'>{}</a>".format(reverse("admin:bms_booking_change", args=[obj.booking.id]),
                                             obj.booking.code))

    def get_booking_date(self, obj):
        if obj and obj.booking:
            return obj.booking.booking_date
        return "-"

    def get_booking_departure_date(self, obj):
        if obj and obj.booking:
            return obj.booking.departure_at
        return "-"

    def get_cancellation_code(self, obj):
        if obj and obj.cancellation_code and obj.request_type_id == settings.REQUEST_TYPE_MANUAL_ID:
            return obj.cancellation_code

        elif obj.cancellation_code and obj.booking.category_id == settings.CATEGORY_FLIGHT_ID:
            return mark_safe(
                '<a href="%s">%s</a>' % (
                    settings.FMS_ADMIN_DOMAIN + settings.FMS_CANCELLATION_REQUEST_ENDPOINT.format(
                        obj.cancellation_code), obj.cancellation_code))
        elif obj.cancellation_code and obj.booking.category_id == settings.CATEGORY_HOTEL_ID:
            return mark_safe(
                '<a href="%s">%s</a>' % (
                    settings.HMS_ADMIN_DOMAIN + settings.HMS_CANCELLATION_REQUEST_ENDPOINT.format(
                        obj.cancellation_code), obj.cancellation_code))
        else:
            return '-'

    def get_document_url(self, obj=None):
        if obj and obj.document:
            return mark_safe("<a href='{}'>{}</a>".format(obj.document, obj.document))
        return 'NA'

    def get_seller_booking_code_and_supplier_name(self, obj=None):
        booking_obj = obj.booking
        booking_details_obj = booking_obj.booking_details if hasattr(booking_obj, 'booking_details') else None
        seller_booking_code = booking_details_obj.seller_booking_code
        if obj and booking_details_obj:
            supplier_info_str = seller_booking_code if seller_booking_code else ''
            booking_financial_obj = booking_obj.booking_financial if hasattr(booking_obj, 'booking_financial') else None
            vendor_org_obj = booking_financial_obj.vendor_organization if booking_financial_obj else None
            if vendor_org_obj and vendor_org_obj.name:
                supplier_info_str += ' | ' + vendor_org_obj.name
            return supplier_info_str
        return '-'

    def get_booking_category(self, obj=None):
        if obj and obj.booking.category:
            return obj.booking.category.name
        return "-"

    def save_model(self, request, obj, form, change):
        if obj:
            obj.save(update_fields=form.changed_data)
        super(CancellationRequestAdmin, self).save_model(request, obj, form, change)

    def get_queryset(self, request):

        qs = super(CancellationRequestAdmin, self).get_queryset(request)
        qs = qs.select_related('service_request_status__request_type', 'booking', 'request_type')

        return qs

    booking_link.short_description = "Booking"
    get_booking_departure_date.short_description = "Travel Date"
    get_booking_date.short_description = "Booking Date"
    get_cancellation_code.short_description = "Cancellation Code"
    get_document_url.short_description = "Document Url"
    get_requests_count.short_description = "Total Requests Count"
    get_seller_booking_code_and_supplier_name.short_description = "Seller Booking Code | Supplier"
    get_booking_category.short_description = "Category"

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class CancellationStatusHistoryAdmin(admin.ModelAdmin):
    model = CancellationStatusHistory
    fields = ['booking', 'updated_by', 'updated_at', 'cancellation_request_link']
    readonly_fields = ['booking', 'updated_by', 'updated_at', 'cancellation_request_link', 'cancellation_status']
    list_display = ['id', 'booking_link', 'cancellation_request_link', 'cancellation_status',
                    'updated_by', 'updated_at']
    list_filter = ['booking__code', 'cancellation_request__cancellation_code']
    search_fields = ['booking__code', 'cancellation_request__cancellation_code']
    list_per_page = 5

    def booking_link(self, obj):
        if obj.booking.category and obj.booking.category.id == settings.CATEGORY_FLIGHT_ID:
            return mark_safe(
                "<a href='{}'>{}</a>".format(reverse("admin:bms_bookingflightproxy_change", args=[obj.booking.id]),
                                             obj.booking.code))
        else:
            return mark_safe(
                "<a href='{}'>{}</a>".format(reverse("admin:bms_booking_change", args=[obj.booking.id]),
                                             obj.booking.code))

    def cancellation_request_link(self, obj):
        if obj and obj.cancellation_request:
            return mark_safe(
                "<a href='{}'>{}</a>".format(reverse("admin:bms_cancellationrequest_change",
                                                     args=[obj.cancellation_request.id]), obj.cancellation_request))
        return "-"

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return super(CancellationStatusHistoryAdmin, self).get_queryset(request).select_related(
            'cancellation_request', 'booking', 'booking__type', 'booking__category', 'booking__buyer',
            'booking__seller', 'booking__created_by', 'updated_by')


admin.site.register(BookingCancellationProxy, BookingCancellationProxyAdmin)
admin.site.register(CancellationRequestType, CancellationRequestTypeAdmin)
admin.site.register(CancellationRequest, CancellationRequestAdmin)
admin.site.register(CancellationStatusHistory, CancellationStatusHistoryAdmin)
