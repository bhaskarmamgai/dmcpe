from bms.validators.wallet import actual_payment as actual_payment_validator
from bms.providers.wallet import actual_payment as actual_payment_provider


def create_validated_actual_payment_data(organization_id, member_id, booking_ids, amounts,
                                         claimed_by,
                                         **kwargs):
    return actual_payment_validator.validate_actual_payment_data(organization_id, member_id, booking_ids, amounts,
                                                                 claimed_by, **kwargs)


def update_actual_payment_objects(ids: [], update_params):
    return actual_payment_provider.update_actual_payment(ids=ids, update_params=update_params)


def update_actual_payment_object(id: int, update_params):
    return actual_payment_provider.update_actual_payment(id=id, update_params=update_params)


def record_actual_payments(actual_payment_data):
    return actual_payment_provider.record_actual_payments(actual_payment_data)
