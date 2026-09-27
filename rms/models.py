import uuid
from django.db import models
from common.models import BaseModel, CodeMixin


class RMSProfile(BaseModel):
    """
    RMS specific extension or preferences per member / organization.
    """
    organization = models.OneToOneField(
        'members.Organization',
        on_delete=models.CASCADE,
        related_name='rms_profile'
    )
    is_active_remitter = models.BooleanField(default=True)

    def __str__(self):
        return f"RMS Profile - {self.organization.name}"

    class Meta:
        verbose_name = "RMS Profile"
        verbose_name_plural = "RMS Profiles"


class Beneficiary(CodeMixin, BaseModel):
    """
    Beneficiary Account Model storing bank details and beneficiary contact info.
    """
    organization = models.ForeignKey(
        'members.Organization',
        on_delete=models.CASCADE,
        related_name='beneficiaries'
    )
    
    # Account Info
    account_number = models.CharField(max_length=100)
    swift_code = models.CharField(max_length=50)
    iban = models.CharField(max_length=100, blank=True, null=True)
    bank_name = models.CharField(max_length=255)
    bank_address = models.TextField(blank=True, null=True)
    bank_city = models.CharField(max_length=100, blank=True, null=True)
    bank_country = models.ForeignKey(
        'dmcpesys.Country',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='beneficiary_banks'
    )
    currency = models.ForeignKey(
        'dmcpesys.Currency',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='beneficiary_currencies'
    )

    # Beneficiary Contact Info
    beneficiary_name = models.CharField(max_length=255)
    beneficiary_address = models.TextField(blank=True, null=True)
    beneficiary_country = models.ForeignKey(
        'dmcpesys.Country',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='beneficiary_countries'
    )
    beneficiary_city = models.CharField(max_length=100, blank=True, null=True)
    zone = models.CharField(max_length=100, default="OTHER", blank=True, null=True)
    beneficiary_email = models.EmailField(blank=True, null=True)
    beneficiary_mobile = models.CharField(max_length=30, blank=True, null=True)

    CLASS_PREFIX = "BEN"

    def __str__(self):
        return f"{self.beneficiary_name} - {self.bank_name} ({self.account_number})"

    class Meta:
        verbose_name = "Beneficiary"
        verbose_name_plural = "Beneficiaries"
        ordering = ['-created_at']


class RemittancePurposeChoices(models.TextChoices):
    TOUR_COST = "TOUR_COST", "Tour Cost"
    MICE_BUSINESS_TRAVEL = "MICE_BUSINESS_TRAVEL", "MICE - Business Travel"
    TOUR_COST_OFFLINE_B2B = "TOUR_COST_OFFLINE_B2B", "Tour Cost -Offline B2b"
    OVERSEAS_EDUCATION = "OVERSEAS_EDUCATION", "Overseas Education"


class RemittanceStageChoices(models.TextChoices):
    STAGE_1_INVOICE = "STAGE_1_INVOICE", "Stage 1: Create Invoice"
    STAGE_2_KYC = "STAGE_2_KYC", "Stage 2: KYC & Passenger PAN Verification"
    STAGE_3_PAYMENT = "STAGE_3_PAYMENT", "Stage 3: Payment"
    STAGE_4_CONFIRMATION = "STAGE_4_CONFIRMATION", "Stage 4: Remittance Confirmation"
    COMPLETED = "COMPLETED", "Completed"


