from bms.models import Booking
from bms.models.booking.booking_invoice_config import BookingInvoiceConfig
from django.conf import settings
from bms.services import bookings
from django.db import transaction


def get_booking_invoice_config_obj(id: int):
    obj = BookingInvoiceConfig.objects.select_for_update().get(id=id)
    return obj


def get_booking_config_obj_from_booking_type_id(booking_id: int):
    booking_obj = bookings.get_booking_object_from_id(booking_id)
    for i in settings.MAP__BOOKING_INVOICE_CONFIG__BOOKING_TYPE:
        if booking_obj.type.id in [settings.BOOKING_TYPE_SAFE_REMITTANCE_ID,
                                   settings.BOOKING_TYPE_REMIT_ID] and hasattr(
                booking_obj, 'booking_financial'):
            if booking_obj.booking_financial.gross_profit > 0:
                if i.get('BOOKING_TYPE_ID') == booking_obj.type.id and i.get(
                        'INVOICE_TYPE_CODE') == settings.TRANSACTION_INVOICE.get('code'):
                    return get_booking_invoice_config_obj(i.get('BOOKING_INVOICE_CONFIG_ID'))
            elif booking_obj.booking_financial.gross_profit <= 0:
                if i.get('BOOKING_TYPE_ID') == booking_obj.type.id and i.get(
                        'INVOICE_TYPE_CODE') == settings.REIMBURSEMENT_INVOICE.get('code'):
                    return get_booking_invoice_config_obj(i.get('BOOKING_INVOICE_CONFIG_ID'))
        if booking_obj.type.id == settings.BOOKING_TYPE_PACKAGE_ID and hasattr(
                booking_obj, 'booking_financial'):
            if booking_obj.booking_financial.gross_profit > 0:
                if i.get('BOOKING_TYPE_ID') == settings.BOOKING_TYPE_PACKAGE_ID and i.get(
                        'INVOICE_TYPE_CODE') == settings.TRANSACTION_INVOICE.get('code'):
                    return get_booking_invoice_config_obj(i.get('BOOKING_INVOICE_CONFIG_ID'))
            elif booking_obj.booking_financial.gross_profit <= 0:
                if i.get('BOOKING_TYPE_ID') == settings.BOOKING_TYPE_PACKAGE_ID and i.get(
                        'INVOICE_TYPE_CODE') == settings.REIMBURSEMENT_INVOICE.get('code'):
                    return get_booking_invoice_config_obj(i.get('BOOKING_INVOICE_CONFIG_ID'))
        if booking_obj.type.id == settings.BOOKING_TYPE_OWN_SUPPLY and hasattr(
                booking_obj, 'booking_financial'):
            if booking_obj.booking_financial.gross_profit > 0:
                if i.get('BOOKING_TYPE_ID') == settings.BOOKING_TYPE_OWN_SUPPLY and i.get(
                        'INVOICE_TYPE_CODE') == settings.TRANSACTION_INVOICE.get('code'):
                    return get_booking_invoice_config_obj(i.get('BOOKING_INVOICE_CONFIG_ID'))
            elif booking_obj.booking_financial.gross_profit <= 0:
                if i.get('BOOKING_TYPE_ID') == settings.BOOKING_TYPE_OWN_SUPPLY and i.get(
                        'INVOICE_TYPE_CODE') == settings.REIMBURSEMENT_INVOICE.get('code'):
                    return get_booking_invoice_config_obj(i.get('BOOKING_INVOICE_CONFIG_ID'))
    return None


