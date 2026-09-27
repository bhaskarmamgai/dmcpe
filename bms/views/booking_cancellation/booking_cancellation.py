from django.shortcuts import redirect, render
from django.http import HttpResponse
from django.urls import reverse
from django.contrib import messages
from django.conf import settings
from bms.enums import PARTIAL_CANCELLATION, FULL_CANCELLATION
from bms.models.planned_payment.planned_payment import PlannedPayment
from bms.models.booking.booking import Booking
from bms.forms import CancellationFinalSettlementForm, TypeOfCancellationRequestForm
from bms.services import bookings as bookings, planned_payment
from dmcpesys.services import get_currency_by_symbol
from bms.providers.invoice import create_cancellation_automated_invoice, create_cn_dn, create_cn_dn_delta_record, \
    create_invoice_delta_record
from bms.services.invoice import check_if_cancellation_for_booking_exists


def cancel_booking(request, booking_id: int):
    pending_planned_payments_objs = planned_payment.get_planned_payments_with_status_and_booking_id(
        PlannedPayment.PENDING, booking_id)
    if not pending_planned_payments_objs:
        bookings.update_booking_status(Booking.CANCELLED, booking_id)
        messages.add_message(request, messages.SUCCESS,
                             'Booking {} has been Marked Cancelled Successfully'.format(booking_id))
        return redirect(reverse('admin:trs_booking_change', args=[booking_id]))
    else:
        msg = ""
        for i in pending_planned_payments_objs:
            msg += "<a href='{}'>#{}</a> | {} | {} | {} | {} | {} | - <a href='{}'>Click Here</a><br>".format(
                reverse('admin:trs_booking_change', args=[booking_id]), i.bookings.code, i.member.name,
                i.amount, i.date, i.status, i.payment_type,
                reverse('admin:bms_bookingcancellationproxy_change', args=[booking_id]))
        return HttpResponse(
            "<h1></h1>Error.Please cancel or settle following <b>pending</b> tranches<br><br>{}".format(
                msg))


def cancellation_final_settlement(request, booking_id):
    booking_obj = bookings.get_booking_object_from_id(booking_id)
    if not booking_obj.status == Booking.CANCELLATION_SETTLED:
        if request.method == 'GET':
            final_settlement_form_obj = CancellationFinalSettlementForm()
            return render(request, "booking_cancellation/cancellation_final_settlement_v2.html",
                          {'form': final_settlement_form_obj,
                           'booking_obj': booking_obj,
                           'seller_cost_components': bookings.fetch_seller_cost_components_from_booking_id(
                               booking_id)})
        if request.method == 'POST':
            try:
                member_ids = request.POST.getlist('member_id')
                collect_or_pay = request.POST.getlist('collect_or_pay')
                amounts = request.POST.getlist('amount')
                organization_ids = request.POST.getlist('organization_id')
                due_dates = request.POST.getlist('due_date_id')
                currency_symbols = request.POST.getlist('currency_symbol')
                currencies = [get_currency_by_symbol(symbol).id for symbol in currency_symbols]
                planned_payment.create_planned_payment_record_v2(booking_id, member_ids, organization_ids, amounts,
                                                                 collect_or_pay,
                                                                 payment_type=PlannedPayment.CANCELLATION_FINAL_SETTLEMENT,
                                                                 due_dates=due_dates,
                                                                 currencies=currencies,
                                                                 created_by_id=request.user.id)
                messages.add_message(request, messages.SUCCESS, "Final Settlement has Been Made Successfully")
                bookings.update_booking_status(Booking.CANCELLATION_SETTLED, booking_id)
                return redirect(reverse('admin:bms_bookingcancellationproxy_change', args=[booking_id]))
            except Exception as e:
                return HttpResponse("Error {}".format(e))
    return HttpResponse("Error: Cancellation Settlement Request Has Already Been Made")


def cancellation_process_v2_type_selection(request, **kwargs):
    booking_obj = bookings.get_booking_object_from_id(kwargs.get('booking_id'))
    if request.method == 'GET':
        if not booking_obj.status == Booking.CONFIRMED:
            return HttpResponse("Error: Booking should be in confirmed state")
        cancellation_request_form = TypeOfCancellationRequestForm()
        return render(request, "booking_cancellation/select_cancellation.html", {'form': cancellation_request_form})
    if request.method == 'POST':
        if not booking_obj.status == Booking.CONFIRMED:
            return HttpResponse("Error: Booking should be in confirmed state")
        cancellation_type = request.POST.get('cancellation_type')
        kwargs = {'booking_id': kwargs.get('booking_id')}
        if cancellation_type == FULL_CANCELLATION:
            kwargs.update({'cancellation_type': FULL_CANCELLATION})
        elif cancellation_type == PARTIAL_CANCELLATION:
            kwargs.update({'cancellation_type': PARTIAL_CANCELLATION})
        return redirect(reverse('bms:cancellation_process_v2_fill_cancellation_details', kwargs=kwargs))
    return None


