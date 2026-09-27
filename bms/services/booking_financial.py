from bms.providers import booking_financial


def get_booking_financial_v2_by_booking_id(booking_id):
    return booking_financial.get_booking_financial_by_booking_id(booking_id)


def update_booking_financial_v2(booking_id, **kwargs):
    return booking_financial.update_booking_financial(booking_id, **kwargs)
