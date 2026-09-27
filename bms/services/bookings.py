import math
from django.db.models import Sum
from common.libraries import get_round_off_amount
from bms.models import BookingFinancial, BookingCharges
from bms.providers import bookings as bookings, seller_cost_component
from django.conf import settings
from bms.enums import DEFAULT_SELLER_FX_MARKUP, DEFAULT_SELLER_FX
from dmcpesys.services import get_roe_and_markup_by_currency


def get_booking_object_from_id(booking_id):
    return bookings.get_booking_object_from_id(booking_id)


def get_booking_object_from_code(booking_code):
    return bookings.get_booking_object_from_code(booking_code)


def update_booking_status(status: str, booking_id: int):
    return bookings.update_booking_status(status, booking_id)


def update_booking(booking_id: int, **kwargs):
    return bookings.update_booking(booking_id, **kwargs)


def update_amount_for_booking(booking_obj):
    return bookings.update_amount(booking_obj)


def send_one_time_booking_confirmation_mail(booking_obj):
    return bookings.send_one_time_booking_confirmation_mail(booking_obj)


def send_one_time_booking_pending_mail(booking_obj):
    return bookings.send_one_time_booking_pending_mail(booking_obj)


def send_one_time_booking_failure_mail(booking_obj):
    return bookings.send_one_time_booking_failure_mail(booking_obj)


def send_refund_mail(booking_obj, refund_amount):
    return bookings.send_one_time_refund_mail(booking_obj, refund_amount)


def send_booking_hold_mail(booking_obj):
    return bookings.send_booking_hold_mail(booking_obj)


def send_manual_booking_mail(booking_obj):
    return bookings.send_manual_booking_mail(booking_obj)


def update_booking_financial_for_hotels(booking_financial_obj):
    return bookings.update_booking_financial_for_hotels(booking_financial_obj)


def send_booking_confirmation_notifications(booking_obj):
    return bookings.send_booking_confirmation_notifications(booking_obj)



def get_booking_object_for_update_by_booking_id(booking_id: int):
    return bookings.get_booking_object_for_update_by_booking_id(booking_id)


def get_booking_as_buyer_or_seller_by_booking_code_and_member_id(member_id, booking_code):
    return bookings.get_booking_as_buyer_or_seller_by_booking_code_and_member_id(member_id, booking_code)


def get_member_currency_by_id(member_id):
    return bookings.get_member_currency_by_id(member_id)


def fetch_seller_cost_components_from_booking_id(booking_id):
    return bookings.fetch_seller_cost_components_from_booking_id(booking_id)


def get_total_net_payable_from_seller_component(seller_cost_component):
    return get_round_off_amount(seller_cost_component.seller_net_payable_in_collection_currency,
                                seller_cost_component.booking.collection_currency.id)


def get_total_seller_service_charge_from_seller_component(seller_cost_component):
    return get_round_off_amount(seller_cost_component.seller_service_charge * (
            seller_cost_component.seller_fx + seller_cost_component.seller_fx_markup),
                                seller_cost_component.booking.collection_currency.id)


def get_total_tax_on_seller_service_charge_from_seller_component(seller_cost_component):
    return get_round_off_amount(
        seller_cost_component.tax * (seller_cost_component.seller_fx + seller_cost_component.seller_fx_markup),
        seller_cost_component.booking.collection_currency.id)


def get_total_tcs_from_seller_component(seller_cost_component):
    return get_round_off_amount(seller_cost_component.tcs, seller_cost_component.booking.collection_currency.id)


def get_total_cost_price_from_seller_component(seller_cost_component):
    return get_round_off_amount(seller_cost_component.cost_in_collection_currency,
                                seller_cost_component.booking.collection_currency.id)


def update_booking_financials_v2(approved_discount):
    return bookings.update_booking_financials_v2(approved_discount)


def get_total_commission_received_from_seller_component(seller_cost_component):
    return get_round_off_amount(seller_cost_component.commission_received * (
            seller_cost_component.seller_fx + seller_cost_component.seller_fx_markup),
                                seller_cost_component.booking.collection_currency.id)


def get_total_tds_from_seller_component(seller_cost_component):
    return get_round_off_amount(
        seller_cost_component.tds * (seller_cost_component.seller_fx + seller_cost_component.seller_fx_markup),
        seller_cost_component.booking.collection_currency.id)


def calculate_amount_in_collection_currency_for_payment(collection_currency_id, amount, seller_cost_components):
    return bookings.calculate_amount_in_collection_currency_for_payment(collection_currency_id, amount,
                                                                        seller_cost_components)


def calculate_amount_in_collection_currency_for_collection(base_currency, currency, booking_date, amount):
    return bookings.calculate_amount_in_collection_currency_for_collection(base_currency, currency, booking_date,
                                                                           amount)


def update_transaction_amount_in_collection_currency(booking_charge_object):
    return bookings.update_transaction_amount_in_collection_currency(booking_charge_object)


def get_total_approved_discount_amount(booking):
    return bookings.get_total_approved_discount_amount(booking)


def get_seller_cost_components_by_booking_code(booking_code, **kwargs):
    return bookings.get_seller_cost_components_by_booking_code(booking_code, **kwargs)


def booking_charges_v2_save(booking_id, roe, markup, bank_charges):
    BookingCharges.objects.get_or_create(booking_id=booking_id,
                                         defaults={'roe_on_booking_date': roe, 'convenience_charges_on_roe': markup,
                                                   'service_charge_collected_from_buyer': bank_charges})


