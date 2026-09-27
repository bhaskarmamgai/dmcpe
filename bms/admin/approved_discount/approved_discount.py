from django.contrib import admin
from bms.models.approved_discount.approved_discount import ApprovedDiscount, DiscountType
from dmcpesys.services import get_enabled_currencies
from bms.forms import ApprovedDiscountAdminForm


class ApprovedDiscountAdmin(admin.ModelAdmin):
    model = ApprovedDiscount
    fields = ['discount_type', 'collection_currency', 'amount', 'booking', 'remark', 'attachment', 'created_at', 'created_by']
    list_display = ['discount_type', 'collection_currency', 'amount', 'booking', 'remark', 'created_at', 'created_by']
    autocomplete_fields = ['booking', 'discount_type', 'collection_currency']
    readonly_fields = ['collection_currency', 'created_at', 'created_by']
    form = ApprovedDiscountAdminForm

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "discount_type":
            kwargs['queryset'] = DiscountType.objects.filter(is_deleted=False, is_active=True)
        if db_field.name == "collection_currency":
            kwargs['queryset'] = get_enabled_currencies()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


    def get_changeform_initial_data(self, request):
        booking_id = request.GET.get('booking_id')
        initial = {}
        if booking_id:
            initial['booking'] = booking_id
        return initial

    def has_change_permission(self, request, obj=None):
        if obj and obj.booking and hasattr(obj.booking, 'booking_details') and obj.booking.booking_details.is_completed:
            return False
        return True


class DiscountTypeAdmin(admin.ModelAdmin):
    model = DiscountType
    fields = ['name', 'is_active', 'is_deleted']
    search_fields = ['name']
    list_display = ['name', 'is_active', 'is_deleted']


admin.site.register(ApprovedDiscount, ApprovedDiscountAdmin)
admin.site.register(DiscountType, DiscountTypeAdmin)
