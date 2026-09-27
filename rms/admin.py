from django.contrib import admin
from .models import (
    RMSProfile,
    Beneficiary,
    RemittanceRequest,
    RemittancePassenger,
)


@admin.register(RMSProfile)
class RMSProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'organization', 'is_active_remitter', 'created_at')
    search_fields = ('organization__name',)


@admin.register(Beneficiary)
class BeneficiaryAdmin(admin.ModelAdmin):
    list_display = (
        'code', 'beneficiary_name', 'organization', 'bank_name',
        'account_number', 'swift_code', 'currency', 'created_at'
    )
    search_fields = (
        'code', 'beneficiary_name', 'organization__name',
        'bank_name', 'account_number', 'swift_code', 'beneficiary_email'
    )
    list_filter = ('currency', 'bank_country', 'beneficiary_country')


class RemittancePassengerInline(admin.TabularInline):
    model = RemittancePassenger
    extra = 0
    fields = ('pan_number', 'passenger_name', 'amount', 'date_of_journey', 'is_pan_verified')


@admin.register(RemittanceRequest)
class RemittanceRequestAdmin(admin.ModelAdmin):
    list_display = (
        'code', 'organization', 'purpose', 'invoice_reference_number',
        'invoice_amount', 'remittance_amount', 'is_part_payment',
        'current_stage', 'status', 'created_at'
    )
    search_fields = (
        'code', 'organization__name', 'beneficiary_name',
        'invoice_reference_number', 'bank_reference_number'
    )
    list_filter = ('current_stage', 'status', 'purpose', 'is_part_payment')
    inlines = [RemittancePassengerInline]


@admin.register(RemittancePassenger)
class RemittancePassengerAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'remittance_request', 'pan_number', 'passenger_name',
        'amount', 'date_of_journey', 'is_pan_verified'
    )
    search_fields = ('pan_number', 'passenger_name', 'remittance_request__code')
    list_filter = ('is_pan_verified', 'date_of_journey')
