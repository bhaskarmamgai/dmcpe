from django.contrib import admin

from bms.models import BookingFinancial

class BookingFinancialInline(admin.TabularInline):
    model = BookingFinancial
    readonly_fields = ['total_net_payable', 'total_net_receivable', 'total_cost_price',
                       'total_seller_service_charge', 'total_tax_on_seller_service_charge',
                       'total_commission_received', 'total_tds', 'booking',
                       'approved_discount', 'tcs', 'gross_profit', 'net_profit']
    autocomplete_fields = ['booking']

    def get_queryset(self, request):
        return super(BookingFinancialInline, self).get_queryset(request).select_related('booking')



