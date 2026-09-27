from django.db import transaction
import datetime
from bms.models.actual_payment.actual_payment import ActualPayment
from bms.models.planned_payment.planned_payment import PlannedPayment

from bms.services import planned_payment, release_request, transaction_summary
from bms.services.wallet import release_request as wallet_release_request
from wallets.services import WalletServices
from bms.enums import RefundMode


@transaction.atomic
def process_refund(planned_payment_obj, created_by, release_mode, **kwargs):
    release_request.create_release_request_for_refund(planned_payment_obj.organization.id,
                                                      planned_payment_obj.member.id,
                                                      [planned_payment_obj.bookings.id],
                                                      [planned_payment_obj.amount], created_by,
                                                      description=get_default_description_for_refund(
                                                          planned_payment_obj.bookings.code, release_mode),
                                                      release_mode=release_mode,
                                                      actual_payment_status=ActualPayment.PENDING,
                                                      to_be_released_on=datetime.datetime.now().date(),
                                                      type=ActualPayment.PAID_TO_MEMBER,
                                                      organization_bank_account=kwargs.get('bank_account_id'),
                                                      currency_id=planned_payment_obj.member_currency.id if planned_payment_obj.member_currency else None)
    planned_payment.update_planned_payment_record_for_scheduled_collection([planned_payment_obj.bookings.id],
                                                                           planned_payment_obj.member.id)
    planned_payment.update_planned_payment_record_for_scheduled_payment([planned_payment_obj.bookings.id],
                                                                        planned_payment_obj.member.id)
    return True


@transaction.atomic
def process_refund_for_failed_booking(booking_obj, refund_amount, release_mode, **kwargs):
    planned_payment_record = planned_payment.create_planned_payment_record(booking_obj.id, [booking_obj.buyer.id],
                                                                           [booking_obj.buyer_organization.id],
                                                                           [refund_amount],
                                                                           [PlannedPayment.DUE_TO_MEMBER],
                                                                           currency_id=booking_obj.collection_currency.id,
                                                                           created_by_id=kwargs.get('created_by_id'))
    planned_payment_obj = planned_payment_record[0]
    release_request_obj = release_request.create_release_request_for_refund(planned_payment_obj.organization.id,
                                                                            planned_payment_obj.member.id,
                                                                            [planned_payment_obj.bookings.id],
                                                                            [planned_payment_obj.amount],
                                                                            booking_obj.created_by,
                                                                            description=get_default_description_for_refund(
                                                                                booking_obj.code, release_mode),
                                                                            release_mode=release_mode,
                                                                            actual_payment_status=ActualPayment.PENDING,
                                                                            to_be_released_on=datetime.datetime.now().date(),
                                                                            type=ActualPayment.PAID_TO_MEMBER,
                                                                            refund_mode=RefundMode.MANUAL_REFUND.value if kwargs else RefundMode.AUTO_REFUND.value,
                                                                            currency_id=booking_obj.collection_currency.id,
                                                                            **kwargs)
    wallet_obj = WalletServices.get_wallet_obj_by_organization_id(booking_obj.buyer_organization.id)
    wallet_release_request.release_via_add_to_wallet(release_request_obj,
                                                     wallet_obj)
    wallet_release_request.update_stats_on_post_approval_of_release_request(release_request_obj)
    planned_payment.update_planned_payment_record_for_scheduled_payment([planned_payment_obj.bookings.id],
                                                                        planned_payment_obj.member.id)
    return True


def get_default_description_for_refund(booking_code, release_mode: str) -> str:
    message = '[Refund through {}]::Against Booking {} At {}'.format(release_mode, booking_code,
                                                                     datetime.datetime.now().date())
    return message


def get_default_remark_for_bank_record_against_refund(planned_payment_obj: PlannedPayment) -> str:
    message = 'Refund against {}'.format(planned_payment_obj.bookings.code)
    return message


def validate_initiate_refund_tranche_request(planned_payment_id: int):
    _planned_payment_obj = planned_payment.get_planned_payment_object_by_planned_payment_id(planned_payment_id)
    _booking_summary_obj = transaction_summary.get_booking_summary_object_by_booking_id(
        _planned_payment_obj.bookings.id)
    _error_msg = None
    if _booking_summary_obj.net_hold < _planned_payment_obj.amount:
        _error_msg = 'Refund Tranche Amount <strong>{}</strong> Cant be Greater Than Net Hold Amount <strong>{}</strong>'.format(
            _planned_payment_obj.amount, _booking_summary_obj.net_hold)
        return False, _error_msg
    return True, _error_msg
