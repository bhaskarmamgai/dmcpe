from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.conf import settings
from auditlog.registry import auditlog
from common.models import BaseModel

class BookingInvoices(BaseModel):
    booking = models.ForeignKey("bms.Booking", related_name="invoices", on_delete=models.PROTECT)
    tax_invoice_number = models.CharField(max_length=100, blank=False, null=False)
    document_path = models.URLField(blank=True, null=True, max_length=512)
    description_of_reimbursement = models.CharField(max_length=200, blank=False, null=False)
    reimbursement_amount = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(10000000)],
                                             verbose_name="Reimbursement Amount", default=0)
    description_of_service_charges = models.CharField(max_length=200, blank=False, null=False)
    service_charges = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(3000000)],
                                        verbose_name="Service Charges", default=0)
    igst_percentage_on_service_charges = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(100)],
                                                           verbose_name="IGST(%)", default=0)
    igst_amount_on_service_charges = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(3000000)],
                                                       verbose_name="IGST Amount", default=0)
    cgst_percentage_on_service_charges = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(100)],
                                                           verbose_name="CGST(%)", default=0)
    cgst_amount_on_service_charges = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(3000000)],
                                                       verbose_name="CGST Amount", default=0)
    sgst_percentage_on_service_charges = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(100)],
                                                           verbose_name="SGST(%)", default=0)
    sgst_amount_on_service_charges = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(10000000)],
                                                       verbose_name="SGST Amount", default=0)
    total_service_charges_with_tax = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(10000000)],
                                                       verbose_name="Total Service Charge With Tax", default=0)
    invoice_amount = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(10000000)],
                                       verbose_name="Invoice Amount", default=0)
    sac_code_service = models.CharField(max_length=50, blank=False, null=False)
    invoice_reference_number = models.CharField(max_length=100, blank=True, null=True)
    approved_discount = models.FloatField(default=0, verbose_name="Approved Discount")
    invoice_type = models.CharField(max_length=100, choices=settings.TRANSACTION_INVOICE_TYPE_CHOICES, null=True)

    def __str__(self):
        return "Invoice Number : %s" % (self.tax_invoice_number)

    class Meta:
        verbose_name_plural = "Invoices"

    @property
    def get_file_url(self):
        return '{}'.format(self.document_path) if self.document_path else None

    @property
    def get_previous_file_url(self):
        return '{}/{}/{}'.format(settings.AWS_S3_ENDPOINT_URL,
                                 settings.AWS_S3_TRANSACTION_INVOICES_BUCKET_NAME,
                                 self.document_path) if self.id else ''


class BookingVoucher(BaseModel):
    booking = models.ForeignKey("bms.Booking", related_name="vouchers", on_delete=models.PROTECT)
    document_url = models.URLField(blank=False, null=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Vouchers"

    def __str__(self):
        return "Voucher : %s" % self.document_url


auditlog.register(BookingInvoices)
auditlog.register(BookingVoucher)
