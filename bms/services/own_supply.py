from bms.providers.invoice import validate_booking_invoice_request,validate_booking_invoice_object
from bms.services import invoice as invoice_service


def handle_own_supply_booking_invoice_request(booking_id, created_by_id):
    error_message, is_valid = validate_booking_invoice_request(
        booking_id)
    if is_valid:
        invoice_obj = invoice_service.create_invoice(booking_id, created_by_id)
        error_message, is_valid = validate_booking_invoice_object(booking_id)
        if is_valid :
            if invoice_obj.document_path:
                invoice_service.send_booking_invoice_notification(invoice_obj.id)
            return None, invoice_obj.id
        return error_message, None
    return error_message, None