def get_weighted_seller_fx_and_markup(seller_cost_components):
    return bookings.get_weighted_seller_fx_and_markup(seller_cost_components)


def update_booking_summary_fx_profit_loss(booking_id, old_net_profit, new_net_profit):
    return bookings.update_booking_summary_fx_profit_loss(booking_id, old_net_profit, new_net_profit)


def get_scratch_card_details_by_booking_code_and_org_code(booking_code, org_code, **kwargs):
    return bookings.get_scratch_card_details_by_booking_code_and_org_code(booking_code, org_code, **kwargs)


def update_scratch_card_details_by_code(booking_id, **kwargs):
    return bookings.update_scratch_card_details_by_code(booking_id, **kwargs)


def create_latest_booking_financial(booking_id):
    return bookings.create_latest_booking_financial(booking_id)


def update_latest_booking_financials(booking_id, **kwargs):
    return bookings.update_latest_booking_financials(booking_id, **kwargs)


def validate_booking_confirm_request(booking_obj, request_data):
    return bookings.validate_booking_confirm_request(booking_obj, request_data)


def update_booking_financial_v2(booking_id: int):
    booking_obj = get_booking_object_from_id(booking_id)
    seller_cost_components = seller_cost_component.get_seller_cost_components_by_booking(booking_obj)
    approved_discounts = booking_obj.approved_discounts.all()

    total_approved_discount = approved_discounts.aggregate(Sum('amount')).get('amount__sum') or 0
    print(f"Total Approved Discount: {total_approved_discount}")

    default_finance_dict = {
        "total_net_payable": 0,
        "tcs": 0,
        "total_net_receivable": 0,
        "total_cost_price": 0,
        "gross_profit": 0,
        "net_profit": 0,
        "approved_discount": total_approved_discount,
        "total_seller_service_charge": 0,
        "total_tax_on_seller_service_charge": 0,
        "total_commission_received": 0,
        "total_tds": 0
    }
    if booking_obj.amount_in_collection_currency is not None:
        default_finance_dict["total_net_receivable"] = math.ceil(
            booking_obj.amount_in_collection_currency - total_approved_discount)
        default_finance_dict["gross_profit"] = math.ceil(booking_obj.amount_in_collection_currency)
    booking_financial_summary_instance, created = BookingFinancial.objects.get_or_create(booking_id=booking_id,
                                                                                         defaults=default_finance_dict)
    print(f"Seller Cost Components Count: {seller_cost_components.count()}")

    if seller_cost_components:
        seller_cost_components = seller_cost_components.exclude(
            seller_status=settings.SELLER_COST_COMPONENT_CANCELLED_ID)
        component_wise_sum = []

        for component in seller_cost_components:
            if not component.seller_fx or not component.seller_fx_markup:
                current_roe, current_markup = get_roe_and_markup_by_currency(
                    booking_obj.collection_currency.id,
                    component.seller_currency.id,
                    booking_obj.created_at
                )
                if not component.seller_fx and component.seller_fx != 0:
                    component.seller_fx = current_roe.roe if current_roe else DEFAULT_SELLER_FX
                if not component.seller_fx_markup:
                    component.seller_fx_markup = DEFAULT_SELLER_FX_MARKUP

            fx_total = component.seller_fx + component.seller_fx_markup
            component_wise_sum.append({
                'total_seller_service_charge': component.seller_service_charge * fx_total,
                'total_commission_received': component.commission_received * fx_total,
                'total_tds': component.tds * fx_total,
                'total_tax_on_seller_service_charge': component.tax * fx_total,
                'tcs': component.tcs,
                'total_net_payable': component.seller_net_payable_in_collection_currency,
                'total_cost_price': component.cost_in_collection_currency
            })
        if component_wise_sum:
            agg_component_wise_sum = {
                key: math.ceil(sum(item[key] or 0 for item in component_wise_sum))
                for key in component_wise_sum[0]
            }

            print(f"Component Wise Sum: {component_wise_sum}")
            print(f"Aggregated Component Wise Sum: {agg_component_wise_sum}")

            updated_financials = {
                'total_net_payable': agg_component_wise_sum['total_net_payable'],
                'total_net_receivable': booking_obj.amount_in_collection_currency - total_approved_discount +
                                        agg_component_wise_sum['tcs'],
                'total_cost_price': agg_component_wise_sum['total_cost_price'],
                'total_seller_service_charge': agg_component_wise_sum['total_seller_service_charge'],
                'total_commission_received': agg_component_wise_sum['total_commission_received'],
                'total_tds': agg_component_wise_sum['total_tds'],
                'total_tax_on_seller_service_charge': agg_component_wise_sum['total_tax_on_seller_service_charge'],
                'approved_discount': total_approved_discount,
                'tcs': agg_component_wise_sum['tcs'],
                'gross_profit': booking_obj.amount_in_collection_currency - agg_component_wise_sum['total_cost_price'],
            }
            updated_financials['net_profit'] = (
                    updated_financials['total_net_receivable'] - updated_financials['total_net_payable']
                    + updated_financials['total_tax_on_seller_service_charge'] + updated_financials['total_tds']
            )
            print(f"Updated Financials: {updated_financials}")
            booking_financial_summary_instance.__dict__.update(**updated_financials)
            booking_financial_summary_instance.save()
            return booking_financial_summary_instance

    print(f"Updated Financials: {default_finance_dict}")
    booking_financial_summary_instance.__dict__.update(**default_finance_dict)
    booking_financial_summary_instance.save()
    return booking_financial_summary_instance
