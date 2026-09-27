from datetime import timedelta
from django.utils import timezone
from bms.services import booking_history
from bms.models import Booking
from dmcpesys.constants import CATEGORY_FLIGHT_ID, CATEGORY_HOTEL_ID
from django.conf import settings


def validate_manual_refund_request_for_failed_booking(booking_obj, ts_obj):
    booking_status_history_obj = booking_history.get_last_booking_status_history_obj_by_status(
        booking_obj, booking_obj.status)
    is_hold_booking = booking_history.get_last_booking_status_history_obj_by_status(booking_obj, Booking.HOLD)

    if booking_obj.status != Booking.FAILED:
        return False, "Refund Is Allowed For Failed Bookings Only"

    if booking_obj.category_id not in [CATEGORY_HOTEL_ID, CATEGORY_FLIGHT_ID]:
        return False, "Refund Is Allowed Only For Category Hotel And Flight"

    obj = booking_status_history_obj if is_hold_booking else booking_obj
    if obj and (obj.created_at + timedelta(days=10) < timezone.now()):
        return False, "Refund Time Limit Exceeded"

    if ts_obj.net_hold <= 0:
        return False, "Net Hold Should be greater than 0"

    if booking_status_history_obj.updated_by_id not in [
        settings.INTERNAL_API_USER_FLIGHT, settings.INTERNAL_API_USER_HOTEL]:
        return False, "Refund Is Allowed For API Bookings Only"

    return True, None