class RemittanceStatusChoices(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    INVOICE_SUBMITTED = "INVOICE_SUBMITTED", "Invoice Submitted"
    PAN_VERIFIED = "PAN_VERIFIED", "PAN Verified & LRS Declared"
    PAYMENT_PENDING = "PAYMENT_PENDING", "Payment Pending"
    PAYMENT_RECEIVED = "PAYMENT_RECEIVED", "Payment Received"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"
    REJECTED = "REJECTED", "Rejected"


class PaymentOptionChoices(models.TextChoices):
    RATE_BLOCKING = "RATE_BLOCKING", "Rate Blocking"
    PAY_100_PERCENT_ONLINE = "PAY_100_PERCENT_ONLINE", "Pay 100% Online"


class PaymentModeChoices(models.TextChoices):
    NETBANKING = "Netbanking", "Netbanking"
    NEFT_RTGS = "NEFT_RTGS", "NEFT / RTGS"
    UPI = "UPI", "UPI"
    DEBIT_CARD = "DEBIT_CARD", "Debit Card"
    OTHER = "OTHER", "Other"


def remittance_invoice_upload_path(instance, filename):
    req_id = instance.id or uuid.uuid4()
    return f"remittances/{req_id}/invoices/{filename}"


def remittance_payment_proof_upload_path(instance, filename):
    req_id = instance.id or uuid.uuid4()
    return f"remittances/{req_id}/payment_proofs/{filename}"


def remittance_swift_copy_upload_path(instance, filename):
    req_id = instance.id or uuid.uuid4()
    return f"remittances/{req_id}/swift_copies/{filename}"


class RemittanceRequest(CodeMixin, BaseModel):
    """
    Main Remittance Request model tracking all 4 stages & journey resume state.
    """
    organization = models.ForeignKey(
        'members.Organization',
        on_delete=models.CASCADE,
        related_name='remittances'
    )
    member = models.ForeignKey(
        'members.Member',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='remittances'
    )
    beneficiary = models.ForeignKey(
        Beneficiary,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='remittances'
    )

    # Journey Stage & Status Tracker
    current_stage = models.CharField(
        max_length=30,
        choices=RemittanceStageChoices.choices,
        default=RemittanceStageChoices.STAGE_1_INVOICE,
        help_text="Tracks exact stage for journey resume"
    )
    status = models.CharField(
        max_length=30,
        choices=RemittanceStatusChoices.choices,
        default=RemittanceStatusChoices.DRAFT
    )

    # ================= Stage 1: Create Invoice =================
    purpose = models.CharField(
        max_length=50,
        choices=RemittancePurposeChoices.choices,
        default=RemittancePurposeChoices.TOUR_COST
    )
    beneficiary_name = models.CharField(max_length=255, blank=True, null=True)
    beneficiary_email = models.EmailField(blank=True, null=True)
    beneficiary_mobile = models.CharField(max_length=30, blank=True, null=True)
    
    invoice_reference_number = models.CharField(max_length=100, blank=True, null=True)
    invoice_date = models.DateField(blank=True, null=True)
    invoice_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    
    # Part Payment Fields
    is_part_payment = models.BooleanField(
        default=False,
        help_text="True if remitting a portion of the total invoice amount"
    )
    remittance_amount = models.DecimalField(
        max_digits=14, decimal_places=2, default=0.00,
        help_text="Actual amount being remitted in this request"
    )

    currency = models.ForeignKey(
        'dmcpesys.Currency',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='remittance_requests'
    )
    intermediary_bank_charges = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00
    )
    no_of_travellers = models.PositiveIntegerField(default=1)
    invoice_document = models.FileField(
        upload_to=remittance_invoice_upload_path,
        blank=True, null=True
    )

    # ================= Stage 2: KYC & LRS / TCS Declarations =================
    lrs_declaration_accepted = models.BooleanField(default=False)
    lrs_declaration_accepted_at = models.DateTimeField(blank=True, null=True)
    lrs_declaration_text = models.TextField(blank=True, null=True)

    tcs_declaration_accepted = models.BooleanField(default=False)
    tcs_declaration_accepted_at = models.DateTimeField(blank=True, null=True)

    tcs_liability_declaration_accepted = models.BooleanField(default=False)
    tcs_liability_declaration_accepted_at = models.DateTimeField(blank=True, null=True)

    # ================= Stage 3: Payment Process (Rate Blocking & Breakup) =================
    payment_option_type = models.CharField(
        max_length=30,
        choices=PaymentOptionChoices.choices,
        default=PaymentOptionChoices.RATE_BLOCKING,
        blank=True, null=True
    )
    exchange_rate = models.DecimalField(
        max_digits=10, decimal_places=4, default=75.1697,
        help_text="Forex deal rate e.g. 75.1697 INR/Currency"
    )
    deal_value_inr = models.DecimalField(
        max_digits=14, decimal_places=2, default=0.00,
        help_text="Total Foreign Currency Amount * Exchange Rate"
    )
    processing_fee_inr = models.DecimalField(
        max_digits=10, decimal_places=2, default=300.00
    )
    gst_amount_inr = models.DecimalField(
        max_digits=10, decimal_places=2, default=3549.00
    )
    final_amount_inr = models.DecimalField(
        max_digits=14, decimal_places=2, default=0.00,
        help_text="Total INR Payable = Deal Value + Processing Fee + GST"
    )

    payment_method = models.CharField(
        max_length=50,
        choices=PaymentModeChoices.choices,
        default=PaymentModeChoices.NETBANKING,
        blank=True, null=True
    )
    payment_reference_number = models.CharField(max_length=100, blank=True, null=True)
    payment_proof_document = models.FileField(
        upload_to=remittance_payment_proof_upload_path,
        blank=True, null=True
    )
    paid_amount = models.DecimalField(
        max_digits=14, decimal_places=2, blank=True, null=True
    )
    payment_date = models.DateTimeField(blank=True, null=True)

    payment_disclaimer_accepted = models.BooleanField(default=False)
    payment_disclaimer_accepted_at = models.DateTimeField(blank=True, null=True)

    # ================= Stage 4: Confirmation =================
    bank_reference_number = models.CharField(max_length=100, blank=True, null=True)
    swift_copy_document = models.FileField(
        upload_to=remittance_swift_copy_upload_path,
        blank=True, null=True
    )
    completed_at = models.DateTimeField(blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)

    CLASS_PREFIX = "REM"

    def __str__(self):
        return f"{self.code or self.id} - {self.organization.name} ({self.get_current_stage_display()})"

    class Meta:
        verbose_name = "Remittance Request"
        verbose_name_plural = "Remittance Requests"
        ordering = ['-created_at']


class RemittancePassenger(BaseModel):
    """
    Passenger PAN, Mobile, and journey details associated with a Remittance Request under Stage 2 (KYC/LRS/TCS).
    """
    remittance_request = models.ForeignKey(
        RemittanceRequest,
        on_delete=models.CASCADE,
        related_name='passengers'
    )
    pan_number = models.CharField(max_length=10)
    passenger_name = models.CharField(max_length=255, blank=True, null=True)
    passenger_mobile = models.CharField(max_length=30, blank=True, null=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    date_of_journey = models.DateField()
    
    currency = models.ForeignKey(
        'dmcpesys.Currency',
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    is_pan_verified = models.BooleanField(default=False)
    pan_verified_at = models.DateTimeField(blank=True, null=True)
    verification_response = models.JSONField(blank=True, null=True)

    def __str__(self):
        return f"Passenger PAN: {self.pan_number} ({self.passenger_name or 'No name'}) - Amount: {self.amount}"

    class Meta:
        verbose_name = "Remittance Passenger"
        verbose_name_plural = "Remittance Passengers"
        ordering = ['id']
