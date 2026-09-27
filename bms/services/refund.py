from django.db import transaction
from bms.providers import refund
from bms.enums import BANK_TRANSFER, ADD_TO_WALLET
from bms.services import bookings as booking_service, transaction_summary as booking_summary_services
from dmcpesys.constants import CATEGORY_FLIGHT_ID, CATEGORY_HOTEL_ID
from bms.models import Booking as Booking
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse
from bms.validators import manual_refund


def record_cash_refund(planned_payment_obj, created_by, **kwargs):
    return refund.process_refund(planned_payment_obj, created_by, BANK_TRANSFER, **kwargs)


def record_refund_as_adjust_with_another_booking(planned_payment_obj, created_by):
    return refund.process_refund(planned_payment_obj, created_by, ADD_TO_WALLET)


def validate_initiate_refund_tranche_request(planned_payment_id: int):
    return refund.validate_initiate_refund_tranche_request(planned_payment_id)


def validate_refund_request_for_failed_booking(booking_previous_status, _booking_details, booking_obj):
    if _booking_details and _booking_details.get('process_refund'):
        if booking_previous_status not in [Booking.PENDING, Booking.HOLD]:
            return False
        if booking_obj.status not in [Booking.FAILED]:
            return False
        return True
    return False


def initiate_refund_for_failed_booking(booking_id: int, **kwargs):
    with transaction.atomic():
        booking_obj = booking_service.get_booking_object_for_update_by_booking_id(booking_id)
        ts_obj = booking_summary_services.get_booking_summary_object_for_update_by_booking_id(booking_id)
        if booking_obj.category_id in [CATEGORY_FLIGHT_ID, CATEGORY_HOTEL_ID]:
            if ts_obj.net_hold > 0:
                refund.process_refund_for_failed_booking(booking_obj, ts_obj.net_hold, ADD_TO_WALLET, **kwargs),


def initiate_manual_refund_for_failed_booking(booking_obj, ts_obj, **kwargs):
    if booking_obj.category_id in [CATEGORY_FLIGHT_ID, CATEGORY_HOTEL_ID]:
        if ts_obj.net_hold > 0:
            refund.process_refund_for_failed_booking(booking_obj, ts_obj.net_hold, ADD_TO_WALLET, **kwargs),


@login_required
def manual_refund_to_wallet(request, code: str):
    try:
        with transaction.atomic():
            booking_obj = booking_service.get_booking_object_from_code(code)
            ts_obj = booking_summary_services.get_booking_summary_object_for_update_by_booking_id(booking_obj.id)
            is_valid, err_msg = manual_refund.validate_manual_refund_request_for_failed_booking(
                booking_obj, ts_obj)
            if not is_valid:
                messages.add_message(request, messages.ERROR, err_msg)
                return redirect(reverse('admin:bms_booking_change', args=[booking_obj.id]))

            if request.method == "POST":
                data = {
                    "remark": request.POST['remarks'],
                    "proof": request.FILES['proof'],
                    "created_by_id": request.user.id
                }
                initiate_manual_refund_for_failed_booking(booking_obj, ts_obj, **data)
                messages.add_message(request, messages.SUCCESS, "Refund Has Been Processed")
                return redirect(reverse('admin:bms_booking_change', args=[booking_obj.id]))
            return render(request, 'refund/payback.html')

    except Exception as e:
        return None
