from django.db import transaction
from django.shortcuts import render, reverse, redirect
from django.contrib import messages
from django.utils.safestring import mark_safe
from accounts.services.bank_record import get_bank_record_obj_by_id
from wallets.services import WalletServices as wallet
from accounts.services.posting import add_money_into_wallet
from accounts.services.bank_record import update_bank_record
from bms.forms import SelectService
from django.http import HttpResponse


@transaction.atomic
def add(request, **kwargs):
    bank_record_obj = get_bank_record_obj_by_id(kwargs.get('bank_record_id'))
    wallet_obj = wallet.get_wallet_obj_by_organization_id(kwargs.get('organization_id'))

    if request.method == "GET":
        if bank_record_obj.currency != wallet_obj.currency:
            return HttpResponse("Error : {}".format('Bank record and Wallet Currency does not match.'))
        form_obj = SelectService()
        wallet_obj.updated_balance = round((wallet_obj.current_balance + bank_record_obj.amount), 2)
        return render(request, "bank_record/wallet/add.html",
                      {"bank_record_obj": bank_record_obj, "wallet_obj": wallet_obj, "form_obj": form_obj})
    elif request.method == "POST":
        if bank_record_obj.claimed:
            messages.add_message(request, messages.ERROR, mark_safe('Bank Record {} is already claimed'.format(
                mark_safe("<a href={}>{}</a>".format(
                    reverse('admin:accounts_bankrecord_change', args=[bank_record_obj.id]),
                    bank_record_obj)))))

        else:
            service_id = request.POST.get('service')

            technical_description = "From Bank Record id {} by {}".format(bank_record_obj.id, request.user.email)
            description = "Money added to Travel Supply Wallet. Record ID: {}".format(bank_record_obj.id)
            posting_id = add_money_into_wallet(kwargs.get('organization_id'),
                                               wallet_obj.id, bank_record_obj.amount, description=description,
                                               member_id=kwargs.get('member_id'),
                                               technical_description=technical_description,
                                               currency_id=bank_record_obj.currency.id)
            update_bank_record(bank_record_obj.id, request.user, service_id,
                               organization_id=kwargs.get('organization_id'), posting_id=posting_id)
            messages.add_message(request, messages.SUCCESS,
                                 mark_safe('Bank Record {} has been Successfully Added to Wallet {}'.format(
                                     mark_safe("<a href={}>{}</a>".format(
                                         reverse('admin:accounts_bankrecord_change', args=[bank_record_obj.id]),
                                         bank_record_obj))
                                     , mark_safe("<a href={}>{}</a>".format(
                                         reverse('admin:wallets_wallet_change', args=[wallet_obj.id]), wallet_obj)))))
        return redirect(reverse('admin:accounts_bankrecord_change', args=[bank_record_obj.id]))
    return HttpResponse("Invalid HTTP Method")
