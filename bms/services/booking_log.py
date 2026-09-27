from bms.providers import booking_log

def create_booking_api_call_log(**kwargs):
    return booking_log.create_booking_api_call_log(**kwargs)


def update_booking_api_call_log(id: int, **kwargs):
    return booking_log.update_booking_api_call_log(id, **kwargs)