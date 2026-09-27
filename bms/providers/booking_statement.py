
from bms.models import Booking, BookingStatement
from django.db.models import Q


def create_booking_statement(**data):
    return BookingStatement.objects.create(**data)

def get_bookings_within_booking_date_range_by_member_id(member_id,booking_start_date,booking_end_date):
    return Booking.objects.filter((Q(buyer=member_id) | Q(seller=member_id)), (Q(booking_date__range = [booking_start_date,booking_end_date]) | Q(booking_date__icontains = booking_end_date)))