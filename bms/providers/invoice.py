import datetime
from io import BytesIO
from django.conf import settings
from django.core.files import File
from common.libraries import render_and_upload_pdf
from bms.config.invoice import TRANSACTION_INVOICE_TYPE__CANCELLATION_TAX_INVOICE, \
    TRANSACTION_INVOICE_TYPE__CANCELLATION_REIMBURSEMENT_INVOICE
from bms.models import Booking, ActualPayment, BookingDocument, BookingInvoices
from bms.providers.booking_invoice_config import generate_invoice_number
from bms.serializers.booking import BookingInvoiceSerializer
from bms.services import bookings
from dmcpesys.constants import IGST, SGST, CGST
from bms.validators import booking as booking_validator
from bms.services.bookings import get_booking_object_from_id
from bms.services.booking_invoice import get_transaction_invoice_obj_from_booking
from bms.services.booking_financial import get_booking_financial_v2_by_booking_id
from bms.services import booking_invoice_config
from django.conf import settings
from datetime import date
from common.libraries import convert_datetime_utc_to_ist
from .booking_document import get_booking_document_by_booking_document_id


def get_description_of_reimbursement_for_invoice(booking_obj):
    seller_booking_code = ""
    if booking_obj.type_id == settings.BOOKING_TYPE_FLIGHT_ID:
        return 'FLIGHT TICKET BOOKING - {} ({})'.format(seller_booking_code, booking_obj.code)
    return '{} BOOKING - {} ({})'.format(booking_obj.category.name, seller_booking_code, booking_obj.code)


def get_default_reimbursement_amount_from_booking_obj(booking_obj):
    if hasattr(booking_obj, 'booking_charges'):
        return round(booking_obj.booking_charges.roe_on_booking_date * booking_obj.amount, 2)
    return booking_obj.amount


def get_default_description_of_reimbursement(booking_obj):
    return "{} {}".format(
        booking_obj.category.name, booking_obj.destination.name if booking_obj.destination else '')

def update_booking_invoice_number(booking_obj, **kwargs):
    if booking_obj.invoice_number:
        return booking_obj.invoice_number
    booking_obj.invoice_number = generate_invoice_number(booking_obj.id)
    booking_obj.save(update_fields=["invoice_number"])
    return booking_obj.invoice_number


def get_invoice_date_for_invoice_generation(booking_invoice):
    if booking_invoice and booking_invoice.created_at:
        return convert_datetime_utc_to_ist(booking_invoice.created_at)


def get_default_service_charges_from_booking_obj(booking_obj):
    """
    Used below formula for Service Charge:
    Service Charge = {[ Bank Charges x (XE.com ROE + Convenience Charges On RoE)] +[Booking Amount x Convenience Fee] } / 1.18
    1. The field shall be editable
    2. Valid only for Remit & Safe (Remit) cases
    GST_FACTOR_FOR_DEFAULT_SERVICE_CHARGE = 1.18
    """
    if hasattr(booking_obj, 'booking_charges'):
        return round(
            (((booking_obj.booking_charges.service_charge_collected_from_buyer * (
                    booking_obj.booking_charges.roe_on_booking_date + booking_obj.booking_charges.convenience_charges_on_roe)) + (
                      booking_obj.amount * booking_obj.booking_charges.convenience_charges_on_roe)) / settings.GST_FACTOR_FOR_DEFAULT_SERVICE_CHARGE),
            2)
    return booking_obj.amount



def create_tax_invoice(booking_id, created_by, **kwargs):
    master_gst_response_data = None
    gstin_invalid = False
    kwargs.update(invoice_type=settings.TRANSACTION_INVOICE_TYPE__TRANSACTION_INVOICE)
    booking_obj = bookings.get_booking_object_from_id(booking_id)
    data = create_tax_invoice_data(booking_obj, created_by, **kwargs)
    booking_invoice = get_transaction_invoice_obj_from_booking(booking_obj)

    if booking_invoice:
        is_tax_invoice = check_invoice_type(booking_invoice.tax_invoice_number)
        if is_tax_invoice and booking_invoice.document_path:
            invoice_date = get_invoice_date_for_invoice_generation(booking_invoice).strftime("%d/%m/%Y")
        message, is_valid = validate_booking_invoice_object(booking_id)
        if is_tax_invoice and is_valid:
            return create_invoice_pdf(booking_invoice, booking_obj, **kwargs)
        return booking_invoice
    else:
        serializer_obj = BookingInvoiceSerializer(data=data)
        if serializer_obj.is_valid():
            transaction_invoice_obj = serializer_obj.save()
            transaction_invoice_obj.save()
            message, is_valid = validate_booking_invoice_object(booking_id)
            if is_valid:
                create_invoice_pdf(transaction_invoice_obj, booking_obj, **kwargs)
    return None


def calculate_total_service_charges_with_tax_for_tax_invoice(booking_obj):
    return booking_obj.booking_financial.gross_profit if hasattr(booking_obj, 'booking_financial') else 0


def create_tax_invoice_data(booking_obj, created_by, **kwargs):
    data_dict = dict(
        booking_id=booking_obj.id,
        tax_invoice_number=booking_invoice_config.get_booking_invoice_number_by_booking_object(booking_obj, **kwargs),
        description_of_service_charges='Service Charges',
        sac_code_service=settings.DEFAULT_SAC_CODE,
        invoice_type=kwargs.get('invoice_type'),
        created_by_id=created_by,
    )
    if kwargs.get('is_cancellation_invoice'):
        data_dict.update(
            description_of_reimbursement="Provider cancellation charges - " + get_description_of_reimbursement_for_invoice(
                booking_obj))
    else:
        data_dict.update(description_of_reimbursement=get_description_of_reimbursement_for_invoice(booking_obj))
    amount_and_tax_metrics = get_financial_metrics_for_tax_invoice(booking_obj, **kwargs)
    data_dict.update(amount_and_tax_metrics)
    return data_dict


def get_reimbursement_amount_for_booking(booking_obj):
    return booking_obj.booking_financial.total_cost_price if hasattr(booking_obj, 'booking_financial') else 0


def calculated_service_charge_tax_invoice(booking_obj):
    if hasattr(booking_obj, 'booking_financial'):
        return round((
                             booking_obj.booking_financial.gross_profit - booking_obj.booking_financial.approved_discount) / settings.GST_FACTOR_FOR_DEFAULT_SERVICE_CHARGE,
                     2)
    return 0


