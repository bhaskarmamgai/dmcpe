from django.conf import settings
from django.contrib import admin
from django.utils.safestring import mark_safe
from django.shortcuts import reverse
from common.libraries import limit_queryset
from bms.models.booking.booking import Booking
from bms.models.booking import BookingStatusHistory
from wallets.services import WalletServices as wallet


class BookingInlineAbstract(admin.TabularInline):
    model = Booking
    fields = ['get_booking_link', 'category', 'status', 'booking_date', 'destination', 'departure_at', 'amount',
              'amount_in_inr']
    readonly_fields = ['get_booking_link']

    def get_booking_link(self, obj):
        if obj.category_id == settings.CATEGORY_FLIGHT_ID:
            return mark_safe(
                "<a href={}>{}</a>".format(reverse('admin:bms_bookingflightproxy_change', args=[obj.code]), obj.code))
        elif obj.status == Booking.PENDING:
            return mark_safe(
                "<a href={}>{}</a>".format(reverse('admin:bms_pendingbookingproxy_change', args=[obj.code]), obj.code))
        return mark_safe("<a href={}>{}</a>".format(reverse('admin:bms_booking_change', args=[obj.code]), obj.code))

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj):
        return False

    get_booking_link.short_description = "Booking Link"


class BuyerBooking(BookingInlineAbstract):
    fk_name = 'buyer'
    verbose_name_plural = "Bookings as Buyer"

    def get_fields(self, request, obj=None):
        return self.fields[0:6] + ['get_member_currency'] + self.fields[6:-1] + ['get_amount_in_collection_currency']

    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields + ['get_member_currency', 'get_amount_in_collection_currency']

    def get_member_currency(self, obj):
        if obj:
            wallet_obj = wallet.get_wallet_obj_by_organization_id(obj.buyer_organization.id)
            return wallet_obj.currency.symbol if hasattr(wallet_obj, 'currency') else None
        return None

    def get_amount_in_collection_currency(self, obj):
        if obj:
            return obj.amount_in_collection_currency
        return None

    def get_formset(self, request, obj=None, **kwargs):
        """This thread is yet not answered over stackoverflow will post this solution to stack overflow
        community.Its payback Time to community that help us alot.Solved on 22-September-11:10 hours"""
        if request.resolver_match.kwargs:
            self.verbose_name_plural = mark_safe(
                "<p>Booking as Buyer <br><a href='{}?buyer_id={}'>View All Bookings</a><br><a href='{}?buyer_id={}'>View All Flight Bookings(Mini)</a></p>".format(
                    reverse('admin:bms_booking_changelist'), request.resolver_match.kwargs.get('object_id'),
                    reverse('admin:bms_bookingflightproxymini_changelist'),
                    request.resolver_match.kwargs.get('object_id')))

            if request.user.groups.filter(
                    id=settings.ALLOWED_GROUP_ID_FOR_FLIGHT_BOOKINGS_ADMIN).exists() or request.user.is_superuser:
                self.verbose_name_plural = mark_safe(
                    "<p>Booking as Buyer <br><a href='{}?buyer_id={}'>View All Bookings</a><br><a href='{}?buyer_id={}'>View All Flight Bookings</a><br><a href='{}?buyer_id={}'>View All Flight Bookings(Mini)</a></p>".format(
                        reverse('admin:bms_booking_changelist'), request.resolver_match.kwargs.get('object_id'),
                        reverse('admin:bms_bookingflightproxy_changelist'),
                        request.resolver_match.kwargs.get('object_id'),
                        reverse('admin:bms_bookingflightproxymini_changelist'),
                        request.resolver_match.kwargs.get('object_id')))

        return super(BuyerBooking, self).get_formset(request, obj, **kwargs)

    def get_queryset(self, request):
        qs = super(BuyerBooking, self).get_queryset(request).select_related(self.fk_name)
        l_qs = limit_queryset(qs, limit=settings.BMS_DEFAULT_RECORD_COUNT_FOR_INLINE)
        return l_qs.select_related(self.fk_name, 'destination', 'currency', 'created_by', 'category', 'type',
                                   'buyer_organization', 'created_by', 'booking_summary', 'booking_charges',
                                   'booking_details', 'booking_financial', 'flight_detail', 'cancelled_booking',
                                   'remittance_documentation')

    get_member_currency.short_description = "Member Currency"
    get_amount_in_collection_currency.short_description = "Amount In Collection Currency"


class BuyerBookingViewOnlyInline(BuyerBooking):
    pass


class BuyerOrganizationBookings(BookingInlineAbstract):
    fk_name = 'buyer_organization'

    verbose_name_plural = "Bookings as Buyer"

    def get_fields(self, request, obj=None):
        return self.fields[0:6] + ['get_member_currency'] + self.fields[6:-1] + ['get_amount_in_collection_currency']

    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields + ['get_member_currency', 'get_amount_in_collection_currency']

    def get_member_currency(self, obj):
        if obj:
            wallet_obj = wallet.get_wallet_obj_by_organization_id(obj.buyer_organization.id)
            return wallet_obj.currency.symbol if hasattr(wallet_obj, 'currency') else None
        return None

    def get_amount_in_collection_currency(self, obj):
        if obj:
            if obj.booking_version_type == Booking.V2:
                return obj.amount_in_collection_currency
            return obj.amount_in_inr
        return None

    def get_formset(self, request, obj=None, **kwargs):
        if request.resolver_match.kwargs:
            self.verbose_name_plural = mark_safe(
                "<p>Booking as Buyer <br><a href='{}?buyer_organization_id={}'>View All Bookings</a><br><a href='{}?buyer_organization_id={}'>View All Flight Bookings(Mini)</a></p>".format(
                    reverse('admin:bms_booking_changelist'), request.resolver_match.kwargs.get('object_id'),
                    reverse('admin:bms_bookingflightproxymini_changelist'),
                    request.resolver_match.kwargs.get('object_id')))
        return super(BuyerOrganizationBookings, self).get_formset(request, obj, **kwargs)

    def get_queryset(self, request):
        qs = super(BuyerOrganizationBookings, self).get_queryset(request).select_related('type', 'category', 'buyer',
                                                                                         'buyer_organization',
                                                                                         'requirement', 'currency',
                                                                                         'destination', 'created_by',
                                                                                         'requirement__member_list')
        return limit_queryset(qs, limit=settings.BMS_DEFAULT_RECORD_COUNT_FOR_INLINE)


class BookingStatusHistoryInline(admin.TabularInline):
    model = BookingStatusHistory
    readonly_fields = ['status', 'created_at', 'updated_by']

    def get_queryset(self, request):
        return super(BookingStatusHistoryInline, self).get_queryset(request).select_related('booking', 'booking__type',
                                                                                            'booking__buyer')
