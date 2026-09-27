from django.db import transaction
from bms.providers import release_request
from bms.services import actual_payment



def get_bookings_where_payment_release_is_due_as_on_given_date(selected_due_date, member_id):
    return release_request.get_bookings_where_payment_release_is_due_as_on_given_date(selected_due_date, member_id)


def filter_booking_ids_whose_collection_is_due_before_today_by_member_id(seller_member_id, bookings_ids):
    return release_request.filter_booking_ids_whose_collection_is_due_before_today_by_member_id(seller_member_id,
                                                                                                bookings_ids)




@transaction.atomic
def create_release_request_for_refund(organization_id, member_id, booking_ids, requested_amounts, created_by,
                                      **kwargs):
    kwargs.update({'booking_id': booking_ids[0]})
    release_request_obj = create_release_request(member_id, requested_amounts, created_by,
                                                 organization_id=organization_id, **kwargs)
    actual_payment_data = actual_payment.create_actual_payment_data(member_id, booking_ids,
                                                                    requested_amounts,
                                                                    created_by,
                                                                    organization_id=organization_id,
                                                                    release_request_id=release_request_obj.id,
                                                                    **kwargs)
    actual_payment.record_actual_payments(actual_payment_data)
    return release_request_obj


def release(release_request):
    return None


def get_release_request_obj(release_request_id):
    return release_request.get_release_request_obj(release_request_id)


def update_release_request_status(release_request_id, status):
    return release_request.update_release_request_status(release_request_id, status)


def check_if_release_request_exist_for_booking(booking_id: int, released_request_status: str, **kwargs):
    return release_request.check_if_release_request_exist_for_booking(booking_id, released_request_status, **kwargs)


def create_release_request(member_id, requested_amounts, created_by, **kwargs):
    return release_request.create_release_request(member_id, requested_amounts, created_by, **kwargs)


def record_release_request_status_history(release_request_id: int, status: str, **kwargs):
    return release_request.record_release_request_status_history(release_request_id, status, **kwargs)


def get_pending_release_requests_by_organization_id_and_mode_of_release(organization_id, mode_of_release):
    return release_request.get_pending_release_requests_by_organization_id_and_mode_of_release(organization_id, mode_of_release)


def create_release_request_payment(release_request_obj, **request_data):
    return release_request.create_release_request_payment(release_request_obj, **request_data)


def get_total_requested_amount_by_release_request_ids(release_request_ids):
    return release_request.get_total_requested_amount_by_release_request_ids(release_request_ids)


def get_remittance_amount_for_release_request_payment(release_request_payment_obj):
    return release_request.get_remittance_amount_for_release_request_payment(release_request_payment_obj)


def get_amount_changed_due_to_fx_for_release_request_payment(release_request_payment_obj):
    return release_request.get_amount_changed_due_to_fx_for_release_request_payment(release_request_payment_obj)


def check_if_release_request_can_be_created(booking_obj, member_id, amount_in_collection_currency):
    return release_request.check_if_release_request_can_be_created(booking_obj, member_id, amount_in_collection_currency)
