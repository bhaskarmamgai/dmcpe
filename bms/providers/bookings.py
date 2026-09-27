import datetime
from bms.models.planned_payment import PlannedPayment
from dmcpesys.constants import CURRENCY_INR_ID, CATEGORY_FLIGHT_ID
from datetime import date
from django.conf import settings
from django.db import connection
import math
from dmcpesys import constants
from bms.services import flight_details
from dmcpesys.services import get_current_roe_for_currency_by_currency_id, get_roe_and_markup_by_currency
from common.libraries import get_dates_by_range, get_round_off_amount
from members.models import Member
from bms.models import Booking, BookingFinancial, ApprovedDiscount, BookingSummary
from bms.enums import CONFIRMED
from django.db.models import Q
from bms.models.seller_cost_component.seller_cost_component import SellerCostComponent
from members.services import OrganizationServices as organization
from wallets.services import WalletServices as wallet
from django.db.models import Sum
from bms.config.base import SELLER_COST_COMPONENT_CANCELLED_ID


def get_transactions_for_review(max_transaction_count: int, reviewer_type: str, departure_date: date,
                                num_of_day_since_trip_end: int):
    transaction_reviewer_field_id = (Member.BUYER + "_id") if reviewer_type == Member.BUYER else (Member.SELLER + "_id")

    qs = Booking.objects.raw(
        "SELECT * "
        "FROM bms_booking as t "
        "WHERE t.deleted = 0 "
        "AND t.%s NOT IN (SELECT r.given_by_id FROM reviews_review as r "
        "WHERE r.booking_id = t.id and r.deleted = 0) "
        "AND ('%s'::date - (departure_at + COALESCE(nights_count, 0) * interval '1 day')::date) = %s "
        "LIMIT %s" % (transaction_reviewer_field_id, departure_date, num_of_day_since_trip_end, max_transaction_count))
    return qs


def get_transactions_count(**kwargs):
    qs = Booking.objects.filter(deleted=False)

    if 'date_range' in kwargs:
        begin_date, end_date = get_dates_by_range(kwargs['date_range'])
        qs = qs.filter(booking_date__gte=begin_date).filter(booking_date__lte=end_date)

    if Member.BUYER in kwargs:
        qs = qs.filter(buyer=kwargs[Member.BUYER])

    if Member.SELLER in kwargs:
        qs = qs.filter(seller=kwargs[Member.SELLER])

    return qs.count()


def get_transactions_count_for_organization(**kwargs):
    qs = Booking.objects.filter(deleted=False)

    if 'date_range' in kwargs:
        begin_date, end_date = get_dates_by_range(kwargs['date_range'])
        qs = qs.filter(booking_date__gte=begin_date).filter(booking_date__lte=end_date)

    if "buyer_organization" in kwargs:
        qs = qs.filter(buyer_organization=kwargs["buyer_organization"])

    if "seller_organization" in kwargs:
        qs = qs.filter(seller_organization=kwargs["seller_organization"])

    return qs.count()


def update_transactions_stats_last_30days_count():
    begin_date, end_date = get_dates_by_range("last_30days")
    with connection.cursor() as cursor:
        buyer_query = "UPDATE members_memberstatistics ms " \
                      "SET buyer_transactions_count_last_30days = COALESCE(tt.cnt, 0) " \
                      "FROM members_memberstatistics ms_all " \
                      "LEFT JOIN (SELECT buyer_id, count(id) as cnt " \
                      "FROM bms_booking " \
                      "WHERE deleted=0 " \
                      "AND booking_date >= %s " \
                      "AND booking_date <= %s " \
                      "GROUP BY buyer_id) tt " \
                      "ON ms_all.member_id = tt.buyer_id " \
                      "WHERE ms.id = ms_all.id "

        cursor.execute(buyer_query, [begin_date, end_date])

        seller_query = "UPDATE members_memberstatistics ms " \
                       "SET seller_transactions_count_last_30days = COALESCE(tt.cnt, 0) " \
                       "FROM members_memberstatistics ms_all " \
                       "LEFT JOIN (SELECT seller_id, count(id) as cnt " \
                       "FROM bms_booking " \
                       "WHERE deleted=0 " \
                       "AND booking_date >= %s " \
                       "AND booking_date <= %s " \
                       "GROUP BY seller_id) tt " \
                       "ON ms_all.member_id = tt.seller_id " \
                       "WHERE ms.id = ms_all.id "

        cursor.execute(seller_query, [begin_date, end_date])


