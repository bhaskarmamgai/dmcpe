from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe

from bms.custom_filters import PlannedPaymentToCollectStatusFilter, PlannedPaymentToPayStatusFilter
from bms.models.planned_payment.planned_payment import PlannedPayment, PlannedPaymentBuyerProxy, \
    PlannedPaymentSellerProxy


class PlannedPaymentAdmin(admin.ModelAdmin):
    model = PlannedPayment
    list_display = ['id', 'member_link', 'booking_link', 'date',
                    'booking_document_status', 'booking_details_remark', 'payment_type',
                    'amount', 'get_booking_currency', 'booking_amount', 'net_hold', 'booking_departure_at',
                    'booking_inr_amount',
                    'get_amount_pending_for_collection_from_buyer',
                    'get_amount_collected_from_buyer', 'get_amount_paid_to_seller',
                    'type', 'status', ]
    list_filter = ('member', 'payment_type',
                   'member__account_manager', 'status',)
    search_fields = (
        'id', 'member__email', 'member__phone', 'member__code', 'booking__category__name',
        'booking__type__name',
        'booking__code', 'booking__buyer__email', 'booking__seller__email',
        'booking__destination__name', 'booking__booking_details__remark', 'booking__destination_text',
        'booking__booking_date', 'booking__amount',
        'booking__requirement__code',
        'booking__buyer__code', 'booking__buyer__name', 'booking__seller__code',
        'booking__seller__name', 'booking__booking_details__seller_booking_code',
        'booking__booking_details__seller_invoice_code',)

    def get_member_link_str(self, member):
        return f"{member.id} - {member.code}"

    def member_link(self, obj):
        return mark_safe('<a href="%s">%s</a>' % (
            reverse("admin:members_member_change", args=[obj.member.id]), self.get_member_link_str(obj.member)))

    def get_booking_link_str(self, booking):
        return f"#{booking.id} | {booking.code} | {booking.type.name}"

    def booking_link(self, obj):
        return mark_safe('<a href="%s">%s</a>' % (reverse("admin:bms_booking_change", args=[obj.booking.id]),
                                                  self.get_booking_link_str(obj.booking)))

    def net_hold(self, obj):
        return obj.booking.booking_summary.net_hold

    def get_amount_pending_for_collection_from_buyer(self, obj):
        return obj.booking.booking_summary.amount_pending_for_collection_from_buyer

    def get_amount_collected_from_buyer(self, obj):
        return obj.booking.booking_summary.amount_collected_from_buyer

    def get_amount_paid_to_seller(self, obj):
        return obj.booking.booking_summary.amount_paid_to_seller

    def booking_details_remark(self, obj):
        if obj.booking.booking_details.remark:
            return obj.booking.booking_details.remark[:20] + (
                " ..." if (len(obj.booking.booking_details.remark) > 20) else "")

    def booking_document_status(self, obj):
        if obj.booking.document_status:
            return obj.booking.document_status

    def get_booking_currency(self, obj):
        if obj.booking.currency:
            return obj.booking.currency

    def booking_amount(self, obj):
        return obj.booking.amount

    def booking_inr_amount(self, obj):
        return obj.booking.amount_in_inr

    def booking_departure_at(self, obj):
        return obj.booking.departure_at

    booking_amount.short_description = "Booking Amount"
    booking_inr_amount.short_description = "Booking Amount(INR)"
    booking_departure_at.short_description = "Trip Start Date"
    booking_document_status.short_description = "Document Status"
    get_booking_currency.short_description = "Booking Currency"
    get_amount_pending_for_collection_from_buyer.short_description = "Pending(Buyer)"
    get_amount_collected_from_buyer.short_description = "Collected(Buyer)"
    get_amount_paid_to_seller.short_description = "Paid(Seller)"
    booking_details_remark.short_description = "Booking Remark"

    def get_queryset(self, request):
        qs = super(PlannedPaymentAdmin, self).get_queryset(request)
        qs = qs.prefetch_related('booking__booking_details', 'booking__booking_summary')
        return qs.filter().select_related('booking__type', 'booking__currency', 'booking__category',
                                          'member', 'booking',
                                          'booking__destination',
                                          'booking__buyer',
                                          'booking__seller')


class PlannedPaymentDueOnMemberAdmin(PlannedPaymentAdmin):
    list_filter = ('member', 'payment_type',
                   'member__account_manager', PlannedPaymentToCollectStatusFilter,)

    def get_queryset(self, request):
        qs = super(PlannedPaymentDueOnMemberAdmin, self).get_queryset(request)
        return qs.filter(type=PlannedPayment.DUE_ON_MEMBER).order_by('date')


class PlannedPaymentDueToMemberAdmin(PlannedPaymentAdmin):
    list_filter = ('member', 'payment_type',
                   'member__account_manager', PlannedPaymentToPayStatusFilter,)

    def get_queryset(self, request):
        qs = super(PlannedPaymentDueToMemberAdmin, self).get_queryset(request)
        return qs.filter(type=PlannedPayment.DUE_TO_MEMBER).order_by('date')


admin.site.register(PlannedPaymentBuyerProxy, PlannedPaymentDueOnMemberAdmin)
admin.site.register(PlannedPaymentSellerProxy, PlannedPaymentDueToMemberAdmin)
