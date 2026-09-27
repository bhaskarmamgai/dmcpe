from common.libraries import get_round_off_amount, get_round_off_amount
from dmcpesys.models import TravelSupplyGroupEntities
from bms.config.base import SELLER_COST_COMPONENT_CANCELLED_ID
from bms.models import SellerStatus, SellerCostComponent
from dmcpesys.services import get_roe_by_currency, get_roe_and_markup_by_currency
from django.db.models import Sum


def get_active_seller_statuses():
    return SellerStatus.objects.filter(is_active=True, is_deleted=False)


def count_no_of_seller_cost_components_for_a_booking(booking_id):
    return SellerCostComponent.objects.filter(booking_id=booking_id).count()


def get_cost_in_collection_currency(seller_cost_component):
    return get_round_off_amount(seller_cost_component.cost_in_seller_currency * (
            seller_cost_component.seller_fx + seller_cost_component.seller_fx_markup),
                                seller_cost_component.booking.collection_currency.id)


def get_travel_supply_group_entity_by_id(travel_supply_group_entity_id):
    try:
        return TravelSupplyGroupEntities.objects.get(id=travel_supply_group_entity_id)
    except Exception as e:
        print("get_travel_supply_group_entity_by_id", e)
        return None


def create_seller_cost_component(booking_id, **kwargs):
    try:
        instance = SellerCostComponent(booking_id=booking_id, **kwargs)
        instance.save()
        return instance
    except Exception as e:
        print("create_seller_cost_component", e)
        return None


def update_seller_cost_component(booking_id, **kwargs):
    qs = SellerCostComponent.objects.filter(booking_id=booking_id)
    if qs:
        qs.update(**kwargs)
        return qs[0]
    return None


def get_seller_status_by_name(seller_status):
    try:
        return SellerStatus.objects.get(name=seller_status)
    except Exception as e:
        print("get_seller_status_by_name", e)
        return None


def get_net_payable_in_collection_currency(seller_cost_component):
    return seller_cost_component.seller_net_payable_in_seller_currency + get_roe_by_currency(
        seller_cost_component.seller_currency).roe


def get_seller_fx_and_markup(instance):
    roe_obj, markup_obj = get_roe_and_markup_by_currency(instance.booking.collection_currency.id,
                                                         instance.seller_currency.id, instance.booking.created_at)
    return roe_obj.roe, markup_obj.selling_mark_up


def get_amount_in_collection_currency_for_seller_of_a_booking(booking_id, **kwargs):
    amount_obj = SellerCostComponent.objects.filter(booking_id=booking_id, **kwargs).exclude(
        seller_status__id=SELLER_COST_COMPONENT_CANCELLED_ID).aggregate(
        amount=Sum('seller_net_payable_in_collection_currency'))
    return amount_obj['amount'] if amount_obj else 0


def check_if_seller_roe_and_markup_exists(booking_obj, seller_currency_id):
    try:
        current_roe, current_markup = get_roe_and_markup_by_currency(booking_obj.collection_currency.id,
                                                                     seller_currency_id,
                                                                     booking_obj.created_at)
        return True
    except Exception as e:
        print("check_if_seller_roe_and_markup_exists", e)
        return False


def get_seller_cost_components_by_booking(booking_obj):
    return SellerCostComponent.objects.filter(booking_id=booking_obj.id)
