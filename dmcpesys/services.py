from django.db.models import Sum
from django.db import connection
from dmcpesys.models import StatsDaily, Airport, Airline, Category, Currency, RateOfExchange, \
    Country, TravelSupplyConfiguration, AcquisitionChannel, Destination, AcmRatingFeedbackOptions, \
    BaseCurrencyCharge, RemitType, TravelSupplyGroupEntities
from rest_framework import exceptions
from datetime import datetime
from common.redis import get_hmset_data, push_data_via_hmset
from django.conf import settings
import json
from django.utils import timezone


def save_daily_stats(date, **kwargs):
    if 'requirements_status_update_count' in kwargs:
        StatsDaily.objects.create_or_update_stats_daily(date=date, requirements_status_update_count=kwargs.get(
            'requirements_status_update_count'))
    if 'requirements_match_count' in kwargs:
        StatsDaily.objects.create_or_update_stats_daily(date=date,
                                                        requirements_match_count=kwargs.get('requirements_match_count'))


def get_aggregated_stats(begin_date, end_date, **kwargs):
    if kwargs.get('field') == 'requirements_status_update_count':
        count = StatsDaily.objects.filter(date__gte=begin_date).filter(date__lte=end_date).aggregate(
            Sum('requirements_status_update_count'))
        return count.get('requirements_status_update_count__sum')
    if kwargs.get('field') == 'requirements_match_count':
        count = StatsDaily.objects.filter(date__gte=begin_date).filter(date__lte=end_date).aggregate(
            Sum('requirements_match_count'))
        return count.get('requirements_match_count__sum')
    return None


def get_airline_object_by_name(airline_name: str):
    try:
        obj, created = Airline.objects.get_or_create(
            name=airline_name,
            defaults={'name': airline_name},
        )
        return obj
    except Airline.MultipleObjectsReturned:
        return None


def get_airport_object_by_code(airport_code: str, **kwargs):
    try:
        obj, created = Airport.objects.get_or_create(
            code=airport_code,
            defaults={**kwargs},
        )
        return obj
    except Airport.MultipleObjectsReturned:
        return None


def get_disabled_categories():
    return Category.objects.filter(enabled=False)


def get_enabled_categories():
    return Category.objects.filter(deleted=False).filter(enabled=True)


def get_category_obj_by_id(category_id: int):
    try:
        return Category.objects.get(pk=category_id)
    except Category.DoesNotExist:
        return None
    except Category.MultipleObjectsReturned:
        return None


def get_currency_by_symbol(symbol: str):
    return Currency.objects.get(symbol=symbol)


def get_country_by_id(id: int):
    return Country.objects.get(id=id)


def get_currency_by_id(id: int):
    return Currency.objects.get(id=id)


def get_current_roe_for_currency_by_currency_id(currency_id: int):
    return RateOfExchange.objects.filter(currency_id=currency_id).latest('created_at')


def get_current_roe_by_currency_symbol(currency_symbol: str):
    return RateOfExchange.objects.filter(currency__symbol=currency_symbol).first()


def get_current_roe_by_currency_symbol_v2(currency_symbol: str, quote_currency: str):
    return RateOfExchange.objects.filter(currency__symbol=currency_symbol,
                                         base_currency__symbol=quote_currency).order_by('-id').first()


def get_current_roe_for_all_currencies():
    query = "select max(id) as id, currency_id from dmcpesys_rateofexchange group by currency_id;"
    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            col = [col[0] for col in cursor.description]
            rows = [dict(zip(col, row)) for row in cursor.fetchall()]
    except Exception as e:
        raise Exception
    roe_ids = []
    for roe in rows:
        roe_ids.append(roe.get('id'))
    return RateOfExchange.objects.filter(id__in=roe_ids)


def get_current_roe_for_all_currencies_v2():
    query = "select max(id) as id, currency_id from dmcpesys_rateofexchangev2 group by currency_id;"
    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            col = [col[0] for col in cursor.description]
            rows = [dict(zip(col, row)) for row in cursor.fetchall()]

    except Exception as e:
        raise Exception

    roe_ids = []
    for roe in rows:
        roe_ids.append(roe.get('id'))
    return RateOfExchange.objects.filter(id__in=roe_ids)


def get_current_roe_for_all_currencies_in_all_currencies_v2():
    query = "select max(id) as id, currency_id, base_currency_id from dmcpesys_rateofexchangev2 group by currency_id, base_currency_id;"
    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            col = [col[0] for col in cursor.description]
            rows = [dict(zip(col, row)) for row in cursor.fetchall()]

    except Exception as e:
        raise Exception

    roe_ids = []
    for roe in rows:
        roe_ids.append(roe.get('id'))
    return RateOfExchange.objects.filter(id__in=roe_ids)


