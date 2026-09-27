from django.contrib import admin
from bms.models.payment.payment import PaymentLogs
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.conf import settings


class PaymentLogsAdmin(admin.ModelAdmin):
    model = PaymentLogs

    list_display = ['id', 'booking_link', 'payload', 'response', 'created_at']
    search_fields = ['id']
    list_filter = ['created_at', 'response']

    def booking_link(self, obj):
        if obj.booking:
            if obj.booking.category and obj.booking.category.id == settings.CATEGORY_FLIGHT_ID:
                return mark_safe(
                    "<a href={}>{}</a>".format(
                        reverse('admin:trs_bookingflightproxy_change', args=[obj.booking_id]),
                        obj.booking))
        return mark_safe(
            "<a href='{}'>{}</a>".format(reverse("admin:trs_booking_change", args=[obj.booking_id]),
                                         obj.booking))

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        qs = super(PaymentLogsAdmin, self).get_queryset(request).select_related('booking', 'booking__category',
                                                                                'booking__buyer', 'booking__type')
        return qs

    booking_link.short_description = "Booking"


admin.site.register(PaymentLogs, PaymentLogsAdmin)
