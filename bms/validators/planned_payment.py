from bms.services.bookings import get_booking_object_from_code
from bms.services.planned_payment import get_planned_payments_by_booking_id_and_type
from bms.models import PlannedPayment, Booking, SellerCostComponent
import math
from django.db.models import Sum
from common.libraries import get_round_off_amount



def get_safe_fee_from_booking_object(booking_obj):
    return booking_obj.booking_charges.safe_fee        if hasattr(booking_obj, 'booking_charges') else 0

def get_booking_financial_v2_obj(booking_obj):
    return booking_obj.booking_financial_v2 if hasattr(booking_obj, 'booking_financial_v2') else None

def get_service_charge_collected_from_buyer(booking_obj):
    return booking_obj.booking_charges.service_charge_collected_from_buyer        if hasattr(booking_obj, 'booking_charges') else 0

def get_roe_on_booking_date(booking_obj):
    return booking_obj.booking_charges.roe_on_booking_date        if hasattr(booking_obj, 'booking_charges') else 1

def get_convenience_charges_on_roe(booking_obj):
    return booking_obj.booking_charges.convenience_charges_on_roe        if hasattr(booking_obj, 'booking_charges') else 0

def get_booking_loss_from_booking_object(booking_obj):
        return booking_obj.booking_charges.booking_loss            if hasattr(booking_obj, 'booking_charges') else 0

def get_safe_collect_fee_from_booking_object(booking_obj):
        return booking_obj.booking_charges.safe_collect_fee            if hasattr(booking_obj, 'booking_charges') else 0


def get_total_amount_of_seller_cost_component_member(member_id,code):
    return  SellerCostComponent.objects.filter(seller_member__id=member_id, booking__code=code).aggregate(total=Sum('seller_net_payable_in_seller_currency'))['total']



def validate_schedule_collection_data(request_data, **kwargs):
    booking_obj = get_booking_object_from_code(kwargs.get('booking_code'))
    if not booking_obj:
        return False, "Booking Does Not Exists For Booking Code {}".format(kwargs.get('booking_code'))

    planned_payment_qs = get_planned_payments_by_booking_id_and_type(booking_obj.id, type=PlannedPayment.DUE_ON_MEMBER)
    total_schedule_collection_amount = 0
    for payment in planned_payment_qs:
        if payment and payment.payment_type                in [PlannedPayment.TRANCHE, PlannedPayment.DIRECT_PAYMENT] and                payment.status in [PlannedPayment.PENDING, PlannedPayment.COLLECTED]:
            total_schedule_collection_amount += payment.amount

    for data in request_data.get('data'):
        if data.get('payment_type') is not None and data.get('payment_type')                in [PlannedPayment.TRANCHE, PlannedPayment.DIRECT_PAYMENT]:
            total_schedule_collection_amount += data.get('amount')
    if booking_obj.booking_financial.total_net_receivable < total_schedule_collection_amount:
        return False, "Sum of all Schedule Collections - Trance and Direct Payment should be equal to / less than Total Net Receivable (Collection Currency)"
    if booking_obj.booking_version_type == Booking.V2:
        if booking_obj.status == Booking.CONFIRMED and hasattr(booking_obj, 'booking_financial') and total_schedule_collection_amount >0 and  total_schedule_collection_amount != booking_obj.booking_financial_v2.total_net_receivable:
            return False, "Sum of all Schedule collections- Tranche and Direct Payment should be equal to Total Net Receivable (Collection Currency)"



    if booking_obj.booking_version_type == Booking.V1:
        if booking_obj.status == Booking.CONFIRMED and not total_schedule_collection_amount == booking_obj.amount_in_inr + get_safe_fee_from_booking_object(booking_obj):
            return False, "Sum of all Schedule collections- Tranche and Direct Payment should be"                                    "equal to the sum of amount in INR and Safe Fee."
        amount_in_inr = math.ceil(round(booking_obj.amount + get_service_charge_collected_from_buyer(booking_obj)) * (get_roe_on_booking_date(booking_obj) + get_convenience_charges_on_roe(booking_obj)))
        if total_schedule_collection_amount > amount_in_inr + get_safe_fee_from_booking_object(booking_obj):
            return False, "Sum of all Schedule collections- Tranche and Direct Payment should "                                    "not be greater than the sum of amount in INR and Safe Fee."
    return booking_obj, None



def validate_schedule_payment_data(request_data, **kwargs):
    booking_obj = get_booking_object_from_code(kwargs.get('booking_code'))
    if not booking_obj:
        return False, "Booking Does Not Exists For Booking Code {}".format(kwargs.get('booking_code'))

    planned_payment_qs = get_planned_payments_by_booking_id_and_type(booking_obj.id, type=PlannedPayment.DUE_TO_MEMBER)
    total_schedule_payment_amount = 0
    scheduled_payments_member_ids_with_amounts = dict()
    for payment in planned_payment_qs:
        schedule_payment_member_id = payment.member_id
        if payment and payment.payment_type in [PlannedPayment.TRANCHE, PlannedPayment.DIRECT_PAYMENT] and                payment.status in [PlannedPayment.PENDING, PlannedPayment.PAID]:
            if schedule_payment_member_id in scheduled_payments_member_ids_with_amounts:
                    scheduled_payments_member_ids_with_amounts[schedule_payment_member_id] += payment.amount
            else:
                scheduled_payments_member_ids_with_amounts[schedule_payment_member_id] = payment.amount
            total_schedule_payment_amount += payment.amount

    for data in request_data.get('data'):
        schedule_payment_member_id = data.get('member').get('id')
        if 'amount' in data and float(data.get('amount')) == 0.0:
            return False, "Schedule Payment with 0 amount is not applicable"

        if data.get('payment_type') is not None and data.get('payment_type')                in [PlannedPayment.TRANCHE, PlannedPayment.DIRECT_PAYMENT]:
            if schedule_payment_member_id in scheduled_payments_member_ids_with_amounts:
                scheduled_payments_member_ids_with_amounts[schedule_payment_member_id] += data.get('amount')
            else:
                scheduled_payments_member_ids_with_amounts[schedule_payment_member_id] = data.get('amount')
            total_schedule_payment_amount += data.get('amount')

    if booking_obj.booking_version_type == Booking.V1:
        if booking_obj.status == Booking.CONFIRMED and not total_schedule_payment_amount == booking_obj.amount_in_inr + get_booking_loss_from_booking_object(booking_obj) - get_safe_collect_fee_from_booking_object(booking_obj):
            return False, "Sum of all Schedule Payments- Tranche and Direct Payment should be equal to the sum of amount in INR "                            "and Booking loss minus Collect Fee (Supplier)"

    else:
        for data in request_data.get('data'):
            if not data.get('member') or not data.get('member').get('id'):
                return False, "Member is Required"
            if not data.get('date'):
                return False, "Date is Required"
        for member_id, amount in scheduled_payments_member_ids_with_amounts.items():
            schedule_payment_member_id = member_id
            calculated_total_amount = get_total_amount_of_seller_cost_component_member(schedule_payment_member_id,
                                                                                       booking_obj.code)
            if get_round_off_amount(calculated_total_amount) < get_round_off_amount(amount):
                return False, "Sum of all Schedule Payments - Tranche and Direct Payment should be equal to the respective seller's sum of Net Payable to Seller (Seller Currency) "
            pass
    return booking_obj, None



def validate_create_schedule_collection_data(request_data , **kwargs):
    pass


def validate_create_schedule_payment_data(request_data , **kwargs):
    pass