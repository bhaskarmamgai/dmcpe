from django.db import transaction
from bms.services.wallet import actual_payment
from bms.providers.wallet import release_request as wallet_release_request_providers
from accounts.services import posting
from bms.models import ActualPayment, ReleaseRequest
from bms.services import transaction_summary, planned_payment, release_request
from django.conf import settings


def create_release_request(organization_id, member_id, requested_amounts, created_by, **kwargs):
    return wallet_release_request_providers.create_release_request(organization_id, member_id, requested_amounts,
                                                                   created_by, **kwargs)


def get_bookings_where_payment_release_is_due_in_given_date_range(selected_due_date: str, member_id: int,
                                                                  organization_id: int, booking_start_date: str,
                                                                  booking_end_date: str, **kwargs):
    return wallet_release_request_providers.get_bookings_where_payment_release_is_due_in_given_date_range(
        selected_due_date, member_id,
        organization_id, booking_start_date, booking_end_date, **kwargs)


def get_bookings_where_payment_release_is_due_in_given_date_range_for_version_2(selected_due_date: str, member_id: int,
                                                                                organization_id: int,
                                                                                booking_start_date: str,
                                                                                booking_end_date: str, **kwargs):
    return wallet_release_request_providers.get_bookings_where_payment_release_is_due_in_given_date_range_for_version_2(
        selected_due_date, member_id, organization_id, booking_start_date, booking_end_date, **kwargs)


def get_bookings_where_payment_release_is_due_in_given_date_range_v2(selected_due_date: str, member_id: int,
                                                                     organization_id: int, booking_start_date: str,
                                                                     booking_end_date: str, **kwargs):
    return wallet_release_request_providers.get_bookings_where_payment_release_is_due_in_given_date_range_v2(
        selected_due_date, member_id, organization_id, booking_start_date, booking_end_date, **kwargs)


def get_bookings_where_payment_release_is_due_in_given_date_range_v2_for_bmsv2(selected_due_date: str, member_id: int,
                                                                               organization_id: int,
                                                                               booking_start_date: str,
                                                                               booking_end_date: str, **kwargs):
    return wallet_release_request_providers.get_bookings_where_payment_release_is_due_in_given_date_range_v2_for_bmsv2(
        selected_due_date, member_id, organization_id, booking_start_date, booking_end_date, **kwargs)


@transaction.atomic
def create_release_request_for_collection(organization_id, member_id, booking_ids, requested_amounts, selected_due_date,
                                          created_by,
                                          **kwargs):
    booking_id = booking_ids[0]
    pending_booking_details = get_bookings_where_payment_release_is_due_in_given_date_range_v2_for_bmsv2(
        selected_due_date, member_id, organization_id, kwargs.get('booking_start_date'),
        kwargs.get('booking_end_date'), booking_id=booking_id)
    kwargs.update({'booking_id': booking_id})
    release_request_obj = create_release_request(organization_id, member_id, requested_amounts, created_by, **kwargs)
    actual_payment_data = actual_payment.create_validated_actual_payment_data(organization_id, member_id, booking_ids,
                                                                              requested_amounts,
                                                                              created_by,
                                                                              release_request_id=release_request_obj.id,
                                                                              pending_booking_details=pending_booking_details,
                                                                              **kwargs)
    actual_payment.record_actual_payments(actual_payment_data)
    return True, release_request_obj


@transaction.atomic
def release_via_bank_transfer(release_request_obj, wallet_obj):
    booking_ids = []
    transaction_codes = []
    for ap in release_request_obj.actual_payments.all():
        booking_ids.append(str(ap.booking.id))
        transaction_codes.append(ap.booking.code)
        actual_payment.update_actual_payment_object(id=ap.id, update_params={
            'status': ActualPayment.PAID})

    description = "Money released to wallet for booking(s): {}".format(", ".join(transaction_codes))
    technical_description = "[Bank Transfer] Payment approved against bookings(s) : {} for release request #{}".format(
        ", ".join(booking_ids), release_request_obj.id)
    posting.add_money_into_wallet(release_request_obj.organization.id, wallet_obj.id,
                                  release_request_obj.requested_amount, description,
                                  member_id=release_request_obj.member.id,
                                  technical_description=technical_description,
                                  currency_id=wallet_obj.currency.id if hasattr(wallet_obj,
                                                                                'currency') else settings.DEFAULT_CURRENCY_ID)
    description = "Request to pay to bank account for booking(s): {}".format(", ".join(transaction_codes))
    technical_description = "[Bank Transfer] Payment released against bookings(s) : {} for release request #{}".format(
        ", ".join(booking_ids), release_request_obj.id)
    posting.release_money_from_wallet(release_request_obj.organization.id, wallet_obj.id,
                                      release_request_obj.requested_amount, description,
                                      member_id=release_request_obj.member.id,
                                      technical_description=technical_description,
                                      currency_id=wallet_obj.currency.id if hasattr(wallet_obj,
                                                                                    'currency') else settings.DEFAULT_CURRENCY_ID)
    return True


@transaction.atomic
def release_via_add_to_wallet(release_request_obj, wallet_obj):
    booking_ids = []
    transaction_codes = []
    for ap in release_request_obj.actual_payments.all():
        booking_ids.append(str(ap.booking.id))
        transaction_codes.append(ap.booking.code)
        actual_payment.update_actual_payment_object(id=ap.id, update_params={
            'status': ActualPayment.PAID})
    technical_description = "[Add To Wallet] Payment approved against booking(s) : {} for release request #{}".format(
        ", ".join(booking_ids), release_request_obj.id)
    description = "Money released to wallet for booking(s): {}".format(", ".join(transaction_codes))
    posting.add_money_into_wallet(release_request_obj.organization.id, wallet_obj.id,
                                  release_request_obj.requested_amount, description,
                                  member_id=release_request_obj.member.id,
                                  technical_description=technical_description,
                                  currency_id=wallet_obj.currency.id if hasattr(wallet_obj,
                                                                                'currency') else settings.DEFAULT_CURRENCY_ID)
    return True


@transaction.atomic
def update_stats_on_post_approval_of_release_request(release_request_obj):
    release_request.update_release_request_status(release_request_obj.id, ReleaseRequest.RELEASED)
    transaction_summary.update_booking_summary_with_booking_objs(
        [i.booking for i in release_request_obj.actual_payments.all()])
    planned_payment.update_planned_payment_record_for_scheduled_payment(
        [i.booking.id for i in release_request_obj.actual_payments.all()], release_request_obj.member.id)
    return True
