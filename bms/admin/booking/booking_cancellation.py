from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe

from bms.models.cancellation.booking_cancellation import BookingCancellation


class BookingCancellationAdmin(admin.ModelAdmin):
    model = BookingCancellation
    list_display = ['id', 'booking_link', 'status', 'cancellation_process', 'charged_to', 'charged_amount', 'owed_to',
                    'owed_amount', 'get_proof_link', 'created_at', 'created_by']
    autocomplete_fields = ['booking', ]
    readonly_fields = ['created_by']
    list_per_page = 5

    def booking_link(self, obj):
        return mark_safe(
            "<a href='{}'>{}</a>".format(reverse("admin:bms_booking_change", args=[obj.booking.id]), obj.booking))

    booking_link.short_description = "Booking"

    def get_proof_link(self, obj):
        return mark_safe("<a href='{}'>Link</a>".format(obj.get_proof_url())) if obj.proof else 'NA'

    def status(self, obj):
        return obj.booking.status

    def cancellation_process(self, obj):
        return mark_safe(
            "<a href='{}'>Cancellation Process</a>".format(reverse('admin:bms_bookingcancellationproxy_change',
                                                                   args=[obj.booking.id])))

    def get_queryset(self, request):
        return super(BookingCancellationAdmin, self).get_queryset(request).prefetch_related('booking')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(BookingCancellation, BookingCancellationAdmin)
