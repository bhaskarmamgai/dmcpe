from bms.services import bookings as bookings as bookings
from bms.providers import parent_child_booking


def remove_parent_booking_from_booking(booking_obj):
    parent_child_booking.remove_parent_booking_from_booking(booking_obj)


def update_parent_booking_of_booking_object(booking_obj, parent_booking_obj):
    parent_child_booking.update_parent_booking_of_booking_object(booking_obj, parent_booking_obj)


def remove_child_booking_from_parent_booking(booking_obj):
    parent_child_booking.remove_child_booking_from_parent_booking(booking_obj)


def check_if_booking_is_linked(booking_obj):
    return parent_child_booking.check_if_booking_is_linked(booking_obj)


def add_parent_booking_to_child_booking(booking_obj, child_booking_obj):
    parent_child_booking.add_parent_booking_to_child_booking(booking_obj, child_booking_obj)


def check_if_requested_parent_booking_is_child_of_current_booking(booking_obj, parent_booking_obj):
    return parent_child_booking.check_if_requested_parent_booking_is_child_of_current_booking(booking_obj,
                                                                                              parent_booking_obj)


def check_if_requested_child_booking_is_parent_of_current_booking(booking_obj, child_booking_obj):
    return parent_child_booking.check_if_requested_child_booking_is_parent_of_current_booking(booking_obj,
                                                                                              child_booking_obj)


def handle_parent_booking(booking_obj, request_data):
    requested_parent_booking_code = request_data['parent_booking']
    if requested_parent_booking_code is None:
        remove_parent_booking_from_booking(booking_obj)
        return True, ""
    parent_booking_obj = bookings.get_booking_object_from_code(requested_parent_booking_code)
    if not parent_booking_obj:
        return False, f"Booking Does Not Exists For Booking Code {requested_parent_booking_code}"
    requested_booking_is_already_child_of_current_booking = (
        check_if_requested_parent_booking_is_child_of_current_booking(booking_obj, parent_booking_obj))
    if requested_booking_is_already_child_of_current_booking:
        return False, f"Booking {requested_parent_booking_code} is already child of current booking"
    update_parent_booking_of_booking_object(booking_obj, parent_booking_obj)
    return True, ""


def handle_child_booking(booking_obj, request_data):
    requested_child_booking_obj = request_data['child_booking']
    child_booking_obj = bookings.get_booking_object_from_code(requested_child_booking_obj.get('code'))
    if not child_booking_obj:
        return False, f"Booking Does Not Exists For Booking Code {requested_child_booking_obj.get('code')}"
    if requested_child_booking_obj.get('is_active') is True:
        requested_booking_is_parent_of_current_booking = (
            check_if_requested_child_booking_is_parent_of_current_booking(booking_obj, child_booking_obj))
        if requested_booking_is_parent_of_current_booking:
            return False, f"Booking {child_booking_obj} is already parent of current booking"
        booking_is_linked = check_if_booking_is_linked(child_booking_obj)
        if not booking_is_linked or requested_child_booking_obj.get('force_linking'):
            add_parent_booking_to_child_booking(booking_obj, child_booking_obj)
            return True, ""
        return False, f"Booking code {requested_child_booking_obj.get('code')} is linked to another booking"
    elif requested_child_booking_obj.get('is_active') is False:
        remove_child_booking_from_parent_booking(child_booking_obj)
        return True, ""
    else:
        return False, "Invalid Operation"


def handle_update_parent_child_booking(booking_obj, request_data):
    if 'parent_booking' in request_data:
        return handle_parent_booking(booking_obj, request_data)
    elif 'child_booking' in request_data:
        return handle_child_booking(booking_obj, request_data)
