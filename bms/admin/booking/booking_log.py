from django.contrib import admin
from django.conf import settings
from django.urls import reverse
from django.utils.safestring import mark_safe
from bms.models.booking.booking_log import BookingLog


class BookingLogAdmin(admin.ModelAdmin):
    model = BookingLog

    list_display = ['id', 'get_booking', 'column_name', 'old_value', 'new_value']

    def get_booking(self, obj):
        if obj.bookings:
            return f"{obj.bookings.id} | {obj.bookings.code} | {obj.bookings.type.name}"
        return "-"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('booking', 'bookings__type').defer('bookings__created_by')

    get_booking.short_description = "Booking"




admin.site.register(BookingLog, BookingLogAdmin)


