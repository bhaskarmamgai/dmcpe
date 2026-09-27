import datetime
from django.utils.safestring import mark_safe
from django.shortcuts import reverse
from bms.config.base import SELLER_COST_COMPONENT_CANCELLED_ID
from bms.models import SellerCostComponent
from common.libraries import get_round_off_amount
from bms.models import ActualPayment, Booking
from bms.services import actual_payment
from rest_framework import exceptions
from bms.services.bookings import calculate_amount_in_collection_currency_for_collection, get_booking_object_from_id, \
    calculate_amount_in_collection_currency_for_payment
from datetime import datetime


def validate_actual_payment_data(organization_id, member_id, booking_ids, payment_amounts, created_by,
                                 **kwargs):
    print("=== START validate_actual_payment_data ===")
    print("organization_id:", organization_id)
    print("member_id:", member_id)
    print("booking_ids:", booking_ids)
    print("payment_amounts:", payment_amounts)
    print("currency_id:", kwargs.get('currency_id'))
    print("pending_booking_details:", kwargs.get('pending_booking_details'))

    error_msg = ""
    data = []
    total_payment_amount = 0
    currency_id = kwargs.get('currency_id')


    for booking_id, amount in zip(booking_ids, payment_amounts):

        print("\n--- LOOP START ---")
        print("booking_id:", booking_id)
        print("amount:", amount)

        pending_list = [d for d in kwargs.get('pending_booking_details') if int(d['booking_id']) == int(booking_id)]
        print("matching pending_list:", pending_list)

        if not pending_list:
            print("❌ No matching pending_booking_details found for booking_id:", booking_id)
            continue

        pending_payment_dict = dict(*pending_list)
        print("pending_payment_dict:", pending_payment_dict)

        if booking_id and amount:
            booking_obj = get_booking_object_from_id(booking_id)
            print("booking_obj:", booking_obj)

            collection_currency_id = booking_obj.collection_currency.id
            booking_date = booking_obj.created_at

            print("collection_currency_id:", collection_currency_id)
            print("booking_date:", booking_date)

            if pending_payment_dict.get('due_amount'):
                print("due_amount:", pending_payment_dict.get('due_amount'))

                if booking_obj.buyer.id == int(member_id):
                    print("Flow: Buyer")
                    amount_in_collection_currency = calculate_amount_in_collection_currency_for_collection(
                        collection_currency_id, currency_id,
                        booking_date, float(amount)
                    ) if currency_id and collection_currency_id else None
                else:
                    print("Flow: Seller")
                    seller_cost_components = SellerCostComponent.objects.filter(
                        seller_member__id=member_id, booking__code=booking_obj.code
                    ).exclude(
                        seller_status__id=SELLER_COST_COMPONENT_CANCELLED_ID
                    )

                    print("seller_cost_components:", seller_cost_components)

                    amount_in_collection_currency = calculate_amount_in_collection_currency_for_payment(
                        collection_currency_id, float(amount), seller_cost_components
                    )

                print("amount_in_collection_currency:", amount_in_collection_currency)

                due_amt = float(pending_payment_dict.get('due_amount'))
                print("Rounded due:", get_round_off_amount(due_amt, collection_currency_id))
                print("Rounded amount:", get_round_off_amount(float(amount), collection_currency_id))

                if get_round_off_amount(due_amt, collection_currency_id) >= \
                        get_round_off_amount(float(amount), collection_currency_id):

                    print("✅ Amount valid, appending data")

                    data.append(dict({
                        'booking_id': booking_id,
                        'amount': float(amount),
                        'amount_in_collection_currency': amount_in_collection_currency,
                        'member_currency_id': int(currency_id) if currency_id else None,
                        'member_id': member_id,
                        'organization_id': organization_id,
                        'date': datetime.now().date(),
                        'type': kwargs.get('type'),
                        'posting_id': kwargs.get('posting_id') if kwargs.get('bank_record_id') else None,
                        'record_id': kwargs.get('bank_record_id') if kwargs.get('bank_record_id') else None,
                        'release_request_id': kwargs.get('release_request_id') if kwargs.get(
                            'release_request_id') else None,
                        'created_by_id': created_by.id,
                        'amount_in_member_currency':  amount,
                        'status': kwargs.get('actual_payment_status') if kwargs.get('actual_payment_status') else None,
                    }))

                    total_payment_amount += float(amount)

                else:
                    print("❌ Amount greater than due")
                    error_msg += "<li>payment Amount for booking_id %s should Not be Greater than Due Amount</li><br>" % (
                        booking_id)
                    raise exceptions.ValidationError(error_msg)

            else:
                print("❌ due_amount missing or None")
                error_msg += "<li>No Due Amount</li><br>"
                raise exceptions.ValidationError(error_msg)

    print("\n=== LOOP END ===")
    print("Final data:", data)
    print("Total payment amount:", total_payment_amount)

    if kwargs.get('wallet_balance'):
        print("wallet_balance:", kwargs.get('wallet_balance'))

        if abs(kwargs.get('wallet_balance')) < total_payment_amount:
            print("❌ Wallet balance insufficient")
            error_msg += "<li>Error : Total Claim Payment Amount {} Cant be Greater than available balance {} in wallet</li><br>".format(
                total_payment_amount, abs(kwargs.get('wallet_balance')))
            raise exceptions.ValidationError(error_msg)

    print("=== RETURNING DATA ===")
    return data


