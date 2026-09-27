from django.contrib import admin

from bms.models.booking.booking_summary import BookingSummary


class BookingSummaryAdmin(admin.ModelAdmin):
    model = BookingSummary
    list_display = [field.name for field in BookingSummary._meta.get_fields()]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    verbose_name_plural = "Booking Summary"


admin.site.register(BookingSummary, BookingSummaryAdmin)