def calculate_service_charge_for_invoice(total_service_charges):
    return round(total_service_charges / settings.GST_FACTOR_FOR_DEFAULT_SERVICE_CHARGE, 2)


def calculate_total_approved_discount(booking_obj):
    return (abs(min(booking_obj.booking_financial.gross_profit,
                    0)) + booking_obj.booking_financial.approved_discount) if hasattr(booking_obj,
                                                                                      'booking_financial') else 0


def get_financial_metrics_for_tax_invoice(booking_obj, **kwargs):
    financial_obj = booking_obj.latest_booking_financials
    if financial_obj:
        tax_dict = dict(
            igst_percentage_on_service_charges=0,
            igst_amount_on_service_charges=0,
            cgst_percentage_on_service_charges=0,
            cgst_amount_on_service_charges=0,
            sgst_percentage_on_service_charges=0,
            sgst_amount_on_service_charges=0,
            scratch_card_amount=0,
            approved_discount=0,
            invoice_amount=0,
        )
        if kwargs.get("is_cancellation_invoice"):
            tax_dict.update(
                total_service_charges_with_tax=financial_obj.gross_profit + kwargs.get(
                    'travelsupply_cancellation_charges',
                    0))
            tax_dict.update(
                reimbursement_amount=financial_obj.total_cost_price + kwargs.get('provider_cancellation_charges', 0))
            tax_dict.update(scratch_card_amount=kwargs.get('scratch_card_amount', 0))
            tax_dict.update(approved_discount=financial_obj.approved_discount)
        else:
            tax_dict.update(
                total_service_charges_with_tax=calculate_total_service_charges_with_tax_for_tax_invoice(booking_obj))
            tax_dict.update(reimbursement_amount=get_reimbursement_amount_for_booking(booking_obj))
            tax_dict.update(approved_discount=calculate_total_approved_discount(booking_obj))

        tax_dict.update({'service_charges': calculate_service_charge_for_invoice(
            tax_dict.get('total_service_charges_with_tax', 0))})
        gst_metrics_data = get_gst_metrics_for_invoice(booking_obj, tax_dict.get('service_charges', 0))
        tax_dict.update(gst_metrics_data)
        if booking_obj.buyer_organization.organization_details.state.id == settings.DELHI_STATE_ID:
            tax_dict.update({'cgst_percentage_on_service_charges': settings.DEFAULT_GST_DELHI.get('cgst')})
            tax_dict.update({'cgst_amount_on_service_charges': round(tax_dict.get('service_charges', 0) *
                                                                     settings.CGST_FACTOR_FOR_DEFAULT_SERVICE_CHARGE,
                                                                     2)})
            tax_dict.update({'sgst_percentage_on_service_charges': settings.DEFAULT_GST_DELHI.get('sgst')})
            tax_dict.update({'sgst_amount_on_service_charges': round(tax_dict.get('service_charges', 0) *
                                                                     settings.SGST_FACTOR_FOR_DEFAULT_SERVICE_CHARGE,
                                                                     2)})
        else:
            tax_dict.update({'igst_amount_on_service_charges': round(tax_dict.get('service_charges', 0) *
                                                                     settings.IGST_FACTOR_FOR_DEFAULT_SERVICE_CHARGE,
                                                                     2)})
            tax_dict.update({'igst_percentage_on_service_charges': settings.DEFAULT_GST_INDIA.get('igst')})
        if kwargs.get("is_cancellation_invoice"):
            tax_dict.update({'invoice_amount': abs(round(kwargs.get('travelsupply_cancellation_charges', 0) +
                                                         kwargs.get('provider_cancellation_charges', 0) -
                                                         kwargs.get('scratch_card_amount', 0), 2))})
        else:
            tax_dict.update({'invoice_amount': round(tax_dict.get('total_service_charges_with_tax') +
                                                     tax_dict.get('reimbursement_amount') -
                                                     tax_dict.get('approved_discount'), 2)})
        return tax_dict
    return None


def get_cost_price_for_booking(booking_obj):
    if hasattr(booking_obj, 'booking_financial'):
        return booking_obj.booking_financial.total_cost_price
    return 0


def create_reimbursement_invoice(booking_id: int, created_by: int, **kwargs):
    booking_obj = bookings.get_booking_object_from_id(booking_id)
    kwargs.update(invoice_type=settings.TRANSACTION_INVOICE_TYPE__REIMBURSEMENT_NOTE)
    data = create_reimbursement_invoice_data(booking_obj, created_by, **kwargs)
    transaction_invoice_obj = get_transaction_invoice_obj_from_booking(booking_obj)
    if transaction_invoice_obj:
        message, is_valid = validate_booking_invoice_object(booking_id)
        if is_valid:
            return create_invoice_pdf(transaction_invoice_obj, booking_obj, **kwargs)
        return transaction_invoice_obj
    else:
        serializer_obj = BookingInvoiceSerializer(data=data)
        if serializer_obj.is_valid():
            transaction_invoice_obj = serializer_obj.save()
            message, is_valid = validate_booking_invoice_object(booking_id)
            if is_valid:
                return create_invoice_pdf(transaction_invoice_obj, booking_obj, **kwargs)
            return transaction_invoice_obj
    return None


def create_reimbursement_invoice_data(booking_obj, created_by, **kwargs):
    financial_obj = booking_obj.booking_financial
    if financial_obj:
        data_dict = dict(
            booking_id=booking_obj.id,
            tax_invoice_number=booking_invoice_config.get_booking_invoice_number_by_booking_object(booking_obj,
                                                                                                   **kwargs),
            description_of_service_charges='Discount Provided',
            sac_code_service=settings.DEFAULT_SAC_CODE,
            created_by_id=created_by,
            invoice_type=kwargs.get('invoice_type'),
            approved_discount=0,
            scratch_card_amount=0,
            total_service_charges_with_tax=0,
        )
        if kwargs.get("is_cancellation_invoice"):
            data_dict.update(
                description_of_reimbursement="Provider cancellation charges - " + get_description_of_reimbursement_for_invoice(
                    booking_obj))
            data_dict.update(total_service_charges_with_tax=financial_obj.gross_profit)
            data_dict.update(
                service_charges=calculate_service_charge_for_invoice(data_dict.get('total_service_charges_with_tax')))
            gst_metrics = get_gst_metrics_for_invoice(booking_obj, data_dict.get('service_charges'))
            data_dict.update(gst_metrics)
            data_dict.update(
                reimbursement_amount=financial_obj.total_cost_price + kwargs.get('provider_cancellation_charges', 0))
            data_dict.update(scratch_card_amount=kwargs.get('scratch_card_amount', 0))
            data_dict.update(approved_discount=financial_obj.approved_discount)
            data_dict.update(invoice_amount=abs(round(kwargs.get('travelsupply_cancellation_charges', 0) +
                                                      kwargs.get('provider_cancellation_charges', 0) -
                                                      kwargs.get('scratch_card_amount', 0), 2)))
        else:
            data_dict.update(
                service_charges=calculate_service_charge_for_invoice(data_dict.get('total_service_charges_with_tax')))
            gst_metrics = get_gst_metrics_for_invoice(booking_obj, data_dict.get('service_charges'))
            data_dict.update(gst_metrics)
            data_dict.update(description_of_reimbursement=get_description_of_reimbursement_for_invoice(booking_obj))
            data_dict.update(reimbursement_amount=get_reimbursement_amount_for_booking(booking_obj))
            data_dict.update(approved_discount=calculate_total_approved_discount(booking_obj))
            data_dict.update(
                invoice_amount=data_dict.get('reimbursement_amount') + data_dict.get('total_service_charges_with_tax')
                               - data_dict.get('scratch_card_amount') - data_dict.get('approved_discount'))
        return data_dict
    return None


