from bms.providers import booking_history


def create_booking_status_history(booking_id: int, **kwargs):
    return booking_history.create_booking_status_history(booking_id, **kwargs)


def get_booking_status_history_for_booking_by_status(booking_obj, booking_status):
    return booking_history.get_booking_status_history_for_booking_by_status(booking_obj, booking_status)


def get_last_booking_status_history_obj_by_status(booking_obj, booking_status):
    return booking_history.get_last_booking_status_history_obj_by_status(booking_obj, booking_status)
