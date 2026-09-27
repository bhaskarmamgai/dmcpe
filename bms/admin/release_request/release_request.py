from django.conf import settings
from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe
from bms.admin_inlines.actual_payment.actual_payment import ActualPaymentPaidToMemberInline
from bms.models.release_request.release_request import ReleaseRequest, ReleaseRequestPayments
from bms.admin_inlines.release_request.release_request import ReleaseRequestStatusHistoryInline
from members.services import OrganizationServices as organization
from dmcpesys.services import get_travel_supply_configuration_by_app_and_key, get_enabled_currencies, \
    get_enabled_remit_types
from bms.forms import ReleaseRequestPaymentsForm


class ReleaseRequestAdmin(admin.ModelAdmin):
    model = ReleaseRequest
    list_display = ['id', 'get_booking', 'get_booking_type', 'get_booking_destination', 'get_member',
                    'get_organization', 'requested_currency', 'requested_amount', 'to_be_released_on', 'description',
                    'created_at', 'created_by', 'status', 'release_request_actions', 'mode',
                    'amount_released_including_charges', 'release_notes', 'remark', 'get_proof_link',
                    'get_organization_bank_account', 'refund_mode']

    inlines = [ActualPaymentPaidToMemberInline, ReleaseRequestStatusHistoryInline]
    list_per_page = 10
    autocomplete_fields = []
    search_fields = ['member__email', 'requested_amount', 'description', 'release_notes']
    list_filter = ('to_be_released_on','member__account_manager',
                   'created_by', 'created_at', 'status', 'refund_mode', 'mode')
    readonly_fields = ['get_proof_link', 'booking', 'member', 'organization', 'mode', 'requested_amount',
                       'to_be_released_on', 'description', 'created_at', 'created_by', 'status',
                       'amount_released_including_charges', 'remark', 'release_request_actions',
                       'refund_mode']


    def get_booking(self, obj):
        booking_obj = obj.booking
        return mark_safe(
            "<a href='{}'>{}</a>".format(
                reverse('admin:bms_booking_change', args=[booking_obj.id]), booking_obj.code))
        return '-'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        release_req_obj = ReleaseRequest.objects.filter(id=request.resolver_match.kwargs['object_id'])
        if db_field.name == "organization_bank_account":
            if request.resolver_match.kwargs:
                if [i.organization.id for i in release_req_obj if i.organization]:
                    kwargs["queryset"] = organization.get_bank_accounts_by_organization_id(
                        *[i.organization.id for i in release_req_obj])
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def release(self, obj):
        return mark_safe(
            '<a href="#" onClick="MyWindow=window.open(\'%s\',\'MyWindow\',\'width=1100,height=700\'); return false;">%s</a>' % (
                reverse("bms:release_request_approve_release_request", args=[obj.id]),
                'Release'))

    def reject(self, obj):
        return mark_safe(
            '<a href="#" onClick="MyWindow=window.open(\'%s\',\'MyWindow\',\'width=1000,height=700\'); return false;">%s</a>' % (
                reverse("bms:release_request_reject_release_request", args=[obj.id]),
                'Reject'))

    def release_amount_in_bank(self, obj):
        if obj.status == ReleaseRequest.PENDING:
            return mark_safe("<ul><li>{}</li><li>{}</li></ul>".format(self.release(obj), self.reject(obj)))
        return obj.status

    def release_request_action(self, obj):
        return mark_safe(
            '<a href="#" onClick="MyWindow=window.open(\'%s\',\'MyWindow\',\'width=1000,height=700\'); return false;">%s</a>' % (
                reverse("bms:wallet_release_request_approve_release_request", args=[obj.id]),
                'Release'))

    def release_request_actions(self, obj):
        if obj.status == ReleaseRequest.PENDING:
            return mark_safe(
                "<ul><li>{}</li><li>{}</li></ul>".format(self.release_request_action(obj), self.reject(obj)))
        return obj.status

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('member', 'organization',
                                                          'organization_bank_account', 'created_by',
                                                          'booking')
        return qs

    def get_proof_link(self, obj):
        if obj and obj.proof:
            return mark_safe('<a href="{}">Proof Link</a>'.format(obj.proof.name))
        return 'NA'

    def get_booking_destination(self, obj):
        booking_obj = obj.booking
        if hasattr(booking_obj, "destination"):
            return booking_obj.destination.name
        return '-'

    def get_booking_type(self, obj):
        booking_obj = obj.booking
        if hasattr(booking_obj, "type"):
            return booking_obj.type.name
        return '-'

    def get_organization(self, obj):
        if obj.organization:
            return f"#{obj.organization.id} | {obj.organization.code}"
        return "-"

    def get_member(self, obj):
        if obj.member:
            return f"{obj.member.id} - {obj.member.code}"
        return "-"

    def get_organization_bank_account(self, obj):
        if obj.organization_bank_account:
            return (f"{obj.organization_bank_account.organization.code} | "
                    f"{obj.organization_bank_account.bank} | "
                    f"{'Verified' if obj.organization_bank_account.is_primary else 'Not Verified'}")
        return "-"

    def get_readonly_fields(self, request, obj=None):
        if not request.user.has_perm('bms.change_releaserequest'):
            self.readonly_fields = self.readonly_fields + ['release_notes',
                                                           'proof', ] if not 'release_notes' in self.readonly_fields else self.readonly_fields
        return self.readonly_fields


    def get_search_results(self, request, queryset, search_term):
        if search_term.isdigit():
            queryset = queryset.filter(id=search_term) | queryset.filter(
                requested_amount=search_term) | queryset.filter(amount_released_including_charges=search_term)
            use_distinct = False
        else:
            queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        return queryset, use_distinct

    get_organization.short_description = "Organization"
    get_member.short_description = "Member"
    get_organization_bank_account.short_description = "Organization Bank Account"
    release_amount_in_bank.short_description = "Action V1"
    release_request_actions.short_description = "Action"
    get_proof_link.short_description = "Proof Link"
    get_booking.short_description = "Booking"
    get_booking_destination.short_description = "Destination"
    get_booking_type.short_description = " Booking Type"


