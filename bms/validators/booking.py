from django.shortcuts import reverse
from django.conf import settings
from members.models import Organization
from bms.services.booking_invoice import check_booking_invoice_exist
from bms.enums import CONFIRMED
from common.libraries import get_date_from_given_str_format, subtract_years_from_date
from datetime import datetime
from dmcpesys.constants import CURRENCY_INR_ID
from members.services import MemberServices


def validate_members_organization_mandatory_fields_for_invoice(member_organization_obj: Organization):
    error_message = ""
    admin_field_ids = []

    if not member_organization_obj.name:
        error_message += "Company Name Missing.<br />"
        admin_field_ids.append('#id_name')

    if not member_organization_obj.addresses.last():
        error_message += "Address Details Missing.<br />"
        admin_field_ids.append('#id_addresses-0-line1')

    else:
        address = member_organization_obj.addresses.last()
        for field in ['line1', 'city', 'state']:
            if not getattr(address, field):
                error_message += ("%s is missing in address. <br />" % field)
                admin_field_ids.append('#id_addresses-0-line1')

    if not hasattr(member_organization_obj, 'organization_details'):
        error_message += "Company Details Missing.<br />"
        admin_field_ids.append('#id_organization_details-0-primary_business')

    if hasattr(member_organization_obj, 'organization_details') and (
            not getattr(member_organization_obj, 'organization_details').gstin_number):
        error_message += "GSTIN Missing.<br />"
        admin_field_ids.append('#id_organization_details-0-gstin_number')

    if hasattr(member_organization_obj, 'organization_details') and (
            not getattr(member_organization_obj, 'organization_details').state):
        error_message += "State Missing in Company/Business Details.<br />"
        admin_field_ids.append('#id_organization_details-0-state')
    return error_message, admin_field_ids


def validate_member_organization_details_for_invoice(booking_obj):
    _error_message = ""
    is_valid = False
    if not hasattr(booking_obj.buyer_organization, 'organization_details'):
        _error_message += "Organization Details Missing or KYC Pending.<br />"
    if not booking_obj.buyer_organization:
        _error_message += "Member Organization Missing In Booking"
    if booking_obj.buyer_organization:
        organization_detail_error_message, admin_page_field_id = validate_members_organization_mandatory_fields_for_invoice(
            booking_obj.buyer_organization)
        if organization_detail_error_message:
            _error_message += "<br><strong>Following Members Organization Details Missing:</strong><br>{}<a href='{}'><b>Click Here</b></a>To Update Member Details<br /><br />".format(
                organization_detail_error_message,
                '/admin/organization/organization/{}/change/{}'.format(booking_obj.buyer_organization.id,
                                                                       admin_page_field_id[0]),
                booking_obj.buyer.id, admin_page_field_id)
        else:
            is_valid = True
    return _error_message, is_valid


