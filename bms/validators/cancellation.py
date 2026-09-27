
from django.conf import settings
from bms.services.bookings import get_booking_object_from_code
from bms.providers.cancellation import check_cancellation_allowed_by_booking_code, get_cancellation_request_object_by_cancellation_code
from bms.models import Booking
from bms.enums import CancellationStatus

def cancellation_request_validator(booking_code):

    booking_obj = get_booking_object_from_code(booking_code)
    if not booking_obj:
        return False, "Invalid Booking Code! Booking With This Code Does Not Exist."

    if booking_obj.status != Booking.CONFIRMED:
        return False, "Cancellation Not Allowed For This Booking: {}.Booking Not Confirmed.".format(booking_obj.code)
    is_cancellation_allowed = check_cancellation_allowed_by_booking_code(booking_code)
    if not is_cancellation_allowed:
        return False, "Cancellation Can only be done prior to {} hours of Booking." .format(settings.FLIGHT_BOOKING_CANCELLATION_REQUEST_ALLOWED_DURATION_IN_HOURS)
    return True, None


def validate_cancellation_abort_request_by_cancellation_Code(cancellation_code):
    cancellation_request_obj = get_cancellation_request_object_by_cancellation_code(cancellation_code)

    if not cancellation_request_obj:
        return False, "Invalid Cancellation Code {}".format(cancellation_code)

    if cancellation_request_obj.service_request_status.status_order == CancellationStatus.CANCELLATION_STATUS__ABORTED.value:
        return False, "Cancellation Status For This Request {} Is Already Aborted.".format(cancellation_code)
    return True, None

