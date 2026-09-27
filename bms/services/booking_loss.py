from bms.providers import booking_loss


def get_booking_loss_object_from_booking_loss_id(approved_discount_id):
    return booking_loss.get_booking_loss_object_from_booking_loss_id(approved_discount_id)


def create_booking_loss(data):
    return booking_loss.create_booking_loss(data=data)
