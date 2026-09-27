from bms.providers.invoice import validate_booking_invoice_request
from bms.providers import invoice

def handle_flight_booking_invoice_request(booking_id, created_by_id):
    error_message, is_valid = validate_booking_invoice_request(
        booking_id)
    if is_valid:
        invoice_obj = invoice.create_invoice(booking_id, created_by_id)
        error_message, is_valid_invoice_object = invoice.validate_booking_invoice_object(booking_id)
        if is_valid_invoice_object and invoice_obj.document_path:
            return None, invoice_obj.id
        return error_message, None
    return error_message, None

