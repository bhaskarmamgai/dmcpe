def remove_parent_booking_from_booking(booking_obj):
    booking_obj.parent_booking_id = None
    booking_obj.parent_booking_code = None
    booking_obj.save()


def update_parent_booking_of_booking_object(booking_obj, parent_booking_obj):
    booking_obj.parent_booking_id = parent_booking_obj.id
    booking_obj.parent_booking_code = parent_booking_obj.code
    booking_obj.save()


def remove_child_booking_from_parent_booking(booking_obj):
    booking_obj.parent_booking_id = None
    booking_obj.parent_booking_code = None
    booking_obj.save()


def check_if_booking_is_linked(booking_obj):
    if booking_obj.parent_booking_id or booking_obj.parent_booking_code:
        return True
    return False


def add_parent_booking_to_child_booking(booking_obj, child_booking_obj):
    child_booking_obj.parent_booking_id = booking_obj.id
    child_booking_obj.parent_booking_code = booking_obj.code
    child_booking_obj.save()


def check_if_requested_parent_booking_is_child_of_current_booking(booking_obj, parent_booking_obj):
    if (parent_booking_obj.parent_booking_id == booking_obj.id or
            parent_booking_obj.parent_booking_code == booking_obj.code):
        return True
    return False


def check_if_requested_child_booking_is_parent_of_current_booking(booking_obj, child_booking_obj):
    if (booking_obj.parent_booking_id == child_booking_obj.id or
            booking_obj.parent_booking_code == child_booking_obj.code):
        return True
    return False