def validate_invoice_generation_request(booking_obj):
    _error_message = ""
    is_valid = True

    if booking_obj.agent_collection_entity_id != settings.TC_INDIA_TRAVEL_SUPPLY_GROUP_ENTITY:
        _error_message += ("<br><strong>The Agent Collection Entity Should be TC India for the Booking.</strong></br>")
        is_valid = False

    if hasattr(booking_obj.buyer_organization, 'organization_details'):
        if not getattr(booking_obj.buyer_organization, 'organization_details').state:
            _error_message += "State Missing in Company/Business Details.<br />"
            is_valid = False
        if hasattr(booking_obj.buyer_organization, 'wallets') and getattr(booking_obj.buyer_organization,
                                                                          'wallets').last().currency_id != CURRENCY_INR_ID:
            _error_message += "Wallet Currency Of Organization is Non Inr.<br />"
            is_valid = False
    else:
        _error_message += "Organization Details Missing or KYC Pending.<br />"
        is_valid = False

    if not booking_obj.status == CONFIRMED:
        _error_message += ("<br><strong>Incorrect Booking Status</strong></br>")
        is_valid = False
    if not booking_obj.status == CONFIRMED:
        _error_message += ("<br><strong>Incorrect Booking Status</strong></br>")
        is_valid = False

    if not check_transaction_type_and_category(booking_obj):
        _error_message += ("<br><strong>Incorrect Booking Type"
                           "or Category for this booking ><a href={} target=_blank><b>Click here</b></a></strong><br>".format(
            reverse('admin:bms_booking_change', args=[booking_obj.id])))
        is_valid = False
    invoice_exist, invoice_pdf_exist = check_booking_invoice_exist(booking_obj)

    if (invoice_exist and invoice_pdf_exist) or is_invoice_regeneration_enabled():
        _error_message += "<br><strong>Invoice Already Generated</strong><a href={} target=_blank><b> "                          "Click Here </b></a>To View Invoice<br><hr>".format(
            reverse('admin:bms_bookinginvoices_change',
                    args=[booking_obj.invoices.last().id]))
        is_valid = False

    if not booking_obj.booking_version_type == BOOKING_VERSION_TYPE_V2:
        if not (hasattr(booking_obj, 'booking_financial') and hasattr(getattr(booking_obj, 'booking_financial'),
                                                                      'cost_price')):
            _error_message += "<br><strong>Please fill the cost price <a href={} target=_blank><b>Click "                              "here</b></a><br /><br />".format(
                reverse('admin:bms_booking_change', args=[booking_obj.id]))
            is_valid = False

        if hasattr(booking_obj, 'booking_financial') and (booking_obj.booking_financial.gross_profit is None):
            _error_message += "<br><strong> Gross Profit is not Calculated yet <a href={} target=_blank><b>Click "                              "here</b></a><br /><br />".format(
                reverse('admin:bms_booking_change', args=[booking_obj.id]))
            is_valid = False
    else:
        if not (hasattr(booking_obj, 'booking_financial') and hasattr(getattr(booking_obj, 'booking_financial_v2'),
                                                                      'total_cost_price')):
            _error_message += "<br><strong>Please fill the cost price <a href={} target=_blank><b>Click "                              "here</b></a><br /><br />".format(
                reverse('admin:trs_booking_change', args=[booking_obj.id]))
            is_valid = False

        if hasattr(booking_obj, 'booking_financial') and (booking_obj.booking_financial_v2.gross_profit is None):
            _error_message += "<br><strong> Gross Profit is not Calculated yet <a href={} target=_blank><b>Click "                              "here</b></a><br /><br />".format(
                reverse('admin:bms_booking_change', args=[booking_obj.id]))
            is_valid = False
    return _error_message, is_valid


def is_invoice_regeneration_enabled():
    if settings.INVOICE_REGENERATION_ENABLED:
        return True
    return False


def check_transaction_type_and_category(booking_obj):
    if (booking_obj.type.id in (
            settings.BOOKING_TYPE_SAFE_REMITTANCE_ID,
            settings.BOOKING_TYPE_REMIT_ID,
            settings.BOOKING_TYPE_OWN_SUPPLY,
            settings.BOOKING_TYPE_FLIGHT_ID)):
        return True
    return False


def validate_booking_statement_request(booking_start_date, booking_end_date):
    if not booking_start_date:
        return False, "Start Date is Required"

    if not booking_end_date:
        return False, "End Date is Required"

    if booking_start_date == booking_end_date:
        return False, "Start Date Should not be Same as End Date"

    if booking_start_date and booking_end_date:
        start_date = get_date_from_given_str_format(booking_start_date)
        end_date = get_date_from_given_str_format(booking_end_date)
        todays_date = datetime.now().date()

        if not start_date:
            return False, "Invalid Format, It must be in YYYY-MM-DD format."

        if not end_date:
            return False, "Invalid Format, It must be in YYYY-MM-DD format."

        if start_date > todays_date:
            return False, "Start Date Should not be Greater Than Today"

        if end_date > todays_date:
            return False, "End Date Should not be Greater Than Today"

        if start_date > end_date:
            return False, "Start Date Should be Less Than End Date."

        if start_date < subtract_years_from_date(todays_date,
                                                 settings.BOOKING_STATEMENT_OLDEST_START_DATE_ALLOWED_IN_YEARS):
            return False, "Start Date should not be less than {} Year".format(
                settings.BOOKING_STATEMENT_OLDEST_START_DATE_ALLOWED_IN_YEARS)

        if end_date < subtract_years_from_date(todays_date,
                                               settings.BOOKING_STATEMENT_OLDEST_END_DATE_ALLOWED_IN_YEARS):
            return False, "End Date should not be less than {} Year".format(
                settings.BOOKING_STATEMENT_OLDEST_END_DATE_ALLOWED_IN_YEARS)

    return True, None
