from bms.models import FlightDetail


def create_flight_details(booking_id, **kwargs):
    try:
        instance, created = FlightDetail.objects.get_or_create(booking_id=booking_id, defaults={**kwargs})
        return instance, created
    except FlightDetail.MultipleObjectsReturned:
        return None, None


def get_flight_details_by_booking_id(booking_id: int):
    try:
        return FlightDetail.objects.get(booking_id=booking_id)
    except FlightDetail.DoesNotExist:
        return None
