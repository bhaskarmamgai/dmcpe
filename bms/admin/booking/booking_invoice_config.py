from django.contrib import admin

from bms.models.booking.booking_invoice_config import BookingInvoiceConfig


class BookingInvoiceConfigAdmin(admin.ModelAdmin):
    model = BookingInvoiceConfig
    list_display = [field.name for field in BookingInvoiceConfig._meta.get_fields()]


admin.site.register(BookingInvoiceConfig, BookingInvoiceConfigAdmin)
