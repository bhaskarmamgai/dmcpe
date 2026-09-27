from accounts.providers import posting


def release_money_from_wallet(organization_id, wallet_id, amount, description, **kwargs):
    return posting.release_money_from_wallet(organization_id, wallet_id, amount, description, **kwargs)


def add_money_into_wallet(organization_id, wallet_id, amount, description, **kwargs):
    return posting.add_money_to_wallet(organization_id, wallet_id, amount, description, **kwargs)
