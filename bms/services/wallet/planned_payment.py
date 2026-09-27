from bms.providers.wallet import planned_payment


def get_bookings_where_collection_is_due_as_on_given_date(date, organization_id, member_id):
    return planned_payment.get_bookings_where_collection_is_due_as_on_given_date(date, organization_id, member_id)
