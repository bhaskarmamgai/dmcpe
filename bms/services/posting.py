
from accounts.services import posting


def collect_money(member_id, amount, description=None):
    return posting.collect_money(member_id, amount, description)


def lock_money(member_id, amount, description=None):
    return posting.lock_money(member_id, amount, description)


def payment_approved(member_id, amount, description=None):
    return posting.payment_approved(member_id, amount, description)


def payment_released(member_id, amount, description=None):
    return posting.payment_released(member_id, amount, description)
