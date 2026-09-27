from bms.models.booking.booking_invoice import BookingInvoices


def get_transaction_invoice_from_bookingobj(booking_obj, **kwargs):
    try:
        return BookingInvoices.objects.get(bookings=booking_obj, **kwargs)
    except BookingInvoices.DoesNotExist:
        return None


def check_invoice_exist(booking_obj):
    invoice_exist = False
    invoice_pdf_exist = False
    try:
        transaction_invoice = BookingInvoices.objects.get(bookings=booking_obj)
        if transaction_invoice:
            invoice_exist = True
            if transaction_invoice.document_path:
                invoice_pdf_exist = True
        return invoice_exist, invoice_pdf_exist
    except BookingInvoices.DoesNotExist:
        return invoice_exist, invoice_pdf_exist


def check_invoice_pdf_exist(booking_obj):
    booking_invoices_list = booking_obj._invoices
    if booking_invoices_list and booking_invoices_list[-1].document_path:
        return True
    return False