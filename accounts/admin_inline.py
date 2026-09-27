from django.contrib import admin
from common.libraries import get_dates_by_range
from accounts.models import Posting, BankRecord


class PostingInline(admin.TabularInline):
    model = Posting

    fields = ['id', 'datetime', 'member', 'organization', 'journal', 'debit', 'credit', 'balance', 'description', 'wallet']

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('journal', 'member', 'organization')
        begin_date, end_date = get_dates_by_range('last_30days')
        return qs.filter(created_at__gte=begin_date, created_at__lte=end_date)

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class BankRecordInline(admin.TabularInline):
    model = BankRecord

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
