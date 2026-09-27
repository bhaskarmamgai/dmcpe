from django.shortcuts import HttpResponse, render, redirect, reverse
import datetime
from bms.services.wallet import get_bookings_where_collection_is_due_as_on_given_date
from bms.services.bookings import get_booking_object_from_id
from bms.services.booking_charges import get_default_roe_charged_to_buyer
from bms.forms import SelectPlannedTransactionsV2, ClaimFromWalletForm
from members.services import OrganizationServices as organization
from wallets.services import WalletServices as wallet
from bms.services.wallet.wallet import claim_booking_tranche_via_wallet
from bms.models import ActualPayment


def select_service(request, **kwargs):
    if request.method == "GET":
        form = ClaimFromWalletForm()
        return render(request, 'wallet/claim/select_service.html',
                      {'form': form, 'date': datetime.datetime.now().date()})
    if request.method == "POST":
        return redirect(reverse('trs:wallet__claim__select__bookings',
                                kwargs={'service_id': request.POST['service'],
                                        'member_id': request.POST['member'],
                                        'organization_id': request.POST['organization'],
                                        'selected_due_date': request.POST['selected_due_date']}))


def select_bookings(request, **kwargs):
    wallet_obj = wallet.get_wallet_obj_by_organization_id(kwargs.get('organization_id'))
    if request.method == "GET":
        selected_due_date = datetime.datetime.strptime(kwargs.get('selected_due_date'),
                                                       '%Y-%m-%d').date() if kwargs.get(
            'selected_due_date') else datetime.datetime.now().date().strftime("%Y-%m-%d")
        if selected_due_date < datetime.datetime.now().date():
            return HttpResponse("Back Date Claim Are not Allowed !!!")
        pending_payments = get_bookings_where_collection_is_due_as_on_given_date(
            selected_due_date,
            kwargs.get('organization_id'), kwargs.get('member_id'))
        organization_obj = organization.get_organization_object_by_id(kwargs.get('organization_id'))
        for i in pending_payments:
            i.update({'booking_obj': get_booking_object_from_id(i['booking_id'])})
            i.update(
                {'default_roe_charged_to_buyer': get_default_roe_charged_to_buyer(i['booking_id'])})

        form = SelectPlannedTransactionsV2(
            initial={'organization_id': kwargs.get('organization_id'), 'wallet_id': 1})
        return render(request, 'wallet/claim/select_bookings.html',
                      {'form': form, 'pending_payments': pending_payments, 'wallet_obj': wallet_obj,
                       'organization_obj': organization_obj, 'selected_due_date': selected_due_date,
                       'member_id': kwargs.get('member_id')})
    if request.method == "POST":
        wallet_id = request.POST['wallet_id']
        assert int(wallet_id) == int(wallet_obj.id), 'Wallet Error !! Organization and Wallet Mis-match'
        organization_id = request.POST['organization_id']
        member_id = request.POST['member_id']
        selected_due_date = datetime.datetime.strptime(request.POST.get('selected_due_date'),
                                                       '%Y-%m-%d') if request.POST.get(
            'selected_due_date') else datetime.datetime.now().date().strftime("%Y-%m-%d")
        booking_ids = request.POST.getlist('booking_id')
        currency_id = request.POST.get('currency_id')
        booking_date = request.POST.get('booking_date')
        collection_currency_id = request.POST.get('collection_currency_id')
        claimed_amounts = request.POST.getlist('amount')
        try:
            claim_booking_tranche_via_wallet(organization_id, member_id, booking_ids, claimed_amounts, wallet_id,
                                             request.user,
                                             selected_due_date,
                                             service_id=kwargs.get('service_id'),
                                             type=ActualPayment.PAID_BY_MEMBER,
                                             actual_payment_status=ActualPayment.COLLECTED,
                                             booking_date=booking_date, collection_currency_id=collection_currency_id,
                                             currency_id=currency_id)
            return redirect(
                reverse(
                    'admin:accounts_posting_changelist') + "?organization__id__exact={}&wallet__id__exact={}".format(
                    organization_id, wallet_id))
        except Exception as e:
            return HttpResponse(
                "Claim Error: {} <br> {}".format(e, "<a href=\"javascript:history.go(-1)\">Back</a>"))
