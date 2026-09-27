from django.contrib import admin
from bms.models import SellerStatus


class SellerStatusAdmin(admin.ModelAdmin):
    model = SellerStatus
    fields = ['name', 'is_active', 'is_deleted']
    list_filter = ['is_active', 'is_deleted']
    search_fields = ['name']
    list_display = ['name', 'is_active', 'is_deleted']



admin.site.register(SellerStatus, SellerStatusAdmin)
