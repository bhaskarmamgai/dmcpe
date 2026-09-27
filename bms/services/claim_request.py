from bms.services.bookings import get_booking_object_from_code
from bms.providers import claim_request as claim_request_provider


def validate_claim_request(payload):
    booking_code = payload.get('code')
    booking_obj = get_booking_object_from_code(booking_code)
    if not booking_obj:
        error_msg = "InValid Booking Code"
        return False, error_msg
    return True, ""


def record_claim_request_logs(payload, **kwargs):
    booking_code = payload.get('code')
    booking_id = get_booking_object_from_code(booking_code).id
    return claim_request_provider.record_claim_request_logs(booking_id, payload, **kwargs)


def update_claim_request_log_object(claim_request_log_id: int, **kwargs):
    return claim_request_provider.update_claim_request_log_object(claim_request_log_id, **kwargs)
