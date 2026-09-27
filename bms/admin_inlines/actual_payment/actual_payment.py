from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe
from bms.models.actual_payment.actual_payment import ActualPayment


class ActualPaymentInline(admin.TabularInline):
    model = ActualPayment
    extra = 0

    def member_link(self, obj):
        return mark_safe(
            '<a href="%s">%s </a>' % (reverse('admin:members_member_change', args=(obj.member.id,)), obj.member))

    def bank_record(self, obj):
        return mark_safe(
            '<a href="%s">%s</a>' % (reverse('admin:accounts_bankrecord_change', args=(obj.record.id,)), obj.record.id))

    def posting_link(self, obj):
        return mark_safe(
            '<a href="{}">{}</a>'.format(reverse('admin:accounts_posting_change', args=(obj.posting.id,)),
                                         obj.posting))


class ActualPaymentPaidByMemberInline(ActualPaymentInline):
    readonly_fields = ('id', 'member_link', 'bank_record', 'member_currency',
                       'amount_in_collection_currency', 'posting_link',
                       'amount_in_member_currency', 'created_at', 'created_by')

    def get_fields(self, request, obj=None):
        return ['id', 'member_link', 'posting_link', 'amount_in_collection_currency', 'date',
                'member_currency', 'amount_in_member_currency', 'status', 'created_at', 'created_by']


class ActualPaymentPaidToMemberInline(ActualPaymentInline):
    def release_request_link(self, obj):
        return mark_safe(
            '<a href="%s">%s - %s</a>' % (
                reverse('admin:bms_releaserequest_change', args=(obj.release_request.id,)), obj.release_request.id,
                obj.release_request.status if obj.release_request.status else ""))

    fields = ['id', 'amount', 'status', 'amount_in_member_currency', 'release_request_link', 'date', ]
    readonly_fields = ('id',
                       'release_request_link',
                       'created_at', 'created_by')

    def get_fields(self, request, obj=None):
        return ['id', 'amount_in_collection_currency',
                'status', 'member_currency', 'amount_in_member_currency',
                'release_request_link', 'date', 'created_at', 'created_by']

    def get_queryset(self, request):
        qs = super(ActualPaymentPaidToMemberInline, self).get_queryset(request)
        return qs.filter(type=ActualPayment.PAID_TO_MEMBER)

    verbose_name_plural = "Actual Payment"
