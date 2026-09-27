from django.contrib import admin
from bms.models import SellerCostComponent
from bms.forms import SellerCostComponentAdminForm


class SellerCostComponentAdmin(admin.ModelAdmin):
    model = SellerCostComponent
    autocomplete_fields = ['booking', 'seller_member', 'seller_status', 'seller_status', 'seller_currency']
    readonly_fields = ['created_by', 'serial_number', 'seller_net_payable_in_seller_currency',
                       'seller_net_payable_in_collection_currency']
    list_display = ['serial_number', 'get_seller_member', 'seller_status', 'sce', 'seller_currency',
                    'cost_in_seller_currency', 'seller_service_charge', 'tax', 'commission_received', 'tds', 'tcs',
                    'seller_fx', 'seller_fx_markup', 'seller_net_payable_in_seller_currency', 'component_markup',
                    'cost_in_collection_currency', 'seller_net_payable_in_collection_currency', 'seller_booking_code',
                    'seller_reference_number', 'seller_invoice_code', 'seller_performa_invoice', 'get_booking',
                    'get_seller_organization', 'component', 'created_at', 'created_by']
    form = SellerCostComponentAdminForm

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('seller_organization', 'seller_member', 'booking', 'sce',
                                                            'seller_status', 'seller_currency', 'booking__type',
                                                            'created_by')

    def get_booking(self, obj):
        if obj.booking:
            return f"#{obj.booking.id} | {obj.booking.code} | {obj.booking.type.name}"
        return "-"

    def get_seller_organization(self, obj):
        if obj.seller_organization:
            return f"#{obj.seller_organization.id} | {obj.seller_organization.code}"
        return "-"

    def get_seller_member(self, obj):
        if obj.seller_member:
            return f"{obj.seller_member.id} - {obj.seller_member.code}"
        return "-"

    def has_change_permission(self, request, obj=None):
        if obj and obj.booking and hasattr(obj.booking, 'booking_details') and obj.booking.booking_details.is_completed:
            return False
        return True

    get_booking.short_description = "Booking"
    get_seller_organization.short_description = "Seller Organization"
    get_seller_member.short_description = "Seller Member"


admin.site.register(SellerCostComponent, SellerCostComponentAdmin)
