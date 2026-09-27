from django.contrib import admin

from bms.models import ApprovedDiscount, DiscountType, Booking
from dmcpesys.services import get_enabled_currencies
from bms.custom_formset import ApprovedDiscountInlineFormset
from bms.services.bookings import get_booking_object_from_id
from django.conf import settings


class ApprovedDiscountAdminInline(admin.TabularInline):
    model = ApprovedDiscount
    fields = ['discount_type', 'collection_currency', 'amount', 'booking', 'remark', 'attachment', 'created_at', 'created_by']
    list_display = ['discount_type', 'collection_currency', 'amount', 'booking', 'remark']
    readonly_fields = ['collection_currency', 'created_at', 'created_by']
    autocomplete_fields = ['discount_type']
    formset = ApprovedDiscountInlineFormset
    extra = 0

    def get_max_num(self, request, obj=None, **kwargs):
        return super().get_max_num(self, request, **kwargs) if request.user.is_superuser or request.user.groups.filter(
            id=settings.ALLOWED_GROUP_ID_FOR_APPROVED_DISCOUNT_ADMIN).exists() else 0

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "discount_type":
            kwargs['queryset'] = DiscountType.objects.filter(is_deleted=False, is_active=True)
        if db_field.name == "collection_currency":
            kwargs['queryset'] = get_enabled_currencies()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_readonly_fields(self, request, obj=None):
        booking_obj = get_booking_object_from_id(obj.id) if obj else None
        if booking_obj and booking_obj.status == Booking.CONFIRMED and not request.user.is_superuser:
            return self.fields
        return self.readonly_fields


