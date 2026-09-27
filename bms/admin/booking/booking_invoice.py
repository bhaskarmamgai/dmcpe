import json

from django.contrib import admin
from django.utils.safestring import mark_safe
from bms.models.booking.booking_invoice import BookingInvoices, BookingVoucher
from bms.config.invoice import BOOKING_TYPE_FLIGHT_ID
from django.urls import reverse


class BookingInvoicesAdmin(admin.ModelAdmin):
    model = BookingInvoices

    list_display = ['id', 'invoice_type', 'tax_invoice_number', 'invoice_reference_number', 'get_qr_code_url', 'description_of_reimbursement',
                    'reimbursement_amount', 'description_of_service_charges', 'service_charges',
                    'igst_percentage_on_service_charges', 'igst_amount_on_service_charges',
                    'cgst_percentage_on_service_charges', 'cgst_amount_on_service_charges',
                    'sgst_percentage_on_service_charges', 'sgst_amount_on_service_charges',
                    'total_service_charges_with_tax','invoice_amount',
                    'sac_code_service', 'approved_discount',
                    'created_by', 'booking_code', 'booking_amount', 'safe_id',
                    'created_at']

    fields = ['booking', 'invoice_type', 'tax_invoice_number', 'invoice_reference_number', 'ack_date', 'ack_no', 'get_qr_code_url', 'is_einvoice', 'get_s3_invoice_link', 'description_of_reimbursement',
              'reimbursement_amount', 'description_of_service_charges', 'service_charges',
              'igst_percentage_on_service_charges',
              'igst_amount_on_service_charges', 'cgst_percentage_on_service_charges', 'cgst_amount_on_service_charges',
              'sgst_percentage_on_service_charges', 'sgst_amount_on_service_charges',
              'total_service_charges_with_tax','invoice_amount',
              'sac_code_service', 'approved_discount', 'scratch_card_amount',
              'created_by', 'created_at']

    readonly_fields = []

    search_fields = ['tax_invoice_number', 'booking__buyer__name', 'booking__buyer__username',
                     'booking__buyer__code',
                     'booking__buyer__phone', 'booking__buyer__email', 'booking__code'
                     ]
    list_per_page = 20

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.filter().select_related('booking')
        return qs

    def get_qr_code_url(self, instance):
        if instance and instance.qr_code:
            return mark_safe("<a href={} target='_blank' rel='noopener'>qr_code</a>".format(instance.qr_code))
        return '-'
    def safe_id(self, obj):
        return mark_safe('%s' % (obj.booking.safe_id))

    def booking_amount(self, obj):
        return mark_safe('%s' % (obj.booking.amount))

    def booking_code(self, obj):
        if obj.booking.type.id == BOOKING_TYPE_FLIGHT_ID:
            return mark_safe('<a href={}>{}</a>'.format(
                reverse('admin:trs_bookingflightproxy_change', args={obj.booking.id}), obj.booking.code))

        return mark_safe('<a href={}>{}</a>'.format(
            reverse('admin:trs_booking_change', args={obj.booking.id}), obj.booking.code))




class BookingVoucherAdmin(admin.ModelAdmin):
    model = BookingVoucher

    fields = ['id', 'booking', 'document_url', 'is_active', 'created_by', 'created_at']
    readonly_fields = ['id', 'booking', 'document_url', 'created_by', 'created_at']
    list_display = ['id', 'booking', 'created_by', 'created_at']

    def booking_voucher(self, obj):
        file= obj.document_url
        if file:
            return mark_safe('<a href="%s" target="_blank">Download Voucher</a>' % file)
        else:
            return "-"


admin.site.register(BookingInvoices, BookingInvoicesAdmin)
admin.site.register(BookingVoucher, BookingVoucherAdmin)
