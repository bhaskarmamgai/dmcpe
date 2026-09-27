from django.shortcuts import redirect, render, HttpResponse
from django.urls import reverse
from django.contrib import messages

from bms.forms import BookingRefundOptionsForm
from bms.services import planned_payment, release_request, refund
from members.services import OrganizationServices
from bms.models import ReleaseRequest, Booking

def select_booking_refund_options(request, planned_payment_id):
    print("Selecting Refund Option for Planned Payment id {}".format(planned_payment_id))
    is_valid, error_message = refund.validate_initiate_refund_tranche_request(planned_payment_id)
    if not is_valid:
        return HttpResponse("Validation Error : {}".format(error_message))
    booking_refund_option_form = BookingRefundOptionsForm()
    if request.method == "POST":
        print("Selected Option for refund of tranche {} is {}".format(planned_payment_id,
                                                                            request.POST.get('booking_refund_option')))
        if request.POST.get('booking_refund_option') == BookingRefundOptionsForm.RELEASE_REQUEST_AS_ADD_TO_WALLET:
            return redirect(reverse('bms:booking_refund_add_to_wallet',
                                    kwargs={'planned_payment_id': planned_payment_id, }))
        if request.POST.get('booking_refund_option') == BookingRefundOptionsForm.RELEASE_REQUEST_AS_BANK_TRANSFER:
            return redirect(reverse('bms:booking_refund_bank_transfer',
                                    kwargs={'planned_payment_id': planned_payment_id, }))
    return render(request, "refund/select_refund_options.html",
                  {'booking_refund_option_form': booking_refund_option_form})


def create_refund_as_add_to_wallet(request, planned_payment_id):
    planned_payment_obj = planned_payment.get_planned_payment_object_by_planned_payment_id(planned_payment_id)
    booking_obj = planned_payment_obj.bookings
    if request.method == "POST":
        try:
            if booking_obj:
                check_release_req_func_obj = release_request.check_if_release_request_can_be_created(
                        booking_obj,
                        planned_payment_obj.member_id,
                        planned_payment_obj.amount_in_collection_currency)
                if check_release_req_func_obj.get('status'):
                    return HttpResponse(check_release_req_func_obj.get('response_message'))
            refund.record_refund_as_adjust_with_another_booking(planned_payment_obj, request.user)
            messages.add_message(request, messages.SUCCESS, "Refund has been made Successfully")
            return redirect(reverse('admin:bms_booking_change', args=[planned_payment_obj.bookings.id]))
        except Exception as e:
            return HttpResponse("Error: {} <br> {}".format(e, "<a href=\"javascript:history.go(-1)\">GO BACK</a>"))
    return render(request, "refund/refund_options/add_to_wallet.html",
                  {'planned_payment_obj': planned_payment_obj})


def create_refund_as_bank_transfer(request, planned_payment_id):
    planned_payment_obj = planned_payment.get_planned_payment_object_by_planned_payment_id(planned_payment_id)



    organization_bank_account_objects = OrganizationServices.get_bank_accounts_by_organization_id(
        planned_payment_obj.organization.id)
    booking_obj = planned_payment_obj.bookings
    if request.method == "POST":
        try:
            if booking_obj:
                check_release_req_func_obj = release_request.check_if_release_request_can_be_created(booking_obj,
                                                                                                         planned_payment_obj.member_id,
                                                                                                         planned_payment_obj.amount_in_collection_currency)
                if check_release_req_func_obj.get('status'):
                    return HttpResponse(check_release_req_func_obj.get('response_message'))
            bank_account_id = request.POST['organization_bank_account_id']
            refund.record_cash_refund(planned_payment_obj, request.user, bank_account_id=bank_account_id)
            messages.add_message(request, messages.SUCCESS, "Refund has been made Successfully")
            return redirect(reverse('admin:bms_booking_change', args=[planned_payment_obj.bookings.id]))
        except Exception as e:
            return HttpResponse("Error: {} <br> {}".format(e, "<a href=\"javascript:history.go(-1)\">Back</a>"))
    return render(request, "refund/refund_options/bank_transfer.html",
                  {'planned_payment_obj': planned_payment_obj,
                   'organization_bank_account_objects': organization_bank_account_objects})
