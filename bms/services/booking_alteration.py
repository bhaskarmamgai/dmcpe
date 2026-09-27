from django.shortcuts import render, reverse, redirect
from django.conf import settings
from bms.providers.invoice import create_cn_dn, create_cn_dn_delta_record
from django.shortcuts import render
from bms.services import bookings as bookings
from django.http import HttpResponse
from bms.models import Booking


def initiate_booking_alteration(request, booking_id: int):
    booking_obj = bookings.get_booking_object_from_id(booking_id)
    data = prepare_alteration_data(booking_obj)
    if request.method == "GET":
        if not booking_obj.status == Booking.CONFIRMED:
            return HttpResponse("Error: Booking should be in confirmed state")
        if not data:
            return HttpResponse("Error: Booking Financials Not Found for this booking")
        return render(request, "booking_alteration/booking_alteration.html", {"data": data})
    if request.method == "POST":
        financial_obj = booking_obj.booking_financial

        if not booking_obj.status == Booking.CONFIRMED:
            return HttpResponse("Error: Booking should be in confirmed state")

        if 'confirm' not in request.POST:
            return HttpResponse("Confirm the Details")

        if not data['reimbursement_amount']['change'] and not data['service_charges_with_tax']['change'] and                not data['discount']['change']:
            return HttpResponse("Nothing has been Changed")

        reimbursement_amount = data['reimbursement_amount']['change'] * abs(data['reimbursement_amount']['changed_by'])
        service_charges = data['service_charges_with_tax']['change'] * abs(data['service_charges_with_tax']['changed_by'])
        discount = data['discount']['change'] * abs(data['discount']['changed_by'])

        new_gross_profit = financial_obj.gross_profit + service_charges
        new_discount = booking_obj.booking_financial.approved_discount - financial_obj.approved_discount
        if financial_obj.gross_profit <= 0 and new_gross_profit > 0:

            service_charges = new_gross_profit + new_discount
            discount = discount + new_discount
        elif financial_obj.gross_profit > 0 and new_gross_profit <= 0:

            service_charges = (-1) * financial_obj.gross_profit
            discount = discount + abs(new_gross_profit)
        elif new_gross_profit <= 0:

            discount = discount + abs(service_charges)
            service_charges = 0

        if data['service_charges_with_tax']['change'] and service_charges:
            cn_dn_delta_record_for_service_fee = create_cn_dn_delta_record(booking_obj.id,
                                                                           reimbursement_amount=0,
                                                                           discount=0,
                                                                           service_charges=service_charges)
            cn_dn_for_service_fee = create_cn_dn(booking_obj.id, request.user.id, cn_dn_delta_record_for_service_fee,
                                                 invoice_type=settings.TRANSACTION_INVOICE_TYPE__CREDIT_NOTE if
                                                 data['service_charges_with_tax']['change'] == -1 else settings.TRANSACTION_INVOICE_TYPE__DEBIT_NOTE,
                                                 description_of_invoice_note="Credit Note" if data['service_charges_with_tax']['change'] == -1 else "Debit Note",
                                                 is_credit_note=True if data['service_charges_with_tax']['change'] == -1 else False,
                                                 is_debit_note=False if data['service_charges_with_tax']['change'] == -1 else True,
                                                 reimbursement_amount=0,
                                                 service_charges=service_charges,
                                                 discount=0)
            update_booking(booking_id)

        update_booking(booking_id)

        if booking_obj.type_id == settings.BOOKING_TYPE_FLIGHT_ID:
            return redirect(reverse('admin:trs_bookingflightproxymini_change', args=[booking_obj.id]))
        return redirect(reverse('admin:trs_booking_change', args=[booking_obj.id]))
    return None


def prepare_alteration_data(booking_obj):
    return dict(
        reimbursement_amount={'change': 0, 'changed_by': 0},
        service_charges_with_tax={'change': 0, 'changed_by': 0},
        discount={'change': 0, 'changed_by': 0}
    )
