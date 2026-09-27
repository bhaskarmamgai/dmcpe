from bms.providers import remittance


def get_remittance_provider_object_by_id(remittance_provider_id: int):
    return remittance.get_remittance_provider_object_by_id(remittance_provider_id)
