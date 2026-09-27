SELLER = 'seller'
BUYER = 'buyer'

BUYER_OR_SELLER = (
    (BUYER, BUYER),
    (SELLER, SELLER)
)


AT_THE_TIME_OF_BOOKING = 'at_time_of_booking'
NON_REFUNDABLE = 'non_refundable'
DAYS_BEFORE_TRIP_START = 'days_before_trip_start'

PAYMENT_POLICY = (
    (AT_THE_TIME_OF_BOOKING, "At The Time Of Booking"),
    (DAYS_BEFORE_TRIP_START, "Days Before Trip Start")
)

CANCELLATION_POLICY = (
    (NON_REFUNDABLE, "Non-Refundable / At time of Booking"),
    (DAYS_BEFORE_TRIP_START, "Days Before Trip Start")
)
