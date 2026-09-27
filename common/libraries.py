import base64,jwt
import math
import re
from datetime import datetime, date
import base36
from dateutil.relativedelta import relativedelta
from datetime import timedelta

from django.conf import settings
import pytz
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
import io
import csv
from collections import namedtuple
import urllib
from babel.numbers import format_currency



def get_dates_by_range(date_range):
    if date_range == "today":
        begin_date = date.today()
        end_date = date.today()
    elif date_range == "month_to_date":
        begin_date = date.today().replace(day=1)
        end_date = date.today()
    elif date_range == "last_month":
        today = date.today()
        d = today - relativedelta(months=1)
        begin_date = date(d.year, d.month, 1)
        end_date = date(today.year, today.month, 1) - relativedelta(days=1)
    elif date_range == "2nd_last_month":
        today = date.today()
        d = today - relativedelta(months=2)
        begin_date = date(d.year, d.month, 1)
        end_date = date(today.year, today.month, 1) - relativedelta(months=1) - relativedelta(days=1)
    elif date_range == "last_30days":
        today = date.today()
        end_date = date(today.year, today.month, today.day)
        begin_date = end_date - relativedelta(days=30)
    elif date_range == "48hours":
        end_date = datetime.now()
        begin_date = end_date - relativedelta(hours=48)
    else:
        return False

    if type(begin_date) is not datetime:
        # https://stackoverflow.com/questions/23050392/whats-wrong-with-this-tzinfo-variable
        tz = pytz.timezone(settings.TIME_ZONE)
        begin_date = tz.localize(datetime(begin_date.year, begin_date.month, begin_date.day, 0, 0, 0))
        end_date = tz.localize(datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59))

    return begin_date, end_date


def add_environment_name_to_text(text):
    return (("%s - " % settings.APP_ENVIRONMENT) if settings.APP_ENVIRONMENT.lower().find("prod") == -1 else "") + \
           text


def filter_blocked_emails(email_addresses: list):
    # Dont block any mails - for Production where Debug mode is OFF
    if not settings.DEBUG:
        return email_addresses

    ems = [em for em in email_addresses if em.find("@travelsupply.com") >= 1 or whitelisted_patterns(em)]
    return list(set(ems))


def sanitize_emails(email_addresses: list):
    ems = [sanitize_email(em) for em in email_addresses if em]
    return list(set(ems))


def sanitize_email(email_address: str):
    return email_address.strip().lower()


def whitelisted_patterns(email_address):
    for un in settings.WHITELISTED_EMAIL_USERNAMES:
        if email_address.find(un) >= 0:
            return True

    return False



def sanitize_phone_number(number: str):
    return re.sub(r'[^0-9]*', r'', number)


def convert_comma_separated_email_addressess_to_list(emails_string: str) -> list():
    # https://www.geeksforgeeks.org/check-if-email-address-valid-or-not-in-python/

    """This function will take input str of email separated by comma and will
    first split the string,remove empty string and check is email id form after split is
    valid or not.This will return only valid mail ids in a list

    Test case where it fails = 'sales@islandlife.travel.co.in,sales3@islandlife.travel'
    The following two regex cann be used one
    regex1 = "^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,})+$"
    regex2 = "^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,30})+$"
    Lets for now use regex2
    """

    regex = "^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,30})+$"
    email_list = [x.strip() for x in emails_string.split(',') if x and re.search(regex, x)]
    return email_list


def read_csv_file(file_obj=None):
    # https://docs.python.org/2/library/csv.html
    """This Function will take URL as input and return the
    csv content in a namedtuple having containing obj list and header attributes"""
    url_open = urllib.request.urlopen(file_obj)
    csv_reader = csv.DictReader(io.StringIO(url_open.read().decode('utf-8')), delimiter=",")
    header = csv_reader.fieldnames
    obj_list = [record for record in csv_reader]
    CSV_DATA = namedtuple('CSV_DATA', ['obj_list', 'header'])
    obj = CSV_DATA(obj_list, header)
    return obj

# https://stackoverflow.com/questions/30400498/convert-date-with-format-dd-mm-yy-to-yyyy-mm-dd-in-python
def get_date_from_given_str_format(text):
    """This function will takes input date as str then from str date it will
    check format in collection if a match is found it will return datetime object
    else it will return False"""
    for fmt in ['%d-%m-%y', '%d/%m/%y', '%d-%m-%Y', '%d.%m.%Y', '%d/%m/%Y', '%Y-%m-%d']:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return False

