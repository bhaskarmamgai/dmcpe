from bms.services import release_request
from django.shortcuts import reverse
from bms.models import ReleaseRequest

def validate_scheduled_collection_tranche_for_release_request(bookings_ids: [], seller_id):
    is_valid, error_msg = True, None
    filtered_booking_ids = release_request.filter_booking_ids_whose_collection_is_due_before_today_by_member_id(
        seller_id, bookings_ids)
    if filtered_booking_ids:
        is_valid = False
        error_msg = "Error Due to Scheduled Collection:The Collection For Following Booking is Pending For as on Today<br>"
        for booking_id in filtered_booking_ids:
            error_msg += "<a href={} target ='_blank'>Click Here to update collection schedule for booking id {}</a><br>".format(
                reverse('admin:trs_booking_change', args=[booking_id.get('id'), ]), booking_id)
            "{}".format(error_msg)
    return is_valid, error_msg


def validate_release_request(request, release_request_id):
    is_valid, error_msg = False, None
    release_request_obj = release_request.get_release_request_obj(release_request_id)
    if release_request_obj.status == ReleaseRequest.PENDING:
        is_valid = True
    else:
        release_request_obj_link = "<a href={} target ='_blank'>#{}</a>".format(
                reverse('admin:trs_releaserequest_change', args=[release_request_id]), release_request_id)
        error_msg = "Error: Release Request %s is already %s" % (release_request_obj_link, release_request_obj.status)
    return is_valid, error_msg
