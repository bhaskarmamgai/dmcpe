from django.contrib import admin
from bms.models import BookingInvoices


class BookingInvoicesInline(admin.TabularInline):
    model = BookingInvoices
    readonly_fields = ['created_at', 'get_file_url','updated_at','created_by','updated_by']
    fields = ['invoice_type', 'tax_invoice_number', 'get_file_url','description_of_reimbursement', 'reimbursement_amount',
              'description_of_service_charges', 'service_charges', 'approved_discount',
              'igst_percentage_on_service_charges',
              'igst_amount_on_service_charges', 'cgst_percentage_on_service_charges', 'cgst_amount_on_service_charges',
              'sgst_percentage_on_service_charges', 'sgst_amount_on_service_charges', 'total_service_charges_with_tax',
              'invoice_amount', 'sac_code_service', 'created_by', 'created_at',]