def get_datetime_from_given_str_format(text):
    for fmt in ['%d-%m-%y', '%d/%m/%y', '%d-%m-%Y', '%d.%m.%Y', '%d/%m/%Y', '%Y-%m-%d']:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    return None


def get_start_date_and_end_date_of_current_month():
    import calendar
    current_datetime = datetime.now()
    current_year = current_datetime.year
    current_month = current_datetime.month
    _, num_days = calendar.monthrange(current_year, current_month)
    first_day = date(current_year, current_month, 1)
    last_day = date(current_year, current_month, num_days)
    return {'start_date': first_day, 'end_date': last_day, }


def diff_in_days_since_today(input_date: datetime):
    return (input_date - date.today()).days


# https://stackoverflow.com/questions/6405208/how-to-convert-numeric-string-ranges-to-a-list-in-python
def numeric_string_range__to__integer_list(x):
    result = []
    for part in x.split(','):
        if '-' in part:
            a, b = part.split('-')
            a, b = int(a), int(b)
            result.extend(range(a, b + 1))
        else:
            a = int(part)
            result.append(a)
    return result


def convert_to_default_timezone(date_time):
    tz = pytz.timezone(settings.TIME_ZONE)
    return tz.localize(date_time)

def convert_ist_datetime_to_utc_timezone(date_time):
    utc_dt = date_time.astimezone(pytz.utc)
    return utc_dt

def get_paginate_result_set_from_list(page, data_list, items_per_page):
    """https://simpleisbetterthancomplex.com/tutorial/2016/08/03/how-to-paginate-with-django.html
    You can pass either a list/tuple of objects or an QuerySet.
    """
    paginator = Paginator(data_list, items_per_page)
    try:
        paginated_obj = paginator.page(page)
    except PageNotAnInteger:
        paginated_obj = paginator.page(1)
    except EmptyPage:
        paginated_obj = paginator.page(paginator.num_pages)
    return paginated_obj


def get_numbers_formatted_to_indian_locale(amount):
    return format_currency(amount, '', locale='en_IN')


def is_valid_member_code(member_code):
    if member_code.isalnum() and 4 <= len(member_code) <= 7:
        return True
    return False


def is_valid_organization_code(org_code):
    if org_code.isalnum() and 4 <= len(org_code) <= 50:
        return True
    return False


def encode_using_base64(message:str):
    message_bytes = message.encode('utf-8')
    base64_bytes = base64.b64encode(message_bytes)
    base64_message = base64_bytes.decode('utf-8')
    return base64_message


def decode_using_base64(base64_message:str):
    base64_bytes = base64_message.encode('utf-8')
    message_bytes = base64.b64decode(base64_bytes)
    message = message_bytes.decode('utf-8')
    return message


def encode_using_jwt(message: dict):
    encoded_response_byte = jwt.encode(message, settings.SECRET_KEY, algorithm='HS256')
    # encoded_response_str = encoded_response_byte.decode('utf-8')
    return encoded_response_byte


def decode_using_jwt(jwt_encoded_str:str):
    decoded_response = jwt.decode(jwt_encoded_str, settings.SECRET_KEY, algorithms=['HS256'])
    return decoded_response


def limit_queryset(qs, limit: int = 0):
    ids = list(qs.values_list('id', flat=True)[:limit])
    return qs.model.objects.filter(id__in=ids).select_related().prefetch_related()


def format_str_date_to_date(str_date: str):
    return datetime.strptime(str_date, '%Y-%m-%d').date() \
        if str_date else datetime.datetime().now().date().strftime("%Y-%m-%d")

def subtract_years_from_date(date: date,years):
    return date - relativedelta(years=years)



def convert_datetime_utc_to_ist(datetime_obj):
    return datetime_obj + timedelta(hours=5, minutes=30)


def get_round_off_amount(amount, currency_id=None, is_ceil=False):
    if is_ceil and currency_id == settings.DEFAULT_CURRENCY_ID:
        return math.ceil(round(amount, 2))
    if is_ceil:
        return math.ceil(round(amount, 2))
    return round(amount, 2)


def is_internal_api_request(request):
    url_path = request.path
    internal_keyword = 'internal'

    if internal_keyword in url_path:
        return True
    else:
        return False

def render_and_upload_pdf():
    pass