def cancellation_process_v2_fill_cancellation_details(request, **kwargs):
    booking_obj = bookings.get_booking_object_from_id(kwargs.get('booking_id'))
    if request.method == 'GET':
        if_cancellation_invoice_exist = check_if_cancellation_for_booking_exists(booking_obj.id)
        if kwargs.get("cancellation_type") == FULL_CANCELLATION and if_cancellation_invoice_exist:
            return HttpResponse("Error: Can't do full cancellation for already partially cancelled booking")
        if not booking_obj.status == Booking.CONFIRMED:
            return HttpResponse("Error: Booking should be in confirmed state")
        booking_financials = booking_obj.booking_financial if hasattr(booking_obj, 'booking_financial_v2') else None
        if not booking_financials:
            return HttpResponse("Error: Booking financials not found for this booking")
        reimbursement_amount = booking_financials.total_cost_price
        service_charges = booking_financials.gross_profit
        discount = booking_financials.approved_discount
        return render(request, "booking_cancellation/fill_cancellation_details.html", {
            'cancellation_type': kwargs.get("cancellation_type"),
            "full_cancellation": FULL_CANCELLATION,
            "partial_cancellation": PARTIAL_CANCELLATION,
            'reimbursement_amount': reimbursement_amount,
            'service_charges': service_charges,
            'discount': discount,
            'scratch_card_amount': 0,
            'scratch_card_status': None
        })
    elif request.method == "POST":
        kwargs = dict()
        if not booking_obj.status == Booking.CONFIRMED:
            return HttpResponse("Error: Booking should be in confirmed state")

        booking_financials = booking_obj.booking_financial if hasattr(booking_obj, 'booking_financial_v2') else None

        if float(request.POST.get('discount')) > booking_financials.approved_discount:
            return HttpResponse("Approved Discount value can't be more than Actual Approved Discount value. "
                                "Please fill the form again")
        if float(request.POST.get('reimbursement_amount')) > booking_financials.total_cost_price:
            return HttpResponse("Reimbursement amount value can't be more than Actual Reimbursement Amount value. "
                                "Please fill the form again")
        if float(request.POST.get('service_charges')) > booking_financials.gross_profit:
            return HttpResponse("Service Charges value can't be more than Actual Service Charges value. "
                                "Please fill the form again")
        kwargs.update(reimbursement_amount=(-1) * float(request.POST.get('reimbursement_amount', 0)))
        kwargs.update(service_charges=(-1) * float(request.POST.get('service_charges', 0)))
        kwargs.update(discount=(-1) * float(request.POST.get('discount', 0)))
        kwargs.update(provider_cancellation_charges=float(request.POST.get('provider_cancellation_charges', 0)))
        kwargs.update(travelsupply_cancellation_charges=float(request.POST.get('travelsupply_cancellation_charges', 0)))
        cn_dn_delta_record = create_cn_dn_delta_record(booking_obj.id, **kwargs)
        cn_dn_obj = create_cn_dn(booking_obj.id, request.user.id, cn_dn_delta_record,
                                 is_credit_note=True,
                                 invoice_type=settings.TRANSACTION_INVOICE_TYPE__CREDIT_NOTE,
                                 description_of_invoice_note="Credit Note",
                                 **kwargs)

        if float(request.POST.get('scratch_card_amount', 0)) or kwargs.get('provider_cancellation_charges',
                                                                           0) or kwargs.get(
                'travelsupply_cancellation_charges', 0):
            cancellation_invoice_delta_record = create_invoice_delta_record(booking_obj,
                                                                            scratch_card_amount=0,
                                                                            **kwargs)
            invoice_obj = create_cancellation_automated_invoice(booking_obj, request.user.id,
                                                                cancellation_invoice_delta_record,
                                                                cancellation_type=request.POST.get(
                                                                    'cancellation_type_value'),
                                                                description_of_invoice_note="Cancellation Invoice",
                                                                scratch_card_amount=0,
                                                                **kwargs)

        if request.POST.get('cancellation_type_value') == FULL_CANCELLATION:
            bookings.update_booking_status(Booking.CANCELLED, booking_obj.id)
        if booking_obj.type_id == settings.BOOKING_TYPE_FLIGHT_ID:
            return redirect(reverse('admin:bms_bookingflightproxymini_change', args=[booking_obj.id]))
        return redirect(reverse('admin:bms_booking_change', args=[booking_obj.id]))
    return None
