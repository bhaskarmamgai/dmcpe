from bms.enums import PaymentStatus


def get_payment_status_for_booking(instance):
    if hasattr(instance, 'booking_summary'):
        booking_summary = instance.booking_summary
        if booking_summary:
            amount_collected_from_buyer = booking_summary.amount_collected_from_buyer
            amount_pending_for_collection_from_buyer = booking_summary.amount_pending_for_collection_from_buyer
        else:
            return PaymentStatus.PENDING.value
        if amount_pending_for_collection_from_buyer == 0:
            return PaymentStatus.FULL_AMOUNT_COLLECTED.value
        if amount_collected_from_buyer > 0 and (amount_collected_from_buyer != 0 or amount_collected_from_buyer):
            return PaymentStatus.PARTIALLY_COLLECTED.value
    return PaymentStatus.PENDING.value
