from bms.services.wallet.planned_payment import get_bookings_where_collection_is_due_as_on_given_date
from bms.services.wallet import actual_payment
from accounts.services import posting
from wallets.services import WalletServices as wallet
from bms.services.bookings import get_booking_object_from_id
from django.conf import settings


def collect_payment(organization_id, member_id, booking_ids,  amounts, wallet_id, selected_due_date, claimed_by,
                     **kwargs):
    pending_bookings = get_bookings_where_collection_is_due_as_on_given_date(
        selected_due_date, organization_id, member_id)
    wallet_obj = wallet.get_wallet_object_by_id(wallet_id)
    validated_actual_payment_data = actual_payment.create_validated_actual_payment_data(organization_id, member_id, booking_ids,
                                                                                        amounts, claimed_by,
                                                                                        pending_booking_details=pending_bookings,
                                                                                        wallet_balance=wallet_obj.current_balance,
                                                                                        **kwargs)
    print(validated_actual_payment_data,"validated_actual_payment_data")
    actual_payment_objects = actual_payment.record_actual_payments(validated_actual_payment_data)
    posting_objects = [posting.release_money_from_wallet(organization_id, wallet_id,
                                                         float(amount or 0),
                                                         "Paid for booking(s) : {}".format(
                                                             get_booking_object_from_id(booking_id).code),
                                                         technical_description="Payment Collected Against Booking (s) :"
                                                                               " {}".format(booking_id),
                                                         member_id=member_id, currency_id=wallet_obj.currency.id if hasattr(wallet_obj, 'currency') else settings.DEFAULT_CURRENCY_ID) for
                       booking_id, amount in zip(booking_ids, amounts)]
    print("actual_payment_objects",actual_payment_objects)
    print("posting_objects",posting_objects)
    [actual_payment.update_actual_payment_object(id=ac.id, update_params={'posting': pt}) for ac, pt in
     zip(actual_payment_objects, posting_objects)]
    return True
