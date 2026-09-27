from bms.providers import booking_document


def send_booking_document_mail(instance_id):
    booking_document.send_booking_document_mail(instance_id)


def send_booking_document_whatsapp_notification(instance_id):
    booking_document.send_booking_document_whatsapp_notification(instance_id)


def get_booking_document_by_booking_document_id(instance_id: int):
    return booking_document.get_booking_document_by_booking_document_id(instance_id)


def create_booking_document(**kwargs):
    return booking_document.create_booking_document(**kwargs)


def update_booking_document(booking_document_id, **kwargs):
    return booking_document.update_booking_document(booking_document_id, **kwargs)
