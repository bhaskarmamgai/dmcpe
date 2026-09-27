from django.core.exceptions import ValidationError
from bms.models.cancellation import CancellationStatusHistory, CancellationRequest, CancellationComment, CancellationRequestType, ServiceRequestTypeAndStatusMapping
from bms.models.booking.booking import Booking
from django.conf import settings
from datetime import datetime,timedelta
from bms.enums import CANCELLATION_REQUEST_STATUS_DISCRIPTION, CANCELLATION_REQUEST_STATUS_ACTIVE, CANCELLATION_REQUEST_STATUS_IN_PROGRESS, CancellationStatus
from django.db.models import Q
from bms.services import bookings
from dmcpesys.services import get_travel_supply_configuration_by_app_and_key
from dmcpesys.constants import APP__TRS
from bms.enums import DAYS_ALLOWED_FOR_HOTEL_CANCELLATION , PENDING , FAILED, CONFIRMED, FILE_TYPE__PDF
from common.services.system import common_error_message_format_for_client
from rest_framework import exceptions
import requests

def create_cancellation_status_history(**data):
    return CancellationStatusHistory.objects.create(**data)


def update_cancellation_request(cancellation_request_id: int, **kwargs):
    qs = CancellationRequest.objects.filter(id=cancellation_request_id)
    qs.update(**kwargs)
    return qs


def get_cancellation_status_history_by_booking(booking_obj):
    queryset = CancellationStatusHistory.objects.filter(booking = booking_obj)
    if queryset:
        cancellation_status_history_list = queryset.filter(pk = queryset.first().pk) | queryset.filter(pk = queryset.last().pk).exclude(Q(status = CANCELLATION_REQUEST_STATUS_ACTIVE) | Q(status = CANCELLATION_REQUEST_STATUS_IN_PROGRESS))
        return cancellation_status_history_list
    else:
        return None


def check_cancellation_allowed_by_booking_code(booking_code):
    try:
        booking_obj = Booking.objects.get(code = booking_code)
    except Booking.DoesNotExist:
        raise ValidationError('Invalid Booking Code! Booking With This Code Does Not Exist.')

    try:
        if booking_obj.category_id == settings.CATEGORY_FLIGHT_ID and                booking_obj.type_id == settings.BOOKING_TYPE_FLIGHT_ID:
            booking_detail_obj = booking_details.get_booking_details_by_booking_id(booking_obj.id)
            cancellation_allowed_till_time = datetime(year=booking_obj.departure_at.year,
                                                      month=booking_obj.departure_at.month,
                                                      day=booking_obj.departure_at.day,
                                                      hour=booking_detail_obj.departure_or_checkin_time.hour,
                                                      minute=booking_detail_obj.departure_or_checkin_time.minute) - timedelta(
                hours=settings.FLIGHT_BOOKING_CANCELLATION_REQUEST_ALLOWED_DURATION_IN_HOURS)
            if booking_obj.status == Booking.CONFIRMED and booking_detail_obj and booking_detail_obj.departure_or_checkin_time:
                if cancellation_allowed_till_time > datetime.now():
                    return True
        elif booking_obj.category_id == settings.CATEGORY_HOTEL_ID and booking_obj.status == Booking.CONFIRMED and            booking_obj.type_id == settings.BOOKING_TYPE_OWN_SUPPLY:
            number_of_days = get_travel_supply_configuration_by_app_and_key(APP__TRS, DAYS_ALLOWED_FOR_HOTEL_CANCELLATION)
            if datetime.now() <= datetime.combine(booking_obj.departure_at, datetime.max.time())-timedelta(days=int(number_of_days)):
                return True
        return False
    except Exception as e:
        return False


def get_cancellation_request_status_descripton_from_cancellation_request_status(cancellation_request_status):
    return CANCELLATION_REQUEST_STATUS_DISCRIPTION.get(cancellation_request_status)


def get_cancellation_request_types_by_version_and_category(version, category_id):
    return CancellationRequestType.objects.filter(Q(version=version),
        (Q(category_id=category_id) | Q(category__isnull = True))).exclude(id__in=settings.REQUEST_TYPE_FOR_REFUND_COMMENT).            exclude(id=settings.REQUEST_TYPE_MANUAL_ID)


def get_cancellation_request_type_obj_from_request_type_name(request_type_name):
    try:
        cancellation_request_type_obj = CancellationRequestType.objects.get(request_type = request_type_name)
        return cancellation_request_type_obj.id
    except CancellationRequestType.DoesNotExist:
        return None
    except CancellationRequestType.MultipleObjectsReturned:
        return None


def update_cancellation_request_by_cancellation_code(cancellation_code, **kwargs):
    qs = CancellationRequest.objects.filter(cancellation_code=cancellation_code)
    qs.update(**kwargs)
    qs.first().save(update_fields = kwargs)
    return qs.first()


def create_cancellation_request(**kwargs):
    return CancellationRequest.objects.create(**kwargs)


def get_cancellation_request_object_by_cancellation_code(cancellation_code):
    return CancellationRequest.objects.filter(cancellation_code=cancellation_code).first()


def post_comment_for_cancellation_request(message, file, file_type, member, cancellation_request, **kwargs):
    data = {'message': message, 'file': file, 'file_type': file_type, 'posted_by': member,
            'cancellation_request': cancellation_request, 'service_request_status':cancellation_request.service_request_status, 'internal_comment_by_id':
                settings.TRAVEL_SUPPLY_DEFAULT_COMMENT_USER_ID}

    if kwargs.get('is_default_comment') is False:
        data.pop('internal_comment_by_id')

    return CancellationComment.objects.create(**data)


def set_default_reopen_comment_for_cancellation_request(**kwargs):
    return CancellationComment.objects.create(**kwargs)


def check_if_cancellation_request_code_belongs_to_booking(cancellation_code, booking_code):
    try:
        cancellation_request_obj = get_cancellation_request_object_by_cancellation_code(cancellation_code)
        booking_obj = cancellation_request_obj.booking if cancellation_request_obj else None
        if booking_obj and booking_obj.code == booking_code:
            return True

        return False

    except Exception as e:
        return False


def get_cancellation_comments_by_cancellation_request_obj(cancellation_request_obj):
    return CancellationComment.objects.filter(cancellation_request=cancellation_request_obj).order_by('-id')


def cancellation_response_mapper(bms_cancellation_data, cancellation_data_from_engine):
    response_obj = []
    for data in bms_cancellation_data:
        cancellation_object = dict(data)
        cancellation_object["details"] = cancellation_data_from_engine[cancellation_object.get('cancellation_code')]
        response_obj.append(cancellation_object)
    return response_obj


def get_service_request_status(request_type, status_order):
    if request_type:
        service_request_status = ServiceRequestTypeAndStatusMapping.objects.get(is_active=True, request_type=request_type, status_order=status_order)
        return service_request_status
    return None


def get_service_request_status_by_provider_status(instance ,provider_status):
    if instance and provider_status:
        service_request_status = None
        if provider_status == CONFIRMED:
            service_request_status = get_service_request_status(instance.request_type, CancellationStatus.CANCELLATION_STATUS__REQUEST_SENT.value)
        elif provider_status == PENDING or provider_status == FAILED:
            service_request_status = get_service_request_status(instance.request_type, CancellationStatus.CANCELLATION_STATUS__REQUEST_CONFIRMED.value)
        return service_request_status.id
    return None