def update_transactions_organization_stats_last_30days_count():
    begin_date, end_date = get_dates_by_range("last_30days")
    with connection.cursor() as cursor:
        buyer_query = "UPDATE organization_organizationstatistics os " \
                      "SET buyer_organization_bookings_count_last_30days = COALESCE(tt.cnt, 0) " \
                      "FROM organization_organizationstatistics os_all " \
                      "LEFT JOIN (SELECT buyer_organization_id, count(id) as cnt " \
                      "FROM bms_booking " \
                      "WHERE deleted=0 " \
                      "AND booking_date >= %s " \
                      "AND booking_date <= %s " \
                      "GROUP BY buyer_organization_id) tt " \
                      "ON os_all.organization_id = tt.buyer_organization_id " \
                      "WHERE os.id = os_all.id "
        cursor.execute(buyer_query, [begin_date, end_date])

        seller_query = "UPDATE organization_organizationstatistics os " \
                       "SET seller_organization_bookings_count_last_30days = COALESCE(tt.cnt, 0) " \
                       "FROM organization_organizationstatistics os_all " \
                       "LEFT JOIN (SELECT seller_organization_id, count(id) as cnt " \
                       "FROM bms_booking " \
                       "WHERE deleted=0 " \
                       "AND booking_date >= %s " \
                       "AND booking_date <= %s " \
                       "GROUP BY seller_organization_id) tt " \
                       "ON os_all.organization_id = tt.seller_organization_id " \
                       "WHERE os.id = os_all.id "
        cursor.execute(seller_query, [begin_date, end_date])


def render_to_pdf_locally(template_src, context_dict={}, filename=None):
    return None


def get_booking_object_from_id(booking_id):
    return Booking.objects.get(id=booking_id)


def get_booking_object_from_code(booking_code):
    try:
        return Booking.objects.get(code=booking_code)
    except Booking.DoesNotExist:
        return None


def update_booking_status(status: str, booking_id: int):
    booking_obj = Booking.objects.get(id=booking_id)
    booking_obj.status = status
    return booking_obj.save()


def update_booking(booking_id: int, **kwargs):
    qs = Booking.objects.filter(id=booking_id)
    qs.update(**kwargs)
    return qs


def update_amount(booking_obj):
    """
    Amount in INR =  (Amount+Bank Charge) x ( Xe.com RoE+ Convenience Charges On RoE)
    """
    booking_queryset = booking_obj.__class__.objects.filter(pk=booking_obj.pk)
    booking_queryset_obj = booking_queryset.last() if hasattr(booking_queryset.last(),
                                                              'booking_charges') else booking_obj

    if hasattr(booking_queryset_obj, 'booking_charges'):
        booking_queryset.update(amount_in_inr=math.ceil(round(
            ((
                     booking_queryset_obj.amount + booking_queryset_obj.booking_charges.service_charge_collected_from_buyer) * (
                     booking_queryset_obj.booking_charges.roe_on_booking_date + booking_queryset_obj.booking_charges.convenience_charges_on_roe)),
            2)),
            amount_in_collection_currency=get_round_off_amount(
                (float(
                    booking_queryset_obj.amount) + booking_queryset_obj.booking_charges.service_charge_collected_from_buyer) * (
                        booking_queryset_obj.booking_charges.roe_on_booking_date + booking_queryset_obj.booking_charges.convenience_charges_on_roe),
                booking_queryset_obj.collection_currency.id if booking_queryset_obj.collection_currency else None,
                True))
    else:
        if booking_queryset_obj.amount_in_inr and booking_queryset_obj.created_by.username == settings.API_USER:
            return True
        booking_queryset.update(amount_in_inr=booking_queryset_obj.amount)
    return True


def calculate_amount_in_inr(current_roe_object, amount, currency_id):
    if currency_id is not CURRENCY_INR_ID:
        return math.ceil(current_roe_object.total_roe * amount)
    return amount