class ReleaseRequestPaymentsAdmin(admin.ModelAdmin):
    model = ReleaseRequestPayments
    list_display = ['id', 'get_booking', 'get_organization', 'get_release_request',
                    'amount_released_in_member_currency',
                    'roe_on_date_of_payment', 'transaction_cost', 'remit_type', 'remit_type_cost',
                    'date_of_payment', 'sce', 'sce_currency', 'utr_or_transaction_no',
                    'created_by', 'created_at', 'updated_by', 'updated_at']
    autocomplete_fields = ['booking', 'organization', 'release_request']
    readonly_fields = ['created_at', 'created_by', 'updated_at', 'updated_by']
    search_fields = ['booking__code']
    list_per_page = 20
    form = ReleaseRequestPaymentsForm
    list_filter = ('date_of_payment',)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "sce_currency":
            kwargs["queryset"] = get_enabled_currencies()
        if db_field.name == "remit_type":
            kwargs["queryset"] = get_enabled_remit_types()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('booking', 'organization', 'release_request', 'remit_type',
                                                            'sce', 'sce_currency',
                                                            'booking__type')

    def get_booking(self, obj):
        if obj.booking:
            return f"#{obj.booking.id} | {obj.booking.code} | {obj.booking.type.name}"
        return "-"

    def get_organization(self, obj):
        if obj.organization:
            return f"#{obj.organization.id} | {obj.organization.code}"
        return "-"

    def get_release_request(self, obj):
        if obj.release_request:
            return (
                f"#{obj.release_request.id} | {obj.release_request.requested_amount} | {obj.release_request.created_at:%Y-%m-%d %H:%M} | {obj.release_request.created_by.username}")
        return "-"

    get_organization.short_description = "Organization"
    get_booking.short_description = "Booking"
    get_release_request.short_description = "Release Request"


admin.site.register(ReleaseRequest, ReleaseRequestAdmin)
admin.site.register(ReleaseRequestPayments, ReleaseRequestPaymentsAdmin)
