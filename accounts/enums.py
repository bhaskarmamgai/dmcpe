CREDIT = 'CR'
DEBIT = 'DR'
CREDIT_OR_DEBIT = (
    (CREDIT, CREDIT),
    (DEBIT, DEBIT),
)

JOURNAL_COLLECTION_ID = 1
JOURNAL_PAYMENT_ID = 2

BANK_TRANSFER = 'bank_transfer'
PAYMENT_GATEWAY = 'payment_gateway'
CASH = 'cash'
CASHBACK = 'cashback'
PAYOUT_REVERSAL = 'payout_reversal'
CREDIT_OR_DEBIT_NOTE = 'credit_or_debit_note'
MODE_OF_PAYMENT = (
    (BANK_TRANSFER, 'Bank transfer'),
    (PAYMENT_GATEWAY, 'Payment gateway'),
    (CASH, 'Cash'),
    (CREDIT_OR_DEBIT_NOTE,"Credit/Debit Note"),
    (CASHBACK, "Cashback"),
    (PAYOUT_REVERSAL, "Payout Reversal")
)
