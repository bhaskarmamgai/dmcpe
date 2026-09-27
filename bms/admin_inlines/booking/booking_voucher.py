from django.contrib import admin
from django.utils.safestring import mark_safe

from bms.models.booking.transaction_invoice import BookingVoucher


class BookingVoucherInline(admin.TabularInline):
    model = BookingVoucher
    fields = ['id', 'voucher', 'is_active', 'created_at']
    readonly_fields = ['voucher', 'is_active', 'created_at']

    def voucher(self, obj):
        return mark_safe('<a href="%s" target="_blank">Voucher</a>' % obj.document_url)


class BookingVoucherViewOnlyInline( BookingVoucherInline):
    pass
