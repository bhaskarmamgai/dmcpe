from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from auditlog.registry import auditlog
from bms.models.booking.booking import Booking
from common.models import BaseModel

class PlannedPayment(BaseModel):
    DUE_ON_MEMBER = 'due_on_member'
    DUE_TO_MEMBER = 'due_to_member'
    DUE_TYPE = (
        (DUE_ON_MEMBER, 'To collect'),
        (DUE_TO_MEMBER, 'To pay')
    )
    PENDING = 'pending'
    COLLECTED = 'collected'
    PAID = 'paid'
    CANCELLED = 'cancelled'
    STATUS = (
        (PENDING, PENDING),
        (COLLECTED, COLLECTED),
        (PAID, PAID),
        (CANCELLED, CANCELLED)
    )
    TRANCHE = "tranche"
    CANCELLATION_FINAL_SETTLEMENT = "cfs"
    DIRECT_PAYMENT = "dp"
    REFUND = "refund"
    PAYMENT_TYPE = (
        (TRANCHE, 'Tranche'),
        (CANCELLATION_FINAL_SETTLEMENT, 'Cancellation final settlement'),
        (DIRECT_PAYMENT, "Direct payment"),
        (REFUND, 'Refund')
    )
    member = models.ForeignKey('members.Member', on_delete=models.PROTECT)
    member_currency = models.ForeignKey('dmcpesys.Currency', on_delete=models.PROTECT, null=True, blank=True,
                                        verbose_name="Member Currency")
    amount = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(500000000)],
                               verbose_name="Amount (Member Currency)", default=0)
    amount_in_collection_currency = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(500000000)],
                                                      verbose_name="Amount in Collection Currency", default=0)
    booking = models.ForeignKey(Booking, on_delete=models.PROTECT, related_name="planned_payments")
    date = models.DateField(verbose_name="Due Date")
    type = models.CharField(max_length=30, choices=DUE_TYPE)
    status = models.CharField(max_length=10, choices=STATUS, default=PENDING)
    payment_type = models.CharField(max_length=10, choices=PAYMENT_TYPE, default=TRANCHE)
    remark = models.TextField(null=True, blank=True, verbose_name="Remark (In Case Cancellation)")
    actual_payment_amount = models.FloatField(verbose_name="Actual Payment Amount", default=0)
    actual_payment_amount_in_collection_currency = models.FloatField(verbose_name="Actual Payment Amount (Collection Currency)", default=0)
    organization = models.ForeignKey('members.Organization', on_delete=models.PROTECT, related_name="planned_payments", null=True,
                                     blank=True)

    class Meta:
        verbose_name_plural = "Planned Payment Schedule - Buyers and Sellers"

    def __str__(self):
        return str(self.booking) + " | " + str(self.amount) + " | " + str(self.status) + " | " + str(self.type)


class PlannedPaymentBuyerProxy(PlannedPayment):
    class Meta:
        proxy = True
        verbose_name_plural = "Scheduled Collection  Buyer"


class PlannedPaymentSellerProxy(PlannedPayment):
    class Meta:
        proxy = True
        verbose_name_plural = "Scheduled Payment Seller"


auditlog.register(PlannedPayment)