def calculate_service_charge_for_reimbursement_invoice(booking_obj):
    if hasattr(booking_obj, 'booking_financial'):
        return abs(
            booking_obj.booking_financial.gross_profit) + booking_obj.booking_financial.approved_discount
    return 0


def calculate_total_service_charges_with_tax_for_reimbursement_invoice(booking_obj):
    if hasattr(booking_obj, 'booking_financial'):
        return round(abs(booking_obj.booking_financial.gross_profit), 2)
    return 0


def calculate_invoice_amount_for_reimbursement_invoice(booking_obj):
    if hasattr(booking_obj, 'booking_financial'):
        return round((booking_obj.booking_financial.total_cost_price -
                      abs(booking_obj.booking_financial.gross_profit) -
                      booking_obj.booking_financial.approved_discount), 2)
    return 0


def get_company_dict_object_for_invoice_generation_from_company_name():
    return  dict(
        COMPANY_NAME=settings.TSPL_COMPANY_NAME,
        COMPANY_FULL_NAME=settings.TSPL_COMPANY_FULL_NAME,
        REGISTERED_ADDRESS=settings.TSPL_REGISTERED_ADDRESS,
        CORPORATE_ADDRESS=settings.TSPL_CORPORATE_ADDRESS,
        SPOC_NAME=settings.TSPL_SPOC_NAME,
        SPOC_EMAIL=settings.TSPL_SPOC_EMAIL,
        SPOC_PHONE=settings.TSPL_SPOC_PHONE,
        ACCOUNT_NAME=settings.TSPL_ACCOUNT_NAME,
        NAME_OF_BANK=settings.TSPL_NAME_OF_BANK,
        BANK_ADDRESS=settings.TSPL_BANK_ADDRESS,
        BANK_ACCOUNT_NUMBER=settings.TSPL_BANK_ACCOUNT_NUMBER,
        IFSC_CODE=settings.TSPL_IFSC_CODE,
        GSTIN=settings.TSPL_GSTIN,
        PAN=settings.TSPL_PAN,
        WEBSITE=settings.TSPL_WEBSITE,
        FOOTER_TEXT=settings.TSPL_FOOTER,
        CIN=settings.TSPL_CIN,
    )

def create_automated_invoice(booking_object, created_by_id: int, **kwargs):
    booking_financial_obj = None
    booking_financial_obj = booking_object.booking_financial

    if booking_financial_obj.gross_profit > 0:
        invoice_obj = create_tax_invoice(booking_object.id, created_by_id,
                                         **{'member_code': kwargs.get('member_code')})

    else:
        invoice_obj = create_reimbursement_invoice(booking_object.id, created_by_id,
                                                   **{'member_code': kwargs.get('member_code')})

    return invoice_obj


def create_invoice(booking_id: int, created_by_id: int, **kwargs):
    booking_obj = bookings.get_booking_object_from_id(booking_id)
    if booking_obj.type_id in [settings.BOOKING_TYPE_FLIGHT_ID,
                               settings.BOOKING_TYPE_OWN_SUPPLY]:
        return create_automated_invoice(booking_obj, created_by_id, **{'is_invoice_beta': kwargs.get(
            'is_invoice_beta'), 'member_code': booking_obj.buyer.code})
    return None


def get_initial_form_data_for_remit_invoice(booking_id: int):
    booking_obj = Booking.objects.get(id=booking_id)

    if hasattr(booking_obj.buyer_organization,
               'company_details') and booking_obj.buyer_organization.company_details.state and booking_obj.buyer_organization.company_details.state.id == settings.DELHI_STATE_ID:
        default_gst = DEFAULT_GST_DELHI
    else:
        default_gst = DEFAULT_GST_INDIA

    return {'igst_percentage_on_service_charges': default_gst[IGST],
            'sgst_percentage_on_service_charges': default_gst[SGST],
            'cgst_percentage_on_service_charges': default_gst[CGST],
            'description_of_service_charges': settings.DEFAULT_SERVICE_DESCRIPTION,
            'sac_code_service': settings.DEFAULT_SAC_CODE_FOR_REMIT_TAX_INVOICE,
            'reimbursement_amount': get_default_reimbursement_amount_from_booking_obj(booking_obj),
            'description_of_reimbursement': get_default_description_of_reimbursement(booking_obj),
            'service_charges': get_default_service_charges_from_booking_obj(booking_obj)}


def validate_booking_invoice_object(booking_id):
    booking_obj = get_booking_object_from_id(booking_id)

    if booking_obj.agent_collection_entity_id != settings.TS_INDIA_TRAVEL_SUPPLY_GROUP_ENTITY:
        return "<br><strong>The Agent Collection Entity Should be Travel Supply India for the Booking.</strong></br>", False

    error_message, is_valid = booking_validator.validate_member_organization_details_for_invoice(booking_obj)
    if is_valid:
        return None, True
    return '<br>Errors Message : {}<br>'.format(error_message), False


def check_invoice_type(invoice_number):
    if invoice_number.startswith(settings.TRANSACTION_INVOICE.get('code')):
        return True
    return False


