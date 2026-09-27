from accounts.models import Posting
from datetime import datetime
from accounts.enums import DEBIT, CREDIT, JOURNAL_COLLECTION_ID, JOURNAL_PAYMENT_ID


def release_money_from_wallet(organization_id, wallet_id, amount, description, **kwargs):
    obj = Posting.objects.add(JOURNAL_PAYMENT_ID, datetime.now(), DEBIT, amount, description, wallet_id,
                                organization_id, **kwargs)
    return obj.id


def add_money_to_wallet(organization_id, wallet_id, amount, description, **kwargs):
    obj = Posting.objects.add(JOURNAL_COLLECTION_ID, datetime.now(), CREDIT, amount, description, wallet_id,
                                organization_id, **kwargs)
    return obj.id