def get_travel_supply_configuration_by_app_and_key(app: str, key: str):
    try:
        return TravelSupplyConfiguration.objects.get(app=app, key=key).value
    except Exception as e:
        raise exceptions.ValidationError("Invalid App Name or Key", 400)


def acquisition_channels_list(id_list):
    return AcquisitionChannel.objects.filter(id__in=id_list)


def get_category_list_by_ids(id_list):
    return Category.objects.filter(id__in=id_list)


def get_destination_list_by_ids(id_list):
    return Destination.objects.filter(id__in=id_list)


def get_destination_obj_by_code(code):
    return Destination.objects.filter(code=code)


def get_active_feedback_options_for_acm_rating():
    return AcmRatingFeedbackOptions.objects.filter(is_active=True)


def get_enabled_destinations():
    return Destination.objects.filter(deleted=False, enabled=True)


def get_destination_by_name(name):
    try:
        return Destination.objects.filter(name=name, deleted=False, enabled=True)
    except Destination.DoesNotExist:
        return None
    except Destination.MultipleObjectsReturned:
        return None
    except Exception as e:
        return None


def check_roe_for_negative_value(data):
    is_negative = False
    for currency in Currency.objects.filter(is_active=True, is_deleted=False):
        rate_field_name = currency.symbol
        if rate_field_name in data:
            rate = data[rate_field_name]
            if rate and float(rate) < 0:
                is_negative = True
    return is_negative


def get_datetime_object(date, time):
    datetime_str = date + " " + time
    datetime_object = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
    return datetime_object


def get_roe_by_currency(currency):
    roe = RateOfExchange.objects.filter(date__gte=datetime.now().date(), currency_id=currency.id).order_by(
        '-id').last()
    if roe:
        return roe
    raise Exception(f'ROE Not Found for Currency {currency}. Please Upload ROE from Admin.')


def get_enabled_currencies():
    return Currency.objects.filter(is_active=True, is_deleted=False)


def get_enabled_remit_types():
    return RemitType.objects.filter(is_active=True)


def get_roe_by_currency_and_datetime(base_currency, currency, booking_date):

    roe = RateOfExchange.objects.filter(date__lte=booking_date, currency_id=currency,
                                        base_currency_id=base_currency)
    if roe:
        return roe.last()
    last_roe = RateOfExchange.objects.filter(date__lte=booking_date.date(), currency_id=currency,
                                             base_currency_id=base_currency)
    if last_roe:
        return last_roe.last()
    raise Exception(f'ROE Not Found for Currency {currency}. Please Upload ROE from Admin.')


def get_latest_internal_token():
    return get_hmset_data(key=settings.LMS_INTERNAL_AUTH_REDIS_KEY)


def create_new_access_token_entry(data):
    try:
        # unlimited time ttl
        tt = push_data_via_hmset(key=settings.LMS_INTERNAL_AUTH_REDIS_KEY, data={"data": json.dumps(data)}, ttl=0)
        return tt
    except Exception as e:
        raise e


def get_currency_markup(base_currency, currency):
    markup = BaseCurrencyCharge.objects.filter(currency_id=currency, base_currency_id=base_currency)
    if markup:
        return markup.last()
    raise Exception(f'MARKUP Not Found for Currency {currency}. Please Upload MARKUP from Admin.')


def get_travel_supply_group_entity_by_code(code):
    travel_supply_group_entity_qs = TravelSupplyGroupEntities.objects.filter(code=code)
    if travel_supply_group_entity_qs:
        return travel_supply_group_entity_qs.last()
    raise Exception(f'Travel Supply Group Entity with code {code} not found. Please check data')


def get_roe_and_markup_by_currency(base_currency, currency, booking_date):
    return get_roe_by_currency_and_datetime(base_currency, currency, booking_date), get_currency_markup(base_currency,
                                                                                                        currency)


def check_if_roe_and_markup_exists(base_currency, currency, created_at):
    try:
        current_roe, current_markup = get_roe_and_markup_by_currency(base_currency, currency, created_at)
        return True, ""
    except:
        return False, "ROE or Markup not present for Booking Currency and Wallet Currency"


def get_travel_supply_configuration_by_key(key: str):
    try:
        return TravelSupplyConfiguration.objects.get(key=key, environment=settings.ENV_NAME).value
    except Exception as e:
        raise Exception(f'Configuration not found for Key {key} and Environment {settings.ENV_NAME}. Please check data')