def validate_booking_invoice_request(booking_id):
    booking_obj = get_booking_object_from_id(booking_id)

    if hasattr(booking_obj, 'agent_collection_entity_id'):
        if getattr(booking_obj, 'agent_collection_entity_id') != settings.TC_INDIA_TRAVEL_SUPPLY_GROUP_ENTITY:
            return "Agent colleciton Entity should be TC India for Booking.", False

    error_message, is_valid = booking_validator.validate_invoice_generation_request(booking_obj)
    if is_valid:
        if not hasattr(booking_obj,'booking_financial'):
            return "Booking Financial Summary  Details Are Missing", False
        return None, True
    return '<br>Errors Message : {}<br>'.format(error_message), False


def create_transaction_invoice_for_manual_bookings(booking_obj):
    transaction_invoice_obj = get_transaction_invoice_obj_from_booking(booking_obj)
    gross_profit = get_gross_profit_by_booking_obj(booking_obj)
    if transaction_invoice_obj:
        is_tax_invoice = check_invoice_type(transaction_invoice_obj.tax_invoice_number)
        if gross_profit > 0 and is_tax_invoice:
            return transaction_invoice_obj
    else:
        if gross_profit > 0:
            data = create_tax_invoice_data(booking_obj, 1)

        else:
            data = create_reimbursement_invoice_data(booking_obj, 1)
        transaction_invoice_serializer = BookingInvoiceSerializer(data=data)
        if transaction_invoice_serializer.is_valid():
            obj = transaction_invoice_serializer.save()
            return obj
        else:
            print(transaction_invoice_serializer.errors)
            return None


def get_gross_profit_by_booking_obj(booking_obj):
    return booking_obj.booking_financial.gross_profit or 0

def create_invoice_pdf(transaction_invoice_obj, booking_obj, **kwargs):
    address_obj = booking_obj.buyer_organization.addresses.last()
    company_obj = booking_obj.buyer_organization.organization_details
    template_url = 'tax_invoice/base.html'
    context = {'instance': transaction_invoice_obj,
               'COMPANY_DICT': get_company_dict_object_for_invoice_generation_from_company_name(),
               'address_obj': address_obj,
               'company_obj': company_obj, 'company_logo': settings.INVOICE_LOGO_URL,
               'invoice_date': get_invoice_date_for_invoice_generation(transaction_invoice_obj).strftime(
                   "%^B %d %Y") if isinstance(
                   get_invoice_date_for_invoice_generation(transaction_invoice_obj), datetime.date) else "",
               'ack_date': kwargs.get('ack_date', None),
               'ack_no': kwargs.get('ack_no', None),
               'is_booking_version_type_v2': booking_obj.booking_version_type == Booking.V2,
               'gstin_invalid': kwargs.get('gstin_invalid', False, ),
               'is_cancellation_invoice': kwargs.get('is_cancellation_invoice'),
               'cancellation_invoice_delta_record': kwargs.get('cancellation_invoice_delta_record')}

    booking_financial_v2_obj = get_booking_financial_v2_by_booking_id(booking_obj.id)
    if booking_financial_v2_obj:
        context.update({
            'total_cost_price': booking_financial_v2_obj.approved_discount,
            'tcs': booking_financial_v2_obj.tcs
        })
    if kwargs.get('is_cancellation_invoice'):
        cancellation_invoice_delta_record = kwargs.get('cancellation_invoice_delta_record')
        context.update(total_amount=cancellation_invoice_delta_record.total_service_charges_with_tax -
                                    cancellation_invoice_delta_record.approved_discount +
                                    cancellation_invoice_delta_record.scratch_card_amount)
        if kwargs.get('travelsupply_cancellation_charges') != 0:
            if booking_obj.type_id == settings.BOOKING_TYPE_FLIGHT_ID:
                template_url = 'tax_invoice/flight/flight_v2.html' if settings.CURRENT_INVOICE_VERSION == settings.INVOICE_VERSION_V2 else 'tax_invoice/flight/flight.html'
                flight_v2_url = 'tax_invoice/flight/flight_v2.html'
            elif booking_obj.type_id == settings.BOOKING_TYPE_OWN_SUPPLY:
                template_url = 'tax_invoice/own_supply/own_supply.html'
        else:
            if booking_obj.type_id == settings.BOOKING_TYPE_FLIGHT_ID:
                template_url = 'reimbursement_note/flight/flight_v2.html' if settings.CURRENT_INVOICE_VERSION == settings.INVOICE_VERSION_V2 else 'reimbursement_note/flight/flight.html'
                flight_v2_url = 'reimbursement_note/flight/flight_v2.html'
            elif booking_obj.type_id == settings.BOOKING_TYPE_OWN_SUPPLY:
                template_url = 'reimbursement_note/own_supply/own_supply.html'
    else:
        if  (
                hasattr(booking_obj,
                        'booking_financial')  and booking_obj.booking_financial.gross_profit > 0):
            context.update(total_amount=transaction_invoice_obj.total_service_charges_with_tax - (
                transaction_invoice_obj.approved_discount if transaction_invoice_obj.approved_discount else 0))
            if booking_obj.type_id == settings.BOOKING_TYPE_FLIGHT_ID:
                template_url = 'tax_invoice/flight/flight_v2.html' if settings.CURRENT_INVOICE_VERSION == settings.INVOICE_VERSION_V2 else 'tax_invoice/flight/flight.html'
                flight_v2_url = 'tax_invoice/flight/flight_v2.html'
            elif booking_obj.type_id == settings.BOOKING_TYPE_OWN_SUPPLY:
                template_url = 'tax_invoice/own_supply/own_supply.html'
        else:
            context.update(total_amount=transaction_invoice_obj.approved_discount)
            if booking_obj.type_id == settings.BOOKING_TYPE_FLIGHT_ID:
                template_url = 'reimbursement_note/flight/flight_v2.html' if settings.CURRENT_INVOICE_VERSION == settings.INVOICE_VERSION_V2 else 'reimbursement_note/flight/flight.html'
                flight_v2_url = 'reimbursement_note/flight/flight_v2.html'
            elif booking_obj.type_id == settings.BOOKING_TYPE_OWN_SUPPLY:
                template_url = 'reimbursement_note/own_supply/own_supply.html'
        return flight_v2_url, context
    filename = "{}_{}_{}.pdf".format(transaction_invoice_obj.tax_invoice_number, transaction_invoice_obj.bookings.id,
                                     transaction_invoice_obj.id)
    pdf_url = render_and_upload_pdf(template_url, context, filename)
    if kwargs.get('booking_document_id'):
        booking_doc_obj = get_booking_document_by_booking_document_id(kwargs.get('booking_document_id'))
        booking_doc_obj.file = pdf_url
        booking_doc_obj.save()
    transaction_invoice_obj.document_path = pdf_url
    transaction_invoice_obj.save()
    return transaction_invoice_obj


