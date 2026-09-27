from django.db.models import Q, Sum
from bms.models import BookingFinancial
from bms.models.booking.booking_summary import BookingSummary
from bms.models.actual_payment.actual_payment import ActualPayment
from bms.models.planned_payment.planned_payment import PlannedPayment
from bms.models.booking.booking import Booking
from members.enums import BUYER, SELLER
from bms.services.bookings import get_seller_cost_components_by_booking_code
from bms.services.release_request import get_remittance_amount_for_release_request_payment, \
    get_amount_changed_due_to_fx_for_release_request_payment


def booking_summary_update(booking: Booking):
    """
       Old Formula:
       net_hold: [Buyer(Paid_by)] - [Seller(Paid_to)],

       [New Revised Formulae]
       [Buyer(Paid_by - Paid_to)] - [Seller(Paid_to - Paid_by)]
    """
    obj, created = BookingSummary.objects.update_or_create(booking=booking, defaults={
        "net_hold": (get_amount_collected_v2(booking, BUYER) - get_amount_paid_v2(booking,
                                                                                  BUYER)) - (get_amount_paid_v2(
            booking, SELLER) - (get_amount_collected_v2(booking, SELLER))),
        "fx_profit_loss": get_fx_profit_loss(booking),
        "amount_collected_from_buyer": get_amount_collected_v2(booking, BUYER),
        "amount_pending_for_collection_from_buyer": get_amount_pending_for_collection_v2(booking, BUYER),
        "amount_paid_to_seller": get_amount_paid_v2(booking, SELLER),
        "amount_paid_to_buyer": get_amount_paid_v2(booking, BUYER)
    })


def get_amount_scheduled_for_collection(booking: Booking, member_type: str):
    if booking.planned_payments.all().exists():
        pending_amount = booking.planned_payments.filter(
            member=booking.buyer if member_type == BUYER else booking.seller,
            type=PlannedPayment.DUE_ON_MEMBER).exclude(Q(
            payment_type=PlannedPayment.DIRECT_PAYMENT) | Q(status=PlannedPayment.CANCELLED)).aggregate(Sum('amount'))
        return pending_amount['amount__sum'] or 0
    return 0


def get_amount_scheduled_for_collection_v2(booking: Booking, member_type: str):
    sellers = [cost_component.seller_member for cost_component in
               get_seller_cost_components_by_booking_code(booking.code)]
    if booking.planned_payments.all().exists():
        pending_amount = booking.planned_payments.filter(
            member__in=[booking.buyer] if member_type == BUYER else sellers,
            type=PlannedPayment.DUE_ON_MEMBER).exclude(Q(
            payment_type=PlannedPayment.DIRECT_PAYMENT) | Q(status=PlannedPayment.CANCELLED)).aggregate(Sum('amount'))
        return pending_amount['amount__sum'] or 0
    return 0


def get_amount_pending_for_collection(booking: Booking, member_type: str):
    scheduled_amount = get_amount_scheduled_for_collection(booking, member_type)
    collected_amount = get_amount_collected(booking, member_type)
    return max(scheduled_amount - collected_amount, 0)


def get_amount_scheduled_for_payment(booking: Booking, member_type: str):
    if booking.planned_payments.all().exists():
        pending_payment = booking.planned_payments.filter(
            member=booking.buyer if member_type == BUYER else booking.seller,

            type=PlannedPayment.DUE_TO_MEMBER).exclude(Q(
            payment_type=PlannedPayment.DIRECT_PAYMENT) | Q(status=PlannedPayment.CANCELLED)).aggregate(Sum('amount'))
        return pending_payment['amount__sum'] or 0
    return 0


def get_amount_pending_for_payment(booking: Booking, member_type: str):
    scheduled_amount = get_amount_scheduled_for_payment(booking, member_type)
    paid_amount = get_amount_paid(booking, member_type)
    return max(scheduled_amount - paid_amount, 0)


def get_amount_paid(booking: Booking, member_type: str):
    if booking.actual_payments.all().exists():
        amount_paid = booking.actual_payments.filter(
            member=booking.buyer if member_type == BUYER else booking.seller,
            type=ActualPayment.PAID_TO_MEMBER,
            status=ActualPayment.PAID).aggregate(
            Sum('amount'))
        return amount_paid['amount__sum'] or 0
    return 0


def get_amount_paid_v2(booking: Booking, member_type: str):
    sellers = [cost_component.seller_member for cost_component in
               get_seller_cost_components_by_booking_code(booking.code)]
    if booking.actual_payments.all().exists():
        amount_paid = booking.actual_payments.filter(
            member__in=[booking.buyer] if member_type == BUYER else sellers,
            type=ActualPayment.PAID_TO_MEMBER,
            status=ActualPayment.PAID).aggregate(
            Sum('amount_in_collection_currency'))
        return amount_paid['amount_in_collection_currency__sum'] or 0
    return 0


def get_amount_collected(booking: Booking, member_type: str):
    if booking.actual_payments.all().exists():
        amount_collected = booking.actual_payments.filter(
            member=booking.buyer if member_type == BUYER else booking.seller,
            type=ActualPayment.PAID_BY_MEMBER,
            status=ActualPayment.COLLECTED,
        ).aggregate(Sum('amount'))
        return amount_collected['amount__sum'] or 0
    return 0


