from bms.providers import invoice


def update_booking_invoice_number(booking_objs: list):
    for booking in booking_objs:
        invoice.update_booking_invoice_number(booking)
    return True


def get_booking_invoice_number_by_booking_object(booking_obj, **kwargs):
    return invoice.update_booking_invoice_number(booking_obj, **kwargs)