def create_cancellation_automated_invoice(booking_obj, created_by_id, cancellation_invoice_delta_record, **kwargs):
    kwargs.update(member_code=booking_obj.buyer.code)
    kwargs.update(is_cancellation_invoice=True)
    if kwargs.get('travelsupply_cancellation_charges') > 0:
        kwargs.update(invoice_type=settings.TRANSACTION_INVOICE_TYPE__CANCELLATION_TAX_INVOICE)
        invoice_obj = create_tax_cancellation_invoice(booking_obj.id, created_by_id, cancellation_invoice_delta_record,
                                                      **kwargs)

    elif kwargs.get('travelsupply_cancellation_charges') == 0:
        kwargs.update(invoice_type=settings.TRANSACTION_INVOICE_TYPE__CANCELLATION_REIMBURSEMENT_INVOICE)
        invoice_obj = create_reimbursement_cancellation_invoice(booking_obj.id, created_by_id,
                                                                cancellation_invoice_delta_record, **kwargs)

    else:
        return None
    return invoice_obj


def create_tax_cancellation_invoice(booking_id, created_by_id, cancellation_invoice_delta_record, **kwargs):
    master_gst_response_data = None
    gstin_invalid = False
    booking_obj = bookings.get_booking_object_from_id(booking_id)
    kwargs.update(invoice_type=settings.TRANSACTION_INVOICE_TYPE__CANCELLATION_TAX_INVOICE)
    data = create_tax_invoice_data(booking_obj, created_by_id, **kwargs)
    if kwargs.get('cancellation_type_value') == FULL_CANCELLATION:
        transaction_invoice_obj = get_transaction_invoice_obj_from_booking(booking_obj,
                                                                           invoice_type=settings.TRANSACTION_INVOICE_TYPE__CANCELLATION_TAX_INVOICE)
        if transaction_invoice_obj:
            is_tax_invoice = check_invoice_type(transaction_invoice_obj.tax_invoice_number)
            if is_tax_invoice and is_einvoice_valid and e_invoice_switch and (
                    not transaction_invoice_obj.invoice_reference_number or not transaction_invoice_obj.qr_code or not transaction_invoice_obj.document_path):
                invoice_date = get_invoice_date_for_invoice_generation(transaction_invoice_obj).strftime("%d/%m/%Y")
                master_gst_response_data, gstin_invalid = master_gst.generate_e_invoice_data(data, booking_obj,
                                                                                             invoice_date,
                                                                                             delta_record=cancellation_invoice_delta_record)
                transaction_invoice_obj.is_einvoice = True
                if master_gst_response_data:
                    transaction_invoice_obj.invoice_reference_number = master_gst_response_data.get(
                        'invoice_reference_number')
                    transaction_invoice_obj.qr_code = master_gst_response_data.get('qr_code')
                    transaction_invoice_obj.ack_date = master_gst_response_data.get('ack_date')
                    transaction_invoice_obj.ack_no = master_gst_response_data.get('ack_no')
                    transaction_invoice_obj.save()
                    cancellation_invoice_delta_record.invoice = transaction_invoice_obj
                    cancellation_invoice_delta_record.save()
            message, is_valid = validate_booking_invoice_object(booking_id)
            kwargs.update(cancellation_invoice_delta_record=cancellation_invoice_delta_record)
            if is_tax_invoice and is_valid and is_einvoice_valid:
                return create_e_invoice_pdf(e_invoice_switch, gstin_invalid, transaction_invoice_obj,
                                            master_gst_response_data, booking_obj, **kwargs)
            elif is_valid:
                if transaction_invoice_obj.is_einvoice:
                    transaction_invoice_obj.is_einvoice = False
                    transaction_invoice_obj.save()
                    cancellation_invoice_delta_record.invoice = transaction_invoice_obj
                    cancellation_invoice_delta_record.save()
                kwargs.update(cancellation_invoice_delta_record=cancellation_invoice_delta_record)
                return create_invoice_pdf(transaction_invoice_obj, booking_obj, **kwargs)
            return transaction_invoice_obj
    if is_einvoice_valid and e_invoice_switch:
        master_gst_response_data, gstin_invalid = master_gst.generate_e_invoice_data(data, booking_obj, None,
                                                                                     delta_record=cancellation_invoice_delta_record)
        if master_gst_response_data:
            data.update(master_gst_response_data)
        data.update(is_einvoice=True)
    serializer_obj = TransactionInvoicesSerializer(data=data)
    if serializer_obj.is_valid():
        transaction_invoice_obj = serializer_obj.save()
        transaction_invoice_obj.save()
        cancellation_invoice_delta_record.invoice = transaction_invoice_obj
        cancellation_invoice_delta_record.save()
        booking_doc_obj = booking_document.create_booking_document(
            booking_id=booking_id,
            created_by_id=created_by_id,
            name=transaction_invoice_obj.invoice_type + " - " + transaction_invoice_obj.tax_invoice_number,
            delivery_date=datetime.datetime.now(),
            category_id=booking_obj.category.id,
            status=BookingDocument.ACTIVE,
            document_type=BookingDocument.CANCELLATION_INVOICE
        )
        if booking_doc_obj:
            kwargs.update(booking_document_id=booking_doc_obj.id)
        message, is_valid = validate_booking_invoice_object(booking_id)
        kwargs.update(cancellation_invoice_delta_record=cancellation_invoice_delta_record)
        if is_valid and is_einvoice_valid:
            return create_e_invoice_pdf(e_invoice_switch, gstin_invalid, transaction_invoice_obj,
                                        master_gst_response_data, booking_obj, **kwargs)
        elif is_valid:
            return create_invoice_pdf(transaction_invoice_obj, booking_obj, **kwargs)
    return None


