from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from auditlog.registry import auditlog
from members.models import Organization
from bms.enums import RELEASE_REQUEST_RELEASE_OPTION, BANK_TRANSFER, RefundMode
import datetime
from common.models import BaseModel

class ReleaseRequest(BaseModel):
    PENDING = 'pending'
    RELEASED = 'released'
    REJECTED = 'rejected'
    STATUS = (
        (PENDING, 'PENDING'),
        (RELEASED, 'RELEASED'),
        (REJECTED, 'REJECTED')
    )
    booking = models.ForeignKey('bms.Booking', on_delete=models.PROTECT, related_name="booking_release_requests",
                                null=True, blank=True)
    member = models.ForeignKey('members.Member', on_delete=models.PROTECT)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="release_requests", null=True,
                                     blank=True)
    mode = models.CharField(max_length=20, choices=RELEASE_REQUEST_RELEASE_OPTION, default=BANK_TRANSFER,
                            verbose_name="Selected Mode of Release")
    requested_currency = models.ForeignKey('dmcpesys.Currency', on_delete=models.PROTECT, null=True)
    requested_amount = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(500000000)],
                                         verbose_name="Requested Amount", default=0)
    to_be_released_on = models.DateField(null=True, blank=True)

    organization_bank_account = models.ForeignKey('members.BankAccount', on_delete=models.PROTECT, null=True,
                                                  blank=True,
                                                  verbose_name="Organization Bank Account")
    description = models.CharField(max_length=200, blank=False, null=False)
    status = models.CharField(max_length=10, choices=STATUS, default=PENDING)
    amount_released_including_charges = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(500000000)],
        verbose_name="Amount Released in Member currency", default=0, null=True, blank=True)
    release_notes = models.CharField(max_length=200, null=True, blank=True)

    proof = models.FileField(blank=False, null=True, max_length=255)
    remark = models.CharField(max_length=500, null=True, verbose_name="Remark")
    refund_mode = models.CharField(max_length=20, choices=RefundMode.choices(), default=RefundMode.BLANK.value,
                                   verbose_name="Refund Mode")

    class Meta:
        verbose_name_plural = "Release Requests"

    def __str__(self):
        return "#" + str(self.id) + " | " + str(self.member) + " | " + str(self.requested_amount) + " | " + "{:%Y-%m-%d %H:%M}".format(
            self.created_at)


class ReleaseRequestProxy(ReleaseRequest):
    class Meta:
        proxy = True
        verbose_name_plural = "Release Request"


class ReleaseRequestStatusHistory(BaseModel):
    release_request = models.ForeignKey(ReleaseRequest, on_delete=models.PROTECT)
    status = models.CharField(max_length=50, choices=ReleaseRequest.STATUS, default=ReleaseRequest.PENDING)

    class Meta:
        verbose_name_plural = "Release Request Status History"

    def __str__(self):
        return str(self.status) + " | " + " | " + "{:%Y-%m-%d %H:%M}".format(
            self.created_at)


class ReleaseRequestPayments(BaseModel):
    booking = models.ForeignKey('bms.Booking', on_delete=models.PROTECT, null=True)
    organization = models.ForeignKey('members.Organization', on_delete=models.PROTECT, null=True)
    release_request = models.ForeignKey('bms.ReleaseRequest', on_delete=models.PROTECT, null=True, verbose_name="Release Request")
    amount_released_in_member_currency = models.FloatField(verbose_name="Amount Released in Member Currency", null=True)
    roe_on_date_of_payment = models.FloatField(verbose_name="ROE on Date of Payment", null=True)
    remit_type = models.ForeignKey('dmcpesys.RemitType', verbose_name="Remit Type", on_delete=models.PROTECT, null=True)
    remit_type_cost = models.FloatField(verbose_name="Remit Type Cost", null=True)
    transaction_cost = models.FloatField(null=True, verbose_name="Booking Cost")
    date_of_payment = models.DateField(null=True, blank=True, default=datetime.date.today, verbose_name="Date of Payment")
    sce = models.ForeignKey('dmcpesys.TravelSupplyGroupEntities', on_delete=models.PROTECT, null=True, verbose_name="SCE")
    sce_currency = models.ForeignKey('dmcpesys.Currency', on_delete=models.PROTECT, null=True, verbose_name="SCE Currency")
    utr_or_transaction_no = models.CharField(max_length=100, null=True, verbose_name="UTR / Booking No")

    class Meta:
        verbose_name_plural = "Release Request Payments"


auditlog.register(ReleaseRequest)
auditlog.register(ReleaseRequestProxy)