def get_booking_title_by_booking_obj(booking_obj, title):
    if not booking_obj.category:
        return None
    category_id = booking_obj.category.id
    if category_id == constants.CATEGORY_HOTEL_ID:
        return "Hotel Booking"
    if category_id == constants.CATEGORY_FLIGHT_ID:
        flight_detail_obj = flight_details.get_flight_details_by_booking_id(booking_obj.id)
        return "{origin} - {destination}".format(origin=flight_detail_obj.from_airport.code,
                                                 destination=flight_detail_obj.to_airport.code) if flight_detail_obj else None
    if category_id == constants.CATEGORY_PACKAGE_ID or category_id == constants.CATEGORY_FIXED_DEPARTURE_ID or category_id == constants.CATEGORY_STANDARD_ITINERARY_ID:
        return "{night_count}N {destination_name} Package".format(
            night_count=booking_obj.nights_count,
            destination_name=title)
    if category_id == constants.CATEGORY_VISA_ID:
        return "{destination_name} Visa".format(
            destination_name=title)
    if category_id == constants.CATEGORY_INSURANCE_ID:
        return "Travel Insurance"
    if category_id == constants.CATEGORY_TRANSFER_ID:
        return "{destination_name} Transfer".format(
            destination_name=title)
    if category_id == constants.CATEGORY_ACTIVITY_ID:
        return "{destination_name} Sightseeing".format(
            destination_name=title)
    else:
        return title



def get_booking_object_for_update_by_booking_id(booking_id: int):
    try:
        return Booking.objects.filter(id=booking_id).select_for_update().get()
    except Booking.DoesNotExist:
        return None
    except Booking.MultipleObjectsReturned:
        return None


def get_booking_as_buyer_or_seller_by_booking_code_and_member_id(member_id, booking_code):
    try:
        return Booking.objects.filter(code=booking_code).filter(Q(buyer_id=member_id) | Q(seller_id=member_id))
    except Booking.DoesNotExist:
        return None



def get_member_currency_by_id(member_id):
    try:

        member_organization = organization.get_member_organization_by_member_id(member_id)
        member_wallet = wallet.get_wallet_obj_by_organization_id(member_organization.id)
        return member_wallet.currency
    except Exception as e:
        import traceback
        traceback.print_exc()
        return None


def fetch_seller_cost_components_from_booking_id(booking_id):
    return SellerCostComponent.objects.filter(booking_id=booking_id)


def get_net_approved_discount_by_booking_id(booking_id):
    return ApprovedDiscount.objects.filter(booking_id=booking_id).aggregate(discount=Sum('amount'))


def update_booking_financials_v2(approved_discount_obj):
    try:
        booking_financial = BookingFinancial.objects.get(booking=approved_discount_obj.booking)
        booking_obj = approved_discount_obj.booking
        net_approved_discount = get_net_approved_discount_by_booking_id(approved_discount_obj.booking.id)
        booking_financial.approved_discount = net_approved_discount['discount']
        booking_financial.total_net_receivable = get_round_off_amount(
            booking_obj.amount_in_collection_currency - booking_financial.approved_discount + booking_financial.tcs,
            booking_obj.collection_currency.id, True)
        booking_financial.net_profit = booking_financial.total_net_receivable - booking_financial.total_net_payable
        booking_financial.save()
        return booking_financial
    except:
        return None


def update_transaction_amount_in_collection_currency(booking_charge_obj):
    try:
        booking_obj = booking_charge_obj.booking
        booking_date = booking_obj.booking_date
        base_currency = booking_obj.collection_currency.id
        currency = booking_obj.currency.id
        current_roe, current_markup = get_roe_and_markup_by_currency(base_currency, currency, booking_date)
        booking_obj.amount_in_collection_currency = get_round_off_amount((booking_obj.amount +
                                                                          booking_charge_obj.service_charge_collected_from_buyer) * (
                                                                                 booking_charge_obj.roe_on_booking_date + current_roe.roe),
                                                                         booking_obj.collection_currency.id if booking_obj.collection_currency else None)
        booking_obj.save()
    except:
        import traceback
        traceback.print_exc()
        return None


def get_total_approved_discount_amount(booking):
    if booking:
        approved_discount_list = ApprovedDiscount.objects.filter(booking=booking)
        if approved_discount_list:
            approved_discount_aggregate = approved_discount_list.aggregate(Sum('amount'))
            return get_round_off_amount(approved_discount_aggregate['amount__sum'])
        return 0
    return 0


def get_weighted_seller_fx_and_markup(seller_cost_components):
    number_of_components = len(seller_cost_components)
    weighted_seller_fx = 0
    weighted_seller_fx_markup = 0
    for seller in seller_cost_components:
        weighted_seller_fx += seller.seller_fx
        weighted_seller_fx_markup += seller.seller_fx_markup
    return (weighted_seller_fx / number_of_components), (weighted_seller_fx_markup / number_of_components)


def calculate_amount_in_collection_currency_for_payment(collection_currency_id, amount, seller_cost_components):
    try:
        number_of_components = len(seller_cost_components)
        net_cost_in_collection_currency = 0
        for seller in seller_cost_components:
            net_cost_in_collection_currency += amount * (seller.seller_fx + seller.seller_fx_markup)
        amount_in_collection_currency = get_round_off_amount(
            float(net_cost_in_collection_currency) / float((number_of_components)), collection_currency_id)
        return amount_in_collection_currency
    except:
        return 0


