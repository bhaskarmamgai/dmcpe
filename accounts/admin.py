from django.contrib import admin
from .models import Journal, Posting, BankStatement, BankRecord
from django.utils.safestring import mark_safe
from django.urls import reverse
from bms.admin_inlines.actual_payment.actual_payment import ActualPaymentPaidByMemberInline, \
    ActualPaymentPaidToMemberInline
from accounts import enums


class JournalAdmin(admin.ModelAdmin):
    def has_delete_permission(self, request, obj=None):
        return False

    list_display = ['type']


class PostingAdmin(admin.ModelAdmin):
    autocomplete_fields = ['member', 'currency', 'organization', 'wallet']
    fields = ['datetime', 'member', 'organization', 'journal', 'currency', 'debit', 'credit', 'balance',
              'description', 'wallet']
    readonly_fields = ['balance']
    list_display = ['id', 'datetime', 'get_member', 'get_organization', 'wallet', 'journal', 'currency', 'debit',
                    'credit', 'balance', 'description']
    list_filter = ('datetime', 'journal',)
    search_fields = ['balance', 'member__id', 'description']
    list_per_page = 10

    def get_organization(self, obj):
        if obj.organization:
            return f"#{obj.organization.id} | {obj.organization.code}"
        return "-"

    def get_member(self, obj):
        if obj.member:
            return f"{obj.member.id} - {obj.member.code}"
        return "-"


    def get_queryset(self, request):
        return super(PostingAdmin, self).get_queryset(request).select_related('organization', 'member', 'wallet',
                                                                              'journal')

    get_organization.short_description = "Organization"
    get_member.short_description = "Member"


class BankRecordAdmin(admin.ModelAdmin):
    model = BankRecord
    list_display = ['id', 'mode_of_payment', 'statement', 'date', 'service', 'reference_id', 'description', 'currency',
                    'amount', 'credit_or_debit', 'proof_link', 'created_by', 'created_at', 'claimed',
                    'comment','block_bank_record','add_to_wallet']
    search_fields = ['mode_of_payment', 'reference_id', 'amount', 'description']
    list_filter = (
     'credit_or_debit', 'mode_of_payment', 'statement__bank__name', 'date',
    'statement__created_at', 'statement__created_by', 'claimed',)

    fields = (
        'mode_of_payment', 'statement', 'date', 'reference_id', 'description', 'currency', 'amount', 'credit_or_debit',
        'proof', 'proof_link', 'created_by', 'created_at', 'member', 'organization', 'bank',
        'claimed', 'service', 'is_deleted', 'remark', 'source', 'posting', 'comment','block_bank_record','add_to_wallet')
    readonly_fields = ['statement', 'proof_link', 'created_by', 'created_at', 'claimed',
                       'posting','block_bank_record','add_to_wallet']

    inlines = [ActualPaymentPaidByMemberInline, ActualPaymentPaidToMemberInline]
    autocomplete_fields = ['member', 'organization', 'currency']

    def get_member(self, obj):
        if obj.member:
            return f"{obj.member.id} - {obj.member.code}"
        return "-"

    def proof_link(self, obj):
        return mark_safe("<a href='{}'>Link</a>".format(obj.get_proof_url())) if obj.proof else 'NA'

   
    def block_bank_record(self, obj):
        if not obj.claimed and obj.credit_or_debit == enums.CREDIT:
            return mark_safe(
                '<a href="#" onClick="MyWindow=window.open(\'%s\',\'MyWindow\',\'width=1100,height=700\'); return false;">%s</a>' % (
                    reverse("bms:bank_record__claim__block_bank_record", kwargs={"record_id": obj.id}),
                    'Block Bank Record'))

    def add_to_wallet(self, obj):
        if not obj.claimed and not obj.claimed and obj.credit_or_debit == enums.CREDIT and obj.member and obj.organization:
            return mark_safe("<a href={}>{}</a>".format(
                reverse('bms:bank_record__claim__add_to_wallet',
                        kwargs={'member_id': obj.member.id,
                                'organization_id': obj.organization.id,
                                'bank_record_id': obj.id}), "Add To Wallet"))
        return "NA"

    def get_claimed_bookings(self, obj):
        if not not obj.claimed and obj.credit_or_debit == enums.CREDIT:
            if obj.actualpayment_set.all().exists():
                return mark_safe(",".join([mark_safe(
                    "<a href='{}'>#{}</a>".format(reverse('admin:bms_transaction_change', args=[i.transaction.id]),
                                                  i.transaction.code)) for i in obj.actualpayment_set.all()]))

    get_claimed_bookings.short_description = "Claimed Bookings"
    get_member.short_description = "Member"


    def get_queryset(self, request):
        qs = super(BankRecordAdmin, self).get_queryset(request)
        return qs.filter(is_deleted=False).select_related('statement', 'created_by', 'service', 'member',
                                                       'currency')


class BankRecordInline(admin.TabularInline):
    model = BankRecord
    fields = ['link', 'mode_of_payment', 'statement', 'date', 'block_bank_record',
              'reference_id', 'description',
              'amount',
              'credit_or_debit', 'proof_link',
              'created_by', 'created_at', 'claimed']

  
    def block_bank_record(self, obj):
        if not obj.claimed and obj.credit_or_debit == enums.CREDIT:
            return mark_safe(
                '<a href="#" onClick="MyWindow=window.open(\'%s\',\'MyWindow\',\'width=1100,height=700\'); return '
                'false;">%s</a>' % (reverse("trs:bank_record__claim__block_bank_record", kwargs={"record_id": obj.id}),
                                    'Block Bank Record'))
        return '-'

    def link(self, obj):
        return mark_safe('<a href="%s">%s</a>' % \
                         (reverse('admin:accounts_bankrecord_change',
                                  args=(obj.id,)), obj.id))

    def proof_link(self, obj):
        return mark_safe("<a href='{}'>Link</a>".format(obj.get_proof_url())) if obj.proof else 'NA'

    readonly_fields = ('block_bank_record', 'created_at', 'link', 'proof_link',)

    def get_queryset(self, request):
        qs = super(BankRecordInline, self).get_queryset(request)
        return qs.filter(deleted=False)



class BankStatementAdmin(admin.ModelAdmin):
    model = BankStatement
    list_display = ['id', 'file_url', 'bank', 'from_date', 'to_date', 'created_by', 'created_at', 'import_records_cta',
                    'records_imported', ]
    readonly_fields = ('records_imported', 'created_by')
    inlines = [BankRecordInline]
    search_fields = ['id', 'created_at']
    list_filter = ('bank', 'created_by', 'created_at')

    # cta means call to action
    def import_records_cta(self, obj):
        if not obj.records_imported:
            return mark_safe(
                '<a href="%s">%s</a>' % (
                    reverse("bank_statement_import_record", kwargs={"statement_id": obj.id}), 'Import'))

    # https://stackoverflow.com/questions/4141471/how-to-change-django-admin-custom-list-field-label
    import_records_cta.short_description = 'Import records'

    def save_model(self, request, obj, form, change):
        # https://stackoverflow.com/questions/14931865/what-is-the-diff-between-save-model-and-save-formset-in-django-admin
        if not obj.id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def file_url(self, instance):
        return mark_safe('<a href="%s" target="_blank">Download File</a>' % (instance.file.name))

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.records_imported:
            return self.readonly_fields + ('file_url',)
        return self.readonly_fields


admin.site.register(Journal, JournalAdmin)
admin.site.register(Posting, PostingAdmin)
admin.site.register(BankStatement, BankStatementAdmin)
admin.site.register(BankRecord, BankRecordAdmin)
