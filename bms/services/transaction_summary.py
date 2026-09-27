from bms.providers import transaction_summary


def update_booking_summary_with_booking_objs(booking_objs):
    for booking in booking_objs:
        transaction_summary.booking_summary_update(booking)
    return True


def get_booking_summary_object_by_booking_id(booking_id: int):
    return transaction_summary.get_booking_summary_object_by_booking_id(booking_id)


def get_booking_summary_object_for_update_by_booking_id(booking_id: int):
    return transaction_summary.get_booking_summary_object_for_update_by_booking_id(booking_id)
