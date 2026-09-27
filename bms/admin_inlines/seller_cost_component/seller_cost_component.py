from django.contrib import admin
from django.utils.safestring import mark_safe

from bms.models import SellerCostComponent, Booking
from bms.services.seller_cost_component import get_active_seller_statuses
from bms.services.bookings import get_booking_object_from_id
from django.conf import settings
from bms.custom_formset import SellerCostComponentInlineFormset


class SellerCostComponentInline(admin.TabularInline):
    model = SellerCostComponent
    fields = ['serial_number', 'seller_member', 'categories',
              'seller_status', 'sce', 'seller_currency', 'cost_in_seller_currency', 'seller_service_charge', 'tax',
              'commission_received', 'tds', 'tcs',
              'seller_fx', 'seller_fx_markup', 'seller_net_payable_in_seller_currency',
              'component_markup',
              'cost_in_collection_currency', 'seller_net_payable_in_collection_currency',
              'seller_booking_code', 'seller_reference_number', 'seller_invoice_code',
              'seller_performa_invoice_link', 'seller_performa_invoice',
              'booking', 'seller_organization', 'component', 'created_at', 'created_by']
    autocomplete_fields = ['booking', 'seller_member', 'seller_status', 'sce', 'seller_currency']
    readonly_fields = ['serial_number', 'seller_performa_invoice_link', 'seller_organization', 'created_at',
                       'created_by', 'cost_in_collection_currency', 'seller_net_payable_in_seller_currency',
                       'seller_net_payable_in_collection_currency']
    formset = SellerCostComponentInlineFormset
    extra = 1

    def get_max_num(self, request, obj=None, **kwargs):
        if obj and obj.status == Booking.CONFIRMED and not request.user.is_superuser:
            return 0
        return super().get_max_num(self)

    def seller_performa_invoice_link(self, obj):
        if obj and obj.seller_performa_invoice:
            return mark_safe(
                "<a target='_blank' href='{}'>Performa Invoice Link</a>".format(obj.seller_performa_invoice.name))
        return None

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return self.readonly_fields
        booking_obj = get_booking_object_from_id(obj.id) if obj else None
        if booking_obj.status == Booking.CONFIRMED:
            return self.readonly_fields + ['seller_member', 'seller_organization', 'seller_fx', 'seller_fx_markup',
                                           'seller_status', 'sce', 'seller_currency', 'cost_in_seller_currency',
                                           'seller_service_charge', 'tax', 'commission_received', 'tds', 'tcs',
                                           'component_markup']
            return self.readonly_fields
        return self.fields

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "seller_status":
            kwargs["queryset"] = get_active_seller_statuses()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    seller_performa_invoice_link.short_description = "Seller Performa Invoice Link"
