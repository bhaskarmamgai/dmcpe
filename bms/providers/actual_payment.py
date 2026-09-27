
from bms.serializers.booking import ActualPaymentSerializer
from bms.models.actual_payment.actual_payment import ActualPayment
from django.db.models import Sum
from bms.models import BookingCharges


def record_actual_payments(actual_payment_data):
    error_msg = ""
    if actual_payment_data:
        actual_payment_objs = ActualPaymentSerializer(many=True, data=actual_payment_data)
        if actual_payment_objs.is_valid():
            return actual_payment_objs.save()
        else:
            error_msg += "<li>{}</li>".format(actual_payment_objs.errors)
            raise Exception(error_msg)


def get_actual_payment_objects_from_release_id(release_request_id):
    return ActualPayment.objects.filter(release_request_id=release_request_id)


def get_actual_payment_objects(booking_id, **kwargs):
    filters = {'booking_id': booking_id}
    fields = ['member_id', 'type', 'record_id', 'release_request_id']
    for field in fields:
        if field in kwargs:
            filters[field] = kwargs.get(field)

    return ActualPayment.objects.filter(**filters)


def get_total_amount_collected_for_given_booking_from_given_member(booking, member):
    qs = get_actual_payment_objects(booking.id, member_id=member.id,
                                    type=ActualPayment.PAID_BY_MEMBER)
    amount_collected = qs.aggregate(Sum('amount'))
    return amount_collected['amount__sum'] or 0


def check_if_first_claim(booking_obj):
    """
    To send One Time Booking Confirmation Mail Only Once
    Check if actual payments received  count is equal unity or 1
    """
    if booking_obj.actual_payments.filter(type=ActualPayment.PAID_BY_MEMBER).count() == 1:
        return True
    return False


def get_booking_charges_object_by_booking_id(booking_id):
    try:
        return BookingCharges.objects.get(booking_id=booking_id)
    except BookingCharges.DoesNotExist:
        return None
    except BookingCharges.MultipleObjectsReturned:
        return None
    return None
