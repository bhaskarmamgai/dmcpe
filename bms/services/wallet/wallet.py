from django.db import transaction
from bms.services.bookings import get_booking_object_from_id
from bms.services import planned_payment, transaction_summary
from bms.services.wallet.booking import collect_payment


@transaction.atomic
def claim_booking_tranche_via_wallet(organization_id, member_id, booking_ids, claimed_amounts,
                                     wallet_id,claimed_by, selected_due_date,
                                     **kwargs):
    collect_payment(organization_id, member_id, booking_ids, claimed_amounts, wallet_id,
                    selected_due_date, claimed_by, **kwargs)
    planned_payment.update_planned_payment_record_for_scheduled_collection(booking_ids, member_id)
    transaction_summary.update_booking_summary_with_booking_objs(
        [get_booking_object_from_id(booking_id) for booking_id in booking_ids])
    return True
