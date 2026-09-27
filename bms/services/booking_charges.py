from bms.providers import booking_charges


def get_default_roe_charged_to_buyer(booking_id: int):
    return booking_charges.get_default_roe_charged_to_buyer(booking_id)


def create_booking_charges(booking_id: int, **kwargs):
    return booking_charges.create_booking_charges(booking_id, **kwargs)

def get_booking_charges_object_from_booking_code(booking_code):
    return booking_charges.get_booking_charges_object_from_booking_code(booking_code)