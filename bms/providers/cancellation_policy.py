from members.services import OrganizationServices as organization


def update_cancellation_terms_from_seller_organization_cancellation_terms(booking_detail_object):
    organization_detail_obj = organization.get_organization_detail_object_by_organization_id(
        booking_detail_object.booking.seller_organization.id)
    if organization_detail_obj:
        booking_detail_object.cancellation_terms = organization_detail_obj.cancellation_terms
        booking_detail_object.save()
        return booking_detail_object
    return False