def create_reimbursement_cancellation_invoice(booking_id, created_by_id, cancellation_invoice_delta_record, **kwargs):
    booking_obj = bookings.get_booking_object_from_id(booking_id)
    kwargs.update(invoice_type=settings.TRANSACTION_INVOICE_TYPE__CANCELLATION_REIMBURSEMENT_INVOICE)
    data = create_reimbursement_invoice_data(booking_obj, created_by_id, **kwargs)
    kwargs.update(cancellation_invoice_delta_record=cancellation_invoice_delta_record)
    if kwargs.get('cancellation_type_value') == FULL_CANCELLATION:
        transaction_invoice_obj = get_transaction_invoice_obj_from_booking(booking_obj,
                                                                           invoice_type=settings.TRANSACTION_INVOICE_TYPE__CANCELLATION_REIMBURSEMENT_INVOICE)
        if transaction_invoice_obj:
            message, is_valid = validate_booking_invoice_object(booking_id)
            if is_valid:
                return create_invoice_pdf(transaction_invoice_obj, booking_obj, **kwargs)
            return transaction_invoice_obj
    serializer_obj = TransactionInvoicesSerializer(data=data)
    if serializer_obj.is_valid():
        transaction_invoice_obj = serializer_obj.save()
        cancellation_invoice_delta_record.invoice = transaction_invoice_obj
        cancellation_invoice_delta_record.save()
        booking_doc_obj = booking_document.create_booking_document(
            booking_id=booking_id,
            created_by_id=created_by_id,
            name=transaction_invoice_obj.invoice_type + " - " + transaction_invoice_obj.tax_invoice_number,
            delivery_date=datetime.datetime.now(),
            category_id=booking_obj.category.id,
            status=BookingDocument.ACTIVE,
            document_type=BookingDocument.CANCELLATION_INVOICE
        )
        if booking_doc_obj:
            kwargs.update(booking_document_id=booking_doc_obj.id)
        message, is_valid = validate_booking_invoice_object(booking_id)
        if is_valid:
            return create_invoice_pdf(transaction_invoice_obj, booking_obj, **kwargs)
        return transaction_invoice_obj
    return None


def create_cn_dn_data_for_delta_record(booking_obj, **kwargs):
    reimbursement_amount = round(kwargs.get('reimbursement_amount', 0), 2)
    total_service_charges_with_tax = round(kwargs.get('service_charges', 0), 2)
    discount = round(kwargs.get('discount', 0), 2)
    data_dict = dict(
        booking_id=booking_obj.id,
        reimbursement_amount=abs(reimbursement_amount),
        total_service_charges_with_tax=abs(total_service_charges_with_tax),
        approved_discount=abs(discount),
        invoice_type=kwargs.get('invoice_type'),
        scratch_card_amount=0,
        igst_amount_on_service_charges=0,
        cgst_amount_on_service_charges=0,
        sgst_amount_on_service_charges=0,
    )
    data_dict.update(
        service_charges=calculate_service_charge_for_invoice(data_dict.get('total_service_charges_with_tax')))
    if data_dict.get('total_service_charges_with_tax') != 0:
        if booking_obj.buyer_organization.organization_details.state.id == settings.DELHI_STATE_ID:
            data_dict.update({'cgst_amount_on_service_charges': round(
                data_dict.get('service_charges', 0) * settings.CGST_FACTOR_FOR_DEFAULT_SERVICE_CHARGE, 2)})
            data_dict.update({'sgst_amount_on_service_charges': round(
                data_dict.get('service_charges', 0) * settings.SGST_FACTOR_FOR_DEFAULT_SERVICE_CHARGE, 2)})
        else:
            data_dict.update({'igst_amount_on_service_charges': round(
                data_dict.get('service_charges', 0) * settings.IGST_FACTOR_FOR_DEFAULT_SERVICE_CHARGE, 2)})
    data_dict.update(invoice_amount=round(abs(reimbursement_amount + total_service_charges_with_tax
                                              - data_dict.get('scratch_card_amount') - discount), 2))
    return data_dict


def create_cn_dn_delta_record(booking_id, **kwargs):
    booking_obj = bookings.get_booking_object_from_id(booking_id)
    data = create_cn_dn_data_for_delta_record(booking_obj, **kwargs)
    serializer_obj = InvoicesDeltaRecordSerializer(data=data)
    if serializer_obj.is_valid():
        delta_record_obj = serializer_obj.save()
        delta_record_obj.save()
        return delta_record_obj
    return None


def create_cn_dn_data(booking_obj, created_by_id, **kwargs):
    financial_obj = booking_obj.latest_booking_financials
    if financial_obj:
        reimbursement_amount = round(kwargs.get('reimbursement_amount', 0), 2)
        service_charges = round(kwargs.get('service_charges', 0), 2)
        discount = round(kwargs.get('discount', 0), 2)
        data_dict = dict(
            booking_id=booking_obj.id,
            description_of_service_charges='-',
            sac_code_service=settings.DEFAULT_SAC_CODE,
            created_by_id=created_by_id,
            reimbursement_amount=financial_obj.total_cost_price + reimbursement_amount,
            total_service_charges_with_tax=financial_obj.gross_profit + service_charges,
            approved_discount=financial_obj.approved_discount + discount,
            description_of_reimbursement=kwargs.get('description_of_invoice_note'),
            invoice_type=kwargs.get('invoice_type'),
            scratch_card_amount=financial_obj.scratch_card_amount,
            igst_percentage_on_service_charges=0,
            igst_amount_on_service_charges=0,
            cgst_percentage_on_service_charges=0,
            cgst_amount_on_service_charges=0,
            sgst_percentage_on_service_charges=0,
            sgst_amount_on_service_charges=0,
        )
        data_dict.update(
            service_charges=calculate_service_charge_for_invoice(data_dict.get('total_service_charges_with_tax')))
        if data_dict.get('total_service_charges_with_tax') != 0:
            amount_and_tax_metrics = get_gst_metrics_for_invoice(booking_obj, data_dict.get('service_charges', 0))
            data_dict.update(amount_and_tax_metrics)
        kwargs.update(is_invoice_note=True)
        kwargs.update(total_service_charges_with_tax=data_dict.get('total_service_charges_with_tax'))
        kwargs.update(service_charges=service_charges)
        kwargs.update(is_credit_note=kwargs.get('is_credit_note'))
        kwargs.update(is_debit_note=kwargs.get('is_debit_note'))
        data_dict.update(
            tax_invoice_number=booking_invoice_config.get_booking_invoice_number_by_booking_object(booking_obj,
                                                                                                   **kwargs))
        data_dict.update(invoice_amount=round(abs(reimbursement_amount + service_charges +
                                                  data_dict.get('scratch_card_amount') - discount), 2))
        return data_dict
    return None


