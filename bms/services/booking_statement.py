from django.conf import settings
from datetime import datetime
import csv
from bms.services.booking_details import get_booking_details_by_booking_id
from bms.providers.booking_summary import get_amount_collected,get_amount_paid
from members.enums import BUYER, SELLER
from members.services import get_member_data_from_member_id, OrganizationServices
get_member_organization_by_member_id = OrganizationServices.get_organization_object_by_id
from common.services.microservice import upload_document_to_docs_microservice
from common.services import emails
import validators
from bms.providers import booking_statement
from common.libraries import get_date_from_given_str_format
from common.services.emails import create_file_attachement_array_from_documents_url



def generate_and_send_csv_file_for_booking_statement(member_id, booking_start_date, booking_end_date):
    document_url = generate_booking_statement_csv_file(
        member_id, booking_start_date, booking_end_date)
    booking_statement_obj = create_booking_statement(
        document_url=document_url, booking_start_date=booking_start_date,
        booking_end_date=booking_end_date,
        member_id=member_id,
        organization = get_member_organization_by_member_id(member_id)
    )
    send_booking_statement_email(booking_statement_obj)


def generate_booking_statement_csv_file(member_id, booking_start_date, booking_end_date):
    try:
        booking_list = booking_statement.get_bookings_within_booking_date_range_by_member_id(member_id,booking_start_date,booking_end_date)[0:settings.BOOKING_STATEMENT_RECORDS_MAXIMUM_ALLOWED_LIMIT]
        organization_obj = get_member_organization_by_member_id(member_id)
        member_obj = get_member_data_from_member_id(member_id)
        start_date = get_date_from_given_str_format(booking_start_date).strftime("%d %b %Y")
        end_date = get_date_from_given_str_format(booking_end_date).strftime("%d %b %Y")
        file = settings.TEMP_FILE_DIRECTORY +            "booking_statements/Booking_Ledger-{}-to-{}.csv".format(start_date,end_date)
        fieldnames = ['Booking Code', 'Booking Date', 'Category', 'Title', 'Lead Pax Name', 'Confirmation Number/PNR',
                    'Travel Date', 'Booking Status', 'Trip Amount', 'Invoice Number', 'Invoice Link',
                    'Amount Paid By Buyer', 'Amount Refunded To Buyer', 'Amount Released To Supplier', 'Refund Amount Paid By Supplier']
        with open(file, 'w+') as temp_file:
            booking_details = [
                ["Company Name", organization_obj.name],
                ["Member Code", member_obj.code],
                ["Company Code", organization_obj.code],
                ["Period", start_date + " to " + end_date],
                ["Currency", "INR"]
            ]
            temp_file.write("Booking Ledger\n")
            w = csv.writer(temp_file)
            w.writerows(booking_details)
            temp_file.write("\n")
            w.writerow(fieldnames)
            for booking in booking_list:
                booking_details_obj = get_booking_details_by_booking_id(booking.id)
                w.writerow(
                    [
                        booking.code,
                        booking.booking_date,
                        booking.category,
                        booking_details_obj.title,
                        booking_details_obj.passenger_details,
                        booking_details_obj.seller_booking_code,
                        booking.departure_at,
                        booking.status,
                        booking.amount_in_inr,
                        booking_details_obj.invoice_number,
                        f'=HYPERLINK("{booking.invoices.last().document_path}")' if booking.invoices.last() and booking.invoices.last().document_path else "",
                        get_amount_collected(booking,BUYER) if member_id == booking.buyer_id and get_amount_collected(booking,BUYER) else "",
                        get_amount_paid(booking,BUYER) if member_id == booking.buyer_id and get_amount_paid(booking,BUYER) else "",
                        get_amount_paid(booking,SELLER) if member_id == booking.seller_id and get_amount_paid(booking,SELLER) else "",
                        get_amount_collected(booking,SELLER) if member_id == booking.seller_id and get_amount_collected(booking,SELLER) else "",
                    ]
                )
            booking_statement_file = open(file, "rt")
        document_url = upload_document_to_docs_microservice(
            booking_statement_file)
        if document_url is None:
            return None
        return document_url

    except Exception as e:
        return None


def create_booking_statement(**kwargs):
    data = {
        "document_url": kwargs.get('document_url'),
        "start_date": kwargs.get('booking_start_date'),
        "end_date": kwargs.get('booking_end_date'),
        "request_from_member": get_member_data_from_member_id(kwargs.get('member_id')),
        "organization":kwargs.get('organization')
    }
    return booking_statement.create_booking_statement(**data)

def send_booking_statement_email(booking_statement_obj):
    from_email = settings.BOOKING_STATEMENT_EMAIL_ADDRESS
    validated_document_url = validators.url(booking_statement_obj.document_url) if booking_statement_obj.document_url else None
    start_date = get_date_from_given_str_format(booking_statement_obj.start_date).strftime("%d %b %Y")
    end_date = get_date_from_given_str_format(booking_statement_obj.end_date).strftime("%d %b %Y")
    email_subject = "Booking Ledger-{}-{}-{}".format(booking_statement_obj.organization.code, start_date, end_date)

    params = {
        'document_url': booking_statement_obj.document_url if validated_document_url else None,
        'agent_primary_name': booking_statement_obj.request_from_member.name,
        'start_date': start_date,
        'end_date': end_date,
        'org_code': booking_statement_obj.organization.code,
        'org_legal_name': booking_statement_obj.organization.name,
        'error_msg' : settings.BOOKING_STATEMENT_GENERATION_ERROR if not validated_document_url  else " ",
        'email_subject' : email_subject
    }
    to_email = [booking_statement_obj.request_from_member.email]
    cc_emails = []
    cc_emails.append(
        booking_statement_obj.organization.email) if booking_statement_obj.organization and booking_statement_obj.organization.email else cc_emails
    document_urls_list = [{
        "document_url": booking_statement_obj.document_url if validated_document_url else None,
        "document_name": "booking_ledger"
    }]
    attachments = create_file_attachement_array_from_documents_url(document_urls_list)
    optional_data = {'cc_email': cc_emails, "attachments": attachments}
    return emails.send_template_email(from_email, to_email, settings.BOOKING_STATEMENT_MAIL_TEMPLATE_ID, params, optional_data)