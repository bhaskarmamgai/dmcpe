from django.http import HttpResponseRedirect
from django.contrib import messages
from bms.services import bookings


def fetch_booking_financials(request,booking_id:int):
    bookings.update_booking_financial_v2(booking_id)
    messages.add_message(request, messages.SUCCESS, 'Booking Financials Fetched Successfully.')
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))