from common.models import BaseModel,CodeMixin
from decimal import Decimal
from django.db import models
from django.db import models
from auditlog.registry import auditlog
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth import get_user_model
from members.models import Member
from wallets.enums import PAYOUT_REQUEST_STATUS, PENDING, WALLET_ADD_MONEY_REQUEST_INTERNAL_SERVICE_CHOICES, \
    PAYOUT_REQUEST_TYPE_MANUAL, PAYOUT_REQUEST_TYPE_CHOICES
from members.models import Organization
from dmcpesys.models import Currency
from django.core.validators import ValidationError


class Wallet(CodeMixin,BaseModel):
    organization = models.ForeignKey(
        'members.Organization',
        on_delete=models.CASCADE,
        related_name="wallets"
    )

    currency = models.ForeignKey(
        'dmcpesys.Currency',
        on_delete=models.PROTECT,
        related_name="wallets"
    )

    current_balance = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100000000)], verbose_name='Current Balanace')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "currency"],
                name="unique_wallet_per_org_currency"
            )
        ]
        verbose_name = "Wallet"
        verbose_name_plural = "Wallets"
    
    CLASS_PREFIX = "WB"

    def __str__(self):
        return f"{self.organization} - {self.currency.code}"

    def clean(self):
        super(Wallet, self).clean()
        if self.pk is not None:
            obj = Wallet.objects.get(pk=self.pk)
            if obj.currency and obj.currency != self.currency:
                raise ValidationError("Once Currency Set Cannot be changed")



class PayOutRequest(CodeMixin,BaseModel):
    wallet = models.ForeignKey('wallets.Wallet', on_delete=models.PROTECT, related_name="payout_requests",
                               verbose_name="Wallet")
    code = models.CharField(max_length=20, unique=True, blank=True, null=True)
    member = models.ForeignKey(Member, on_delete=models.PROTECT, related_name="payout_requests", verbose_name="Member")
    organization = models.ForeignKey('members.Organization', on_delete=models.PROTECT,
                                     related_name="payout_requests",
                                     verbose_name="Organization")
    bank_account = models.ForeignKey('members.BankAccount', on_delete=models.PROTECT,
                                     related_name="payout_requests",
                                     verbose_name="Bank Account", null=True, blank=True)
    requested_amount = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(1000000000)],
                                         verbose_name="Requested Amount")
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, default=1, related_name="payout_requests")
    status = models.CharField(max_length=50, choices=PAYOUT_REQUEST_STATUS, default=PENDING, verbose_name="Status")
    release_note = models.CharField(max_length=500, null=True, verbose_name="Release")
    remark = models.CharField(max_length=500, null=True, verbose_name="Remark")
    proof = models.FileField(blank=False, null=True, max_length=255)
    created_by = models.ForeignKey(get_user_model(), on_delete=models.PROTECT,
                                   verbose_name="Created By")
    unique_transaction_reference_id = models.CharField(max_length=255, null=True, blank=True, unique=True,
                                                       verbose_name="UTR")
    type = models.CharField(max_length=50, choices=PAYOUT_REQUEST_TYPE_CHOICES, default=PAYOUT_REQUEST_TYPE_MANUAL,
                            verbose_name="Payout Type")

    CLASS_PREFIX = 'PB'


    
    def __str__(self):
        return "#{} | {} | {}".format(self.bank_account, self.requested_amount, self.status)

    class Meta:
        verbose_name_plural = "Wallet - PayOut Requests"


class PayOutRequestStatusHistory(BaseModel):
    payout_request = models.ForeignKey(PayOutRequest, on_delete=models.PROTECT)
    status = models.CharField(max_length=50, choices=PAYOUT_REQUEST_STATUS, default=PENDING)

    class Meta:
        verbose_name_plural = "Payout Request Status History"

    def __str__(self):
        return str(self.status) + " | " + " | " + "{:%Y-%m-%d %H:%M}".format(
            self.created_at) + " | " + self.created_by.username


class AddToWalletInternalRequest(BaseModel):
    organization_code = models.CharField(max_length=10)
    amount = models.IntegerField()
    service_type = models.CharField(max_length=100, choices=WALLET_ADD_MONEY_REQUEST_INTERNAL_SERVICE_CHOICES)
    description = models.TextField()

    class Meta:
        verbose_name_plural = "Add To Wallet Internal Requests"

    def __str__(self):
        return "{} | {} | {}".format(self.service_type, self.organization_code, self.amount)


class WalletStatement(BaseModel):
    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name="wallet_statements", null=True)
    request_from_member = models.ForeignKey(Member, on_delete=models.PROTECT, related_name="request_from_member",
                                            null=True)
    document_url = models.URLField(null=True)
    start_date = models.DateField(verbose_name="Start Date")
    end_date = models.DateField(verbose_name="End Date")

    class Meta:
        verbose_name_plural = "Wallet Statements"


class PayoutRequestLogs(BaseModel):
    payout_request = models.ForeignKey(PayOutRequest, on_delete=models.PROTECT, related_name='payout_request_logs',
                                       null=True)
    request_from_client = models.TextField(null=True, blank=True)
    request_to_travpay = models.TextField(null=True, blank=True, verbose_name="Request / Message to Travpay")
    response_from_travpay = models.TextField(null=True, blank=True)
    response_to_client = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name_plural = 'Payout Logs'


auditlog.register(Wallet)
auditlog.register(PayOutRequest)
auditlog.register(AddToWalletInternalRequest)
auditlog.register(WalletStatement)