from bms.providers import flight_details


def create_flight_details(booking_id: int, **kwargs):
    return flight_details.create_flight_details(booking_id, **kwargs)


def get_flight_details_by_booking_id(booking_id: int):
    return flight_details.get_flight_details_by_booking_id(booking_id)
