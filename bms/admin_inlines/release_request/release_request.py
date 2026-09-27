from django.contrib import admin
from bms.models import ReleaseRequestStatusHistory


class ReleaseRequestStatusHistoryInline( admin.TabularInline):
    model = ReleaseRequestStatusHistory
    fields = ['id', 'status', 'created_by', 'created_at']
    readonly_fields = ['created_at', 'created_by', 'updated_at', 'updated_by']
