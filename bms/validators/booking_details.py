from bms.services import bookings as bookings as bookings, booking_details
from bms.models import Booking

def validate_booking_details_data(request_data, **kwargs):
    if not request_data:
        return False, "No Data Provided"

    if not kwargs.get('code'):
        return False, "Booking Code Is Required"

    booking_obj = bookings.get_booking_object_from_code(kwargs.get('code'))
    if not booking_obj:
        return False, f"Booking Does Not Exists For Booking Code {kwargs.get('code')}"

    if not request_data.get('passenger_details'):
        return False, "Passenger Details Is Mandatory"

    booking_details_obj = booking_details.get_booking_details_by_booking_id(booking_obj.id)
    if not booking_details_obj:
        return False, f"Booking Details Does Not Exists For Booking Code {kwargs.get('code')}"

    if booking_obj.status == Booking.CONFIRMED:
        if request_data.get('departure_or_checkin_time'):
            return False, f"Time Of Travel Field Un-Editable For Confirmed Bookings"

    return booking_obj, None