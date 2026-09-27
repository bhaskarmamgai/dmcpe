from django.contrib import admin
from bms.models import BookingCharges




class BookingChargesBaseInline(admin.TabularInline):
    model = BookingCharges
    list_display = ['roe_on_booking_date', 'service_charge_collected_from_buyer', 'convenience_charges_on_roe']
    fields =  ['roe_on_booking_date', 'service_charge_collected_from_buyer', 'convenience_charges_on_roe']




