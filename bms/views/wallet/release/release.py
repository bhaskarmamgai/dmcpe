from django.db import transaction
from django.shortcuts import HttpResponse, render, redirect, reverse
from django.conf import settings
import datetime
from django.utils.safestring import mark_safe
from django.contrib import messages
from common.libraries import format_str_date_to_date, get_round_off_amount
from django.db.models import Sum
from bms.forms import ReleaseFromWalletForm, ModeOfReleaseRequestForm, RejectReleaseRequestForm
from bms.services.wallet import release_request as wallet_release_request
from bms.services.wallet import actual_payment as wallet_actual_payment_services
from bms.services import bookings, member, actual_payment, release_request, planned_payment
from bms.providers import planned_payment
from wallets.services import WalletServices as wallet
from bms.models import ActualPayment, ReleaseRequest, PlannedPayment
from bms.forms import ReleaseRequestReleaseOptions
from bms.enums import ADD_TO_WALLET, BANK_TRANSFER
from bms.forms import ReleaseRequestProxyForm
from members.services import OrganizationServices as organization
from bms.validators.release_request import validate_scheduled_collection_tranche_for_release_request, \
    validate_release_request
from dmcpesys.services import get_roe_and_markup_by_currency, get_currency_by_symbol


def edit(request, **kwargs):
    if request.method == "GET":
        form = ReleaseFromWalletForm()
        return render(request, 'wallet/release/edit.html',
                      {'form': form, 'date': datetime.datetime.now().date()})
    if request.method == "POST":
        destination_id = request.POST['destination'] if request.POST['destination'] != "" else 0
        type_id = request.POST['type'] if request.POST['type'] != "" else 0
        category_id = request.POST['category'] if request.POST['category'] != "" else 0
        vendor_organization = request.POST['vendor_organization'] if request.POST['vendor_organization'] != "" else 0
        return redirect(reverse('bms:wallet_release_request_select_booking_v2',
                                kwargs={'service_id': request.POST['service'],
                                        'member_id': request.POST['member'],
                                        'organization_id': request.POST['organization'],
                                        'selected_due_date': request.POST['selected_due_date'],
                                        'booking_start_date': request.POST['booking_start_date'],
                                        'booking_end_date': request.POST['booking_end_date'],
                                        'destination_id': destination_id,
                                        "type_id": type_id,
                                        "category_id": category_id,
                                        "vendor_organization": vendor_organization
                                        }))