def get_amount_collected_v2(booking: Booking, member_type: str):
    sellers = [cost_component.seller_member for cost_component in
               get_seller_cost_components_by_booking_code(booking.code)]
    if booking.actual_payments.all().exists():
        amount_collected = booking.actual_payments.filter(
            member__in=[booking.buyer] if member_type == BUYER else sellers,
            type=ActualPayment.PAID_BY_MEMBER,
            status=ActualPayment.COLLECTED,
        ).aggregate(Sum('amount_in_collection_currency'))
        return amount_collected['amount_in_collection_currency__sum'] or 0
    return 0


def get_amount_pending_for_collection_v2(booking: Booking, member_type: str):
    scheduled_amount = get_amount_scheduled_for_collection_v2(booking, member_type)
    collected_amount = get_amount_collected_v2(booking, member_type)
    return max(scheduled_amount - collected_amount, 0)


def update_review_stats(booking_id: int, data_dict):
    """As relation is O2O"""
    booking_summary_object, created = BookingSummary.objects.update_or_create(booking_id=booking_id,
                                                                              defaults=data_dict)
    return booking_summary_object or created


def get_booking_summary_object_by_booking_id(booking_id: int):
    return BookingSummary.objects.get(booking_id=booking_id)


def get_net_hold_in_member_currency(booking: Booking):
    """
    NetHold Member Currency = [Sum of all Amount in Member Currency Under Actual Collection] - [Sum of all Amount in member currency under Actual Payment]
    :param booking:
    :return:
    """
    return round(
        get_sum_of_actual_collection_in_member_currency(booking) - get_sum_of_actual_payment_in_member_currency(
            booking))


def get_sum_of_actual_collection_in_member_currency(booking: Booking):
    if booking.actual_payments.all().exists():
        amount_collected = booking.actual_payments.filter(
            type=ActualPayment.PAID_BY_MEMBER,
            status=ActualPayment.COLLECTED,
        ).aggregate(Sum('amount_in_member_currency'))
        return amount_collected['amount_in_member_currency__sum'] or 0
    return 0


def get_sum_of_actual_payment_in_member_currency(booking: Booking):
    if booking.actual_payments.all().exists():
        amount_collected = booking.actual_payments.filter(
            type=ActualPayment.PAID_TO_MEMBER,
            status=ActualPayment.PAID,
        ).aggregate(Sum('amount_in_member_currency'))
        return amount_collected['amount_in_member_currency__sum'] or 0
    return 0


def get_remit_profit_loss_ration(booking: Booking):
    """
    Remit P/L (Realised) - New field under Booking summary
    [Sum of all “Amount” under Actual Payment] - [Sum of all “Actual amount released including charges” under Actual Payment]
    :param booking:
    :return:
    """

    actual_payment_sum = get_amount_paid(booking, SELLER) + get_amount_paid(booking, BUYER)
    _sum_actual_payment_including_charges = 0
    actual_payments_objects = booking.actual_payments.all()
    if actual_payments_objects.exists():
        for actual_payment_object in actual_payments_objects:
            if hasattr(actual_payment_object, 'seller_actual_payment_charges'):
                _sum_actual_payment_including_charges += getattr(actual_payment_object,
                                                                 'seller_actual_payment_charges').actual_amount_released_including_charges
    return round(actual_payment_sum - _sum_actual_payment_including_charges, 2)


def get_fx_profit_loss(booking):
    try:
        booking_summary_obj = BookingSummary.objects.get(booking=booking)
        return booking_summary_obj.fx_profit_loss
    except:
        booking_financial_obj = BookingFinancial.objects.get(booking=booking)
        return booking_financial_obj.net_profit


def get_booking_summary_object_for_update_by_booking_id(booking_id: int):
    try:
        return BookingSummary.objects.filter(booking_id=booking_id).select_for_update().get()
    except BookingSummary.DoesNotExist:
        return None
    except BookingSummary.MultipleObjectsReturned:
        return None


def update_fx_profit_loss_for_booking(release_request_payment_obj, prev_instance):
    booking = release_request_payment_obj.booking
    try:
        booking_summary_obj = BookingSummary.objects.get(booking=booking)
        remittance_amount = get_remittance_amount_for_release_request_payment(release_request_payment_obj)
        amount_changed_due_to_fx = get_amount_changed_due_to_fx_for_release_request_payment(release_request_payment_obj)
        fx_profit_loss = booking.booking_financial.net_profit if booking_summary_obj.fx_profit_loss is None else booking_summary_obj.fx_profit_loss
        if not prev_instance:
            booking_summary_obj.fx_profit_loss = fx_profit_loss - remittance_amount - amount_changed_due_to_fx
            booking_summary_obj.save()
        else:
            old_remittance_amount = get_remittance_amount_for_release_request_payment(prev_instance)
            old_amount_changed_due_to_fx = get_amount_changed_due_to_fx_for_release_request_payment(prev_instance)
            new_remittance_amount = remittance_amount - old_remittance_amount
            new_amount_changed_due_to_fx = amount_changed_due_to_fx - old_amount_changed_due_to_fx
            booking_summary_obj.fx_profit_loss = fx_profit_loss - new_remittance_amount - new_amount_changed_due_to_fx
            booking_summary_obj.save()
    except Exception as e:
        print(e)
