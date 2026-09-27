from django.contrib import admin
from bms.models import BookingLoss


class BookingLossInline(admin.TabularInline):
    model = BookingLoss
    autocomplete_fields = ['currency']
    extra = 1
    readonly_fields = ['created_by', 'created_at']