def create_cn_dn(booking_id, created_by_id, cn_dn_delta_record, **kwargs):
    kwargs.update(invoice_type=kwargs.get('invoice_type'))
    kwargs.update(description_of_invoice_note=kwargs.get("description_of_invoice_note"))
    booking_obj = bookings.get_booking_object_from_id(booking_id)
    data = create_cn_dn_data(booking_obj, created_by_id, **kwargs)
    is_einvoice_valid, e_invoice_switch = master_gst.validate_booking_obj_to_create_e_invoice(booking_obj)
    master_gst_response_data, gstin_invalid = None, False
    if kwargs.get('service_charges') != 0:
        if is_einvoice_valid and e_invoice_switch:
            master_gst_response_data, gstin_invalid = master_gst.generate_e_invoice_data(data, booking_obj, None,
                                                                                         delta_record=cn_dn_delta_record,
                                                                                         is_credit_note=kwargs.get(
                                                                                             'is_credit_note'),
                                                                                         is_debit_note=kwargs.get(
                                                                                             'is_debit_note'))
            if master_gst_response_data:
                data.update(master_gst_response_data)
            data.update(is_einvoice=True)
    serializer_obj = TransactionInvoicesSerializer(data=data)
    if serializer_obj.is_valid():
        transaction_invoice_obj = serializer_obj.save()
        transaction_invoice_obj.save()
        cn_dn_delta_record.invoice = transaction_invoice_obj
        cn_dn_delta_record.save()
        booking_doc_obj = booking_document.create_booking_document(
            booking_id=booking_id,
            created_by_id=created_by_id,
            name=transaction_invoice_obj.invoice_type + " - " + transaction_invoice_obj.tax_invoice_number,
            delivery_date=datetime.datetime.now(),
            category_id=booking_obj.category.id,
            status=BookingDocument.ACTIVE,
            document_type=BookingDocument.CREDIT_NOTE if kwargs.get('is_credit_note') else BookingDocument.DEBIT_NOTE
        )
        if booking_doc_obj:
            kwargs.update(booking_document_id=booking_doc_obj.id)
        message, is_valid = validate_booking_invoice_object(booking_id)
        if is_valid and is_einvoice_valid and kwargs.get('service_charges') != 0:
            return create_e_invoice_cn_dn_pdf(e_invoice_switch, gstin_invalid, transaction_invoice_obj,
                                              master_gst_response_data, booking_obj, cn_dn_delta_record, **kwargs)
        elif is_valid:
            return create_cn_dn_pdf(transaction_invoice_obj, booking_obj, cn_dn_delta_record, **kwargs)
    return None


def create_e_invoice_cn_dn_pdf(e_invoice_switch, gstin_invalid, transaction_invoice_obj,
                               master_gst_response_data, booking_obj, cn_dn_delta_record, **kwargs):
    if not e_invoice_switch:
        transaction_invoice_obj.is_einvoice = True
        transaction_invoice_obj.save()
        return transaction_invoice_obj
    if master_gst_response_data:
        return create_cn_dn_pdf(transaction_invoice_obj, booking_obj, cn_dn_delta_record, **kwargs)
    if gstin_invalid:
        transaction_invoice_obj.is_einvoice = False
        transaction_invoice_obj.save()
        return create_cn_dn_pdf(transaction_invoice_obj, booking_obj, cn_dn_delta_record,
                                **{'gstin_invalid': gstin_invalid, **kwargs})
    else:
        return transaction_invoice_obj


def create_cn_dn_pdf(transaction_invoice_obj, booking_obj, cn_dn_delta_record, **kwargs):
    address_obj = booking_obj.buyer_organization.addresses.last()
    company_obj = booking_obj.buyer_organization.organization_details
    template_url = 'cn_dn/base.html'

    debit_details = dict()
    credit_details = dict()
    total_debit_amount = total_credit_amount = 0
    if kwargs.get('reimbursement_amount') and kwargs.get('reimbursement_amount') < 0:
        credit_details.update(reimbursement_amount=cn_dn_delta_record.reimbursement_amount)
        total_credit_amount += cn_dn_delta_record.reimbursement_amount
    elif kwargs.get('reimbursement_amount') != 0:
        total_debit_amount += cn_dn_delta_record.reimbursement_amount
        debit_details.update(reimbursement_amount=cn_dn_delta_record.reimbursement_amount)

    if kwargs.get('service_charges') < 0:
        total_credit_amount += cn_dn_delta_record.total_service_charges_with_tax
        credit_details.update(service_charges=cn_dn_delta_record.service_charges)
        credit_details.update(igst_amount_on_service_charges=cn_dn_delta_record.igst_amount_on_service_charges)
        credit_details.update(cgst_amount_on_service_charges=cn_dn_delta_record.cgst_amount_on_service_charges)
        credit_details.update(sgst_amount_on_service_charges=cn_dn_delta_record.sgst_amount_on_service_charges)
    elif kwargs.get('service_charges') != 0:
        total_debit_amount += cn_dn_delta_record.total_service_charges_with_tax
        debit_details.update(service_charges=cn_dn_delta_record.service_charges)
        debit_details.update(igst_amount_on_service_charges=cn_dn_delta_record.igst_amount_on_service_charges)
        debit_details.update(cgst_amount_on_service_charges=cn_dn_delta_record.cgst_amount_on_service_charges)
        debit_details.update(sgst_amount_on_service_charges=cn_dn_delta_record.sgst_amount_on_service_charges)

    if kwargs.get('discount') < 0:
        total_debit_amount += cn_dn_delta_record.approved_discount
        debit_details.update(approved_discount=cn_dn_delta_record.approved_discount)
    elif kwargs.get('discount') != 0:
        total_credit_amount += cn_dn_delta_record.approved_discount
        credit_details.update(approved_discount=cn_dn_delta_record.approved_discount)
    context = {'instance': transaction_invoice_obj,
               'COMPANY_DICT': get_company_dict_object_for_invoice_generation_from_company_name(
                   settings.TRAVEL_SUPPLY_TECHNOLOGY_INDIA_PVT_LTD),
               'address_obj': address_obj,
               'company_obj': company_obj, 'company_logo': settings.INVOICE_LOGO_URL,
               'invoice_date': get_invoice_date_for_invoice_generation(transaction_invoice_obj).strftime(
                   "%^B %d %Y") if isinstance(
                   get_invoice_date_for_invoice_generation(transaction_invoice_obj), datetime.date) else "",
               'ack_date': kwargs.get('ack_date', None),
               'ack_no': kwargs.get('ack_no', None),
               'gstin_invalid': kwargs.get('gstin_invalid', False),
               'type_of_invoice_note': kwargs.get('description_of_invoice_note'),
               'debit_details': debit_details,
               'credit_details': credit_details,
               'net_total': abs(cn_dn_delta_record.invoice_amount),
               'extra_content_debit_details': [1] * (len(credit_details) - len(debit_details)) if (
                                                                                                          len(credit_details) - len(
                                                                                                      debit_details)) > 0 else None,
               'extra_content_credit_details': [1] * (len(debit_details) - len(credit_details)) if (
                                                                                                           len(debit_details) - len(
                                                                                                       credit_details)) > 0 else None,
               'total_debit_amount': total_debit_amount,
               'total_credit_amount': total_credit_amount
               }
    filename = "{}_{}_{}.pdf".format(transaction_invoice_obj.tax_invoice_number, transaction_invoice_obj.bookings.id,
                                     transaction_invoice_obj.id)
    pdf_url = render_and_upload_pdf(template_url, context, filename)
    transaction_invoice_obj.document_path = pdf_url
    transaction_invoice_obj.save()
    if kwargs.get('booking_document_id'):
        booking_doc_obj = get_booking_document_by_booking_document_id(kwargs.get('booking_document_id'))
        booking_doc_obj.file = pdf_url
        booking_doc_obj.save()
    return transaction_invoice_obj


