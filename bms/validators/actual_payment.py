from django.shortcuts import reverse
from django.utils.safestring import mark_safe
import datetime
from bms.models import ActualPayment
from rest_framework import exceptions
from bms.services import actual_payment


def validate_actual_payment_data(member_id, booking_ids, payment_amounts, created_by,
                                 amount_in_member_currencies,
                                 **kwargs):
    error_msg = ""
    data = []
    total_payment_amount = 0
    for booking_id, amount, amount_in_member_currency in zip(booking_ids, payment_amounts,
                                                                 amount_in_member_currencies):
        pending_payment_dict = dict(
            *[d for d in kwargs.get('transaction_details') if int(d['booking_id']) == int(booking_id)])

        _amount_in_inr = pending_payment_dict.get('amount_in_inr', 0)
        _actual_payment_amount = pending_payment_dict.get('actual_payment', 0)
        _amount_including_actual_payment_amount = _actual_payment_amount + float(amount)
        if booking_id and amount:


            validate_amount_including_actual_payment_amount(booking_id,
                                                            _amount_in_inr, amount, _actual_payment_amount,
                                                            _amount_including_actual_payment_amount,
                                                            pending_payment_dict, **kwargs)

            if pending_payment_dict.get('due_amount'):

                if float(pending_payment_dict.get('due_amount')) >= float(amount):
                    data.append(dict({
                        'booking_id': booking_id,
                        'amount': amount,
                        'member_id': member_id,
                        'date': datetime.datetime.now().date(),
                        'type': kwargs.get('type'),
                        'record_id': kwargs.get('bank_record_id') if kwargs.get('bank_record_id') else None,
                        'created_by_id': created_by.id,
                        'organization_id': kwargs.get('organization_id') if kwargs.get('organization_id') else None,
                        'release_request_id': kwargs.get('release_request_id') if kwargs.get(
                            'release_request_id') else None,
                        'amount_in_member_currency': amount_in_member_currency,
                        'status': kwargs.get('actual_payment_status') if kwargs.get(
                            'actual_payment_status') else None
                    }))
                    total_payment_amount += float(amount)
                else:
                    error_msg += "<li>Payment Amount for Booking ID %s should Not be Greater than Due Amount "                                 "(Planned - Actual)</li><br>" % (booking_id)
                    raise exceptions.ValidationError(error_msg)
            else:
                error_msg += "<li>No Due Amount</li><br>"
                raise exceptions.ValidationError(error_msg)

    if kwargs.get('bank_record_id'):
        if abs(kwargs.get('bank_record_amount') - total_payment_amount) > 0:
            error_msg += "<li>Error : Total Payment Amount Must Match Amount in Bank Record</li><br>"
            raise exceptions.ValidationError(error_msg)
    return data


def validate_amount_including_actual_payment_amount(booking_id, _amount_in_inr,
                                                    amount, _actual_payment_amount,
                                                    _amount_including_actual_payment_amount,
                                                    pending_payment_dict, **kwargs):
    error_msg = ""
    booking_charges_obj = actual_payment.get_booking_charges_object_by_booking_id(booking_id)
    safe_fee = 0.0
    booking_loss = 0.0
    if booking_charges_obj:
        safe_fee = booking_charges_obj.safe_fee
        booking_loss = booking_charges_obj.booking_loss


    if kwargs.get('type') == ActualPayment.PAID_BY_MEMBER and _amount_in_inr + safe_fee < _amount_including_actual_payment_amount:
        error_msg += "Total Collected Amount i.e <strong>({}+{} = {})</strong> for Booking #{} should not be "                     "greater Amount IN INR + Safe Fee <strong>{}</strong><br>".format(
            _actual_payment_amount, float(amount), _amount_including_actual_payment_amount,
            mark_safe("<a href={}>{}</a>".format(
                reverse('admin:trs_booking_change', args=[pending_payment_dict.get('booking_id')
                                                              ]), pending_payment_dict.get('booking_id'))),
            _amount_in_inr + safe_fee)
        raise exceptions.ValidationError(error_msg)

    elif kwargs.get('type') == ActualPayment.PAID_TO_MEMBER and _amount_in_inr + booking_loss < _amount_including_actual_payment_amount:
        error_msg += "Total Payment Amount i.e <strong>({}+{} = {})</strong> for Booking #{} should not be "                     "greater Amount IN INR + Booking loss <strong>{}</strong><br>".format(
            _actual_payment_amount, float(amount), _amount_including_actual_payment_amount,
            mark_safe("<a href={}>{}</a>".format(
                reverse('admin:trs_booking_change', args=[pending_payment_dict.get('booking_id')
                                                              ]), pending_payment_dict.get('booking_id'))),
            _amount_in_inr + booking_loss)
        raise exceptions.ValidationError(error_msg)