def select_bookings(request, *args, **kwargs):
    booking_id = None
    planned_payment_id = None
    if request.GET and request.GET.get('booking_id'):
        booking_id = int(request.GET.get('booking_id'))
    if request.GET and request.GET.get('planned_payment_id'):
        planned_payment_id = int(request.GET.get('planned_payment_id'))

    selected_due_date = format_str_date_to_date(kwargs.get('selected_due_date'))
    booking_start_date = format_str_date_to_date(kwargs.get('booking_start_date'))
    booking_end_date = format_str_date_to_date(kwargs.get('booking_end_date'))

    pending_payments_seller = wallet_release_request.get_bookings_where_payment_release_is_due_in_given_date_range_v2_for_bmsv2(
        selected_due_date,
        kwargs.get('member_id'), kwargs.get('organization_id'), booking_start_date, booking_end_date,
        destination_id=kwargs.get('destination_id'), type_id=kwargs.get('type_id'),
        category_id=kwargs.get('category_id'),
        booking_id=booking_id, vendor_organization=kwargs.get('vendor_organization'))

    if not booking_id:
        booking_ids_where_collection_is_pending = [item.get('id') for item in
                                                   release_request.filter_booking_ids_whose_collection_is_due_before_today_by_member_id(
                                                       kwargs.get('member_id'), [item.get('booking_id') for item in
                                                                                 pending_payments_seller])]
    else:
        booking_ids_where_collection_is_pending = [booking_id]

    if request.method == 'GET':
        if selected_due_date < datetime.datetime.now().date():
            return HttpResponse("Creating Back Date Release Request Are not Allowed !!!")
        if not organization.get_bank_accounts_by_organization_id(kwargs.get('organization_id')):
            return HttpResponse(
                "Selected Organization Bank Account Details Missing.<br><a href={} target ='_blank'>Click Here To "
                "Fill It</a>".format(
                    reverse('admin:members_organization_change', args=[kwargs.get('organization_id')])))

        planned_payment_obj, current_roe, current_roe_markup = None, None, None
        if planned_payment_id and booking_id:
            planned_payment_obj = planned_payment.get_planned_payment_object_by_planned_payment_id(planned_payment_id)
        for i in pending_payments_seller:
            i.update({'booking_obj': bookings.get_booking_object_from_id(i['booking_id'])})
            i.update({'due_amount': get_round_off_amount(i['due_amount'])})
            i.update({'booking_financial': i['booking_obj'].booking_financial})
            i.update(
                {'total_booking_losses': i['booking_obj'].booking_losses.aggregate(
                    total=Sum('amount')).get('total') or 0})
            seller_cost_components = bookings.get_seller_cost_components_by_booking_code(
                i['booking_obj'].code, seller_member__id=kwargs.get('member_id'),
                seller_organization__id=kwargs.get('organization_id'))
            if planned_payment_obj.member.id == i['booking_obj'].buyer.id:
                current_roe, current_markup = get_roe_and_markup_by_currency(
                    planned_payment_obj.bookings.collection_currency.id, planned_payment_obj.member_currency.id,
                    i['booking_obj'].created_at)
                weighted_seller_fx, weighted_seller_fx_markup = current_roe.roe, current_markup.selling_mark_up
            else:
                weighted_seller_fx, weighted_seller_fx_markup = bookings.get_weighted_seller_fx_and_markup(
                    seller_cost_components)
            i.update({'is_refund_or_cancellation': 1 if planned_payment_obj.payment_type in (
                PlannedPayment.CANCELLATION_FINAL_SETTLEMENT, PlannedPayment.REFUND) else 0})
            i.update({'current_roe': weighted_seller_fx})
            i.update({'current_markup': weighted_seller_fx_markup})
            i.update({'planned_payment_tranche_due': get_round_off_amount(
                planned_payment_obj.amount - planned_payment_obj.actual_payment_amount)})
            if planned_payment_obj.member.id == i['booking_obj'].buyer.id:
                i.update({
                    'planned_payment_tranche_due_in_collection_currency': bookings.calculate_amount_in_collection_currency_for_collection(
                        i['booking_obj'].collection_currency.id, planned_payment_obj.member_currency.id,
                        i['booking_obj'].created_at, planned_payment_obj.amount)})
            else:
                i.update({
                    'planned_payment_tranche_due_in_collection_currency': bookings.calculate_amount_in_collection_currency_for_payment(
                        i['booking_obj'].collection_currency.id, planned_payment_obj.amount,
                        seller_cost_components)})
            i.update({'seller_cost_component': seller_cost_components.last()})
            buyer_dict_obj = planned_payment.get_bookings_where_collection_is_due_as_on_given_date_with_booking_id_v2(
                selected_due_date, i['booking_id'])
            i.update(*buyer_dict_obj)
            i.update({'is_collection_pending': True if i.get(
                'booking_id') in booking_ids_where_collection_is_pending else False})
        release_option_form_obj = ReleaseRequestReleaseOptions()
        member_obj = member.get_member_obj_by_id(kwargs.get('member_id'))
        organization_bank_account_objects = organization.get_bank_accounts_by_organization_id(
            kwargs.get('organization_id'))
        wallet_obj = wallet.get_wallet_obj_by_organization_id(kwargs.get('organization_id'))
        return render(request, 'wallet/release/v2/select_bookings.html',
                      {'pending_payments_seller': pending_payments_seller,
                       'selected_due_date': selected_due_date,
                       'member_obj': member_obj, 'default_date': datetime.datetime.now().date(),
                       'organization_bank_account_objects': organization_bank_account_objects,
                       'wallet_obj': wallet_obj,
                       'release_option_form_obj': release_option_form_obj})

    if request.method == 'POST':
        member_id = request.POST['member_id']
        organization_id = request.POST['organization_id']
        selected_due_date = datetime.datetime.strptime(request.POST.get('selected_due_date'),
                                                       '%Y-%m-%d') if request.POST.get(
            'selected_due_date') else datetime.datetime.now().date().strftime("%Y-%m-%d")
        booking_ids = request.POST.getlist('booking_id')
        requested_currency = request.POST.get('requested_currency')
        requested_amounts = request.POST.getlist('amount')
        amount_in_member_currencies = request.POST.getlist('amount_in_member_currency')
        amount_in_collection_currencies = request.POST.getlist('amount_in_collection_currency')
        amount_in_seller_currencies = amount_in_member_currencies if amount_in_member_currencies else amount_in_collection_currencies
        to_be_released_on = request.POST['to_be_released_on']
        description = request.POST['description']
        organization_bank_account = request.POST.get('organization_bank_account_radio', None)
        release_option = request.POST['release_option']
        with transaction.atomic():
            requested_currency_id = None
            if requested_currency:
                requested_currency_id = get_currency_by_symbol(requested_currency).id
            is_valid, error_message = validate_scheduled_collection_tranche_for_release_request(booking_ids, member_id)
            if not is_valid:
                return HttpResponse(error_message)
            if booking_ids:
                try:
                    for index in range(len(booking_ids)):
                        booking_id = booking_ids[index]
                        booking_obj = bookings.get_booking_object_from_id(booking_id)
                        requested_amounts = requested_amounts[index]
                        check_release_req_func_obj = release_request.check_if_release_request_can_be_created(
                            booking_obj, int(member_id), requested_amounts)
                        if check_release_req_func_obj.get('status'):
                            return HttpResponse(check_release_req_func_obj.get('response_message'))
                    wallet_release_request.create_release_request_for_collection(organization_id, member_id,
                                                                                 booking_ids,
                                                                                 requested_amounts,
                                                                                 selected_due_date, request.user,
                                                                                 description=description,
                                                                                 to_be_released_on=to_be_released_on,
                                                                                 type=ActualPayment.PAID_TO_MEMBER,
                                                                                 actual_payment_status=ActualPayment.PENDING,
                                                                                 organization_bank_account=organization_bank_account,
                                                                                 release_option=release_option,
                                                                                 booking_start_date=booking_start_date,
                                                                                 booking_end_date=booking_end_date,
                                                                                 currency_id=requested_currency_id)

                    messages.add_message(request, messages.SUCCESS, 'Release Request Created Successfully')
                    return redirect(reverse('admin:bms_releaserequest_changelist'))
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    return HttpResponse(
                        "Error : {} <br> {}".format(e, "<a href=\"javascript:history.go(-1)\">GO BACK</a>"))
            return HttpResponse("Error : Please Select At least One Booking")


