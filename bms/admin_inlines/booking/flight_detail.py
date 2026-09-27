from django.contrib import admin

from bms.custom_formset import FlightDetailInlineFormset
from bms.models.booking.flight_detail import FlightDetail


class FlightDetailsInline(admin.TabularInline):
    model = FlightDetail
    autocomplete_fields = ['from_airport', 'to_airport', 'airline']
    formset = FlightDetailInlineFormset
