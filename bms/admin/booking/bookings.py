
from django.conf import settings
from django.contrib import admin
from admin_auto_filters.filters import AutocompleteFilter
from django.urls import reverse
from django.utils.safestring import mark_safe

from dmcpesys.constants import CURRENCY_INR_ID

from bms.config.base import SELLER_COST_COMPONENT_CANCELLED_ID
from common.libraries import get_numbers_formatted_to_indian_locale
from bms.forms import BookingForm
from bms.admin_inlines import BookingInvoicesInline, BookingSummaryInline, \
    PlannedPaymentScheduleInline, PlannedPaymentCollectionInline, \
    ActualPaymentPaidByMemberInline, ActualPaymentPaidToMemberInline, \
    BookingCancellationInline, BookingLogInline, \
    BookingChargesBaseInline,\
    BookingStatusHistoryInline, BookingDocumentInline, ApprovedDiscountAdminInline, \
    SellerCostComponentInline,\
    BookingLossInline,BookingFinancialInline
from bms.models import  BookingLog, BookingType, Booking, PlannedPayment, BookingStatusHistory,SellerCostComponent
from bms.services.bookings import get_member_currency_by_id, \
    calculate_amount_in_collection_currency_for_payment, calculate_amount_in_collection_currency_for_collection

class BuyerFilter(AutocompleteFilter):
    title = 'Buyer'
    field_name = 'buyer'

class BuyerOrganizationFilter(AutocompleteFilter):
    title = 'Buyer Organization'
    field_name = 'buyer_organization'

class BookingTypeFilter(AutocompleteFilter):
    title = 'Booking Type'
    field_name = 'type'

class DestinationFilter(AutocompleteFilter):
    title = 'Destination'
    field_name = 'destination'

class AgentCollectionEntityFilter(AutocompleteFilter):
    title = 'TACE'
    field_name = 'agent_collection_entity'

class CategoryFilter(AutocompleteFilter):
    title = 'Category'
    field_name = 'category'

class CreatedByFilter(AutocompleteFilter):
    title = 'Created By'
    field_name = 'created_by'

class BookingAccountManagerFilter(AutocompleteFilter):
    title = 'Account Manager'
    field_name = 'created_by'

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(buyer__account_manager_id=self.value())
        return queryset

