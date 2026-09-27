from bms.providers.booking_invoice import get_transaction_invoice_from_bookingobj, check_invoice_exist, check_invoice_pdf_exist


def get_transaction_invoice_obj_from_booking(booking_obj, **kwargs):
    return get_transaction_invoice_from_bookingobj(booking_obj, **kwargs)


def check_booking_invoice_exist(booking_obj):
    return check_invoice_exist(booking_obj)

def check_booking_invoice_pdf_exist(booking_obj):
    return check_invoice_pdf_exist(booking_obj)
