from bms.services import bookings as bookings
from bms.models import BookingCharges


def get_default_roe_charged_to_buyer(booking_id: int):
    booking_obj = bookings.get_booking_object_from_id(booking_id)
    if hasattr(booking_obj, 'booking_charges'):
        return round(
            booking_obj.booking_charges.roe_on_booking_date + booking_obj.booking_charges.convenience_charges_on_roe, 2)
    return 0


def create_booking_charges(booking_id, **kwargs):
    try:
        instance, created = BookingCharges.objects.get_or_create(booking_id=booking_id, defaults={**kwargs})
        return instance, created
    except BookingCharges.MultipleObjectsReturned:
        return None, None


def get_booking_charges_object_from_booking_code(booking_code):

    try:
        return BookingCharges.objects.get(booking__code= booking_code)

    except:
        return None
