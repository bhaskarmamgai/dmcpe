from bms.models.booking.transaction_log import BookingApiCallLog

def create_booking_api_call_log(**kwargs):
    return BookingApiCallLog.objects.create(**kwargs)


def update_booking_api_call_log(id: int, **kwargs):
    qs = BookingApiCallLog.objects.filter(id=id)
    qs.update(**kwargs)
    return qs[0]
