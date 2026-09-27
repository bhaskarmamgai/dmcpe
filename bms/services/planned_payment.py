from datetime import datetime
from dmcpesys.constants import CURRENCY_INR_ID
from bms.providers import planned_payment
from wallets.services import WalletServices as wallet
from members.services import OrganizationServices
from bms.models import PlannedPayment, Booking
from django.conf import settings


def update_planned_payment_record_for_scheduled_collection(booking_ids, member_id):
    return planned_payment.update_planned_payment_record_for_scheduled_collection(booking_ids, member_id)


def update_planned_payment_record_for_scheduled_payment(booking_ids, member_id):
    return planned_payment.update_planned_payment_record_for_scheduled_payment(booking_ids, member_id)


def create_planned_payment_record(booking_id: int, members_ids: list,organization_ids:list, amount: list, payment_types: list,**kwargs):
    return planned_payment.create_planned_payment_record(booking_id, members_ids,organization_ids, amount, payment_types,**kwargs)


def create_planned_payment_record_v2(booking_id: int, members_ids: list,organization_ids:list, amount: list, payment_types: list,**kwargs):
    return planned_payment.create_planned_payment_record_v2(booking_id, members_ids,organization_ids, amount, payment_types,**kwargs)


def update_planned_payment_status(status: str, planned_payment_id: int):
    return planned_payment.update_planned_payment_status(status, planned_payment_id)


def get_planned_payments_with_status_and_booking_id(status: str, booking_id: int):
    return planned_payment.get_planned_payments_with_status_and_booking_id(status, booking_id)


def get_planned_payment_object_by_planned_payment_id(planned_payment_id: int):
    return planned_payment.get_planned_payment_object_by_planned_payment_id(planned_payment_id)


def get_planned_payment_obj_by_booking_id(booking_id: int, **kwargs):
    return planned_payment.get_planned_payment_obj_by_booking_id(booking_id, **kwargs)


def add__due_amount__for_each_planned_payment__in_response(response):
    return planned_payment.add__due_amount__for_each_planned_payment__in_response(response)


def get_date_of__last_tranche__due_on_member__by_booking_id(booking_id):
    return planned_payment.get_date_of__last_tranche__due_on_member__by_booking_id(booking_id)


def get_planned_payments_by_booking_id_and_type(booking_id, type):
    return planned_payment.get_planned_payments_by_booking_id_and_type(booking_id, type)


def handle_save_planned_payments(booking_obj, tranch_data, **kwargs):
    if kwargs.get('type') == PlannedPayment.DUE_ON_MEMBER:
        _wallet_obj = wallet.get_wallet_obj_by_organization_id(booking_obj.buyer_organization.id)
        return planned_payment.create_planned_payment_record(booking_obj.id, [booking_obj.buyer.id],
                                                            [booking_obj.buyer_organization.id],
                                                            [tranch_data.get('amount')], [kwargs.get('type')],
                                                            currency_id=_wallet_obj.currency.id if hasattr(_wallet_obj, 'currency')                                                            else settings.DEFAULT_CURRENCY_ID,
                                                            date=tranch_data.get('date'),
                                                            payment_type = tranch_data.get('payment_type'),
                                                            created_by_id=kwargs.get('auth_id'))

    organization_obj = OrganizationServices.get_member_organization_by_member_id(member_id=tranch_data.get('member').get('id'))
    return planned_payment.create_planned_payment_record_v2(booking_obj.id, [str(tranch_data.get('member').get('id'))],
                                                            [organization_obj.id],
                                                            [tranch_data.get('amount')], [kwargs.get('type')],
                                                            currencies=[settings.DEFAULT_CURRENCY_ID],
                                                            due_dates=[tranch_data.get('date')],
                                                            payment_type=tranch_data.get('payment_type'),
                                                            created_by_id=kwargs.get('auth_id'))


def create_scheduled_payment_tranche_for_api_bookings(booking_obj, seller_cost_component):
    booking_id = booking_obj.id
    members_ids = [seller_cost_component.seller_member.id]
    organization_ids = [seller_cost_component.seller_organization.id]
    payment_types = [PlannedPayment.DUE_TO_MEMBER]
    amounts = [seller_cost_component.seller_net_payable_in_seller_currency]
    kwargs = {
        'due_dates': [booking_obj.created_at.date() if booking_obj.created_at else datetime.now()],
        'currencies': [CURRENCY_INR_ID],
        'created_by_id': booking_obj.created_by.id
    }

    return planned_payment.create_planned_payment_record_v2(booking_id, members_ids, organization_ids, amounts,
                                                            payment_types, **kwargs)
