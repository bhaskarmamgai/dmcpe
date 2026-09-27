import datetime
from bms.models import Booking
from bms.providers import actual_payment as actual_payment_provider
from bms.validators import actual_payment
from bms.services.bookings import get_booking_object_from_id, calculate_amount_in_collection_currency_for_collection,    get_seller_cost_components_by_booking_code, calculate_amount_in_collection_currency_for_payment


def record_actual_payments(actual_payment_data):
    return actual_payment_provider.record_actual_payments(actual_payment_data)


def get_actual_payment_objects_from_release_id(release_request_id):
    return actual_payment_provider.get_actual_payment_objects_from_release_id(release_request_id)


def create_validated_actual_payment_data(member_id, booking_ids, amounts,
                                         claimed_by, amount_in_member_currencies, **kwargs):
    return actual_payment.validate_actual_payment_data(member_id, booking_ids, amounts,
                                                       claimed_by, amount_in_member_currencies, **kwargs)


def create_actual_payment_data(member_id, booking_ids, amounts,
                               created_by, **kwargs):
    actual_payment_data = []
    currency_id = kwargs.get('currency_id')
    collection_currency_id, booking_date, seller_cost_components, amount_in_collection_currency = None, None, None, 0
    for booking_id, amount in zip(booking_ids, amounts):
        booking_obj = get_booking_object_from_id(booking_id)
        if booking_obj.booking_version_type == Booking.V2:
            collection_currency_id = booking_obj.collection_currency.id
            booking_date = booking_obj.created_at
            if booking_obj.buyer.id == int(member_id):
                amount_in_collection_currency = calculate_amount_in_collection_currency_for_collection(
                        collection_currency_id, int(currency_id),
                        booking_date, amount) if currency_id and collection_currency_id else 0
            else:
                seller_cost_components = get_seller_cost_components_by_booking_code(booking_obj.code,
                                                                                    seller_member__id=member_id)
                amount_in_collection_currency = calculate_amount_in_collection_currency_for_payment(
                    collection_currency_id, amount, seller_cost_components)
        if booking_id and amount:
            actual_payment_data.append(dict({
                'booking_id': booking_id,
                'amount': amount,
                'amount_in_collection_currency': amount_in_collection_currency,
                'member_id': member_id,
                'member_currency_id': int(currency_id) if currency_id else None,
                'date': datetime.datetime.now().date(),
                'type': kwargs.get('type'),
                'record_id': kwargs.get('bank_record_id') if kwargs.get('bank_record_id') else None,
                'created_by_id': created_by.id,
                'release_request_id': kwargs.get('release_request_id') if kwargs.get(
                    'release_request_id') else None,
                'amount_in_member_currency': 0 if booking_obj.booking_version_type == Booking.V1 else amount,
                'status':kwargs.get('actual_payment_status'),
                'organization_id':kwargs.get('organization_id')
            }))
    return actual_payment_data


def check_if_first_claim(booking_obj):
    return actual_payment_provider.check_if_first_claim(booking_obj)


def get_booking_charges_object_by_booking_id(booking_id):
    return actual_payment_provider.get_booking_charges_object_by_booking_id(booking_id)
