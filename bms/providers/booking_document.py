from django.conf import settings
from bms.models.booking.booking_document import BookingDocument


def send_booking_document_mail(booking_document_id):
    cc_emails = []
    acm_email = ''
    booking_document_obj = get_booking_document_by_booking_document_id(booking_document_id)
    booking_obj = booking_document_obj.booking if booking_document_obj else None
    if booking_obj and booking_document_obj.status == BookingDocument.ACTIVE:
        if booking_obj.buyer.account_manager and booking_obj.buyer.account_manager.email:
            acm_email = booking_obj.buyer.account_manager.email
        document_type = None
        for enum, value in booking_document_obj.DOCUMENT_TYPE:
            if enum == booking_document_obj.document_type:
                document_type = value
                break
        params = {
            'document_type': document_type,
            'agent_primary_name': booking_obj.buyer.name,
            'booking_code': booking_obj.code,
            'booking_title': booking_obj.booking_details.title,
            'name': booking_document_obj.name,
            'category': booking_document_obj.category.name,
            'destination': booking_obj.destination.name if booking_obj.destination else None,
            'document_url': booking_document_obj.file.name,
            'lead_pax_name': booking_obj.booking_details.passenger_details.split(',')[0].replace('\n', '').strip(),
            'travel_date': str(booking_obj.departure_at)
        }
        from_email = settings.BOOKING_DOCUMENT_EMAIL_ADDRESS
        to_email = [booking_obj.buyer_organization.email, booking_obj.buyer.email, booking_obj.buyer.email2]
        cc_emails.append(acm_email)
        optional_data = {'cc_email': cc_emails}
        return emails.send_template_email(from_email, to_email, settings.BOOKING_DOCUMENT_MAIL_TEMPLATE_ID, params, optional_data)
    return None



def get_booking_document_by_booking_document_id(booking_document_id):
    return BookingDocument.objects.get(id=booking_document_id)


def create_booking_document(**kwargs):
    return BookingDocument.objects.create(**kwargs)


def update_booking_document(booking_document_id, **kwargs):
    return BookingDocument.objects.filter(id=booking_document_id).update(**kwargs)