class BookingAdmin(admin.ModelAdmin):
    model = Booking
    readonly_fields = ['code', 'get_amount_in_inr_in_indian_locale',
                       'buyer_organization', 'get_proof_link',
                       'collection_currency', 'created_by', 'created_at',
                       'amount_in_collection_currency'
        , 'get_remittance_documentation_link']
    form = BookingForm

    fields = ['code', 'departure_at', 'type', 'category', 'buyer',
              'buyer_organization',
              'currency', 'amount',
              'collection_currency', 'amount_in_collection_currency',
              'get_amount_in_inr_in_indian_locale',
              'booking_date', 'destination', 'nights_count',
              'adults_count', 'children_count', 'document_status', 'proof', 'get_proof_link', 'inclusions',
              'description', 'is_deleted',
              'parent_booking_id', 'parent_booking_code']

    list_display = ['booking_id', 'status', 'code', 'type', 'category', 'destination', 'currency',
                    'get_amount_in_indian_locale',
                    'get_amount_in_inr_in_indian_locale', 'get_amount_pending_for_collection_from_buyer',
                    'get_amount_collected_from_buyer', 'get_amount_paid_to_seller', 'get_net_hold',
                    'booking_date', 'departure_at', 'nights_count',
                    'created_at', 'created_by',
                    ]

    search_fields = ['code', 'agent_collection_entity__name',]

    list_filter = [BuyerFilter, BuyerOrganizationFilter, BookingTypeFilter,
                   DestinationFilter,
                   BookingAccountManagerFilter,
                   'booking_date',
                   AgentCollectionEntityFilter,
                   'departure_at', CategoryFilter,
                   CreatedByFilter,
                   'created_at', 'status',]

    autocomplete_fields = ['buyer', 'buyer_organization']

    list_per_page = 5

    inlines = [
        # 1. Core Booking Info (Top section)
        BookingSummaryInline,
        BookingStatusHistoryInline,
        BookingLogInline,

        # 2. Documents (quick access early)
        BookingDocumentInline,
        #
        # # 3. Financial Overview
        BookingFinancialInline,
        BookingLossInline,
        #
        # # 4. Charges & Pricing Breakdown
        BookingChargesBaseInline,
        SellerCostComponentInline,
        ApprovedDiscountAdminInline,
        #
        # # 5. Invoice & Billing
        BookingInvoicesInline,
        #
        # # 6. Planned Payments
        PlannedPaymentScheduleInline,
        PlannedPaymentCollectionInline,
        #
        # # 7. Actual Payments
        ActualPaymentPaidByMemberInline,
        ActualPaymentPaidToMemberInline,
        #
        # # 8. Cancellation (kept at bottom intentionally)
        BookingCancellationInline,
    ]

    def get_inlines(self, request, obj=None):
        if obj is None:
            return []

        inlines = list(super().get_inlines(request, obj))
        # Show payment inlines only if SellerCostComponent exists
        if not obj.booking_seller_cost_components.exists():
            inlines = [
                inline for inline in inlines
                if inline not in [PlannedPaymentScheduleInline, PlannedPaymentCollectionInline]
            ]

        return inlines

    def booking_id(self, obj):
        return mark_safe(
            "<a href='{}'>{}</a>".format(
                reverse('admin:bms_booking_change', args=[obj.id]), obj.id))

    def get_amount_in_indian_locale(self, obj):
        return get_numbers_formatted_to_indian_locale(obj.amount)

    def get_amount_in_inr_in_indian_locale(self, obj):
        return get_numbers_formatted_to_indian_locale(obj.amount_in_inr)

    def refund_process(self, obj):
        if obj:
            return mark_safe(
                "<a href='{}'>Refund Process</a>".format(
                    reverse('admin:bms_bookingrefundproxy_change', args=[obj.id])))

    def booking_actions(self, obj):
        if not obj.status == Booking.CANCELLED:
            booking_actions_list = "<ul><li>{}</li><li></li><li></li><li>{}</li><li>{}</li>".format(
                self.claim_link(obj),
                self.cancellation_process_link(obj), self.refund_process(obj))
            if obj.status != Booking.CONFIRMED:
                booking_actions_list = booking_actions_list + "<li>{}</li>".format(self.approved_discount(obj))
            booking_actions_list = booking_actions_list + "</ul>"
            return mark_safe(booking_actions_list)

    def booking_invoice_actions(self, obj):
        if obj.buyer_organization and obj.buyer_organization.wallets.last().currency_id != CURRENCY_INR_ID:
            return "-"
        return mark_safe("<ul><li>{}</li></ul>".format(self.generate_invoice(obj), self.download_invoices(obj)))

    def booking_voucher(self, obj):
        if obj.status == Booking.CONFIRMED:
            url = obj.vouchers.filter(is_active=True).last().document_url
            if url:
                return mark_safe('<a href="%s" target="_blank">Download Voucher</a>' % url)
        else:
            return "-"

    def cancellation_process_link(self, obj):
        return mark_safe(
            "<a href='{}' target='_booking'>Cancellation Process</a>".format(
                reverse('admin:bms_bookingcancellationproxy_change',
                        args=[obj.id])))

    def claim_link(self, obj):
        return mark_safe("<a href='{}' target='_booking'>Claim collection</a>".format(
            reverse('admin:accounts_bankrecord_changelist')))

    def approved_discount(self, obj):
        booking_id = obj.id
        return mark_safe(
            "<a href='{}' target='_booking'>Approved Discount</a>".format(
                reverse('admin:bms_approveddiscount_add') + f'?booking_id={booking_id}'))

    def cancellation_process_v2(self, obj):
        return mark_safe(
            "<a href='{}' target='_booking'>Cancellation Process V2</a>".format(
                reverse('bms:select_cancellation_process_v2_type', args=[obj.id])))

    def alterations_cn_dn(self, obj):
        return mark_safe(mark_safe('<a href="{}" target="_blank">Alterations CN/DN</a><br>').format(
            reverse('bms:booking_alteration', args=[obj.id])))

    def current_status(self, obj):
        return obj.status


    def agent_collection_entity_name(self, obj):
        if obj.agent_collection_entity:
            return mark_safe(
                '<a href="/admin/dmcpesys/travelsupplygroupentities/%s/change/">%s</a>' % (obj.agent_collection_entity.id,
                                                                                  obj.agent_collection_entity.name))

    def buyer_name(self, obj):
        buyer_name = "{} {} {}".format(obj.buyer.name[0:20], (" ..." if (len(obj.buyer.name) > 20) else ""),
                                       obj.buyer.company_name[0:20])

        return mark_safe(
            '<a href="/admin/members/member/%s/change/">%s</a>' % (obj.buyer.id, buyer_name))

    def seller_name(self, obj):
        if obj and obj.seller:
            seller_name = "{} {} - {}".format(obj.seller.name[0:20], (" ..." if (len(obj.seller.name) > 20) else ""),
                                              obj.seller.company_name[0:20])

            return mark_safe(
                '<a href="/admin/members/member/%s/change/">%s</a>' % (obj.seller.id, seller_name))
        return None

    def fetch_latest_booking_financials(self, obj):
        if obj:
            return mark_safe(
                f"<a href={reverse('bms:fetch-latest-booking-financials-manually', args=[obj.id])}>Fetch Latest Booking Financials</a>")
        return None

    def get_net_hold(self, obj):
        return get_numbers_formatted_to_indian_locale(obj.booking_summary.net_hold)

    def get_amount_pending_for_collection_from_buyer(self, obj):
        return get_numbers_formatted_to_indian_locale(obj.booking_summary.amount_pending_for_collection_from_buyer)

    def get_amount_collected_from_buyer(self, obj):
        return get_numbers_formatted_to_indian_locale(obj.booking_summary.amount_collected_from_buyer)

    def get_amount_paid_to_seller(self, obj):
        return get_numbers_formatted_to_indian_locale(obj.booking_summary.amount_paid_to_seller)

    def get_remittance_documentation_link(self, obj):
        if obj.type.id in [settings.BOOKING_TYPE_SAFE_REMITTANCE_ID, settings.BOOKING_TYPE_REMIT_ID]:
            return mark_safe(
                '<a href="{}">Upload Remittance Documents</a>'.format(
                    settings.MYTRIPKART_UPLOAD_REMITTANCE_DOCUMENTS_LINK.format(obj.code)
                ))
        return "NA"

    def get_proof_link(self, obj):
        if obj and obj.proof:
            return mark_safe('<a href="{}">Proof Link</a>'.format(obj.proof.name))
        return "NA"

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
            if obj.buyer and not obj.collection_currency:
                obj.collection_currency = get_member_currency_by_id(obj.buyer.id)
        else:
            if change:

                old_object = self.model.objects.get(id=obj.id)

                for field in form.changed_data:
                    tl = BookingLog(booking=obj, column_name=field, old_value=getattr(old_object, field),
                                    new_value=getattr(obj, field), done_by=request.user)
                    tl.save()
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=True)
        for instance in instances:
            if formset.model == PlannedPayment:
                if instance.member.id == instance.booking.buyer.id:
                    instance.type = PlannedPayment.DUE_ON_MEMBER
                    instance.organization = instance.booking.buyer_organization
                    instance.member_currency = instance.booking.collection_currency
                    instance.amount_in_collection_currency = calculate_amount_in_collection_currency_for_collection(
                        instance.booking.collection_currency.id,
                        instance.member_currency.id, instance.booking.created_at, instance.amount)
                if SellerCostComponent.objects.filter(seller_member__id=instance.member.id,
                                                      booking__code=instance.booking.code).exists():
                    seller_cost_components = SellerCostComponent.objects.filter(
                        seller_member__id=instance.member.id,
                        booking__code=instance.booking.code).exclude(
                        seller_status__id=SELLER_COST_COMPONENT_CANCELLED_ID)
                    instance.type = PlannedPayment.DUE_TO_MEMBER
                    instance.organization = seller_cost_components.last().seller_organization if seller_cost_components.last() else None
                    instance.member_currency = seller_cost_components.last().seller_currency if seller_cost_components.last() else None
                    instance.amount_in_collection_currency = calculate_amount_in_collection_currency_for_payment(
                        instance.booking.collection_currency.id, instance.amount, seller_cost_components)
            instance.save()

    def get_readonly_fields(self, request, obj=None):
        if obj:
            read_fields = self.readonly_fields + ['code', 'destination', 'departure_at',

                                                  'destination_text', 'buyer_name', 'buyer_organization',
                                                  'type', 'category', 'booking_date',
                                                  'current_status', 'booking_actions', 'edit_all_fields_link',
                                                  'is_deleted',
                                                  'booking_invoice_actions',
                                                  'booking_voucher', 'currency', 'amount']
            return read_fields + ['agent_collection_entity', 'collection_currency', 'buyer_name']
        return self.readonly_fields


class BookingStatusHistoryAdmin(admin.ModelAdmin):
    model = BookingStatusHistory
    list_display = ['id', 'get_booking', 'status', 'created_at', 'updated_by']
    fields = ['booking', 'status', 'created_at', 'updated_by']
    readonly_fields = ['id', 'created_at', 'updated_by']
    search_fields = ['booking__code']
    list_filter = ['created_at', 'status']
    list_per_page = 5

    def get_booking(self, obj):
        if obj.booking:
            return mark_safe(
                "<a href={}>{}</a>".format(
                    reverse('admin:bms_booking_change', args=[obj.booking.id]),
                    obj.booking.code))
        return "-"


class BookingTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'is_deleted', 'enabled']
    search_fields = ('name', 'description')
    list_per_page = 5


admin.site.register(Booking, BookingAdmin)
admin.site.register(BookingType, BookingTypeAdmin)
admin.site.register(BookingStatusHistory, BookingStatusHistoryAdmin)
