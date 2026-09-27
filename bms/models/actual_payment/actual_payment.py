from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from common.models import BaseModel
from auditlog.registry import auditlog
from accounts.models import BankRecord, Posting
from bms.models.release_request.release_request import ReleaseRequest
from bms.models.booking.booking import Booking
from members.models import Organization
from dmcpesys.models import Currency


class ActualPayment(BaseModel):
    PAID_BY_MEMBER = 'paid_by_member'
    PAID_TO_MEMBER = 'paid_to_member'
    ACTUAL_PAYMENT_TYPE = (
        (PAID_BY_MEMBER, 'Collected'),
        (PAID_TO_MEMBER, 'Paid')
    )
    PAID = 'paid'
    COLLECTED = 'collected'
    PENDING = 'pending'
    REJECTED = 'rejected'
    PAYMENT_STATUS = (
        (PAID, PAID),
        (COLLECTED, COLLECTED),
        (PENDING, PENDING),
        (REJECTED, REJECTED)
    )
    member = models.ForeignKey('members.Member', on_delete=models.PROTECT)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="actual_payments", null=True,
                                     blank=True)
    booking = models.ForeignKey(Booking, on_delete=models.PROTECT, related_name="actual_payments")
    amount = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(500000000)],
                               verbose_name="Amount", default=0)
    amount_in_member_currency = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(500000000)],
                                                  verbose_name="Amount in member currency", default=0)
    amount_in_collection_currency = models.FloatField(validators=[MinValueValidator(1), MaxValueValidator(500000000)],
                                                      verbose_name="Amount in Collection Currency", null=True,
                                                      blank=True, default=0)
    member_currency = models.ForeignKey(Currency, on_delete=models.PROTECT, verbose_name="Member Currency",
                                        related_name="actual_payments", null=True, blank=True)
    date = models.DateField()
    type = models.CharField(max_length=30, choices=ACTUAL_PAYMENT_TYPE)
    record = models.ForeignKey(BankRecord, on_delete=models.PROTECT, null=True, blank=True)
    release_request = models.ForeignKey(ReleaseRequest, on_delete=models.PROTECT, related_name='actual_payments',
                                        null=True, blank=True)
    posting = models.ForeignKey(Posting, on_delete=models.PROTECT, null=True, blank=True,
                                related_name="actual_payments")
    status = models.CharField(max_length=50, choices=PAYMENT_STATUS, null=True, blank=True,
                              verbose_name="Payment Status")

    class Meta:
        verbose_name_plural = "Actual Payments"

    def __str__(self):
        return str(self.booking) + " | " + str(self.amount) + " | " + str(self.date)



class ActualPaymentBuyerProxy(ActualPayment):
    class Meta:
        proxy = True
        verbose_name_plural = "Actual Collection - Buyer"


class ActualPaymentSellerProxy(ActualPayment):
    class Meta:
        proxy = True
        verbose_name_plural = "Actual Payment - Seller"


auditlog.register(ActualPayment)
