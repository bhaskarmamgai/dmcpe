from bms.models.booking import BookingStatusHistory


def create_booking_status_history(booking_id: int, **kwargs):
    return BookingStatusHistory.objects.create(booking_id=booking_id, **kwargs)


def get_booking_status_history_for_booking_by_status(booking_obj, booking_status):
    try:
        return BookingStatusHistory.objects.filter(booking=booking_obj, status=booking_status).order_by('created_at').first()
    except BookingStatusHistory.DoesNotExist:
        return None


def get_last_booking_status_history_obj_by_status(booking_obj, booking_status):
    try:
        return BookingStatusHistory.objects.filter(booking=booking_obj, status=booking_status).order_by('created_at').last()
    except BookingStatusHistory.DoesNotExist:
        return None
