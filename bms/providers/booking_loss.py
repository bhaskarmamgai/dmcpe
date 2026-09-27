from bms.models.booking import BookingLoss


def get_booking_loss_object_from_booking_loss_id(booking_loss_id):
    try:
        return BookingLoss.objects.get(id=booking_loss_id)
    except:
        return None


def create_booking_loss(data):
    return BookingLoss.objects.create(**data)
