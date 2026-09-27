from bms.enums import *
from bms.services import cancellation, service_request
from bms.services.bookings import get_booking_object_from_code
from common.providers import user



def validate_service_request_data(request_data, service_req_code):

    if request_data.get('internal_status') and        SERVICE_REQUEST_INTERNAL_STATUS_MAPPING.get(int(request_data.get('internal_status'))) is None:
        return False, "Invalid Service Request Internal Status"

    service_req_obj = cancellation.get_cancellation_request_object_by_cancellation_code(service_req_code)
    if not service_req_obj:
        return False, f"Service Request Does Not Exists {service_req_code}"

    service_req_status_list = service_request.get_service_request_status_list_by_service_req_obj(service_req_obj)
    service_request_status_id_list = [service_request_status.get('id') for service_request_status in service_req_status_list]

    if request_data.get('service_request_status') and        int(request_data.get('service_request_status')) not in service_request_status_id_list:
        return False, "Invalid Service Request Status"

    if request_data.get('assigned_to'):
        if user.get_user_obj_by_id(request_data.get('assigned_to')) is None:
            return False, "Invalid Assigned To"

    return service_req_obj, None


def validate_create_manual_request(request_data):

    if not request_data:
        return False, "No Data Provided"

    if not request_data.get('booking_code'):
        return False, "Booking Code Is Required"

    if not request_data.get('internal_status'):
        return False, "Internal Status Is Required"

    if not request_data.get('email'):
        return False, "Email Is Required"

    if not request_data.get('assigned_to'):
        return False, "Assigned To is Required"

    booking_obj = get_booking_object_from_code(request_data.get('booking_code'))
    if not booking_obj:
        return False, f"Booking Does Not Exists For Booking Code {request_data.get('booking_code')}"

    return booking_obj.id, None