def create_invoice_delta_record(booking_obj, **kwargs):
    if kwargs.get('travelsupply_cancellation_charges') > 0:
        invoice_obj = create_tax_cancellation_delta_record(booking_obj.id, **kwargs)
    elif kwargs.get('travelsupply_cancellation_charges') == 0:
        invoice_obj = create_reimbursement_cancellation_delta_record(booking_obj.id, **kwargs)
    else:
        return None
    return invoice_obj


def create_tax_cancellation_delta_record_data(booking_obj, **kwargs):
    data = dict(
        booking_id=booking_obj.id,
        igst_amount_on_service_charges=0,
        cgst_amount_on_service_charges=0,
        sgst_amount_on_service_charges=0,
        scratch_card_amount=0,
        approved_discount=0,
        invoice_amount=0,
    )
    data.update(total_service_charges_with_tax=abs(kwargs.get('travelsupply_cancellation_charges', 0)))
    data.update(reimbursement_amount=abs(kwargs.get('provider_cancellation_charges', 0)))
    data.update(scratch_card_amount=abs(kwargs.get('scratch_card_amount', 0)))
    data.update(service_charges=calculate_service_charge_for_invoice(data.get('total_service_charges_with_tax', 0)))
    if booking_obj.buyer_organization.organization_details.state.id == settings.DELHI_STATE_ID:
        data.update({'cgst_amount_on_service_charges': round(data.get('service_charges', 0) *
                                                             settings.CGST_FACTOR_FOR_DEFAULT_SERVICE_CHARGE, 2)})
        data.update({'sgst_amount_on_service_charges': round(data.get('service_charges', 0) *
                                                             settings.SGST_FACTOR_FOR_DEFAULT_SERVICE_CHARGE, 2)})
    else:
        data.update({'igst_amount_on_service_charges': round(data.get('service_charges', 0) *
                                                             settings.IGST_FACTOR_FOR_DEFAULT_SERVICE_CHARGE, 2)})
    data.update({'invoice_amount': round(data.get('total_service_charges_with_tax') +
                                         data.get('reimbursement_amount') +
                                         data.get('scratch_card_amount') +
                                         data.get('approved_discount'), 2)})
    return data


def create_tax_cancellation_delta_record(booking_id, **kwargs):
    booking_obj = bookings.get_booking_object_from_id(booking_id)
    data = create_tax_cancellation_delta_record_data(booking_obj, **kwargs)
    serializer_obj = InvoicesDeltaRecordSerializer(data=data)
    if serializer_obj.is_valid():
        delta_record_obj = serializer_obj.save()
        return delta_record_obj
    return None


def create_reimbursement_cancellation_delta_record_data(booking_obj, **kwargs):
    data_dict = dict(
        booking_id=booking_obj.id,
        approved_discount=0,
        scratch_card_amount=0,
        total_service_charges_with_tax=0,
        service_charges=0
    )
    data_dict.update(reimbursement_amount=abs(kwargs.get('provider_cancellation_charges', 0)))
    data_dict.update(scratch_card_amount=abs(kwargs.get('scratch_card_amount', 0)))
    data_dict.update(
        invoice_amount=data_dict.get('reimbursement_amount') + data_dict.get('total_service_charges_with_tax')
                       + data_dict.get('scratch_card_amount') - data_dict.get('approved_discount'))
    return data_dict


def create_reimbursement_cancellation_delta_record(booking_id, **kwargs):
    booking_obj = bookings.get_booking_object_from_id(booking_id)
    data = create_reimbursement_cancellation_delta_record_data(booking_obj, **kwargs)
    serializer_obj = InvoicesDeltaRecordSerializer(data=data)
    if serializer_obj.is_valid():
        delta_record_obj = serializer_obj.save()
        return delta_record_obj
    return None


def check_if_cancellation_for_booking_exists(booking_id, **kwargs):
    try:
        if TransactionInvoices.objects.filter(booking_id=booking_id,
                                              invoice_type__in=[TRANSACTION_INVOICE_TYPE__CANCELLATION_TAX_INVOICE,
                                                                TRANSACTION_INVOICE_TYPE__CANCELLATION_REIMBURSEMENT_INVOICE],
                                              **kwargs).exists():
            return True
        return False
    except:
        return False


def get_gst_metrics_for_invoice(booking_obj, service_charges):
    data = dict()
    if booking_obj.buyer_organization.organization_details.state.id == settings.DELHI_STATE_ID:
        data.update({'cgst_percentage_on_service_charges': DEFAULT_GST_DELHI.get('cgst')})
        data.update({'cgst_amount_on_service_charges': round(
            service_charges * settings.CGST_FACTOR_FOR_DEFAULT_SERVICE_CHARGE, 2)})
        data.update({'sgst_percentage_on_service_charges': DEFAULT_GST_DELHI.get('sgst')})
        data.update({'sgst_amount_on_service_charges': round(
            service_charges * settings.SGST_FACTOR_FOR_DEFAULT_SERVICE_CHARGE, 2)})
    else:
        data.update({'igst_amount_on_service_charges': round(
            service_charges * settings.IGST_FACTOR_FOR_DEFAULT_SERVICE_CHARGE, 2)})
        data.update({'igst_percentage_on_service_charges': DEFAULT_GST_INDIA.get('igst')})
    return data
