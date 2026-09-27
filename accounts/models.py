from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.contrib.auth import get_user_model
from members.models import Member
from dmcpesys.models import Bank
from common.models import BaseModel
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
from accounts.models_manager import PostingManager
from accounts.enums import CREDIT_OR_DEBIT, MODE_OF_PAYMENT, BANK_TRANSFER
from dmcpesys.models import Service, Currency
from members.models import Organization
from wallets.models import Wallet
from .constants import CURRENCY_ID_INR
from auditlog.registry import auditlog
from django.conf import settings


class Journal(BaseModel):
    type = models.CharField(max_length=50, unique=True, null=False, blank=False)

    def __str__(self):
        return self.type


class Posting(models.Model):
    member = models.ForeignKey(Member, on_delete=models.PROTECT, related_name="postings", null=True)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="postings", null=True)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, default=CURRENCY_ID_INR, related_name="postings")
    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name="postings", null=True)
    journal = models.ForeignKey(Journal, on_delete=models.PROTECT, related_name="postings")
    datetime = models.DateTimeField(blank=False, null=False)
    debit = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(500000000)], verbose_name="Debit",
                              default=0, null=False, blank=False)
    credit = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(500000000)], verbose_name="Credit",
                               default=0, null=False, blank=False)
    balance = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(500000000)],
                                verbose_name="Running Balance", default=0, null=False, blank=False)
    description = models.CharField(max_length=500, blank=True, null=True, verbose_name="Description")
    technical_description = models.CharField(max_length=500, blank=True, null=True,
                                             verbose_name="Technical Description")

    def __str__(self):
        # never ever use nullable fields here i repeat never
        return "{} {}".format(self.id, self.journal)

    # https://docs.djangoproject.com/en/2.2/ref/models/instances/#creating-objects
    objects = PostingManager()


def upload_to_bank_statement_directory(instance, filename):
    import datetime
    year = datetime.datetime.now().year
    month = datetime.datetime.now().strftime("%B")
    return 'accounts/bank_statements/{}/{}/{}/{}'.format(year, instance.bank.name, month,
                                                         filename.replace(" ", "-").lower())


class BankStatement(BaseModel):
    file = models.FileField(blank=False, null=False, max_length=255,upload_to=upload_to_bank_statement_directory)
    bank = models.ForeignKey(Bank, on_delete=models.PROTECT)
    from_date = models.DateField(blank=False, null=False)
    to_date = models.DateField(blank=False, null=False)
    records_imported = models.BooleanField(default=False)
    created_by = models.ForeignKey(get_user_model(), on_delete=models.PROTECT, blank=False, null=False)
    created_at = models.DateTimeField(auto_now_add=True, blank=False, null=False)

    def clean(self):
        if not self.file:
            raise ValidationError({'file_name': mark_safe("Please Upload CSV File")})
        if self.file:
            if not self.file.name.endswith('.csv'):
                raise ValidationError({'file_name': mark_safe("Only CSV File Allowed")})

    def __str__(self):
        return self.bank.name + ":" + str(self.created_at.date())

    class Meta:
        verbose_name_plural = "Bank Statements"


def bank_record_proof_file_path(instance, filename):
    return 'accounts/bank_record/proof/{0}/{1}/{2}/{3}'.format(instance.date.year, instance.date.month, instance.id,
                                                               filename.replace(" ", "-").lower())


class BankRecord(BaseModel):
    COLLECTION = "collection"
    REFUND = "refund"
    SOURCES = (
        (COLLECTION, "Collection"),
        (REFUND, "Refund"),
    )
    mode_of_payment = models.CharField(max_length=30, choices=MODE_OF_PAYMENT, default=BANK_TRANSFER)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, default=CURRENCY_ID_INR,
                                 related_name="bank_records")
    statement = models.ForeignKey(BankStatement, null=True, on_delete=models.PROTECT,
                                  related_name="bank_records_imported")
    date = models.DateField()
    reference_id = models.CharField(max_length=150, blank=True, null=True, verbose_name="Reference/Check No")
    description = models.CharField(max_length=500, blank=True, null=True, verbose_name="Description/Narration")
    amount = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100000000)], verbose_name='Amount')
    credit_or_debit = models.CharField(max_length=20, choices=CREDIT_OR_DEBIT, null=False, blank=False)
    proof = models.FileField(max_length=255)
    claimed = models.BooleanField(default=False)
    service = models.ForeignKey(Service, on_delete=models.PROTECT, null=True, blank=True)
    remark = models.CharField(max_length=200, null=True, blank=True,
                              verbose_name="Remark(in case record mark as deleted)")
    member = models.ForeignKey(Member, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Member")
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="bank_records", null=True,
                                     blank=True, verbose_name="Member Organization")
    posting = models.ForeignKey(Posting, on_delete=models.PROTECT, null=True, blank=True, related_name="bank_records")
    source = models.CharField(max_length=50, choices=SOURCES, default=COLLECTION)
    bank = models.ForeignKey(Bank, on_delete=models.PROTECT, null=True, blank=True)
    comment = models.CharField(max_length=500, blank=True, null=True, verbose_name="Comment")

    class Meta:
        verbose_name_plural = "Bank Records"

    def __str__(self):
        return str(self.date) + " | " + str(self.amount) + " | " + str(self.credit_or_debit) + " | " + str(
            self.reference_id)

    def clean(self):
        if self.is_deleted:
            if not self.remark:
                raise ValidationError({'remark': mark_safe("This field is required")})

    def get_proof_url(self):
        return '%s' % self.proof.name if self.id else ''


auditlog.register(BankRecord)
