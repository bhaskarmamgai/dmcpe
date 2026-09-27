from django.db import models, transaction
from accounts.enums import DEBIT, CREDIT
from accounts.exceptions import NegativePostingBalanceException, ZeroOrNegativePostingAmountException, \
    InvalidDebitCreditTypeException, PostingsAndWalletBalanceMisMatchException
from django.db.models import Sum
from wallets.services import WalletServices
from accounts.constants import CURRENCY_ID_INR



class PostingManager(models.Manager):

    def add(self, journal_id, datetime, dr_or_cr, amount, description, wallet_id,
              organization_id, **kwargs):

        if amount <= 0:
            raise ZeroOrNegativePostingAmountException({'amount': amount})

        amount = round(amount, 2)

        d = {'member_id': kwargs.get('member_id'), 'journal_id': journal_id, 'datetime': datetime,
             'description': description,
             'organization_id': organization_id, 'wallet_id': wallet_id,
             'technical_description': kwargs.get('technical_description'),
             'currency_id': kwargs.get('currency_id') if kwargs.get('currency_id') else CURRENCY_ID_INR }


        with transaction.atomic():
            _wallet = WalletServices.get_wallet_object_for_update_by_wallet_id(wallet_id)
            wallet_balance_from_postings = round(self.calculate_wallet_current_balance_from_postings(wallet_id),2)
            if _wallet.current_balance != wallet_balance_from_postings:
                raise PostingsAndWalletBalanceMisMatchException(
                    {'Wallet Balance From Postings': wallet_balance_from_postings,
                     'Wallet Balance': _wallet.current_balance})
            if dr_or_cr == DEBIT:
                d['debit'] = round(amount, 2)
                new_balance = round(_wallet.current_balance - amount, 2)
            elif dr_or_cr == CREDIT:
                d['credit'] = round(amount, 2)
                new_balance = round(_wallet.current_balance + amount, 2)
            else:
                raise InvalidDebitCreditTypeException()

            if new_balance < 0:
                raise NegativePostingBalanceException({'balance': new_balance})
            d['balance'] = new_balance

            posting = self.create(**d)
            WalletServices.update_wallet_by_id(wallet_id, current_balance=new_balance)
            return posting

    def calculate_wallet_current_balance_from_postings(self, wallet_id):
        wallet_posting_aggregate = self.filter(wallet_id=wallet_id).aggregate(
            current_balance=Sum('credit') - Sum('debit'))
        print(f"[Wallet Current Balance From Posting]: Balance=>{str(wallet_posting_aggregate)}")
        return wallet_posting_aggregate['current_balance'] if wallet_posting_aggregate and \
                                                      wallet_posting_aggregate[
                                                          'current_balance'] else 0
