from bms.enums import PENDING
from common.libraries import  render_and_upload_pdf
from bms.providers import invoice, bookings
from django.conf import settings
from bms.validators.booking import validate_invoice_generation_request
from bms.providers.invoice import validate_booking_invoice_object

def generate_invoice_pdf(invoice_obj, **kwargs):
    company_dict = invoice.get_company_dict_object_for_invoice_generation_from_company_name(
        settings.TRAVEL_SUPPLY_TECHNOLOGY_INDIA_PVT_LTD)
    address_obj = invoice_obj.bookings.buyer_organization.addresses.last()
    company_obj = invoice_obj.bookings.buyer_organization.organization_details
    context = {'instance': invoice_obj, 'COMPANY_DICT': company_dict, 'address_obj': address_obj,
               'company_obj': company_obj, 'company_logo': settings.INVOICE_LOGO_URL,
               'invoice_date': kwargs.get('invoice_date', ''),'gstin_invalid':kwargs.get('gstin_invalid',False)}
    filename = "{}_{}_{}.pdf".format(invoice_obj.tax_invoice_number, invoice_obj.bookings.id,
                                     invoice_obj.id)
    pdf_url = render_and_upload_pdf('tax_invoice/base.html', context, filename)
    invoice_obj.document_path = pdf_url
    invoice_obj.save()
    return invoice_obj


def get_default_reimbursement_amount_from_booking_obj(booking_obj):
    return invoice.get_default_reimbursement_amount_from_booking_obj(booking_obj)


def get_default_description_of_reimbursement(booking_obj):
    return invoice.get_default_description_of_reimbursement(booking_obj)


def get_invoice_date_for_invoice_generation(invoice_obj):
    return invoice.get_invoice_date_for_invoice_generation(invoice_obj)


def get_default_service_charges_from_booking_obj(booking_obj):
    return invoice.get_default_service_charges_from_booking_obj(booking_obj)


def create_tax_invoice_for_flight(booking_id, created_by):
    return invoice.create_tax_invoice_for_flight(booking_id, created_by)


def create_reimbursement_invoice_for_flight(booking_id, created_by):
    return invoice.create_reimbursement_invoice_for_flight(booking_id, created_by)


def create_flight_invoice(booking_object, created_by_id: int):
    return invoice.create_flight_invoice(booking_object, created_by_id)


def create_invoice(booking_id: int, created_by_id: int):
    return invoice.create_invoice(booking_id, created_by_id)

def upload_and_send_booking_invoice(invoice_id):

    pass


def send_booking_invoice_notification(invoice_id):

    pass


def get_initial_form_data_for_remit_invoice(booking_id: int):
    return invoice.get_initial_form_data_for_remit_invoice(booking_id)











def handle_create_remit_invoice_post_request(booking_obj, invoice_obj):
    error_message, is_valid = validate_booking_invoice_object(invoice_obj.bookings.id)
    if is_valid:
        gstin_invalid = False
        if invoice_obj.is_einvoice:
            is_envoice_valid, e_invoice_switch = master_gst.validate_booking_obj_to_create_e_invoice(booking_obj)
            if e_invoice_switch and (not invoice_obj.invoice_reference_number or not invoice_obj.qr_code or not invoice_obj.document_path):
                data = invoice.create_tax_invoice_data(booking_obj, 1)
                invoice_date = get_invoice_date_for_invoice_generation(invoice_obj).strftime("%d/%m/%Y")
                master_gst_response_data, gstin_invalid = master_gst.generate_e_invoice_data(data, booking_obj, invoice_date)
                if master_gst_response_data:
                    invoice_obj.invoice_reference_number = master_gst_response_data.get('invoice_reference_number')
                    invoice_obj.qr_code = master_gst_response_data.get('qr_code')
                    invoice_obj.ack_date = master_gst_response_data.get('ack_date')
                    invoice_obj.ack_no = master_gst_response_data.get('ack_no')
                    invoice_obj.save()
                    invoice_obj = generate_invoice_pdf(invoice_obj, invoice_date=get_invoice_date_for_invoice_generation(invoice_obj), gstin_invalid=gstin_invalid)
                if gstin_invalid:
                    invoice_obj.is_einvoice = False
                    invoice_obj.save()
        elif not invoice_obj.is_einvoice:
            invoice_obj = generate_invoice_pdf(invoice_obj,invoice_date=get_invoice_date_for_invoice_generation(invoice_obj), gstin_invalid=gstin_invalid)
        if invoice_obj.document_path:
            send_booking_invoice_notification(invoice_obj.id)
        return None, invoice_obj
    return error_message, invoice_obj


def create_transaction_invoice_for_manual_booking(booking_obj, **kwargs):
    if not (booking_obj.type_id == settings.BOOKING_TYPE_SAFE_ID or booking_obj.status == PENDING):
        error_message, is_valid = validate_invoice_generation_request(booking_obj)
        if is_valid:
            created_by_id = kwargs.get('created_by') if kwargs.get('created_by') else 1
            return invoice.create_automated_invoice(booking_obj, created_by_id)



def check_if_cancellation_for_booking_exists(booking_id, **kwargs):
    return invoice.check_if_cancellation_for_booking_exists(booking_id, **kwargs)
