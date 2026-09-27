from common.libraries import get_round_off_amount
from bms.providers import seller_cost_component as seller_cost_component_services
from wallets.services import WalletServices as wallet_services
from dmcpesys.services import get_roe_by_currency_and_datetime, get_currency_markup


def get_active_seller_statuses():
    return seller_cost_component_services.get_active_seller_statuses()


def count_no_of_seller_cost_components_for_a_booking(booking_id):
    return seller_cost_component_services.count_no_of_seller_cost_components_for_a_booking(booking_id)


def get_cost_in_collection_currency(seller_cost_component):
    return seller_cost_component_services.get_cost_in_collection_currency(seller_cost_component)


def get_travel_supply_group_entity_by_id(travel_supply_group_entity_id):
    return seller_cost_component_services.get_travel_supply_group_entity_by_id(travel_supply_group_entity_id)


def seller_net_payable_in_collection_currency(seller_cost_component):
    seller_fx = seller_cost_component.seller_fx
    seller_fx_markup = seller_cost_component.seller_fx_markup
    return get_round_off_amount(
        seller_cost_component.seller_net_payable_in_seller_currency * (seller_fx + seller_fx_markup),
        seller_cost_component.booking.collection_currency.id)


def create_seller_cost_component(booking_id, **kwargs):
    return seller_cost_component_services.create_seller_cost_component(booking_id, **kwargs)


def update_seller_cost_component(booking_id, **kwargs):
    return seller_cost_component_services.update_seller_cost_component(booking_id, **kwargs)


def get_seller_status_by_name(seller_status):
    return seller_cost_component_services.get_seller_status_by_name(seller_status)


def get_net_payable_in_collection_currency(seller_cost_component):
    return seller_cost_component_services.get_net_payable_in_collection_currency(seller_cost_component)


def get_seller_fx_and_markup(instance):
    return seller_cost_component_services.get_seller_fx_and_markup(instance)


def get_amount_in_collection_currency_for_seller_of_a_booking(booking_id, **kwargs):
    return seller_cost_component_services.get_amount_in_collection_currency_for_seller_of_a_booking(booking_id,
                                                                                                    **kwargs)


def check_if_seller_roe_and_markup_exists(booking_obj, seller_currency_id):
    return seller_cost_component_services.check_if_seller_roe_and_markup_exists(booking_obj, seller_currency_id)


def set_seller_wallet_currency_and_seller_fx(booking_obj, scc_request_data):
    for scc in scc_request_data:
        wallet_currency = wallet_services.get_wallet_currency_by_member_id(member_id=scc.get("seller_member"))
        if not wallet_currency:
            return False, f"Wallet Currency not Set for Seller => {scc.get('seller_member')} !!"
        scc.update({'seller_currency': wallet_currency.id})
        if 'seller_fx' not in scc.keys():
            try:
                roe_obj = get_roe_by_currency_and_datetime(base_currency=booking_obj.collection_currency.id,
                                                           currency=wallet_currency.id,
                                                           booking_date=booking_obj.created_at)
                scc.update({'seller_fx': roe_obj.roe})
            except Exception as err:
                return False, str(err)

        if 'seller_fx_markup' not in scc.keys():
            try:
                mark_up_obj = get_currency_markup(base_currency=booking_obj.collection_currency.id,
                                                  currency=wallet_currency.id)
                scc.update({'seller_fx_markup': mark_up_obj.selling_mark_up})
            except Exception as err:
                return False, str(err)

    return True, None



def set_seller_wallet_currency(scc_request_data):

    wallet_currency = wallet_services.get_wallet_currency_by_member_id(member_id=scc_request_data.get("seller_member"))
    if not wallet_currency:
        return False, f"Wallet Currency not Set for Seller => {scc_request_data.get('seller_member')} !!"
    scc_request_data.update({'seller_currency': wallet_currency.id})

    return True, None