def approve_release_request(request, release_request_id: int):
    if request.method == "GET":
        release_request_obj = release_request.get_release_request_obj(release_request_id)
        if release_request_obj.mode == ADD_TO_WALLET:
            return redirect(reverse('bms:wallet_release_request_approve_add_to_wallet',
                                    args=[release_request_id]))
        elif release_request_obj.mode == BANK_TRANSFER:
            return redirect(reverse('bms:wallet_release_request_approve_bank_transfer',
                                    args=[release_request_id]))
    return HttpResponse("Oho Hacker Hacker :)")


def add_to_wallet(request, release_request_id: int):
    release_request_obj = release_request.get_release_request_obj(release_request_id)
    wallet_obj = wallet.get_wallet_obj_by_organization_id(release_request_obj.organization.id)
    is_valid, error_msg = validate_release_request(request, release_request_id)
    if release_request_obj.requested_currency.symbol != wallet_obj.currency.symbol:
        error_msg = error_msg + "<p>Wallet Currency is not Matching with Requested Currency</p>"
    if not is_valid:
        return HttpResponse(error_msg)

    if request.method == "GET":
        actual_payment_objs = actual_payment.get_actual_payment_objects_from_release_id(release_request_id)
        release_req_form = ReleaseRequestProxyForm()
        wallet_obj.updated_balance = round((wallet_obj.current_balance + release_request_obj.requested_amount), 2)
        return render(request, 'wallet/release/v2/add_to_wallet.html',
                      {'release_req_form': release_req_form,
                       'actual_payment_objs': actual_payment_objs, 'release_request_obj': release_request_obj,
                       'wallet_obj': wallet_obj})
    if request.method == "POST":
        try:
            release_form_obj = ReleaseRequestProxyForm(request.POST, request.FILES, instance=release_request_obj)
            if release_form_obj.is_valid() and wallet_release_request.release_via_add_to_wallet(release_request_obj,
                                                                                                wallet_obj):
                release_request_obj.action_by = request.user
                release_request_obj.save()
                release_form_obj.save()
                wallet_release_request.update_stats_on_post_approval_of_release_request(release_request_obj)
                messages.add_message(request, messages.SUCCESS,
                                     mark_safe(
                                         'Release Request {} has been Released'.format(
                                             mark_safe("<a href='%s'>%s</a>" % (
                                                 reverse('admin:bms_releaserequest_change',
                                                         args=[release_request_obj.id]),
                                                 release_request_obj)))))
                return redirect(reverse('admin:bms_releaserequest_changelist'))
        except Exception as e:
            import traceback
            traceback.print_exc()
            return HttpResponse("Error {}".format(e))