def validate_amount_including_actual_payment_amount(booking_id, amount,
                                                    pending_payment_dict, **kwargs):
    error_msg = ""
    booking_charges_obj = actual_payment.get_booking_charges_object_by_booking_id(booking_id)
    safe_fee = 0.0
    booking_loss = 0.0
    safe_collect_fee = 0.0
    if booking_charges_obj:
        safe_fee = booking_charges_obj.safe_fee
        booking_loss = booking_charges_obj.booking_loss
        safe_collect_fee = booking_charges_obj.safe_collect_fee

    _amount_in_inr = pending_payment_dict.get('amount_in_inr', 0)
    _actual_payment_amount = pending_payment_dict.get('actual_payment', 0)
    _amount_including_actual_payment_amount = _actual_payment_amount + float(amount)

    if kwargs.get(
            'type') == ActualPayment.PAID_BY_MEMBER and _amount_in_inr + safe_fee < _amount_including_actual_payment_amount:
        error_msg += "Total Collected Amount i.e <strong>({}+{} = {})</strong> for Booking #{} should not be "                     "greater Amount IN INR + Safe Fee <strong>{}</strong><br>".format(
            _actual_payment_amount, float(amount), _amount_including_actual_payment_amount,
            mark_safe("<a href={}>{}</a>".format(
                reverse('admin:trs_booking_change', args=[pending_payment_dict.get('booking_id')
                                                          ]), pending_payment_dict.get('booking_id'))),
            _amount_in_inr + safe_fee)
        raise exceptions.ValidationError(error_msg)



    elif kwargs.get(
            'type') == ActualPayment.PAID_TO_MEMBER and _amount_in_inr + booking_loss - safe_collect_fee < _amount_including_actual_payment_amount:
        error_msg += "Total Payment Amount i.e <strong>({}+{} = {})</strong> for Booking #{} should not be "                     "greater than Amount IN INR + Booking loss - Collect Fee <strong>{}</strong><br>".format(
            _actual_payment_amount, float(amount), _amount_including_actual_payment_amount,
            mark_safe("<a href={}>{}</a>".format(
                reverse('admin:trs_booking_change', args=[pending_payment_dict.get('booking_id')
                                                          ]), pending_payment_dict.get('booking_id'))),
            _amount_in_inr + booking_loss - safe_collect_fee)
        raise exceptions.ValidationError(error_msg)
