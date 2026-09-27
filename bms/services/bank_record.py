from django.db import bookings

from accounts.services.bank_record import update_bank_record, get_bank_record_obj_by_id
from bms.services.bookings import collect_buyer_payment, get_booking_object_from_id
from bms.services import planned_payment, booking_summary, booking_invoice_config




def claim_bank_record(member_id, booking_ids, claimed_amounts, record_id, claimed_by, selected_due_date,
                      roe_charged_to_buyer_list, **kwargs):
    return None


def get_bank_record_by_id(record_id):
    return get_bank_record_obj_by_id(record_id)



def update_planned_payment_record(booking_id):
    return planned_payment.update_planned_payment_record_for_scheduled_collection(booking_id)