def bank_transfer(request, release_request_id):
    release_request_obj = release_request.get_release_request_obj(release_request_id)
    is_valid, error_msg = validate_release_request(request, release_request_id)

    if not is_valid:
        return HttpResponse(error_msg)

    actual_payment_objs = actual_payment.get_actual_payment_objects_from_release_id(release_request_id)
    wallet_obj = wallet.get_wallet_obj_by_organization_id(release_request_obj.organization.id)
    if request.method == "GET":
        release_req_form = ReleaseRequestProxyForm()
        safe_and_remit_id = [settings.BOOKING_TYPE_SAFE_REMITTANCE_ID, settings.BOOKING_TYPE_REMIT_ID]
        return render(request, 'wallet/release/v2/bank_transfer.html',
                      {'release_req_form': release_req_form,
                       'actual_payment_objs': actual_payment_objs, 'release_request_obj': release_request_obj,
                       'safe_id_and_remit_id': safe_and_remit_id, 'wallet_obj': wallet_obj})

    if request.method == "POST":
        try:
            release_form_obj = ReleaseRequestProxyForm(request.POST, request.FILES, instance=release_request_obj)
            if release_form_obj.is_valid() and wallet_release_request.release_via_bank_transfer(
                    release_request_obj, wallet_obj):
                release_form_obj.save()
                release_request_obj.action_by = request.user
                release_request_obj.save()
                wallet_release_request.update_stats_on_post_approval_of_release_request(release_request_obj)
                messages.add_message(request, messages.SUCCESS,
                                     mark_safe(
                                         'Release Request {} has been Released'.format(
                                             mark_safe("<a href='%s'>%s</a>" % (
                                                 reverse('admin:bms_releaserequest_change',
                                                         args=[release_request_obj.id]),
                                                 release_request_obj)))))
                return redirect(reverse('admin:bms_releaserequest_changelist'))
        except Exception as e:
            import traceback
            traceback.print_exc()
            return HttpResponse("Error {}".format(e))


def fetch_release_request_for_organization(request):
    if request.method == "GET":
        release_form = ReleaseFromWalletForm()
        mode_of_release_form = ModeOfReleaseRequestForm()
        return render(request, 'wallet/bulk_release/select_organization_code.html', {'form': release_form,
                                                                                     'mode_of_release_form': mode_of_release_form})
    if request.method == "POST":
        return redirect(reverse('trs:select_release_requests_for_bulk_release',
                                kwargs={'organization_id': request.POST['organization'],
                                        'mode_of_release': request.POST['mode_of_release'],
                                        }))


def select_release_requests_for_bulk_release(request, **kwargs):
    organization_id = kwargs.get('organization_id')
    mode_of_release = kwargs.get('mode_of_release')
    if request.method == "GET":
        pending_release_requests = release_request.get_pending_release_requests_by_organization_id_and_mode_of_release(
            organization_id, mode_of_release)
        return render(request, 'wallet/bulk_release/select_release_requests.html',
                      {'pending_release_requests': pending_release_requests})
    if request.method == "POST":
        release_request_ids = request.POST.getlist('release_request_id')

        for release_request_id in release_request_ids:
            is_valid, error_msg = validate_release_request(request, release_request_id)
            if not is_valid:
                return HttpResponse(error_msg)

        release_request_ids_str = '-'.join(str(request_id) for request_id in release_request_ids)
        if request.POST.get('submit_release') == "Release":
            return redirect(reverse('bms:bulk_release_request_remittance_details',
                                    kwargs={'mode_of_release': mode_of_release,
                                            'release_request_ids_str': release_request_ids_str
                                            }))
        elif request.POST.get('submit_reject') == "Reject":
            return redirect(reverse('bms:wallet_reject_release_request',
                                    kwargs={'release_request_ids_str': release_request_ids_str}))
        release_form = ReleaseFromWalletForm()
        mode_of_release_form = ModeOfReleaseRequestForm()
        return render(request, 'wallet/bulk_release/select_organization_code.html', {'form': release_form,
                                                                                     'mode_of_release_form': mode_of_release_form})


def reject_bulk_release_requests(request, **kwargs):
    release_request_ids = [int(request_id) for request_id in kwargs.get('release_request_ids_str').split("-")]
    if request.method == "GET":
        reject_release_request_form_obj = RejectReleaseRequestForm()
        return render(request, 'release_request/release/reject_release_request.html',
                      {"reject_release_request_form_obj": reject_release_request_form_obj})
    if request.method == "POST":
        for release_request_id in release_request_ids:
            release_request_obj = release_request.get_release_request_obj(release_request_id)
            reject_release_request_form_obj = RejectReleaseRequestForm(request.POST, instance=release_request_obj)
            if reject_release_request_form_obj.is_valid():
                reject_release_request_form_obj.save()
                release_request_obj.action_by = request.user
                release_request_obj.save()
                release_request.update_release_request_status(release_request_id, ReleaseRequest.REJECTED)
                wallet_actual_payment_services.update_actual_payment_objects(ids=[i.id for i in
                                                                                  actual_payment.get_actual_payment_objects_from_release_id(
                                                                                      release_request_obj.id)],
                                                                             update_params={
                                                                                 'status': ActualPayment.REJECTED})
        return redirect(reverse('admin:bms_releaserequest_changelist'))
