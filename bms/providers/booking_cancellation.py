from bms.models.cancellation.booking_cancellation import BookingCancellation

def get_booking_cancellation_object_from_booking_code(booking_code):
    try:
        return BookingCancellation.objects.get(booking__code=booking_code)
    except:
        return None
