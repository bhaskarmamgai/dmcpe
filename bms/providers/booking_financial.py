from bms.models import BookingFinancial


def get_booking_financial_by_booking_id(booking_id):
    try:
        return BookingFinancial.objects.get(booking_id=booking_id)
    except:
        return None


def update_booking_financial(booking_id, **kwargs):
    qs = BookingFinancial.objects.filter(booking_id=booking_id)
    qs.update(**kwargs)