def get_booking_config_obj_from_booking_type_id_v2(booking_id: int, **kwargs):
    booking_obj = bookings.get_booking_object_from_id(booking_id)
    if kwargs.get('is_invoice_note'):
        if kwargs.get('is_credit_note'):
            if kwargs.get('service_charges'):
                return get_booking_invoice_config_obj(settings.BOOKING_INVOICE_CONFIG_ID_FOR_CREDIT_NOTE_WITH_FEE)
            return get_booking_invoice_config_obj(settings.BOOKING_INVOICE_CONFIG_ID_FOR_CREDIT_NOTE_WITHOUT_FEE)
        elif kwargs.get('is_debit_note'):
            if kwargs.get('service_charges'):
                return get_booking_invoice_config_obj(settings.BOOKING_INVOICE_CONFIG_ID_FOR_DEBIT_NOTE_WITH_FEE)
            return get_booking_invoice_config_obj(settings.BOOKING_INVOICE_CONFIG_ID_FOR_DEBIT_NOTE_WITHOUT_FEE)
        return None
    if kwargs.get('is_cancellation_invoice'):
        for i in settings.MAP__BOOKING_INVOICE_CONFIG__BOOKING_TYPE:
            if booking_obj.type.id in [settings.BOOKING_TYPE_SAFE_REMITTANCE_ID,
                                       settings.BOOKING_TYPE_REMIT_ID]:
                if kwargs.get('travelsupply_cancellation_charges') > 0:
                    if i.get('BOOKING_TYPE_ID') == booking_obj.type.id and i.get(
                            'INVOICE_TYPE_CODE') == settings.TRANSACTION_INVOICE.get('code'):
                        return get_booking_invoice_config_obj(i.get('BOOKING_INVOICE_CONFIG_ID'))
                elif kwargs.get('travelsupply_cancellation_charges') == 0:
                    if i.get('BOOKING_TYPE_ID') == booking_obj.type.id and i.get(
                            'INVOICE_TYPE_CODE') == settings.REIMBURSEMENT_INVOICE.get('code'):
                        return get_booking_invoice_config_obj(i.get('BOOKING_INVOICE_CONFIG_ID'))
            if booking_obj.type.id == settings.BOOKING_TYPE_PACKAGE_ID:
                if kwargs.get('travelsupply_cancellation_charges') > 0:
                    if i.get('BOOKING_TYPE_ID') == settings.BOOKING_TYPE_PACKAGE_ID and i.get(
                            'INVOICE_TYPE_CODE') == settings.TRANSACTION_INVOICE.get('code'):
                        return get_booking_invoice_config_obj(i.get('BOOKING_INVOICE_CONFIG_ID'))
                elif kwargs.get('travelsupply_cancellation_charges') == 0:
                    if i.get('BOOKING_TYPE_ID') == settings.BOOKING_TYPE_PACKAGE_ID and i.get(
                            'INVOICE_TYPE_CODE') == settings.REIMBURSEMENT_INVOICE.get('code'):
                        return get_booking_invoice_config_obj(i.get('BOOKING_INVOICE_CONFIG_ID'))
            if booking_obj.type.id == settings.BOOKING_TYPE_OWN_SUPPLY:
                if kwargs.get('travelsupply_cancellation_charges') > 0:
                    if i.get('BOOKING_TYPE_ID') == settings.BOOKING_TYPE_OWN_SUPPLY and i.get(
                            'INVOICE_TYPE_CODE') == settings.TRANSACTION_INVOICE.get('code'):
                        return get_booking_invoice_config_obj(i.get('BOOKING_INVOICE_CONFIG_ID'))
                elif kwargs.get('travelsupply_cancellation_charges') == 0:
                    if i.get('BOOKING_TYPE_ID') == settings.BOOKING_TYPE_OWN_SUPPLY and i.get(
                            'INVOICE_TYPE_CODE') == settings.REIMBURSEMENT_INVOICE.get('code'):
                        return get_booking_invoice_config_obj(i.get('BOOKING_INVOICE_CONFIG_ID'))
    else:
        for i in settings.MAP__BOOKING_INVOICE_CONFIG__BOOKING_TYPE:
            if booking_obj.type.id in [settings.BOOKING_TYPE_SAFE_REMITTANCE_ID,
                                       settings.BOOKING_TYPE_REMIT_ID] and hasattr(
                    booking_obj, 'booking_financial'):
                if booking_obj.booking_financial.gross_profit > 0:
                    if i.get('BOOKING_TYPE_ID') == booking_obj.type.id and i.get(
                            'INVOICE_TYPE_CODE') == settings.TRANSACTION_INVOICE.get('code'):
                        return get_booking_invoice_config_obj(i.get('BOOKING_INVOICE_CONFIG_ID'))
                elif booking_obj.booking_financial.gross_profit <= 0:
                    if i.get('BOOKING_TYPE_ID') == booking_obj.type.id and i.get(
                            'INVOICE_TYPE_CODE') == settings.REIMBURSEMENT_INVOICE.get('code'):
                        return get_booking_invoice_config_obj(i.get('BOOKING_INVOICE_CONFIG_ID'))
            if booking_obj.type.id == settings.BOOKING_TYPE_PACKAGE_ID and hasattr(
                    booking_obj, 'booking_financial'):
                if booking_obj.booking_financial.gross_profit > 0:
                    if i.get('BOOKING_TYPE_ID') == settings.BOOKING_TYPE_PACKAGE_ID and i.get(
                            'INVOICE_TYPE_CODE') == settings.TRANSACTION_INVOICE.get('code'):
                        return get_booking_invoice_config_obj(i.get('BOOKING_INVOICE_CONFIG_ID'))
                elif booking_obj.booking_financial.gross_profit <= 0:
                    if i.get('BOOKING_TYPE_ID') == settings.BOOKING_TYPE_PACKAGE_ID and i.get(
                            'INVOICE_TYPE_CODE') == settings.REIMBURSEMENT_INVOICE.get('code'):
                        return get_booking_invoice_config_obj(i.get('BOOKING_INVOICE_CONFIG_ID'))
            if booking_obj.type.id == settings.BOOKING_TYPE_OWN_SUPPLY and hasattr(
                    booking_obj, 'booking_financial'):
                if booking_obj.booking_financial.gross_profit > 0:
                    if i.get('BOOKING_TYPE_ID') == settings.BOOKING_TYPE_OWN_SUPPLY and i.get(
                            'INVOICE_TYPE_CODE') == settings.TRANSACTION_INVOICE.get('code'):
                        return get_booking_invoice_config_obj(i.get('BOOKING_INVOICE_CONFIG_ID'))
                elif booking_obj.booking_financial.gross_profit <= 0:
                    if i.get('BOOKING_TYPE_ID') == settings.BOOKING_TYPE_OWN_SUPPLY and i.get(
                            'INVOICE_TYPE_CODE') == settings.REIMBURSEMENT_INVOICE.get('code'):
                        return get_booking_invoice_config_obj(i.get('BOOKING_INVOICE_CONFIG_ID'))
    return None


def generate_invoice_number(booking_id: int, **kwargs):
    with transaction.atomic():
        booking_obj = bookings.get_booking_object_from_id(booking_id)
        booking_invoice_config_obj = get_booking_config_obj_from_booking_type_id_v2(booking_id, **kwargs)
        if booking_invoice_config_obj:
            if settings.APP_ENVIRONMENT != 'prod':
                env_type = settings.APP_ENVIRONMENT
                if len(env_type) > 3:
                    env_type = env_type[:3]
                invoice_type = str(booking_invoice_config_obj.invoice_type) + env_type
            else:
                invoice_type = str(booking_invoice_config_obj.invoice_type)

            invoice_number = "{}{}{}{}".format(invoice_type, str(booking_invoice_config_obj.booking_type),
                                                   str(booking_invoice_config_obj.financial_year),
                                                   str(booking_invoice_config_obj.next_sequence))
            booking_invoice_config_obj.next_sequence = booking_invoice_config_obj.next_sequence + 1
            booking_invoice_config_obj.save()
            return invoice_number
        return None