def calculate_amount_in_collection_currency_for_collection(base_currency, currency, booking_date, amount):
    roe_obj, markup_obj = get_roe_and_markup_by_currency(base_currency, currency, booking_date)
    return get_round_off_amount(float(amount) * (roe_obj.roe + markup_obj.selling_mark_up), base_currency)


def get_seller_cost_components_by_booking_code(booking_code, **kwargs):
    return SellerCostComponent.objects.filter(booking__code=booking_code, **kwargs).exclude(seller_status__id=
                                                                                            SELLER_COST_COMPONENT_CANCELLED_ID)


def update_booking_summary_fx_profit_loss(booking_id, old_net_profit, new_net_profit):
    try:
        booking_summary_obj = BookingSummary.objects.get(booking_id=booking_id)
        booking_summary_obj.fx_profit_loss += new_net_profit - old_net_profit
        booking_summary_obj.save()
    except Exception as e:
        print(e)


def validate_booking_confirm_request(booking_obj, request_data):
    from bms.services import planned_payment, booking_financial
    try:
        if request_data.get("status") and request_data.get("status") == CONFIRMED:
            total_payment_amount = 0
            scheduled_payment_amounts = dict()
            seller_cost_components_dict = dict()

            if booking_obj.status == CONFIRMED:
                return True, None

            seller_cost_components = get_seller_cost_components_by_booking_code(booking_code=booking_obj.code)
            if not seller_cost_components:
                return False, "Seller Cost Component cannot be empty for confirmed bookings"

            scheduled_collections = planned_payment.get_planned_payments_by_booking_id_and_type(
                booking_id=booking_obj.id, type=PlannedPayment.DUE_ON_MEMBER)
            scheduled_payments = planned_payment.get_planned_payments_by_booking_id_and_type(booking_id=booking_obj.id,
                                                                                             type=PlannedPayment.DUE_TO_MEMBER)
            if not scheduled_collections:
                return False, "Please Fill Schedule Collection"
            if not scheduled_payments:
                return False, "Please Fill Schedule Payment"

            total_collection_amount = sum(sc.amount for sc in scheduled_collections)

            booking_financials_v2 = booking_financial.get_booking_financial_v2_by_booking_id(booking_id=booking_obj.id)
            if total_collection_amount > 0 and total_collection_amount != booking_financials_v2.total_net_receivable:
                return False, ("Sum of all schedule collections (Tranche and Direct Payment) must equal "
                               "Total Net Receivable (Collection Currency).")

            for sp in scheduled_payments:
                member_id = sp.member_id
                scheduled_payment_amounts[member_id] = scheduled_payment_amounts.get(member_id, 0) + sp.amount
                total_payment_amount += sp.amount

            for sc in seller_cost_components:
                member_id = sc.seller_member.id
                seller_cost_components_dict[member_id] = seller_cost_components_dict.get(member_id,
                                                                                         0) + sc.seller_net_payable_in_seller_currency

            for member_id, amount in seller_cost_components_dict.items():
                if member_id in scheduled_payment_amounts:
                    if get_round_off_amount(amount) != get_round_off_amount(scheduled_payment_amounts[member_id]):
                        return None, ("Sum of all schedule payments (Tranche and Direct Payment) must equal "
                                      "the respective seller's sum of Net Payable to Seller (Seller Currency).")
                else:
                    return None, (f"Schedule Payment not found for Seller Component with Seller Member ID: {member_id}."
                                  f" Please create Schedule Payment first.")

            if request_data.get('category') == CATEGORY_FLIGHT_ID:
                _booking_financial_data = {
                    'cost_price': booking_financials_v2.total_cost_price,
                    'cost_in_vendor_booking_currency': seller_cost_components[0].cost_in_collection_currency,
                    'commission_received': booking_financials_v2.total_commission_received,
                    'tds': booking_financials_v2.total_tds,
                    'vendor_member_id': seller_cost_components[0].seller_member_id,
                    'vendor_organization_id': seller_cost_components[0].seller_organization_id,

                }

                instance, created = booking_financial.create_booking_financial(booking_obj.id, **_booking_financial_data)

                if not instance:
                    return None, "Booking Financial V1 Not Created for Fight Booking. Please Check Data."

            return True, None
        return True, None
    except Exception as e:
        return False, str(e)
