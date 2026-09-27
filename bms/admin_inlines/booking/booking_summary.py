from django.contrib import admin

from bms.models.booking.booking_summary import BookingSummary
from common.libraries import get_numbers_formatted_to_indian_locale
from bms.services.booking_financial import get_booking_financial_v2_by_booking_id



class BookingSummaryInline(admin.TabularInline):
    model = BookingSummary
    readonly_fields = ('get_fx_profit_loss', 'get_amount_pending_for_collection_from_buyer',
                       'get_amount_collected_from_buyer', 'get_amount_paid_to_seller',
                       'get_amount_paid_to_buyer')
    fields = ['get_fx_profit_loss', 'get_amount_pending_for_collection_from_buyer',
              'get_amount_collected_from_buyer', 'get_amount_paid_to_seller',
              'get_amount_paid_to_buyer']

    def get_fx_profit_loss(self, obj):
        return get_numbers_formatted_to_indian_locale(obj.fx_profit_loss) if obj.fx_profit_loss else get_booking_financial_v2_by_booking_id(obj.bookings.id).net_profit

    def get_amount_pending_for_collection_from_buyer(self, obj):
        return get_numbers_formatted_to_indian_locale(obj.amount_pending_for_collection_from_buyer)

    def get_amount_collected_from_buyer(self, obj):
        return get_numbers_formatted_to_indian_locale(obj.amount_collected_from_buyer)

    def get_amount_paid_to_seller(self, obj):
        return get_numbers_formatted_to_indian_locale(obj.amount_paid_to_seller)

    def get_amount_paid_to_buyer(self, obj):
        return get_numbers_formatted_to_indian_locale(obj.amount_paid_to_buyer)

    get_fx_profit_loss.short_description = "FX P/L"
    get_amount_pending_for_collection_from_buyer.short_description = 'Amount Pending for Collection from Buyer'
    get_amount_collected_from_buyer.short_description = 'Amount Collected from Buyer'
    get_amount_paid_to_seller.short_description = 'Amount Paid to Seller'
    get_amount_paid_to_buyer.short_description = 'Amount Paid to Buyer'
