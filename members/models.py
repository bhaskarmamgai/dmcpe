import uuid
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import Q

from common.models import BaseModel, CodeMixin
from dmcpesys.models import Country, State
from auditlog.registry import auditlog


class Action(BaseModel):
    name = models.CharField(max_length=50)
    internal_name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Actions"


class Campaign(BaseModel):
    name = models.CharField(max_length=100)
    internal_name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Campaigns"


class DocumentRequirementType(models.TextChoices):
    MANDATORY = "MANDATORY", "Mandatory"
    CONDITIONAL = "CONDITIONAL", "Conditional"
    OPTIONAL = "OPTIONAL", "Optional"


class BusinessType(models.TextChoices):
    SOLE_PROPRIETORSHIP = "SOLE", "Sole Proprietorship"
    PARTNERSHIP = "PART", "Partnership"
    LLP = "LLP", "LLP"
    PRIVATE_LIMITED = "PVT", "Private Limited"
    PUBLIC_LIMITED = "PUB", "Public Limited"
    FREELANCER = "FREELANCER", "FREELANCER"
    OTHER = "OTHER", "Other"


class KYCStatus(models.TextChoices):
    NOT_STARTED = "NOT_STARTED", "Not Started"
    PENDING = "PENDING", "Pending"
    UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    EXPIRED = "EXPIRED", "Expired"


class DocumentOwnerType(models.TextChoices):
    MEMBER = "MEMBER", "member"
    ORGANIZATION = "ORGANIZATION", "organization"


class DocumentCategory(models.TextChoices):
    IDENTITY_PROOF = "IDENTITY", "Identity Proof"
    ADDRESS_PROOF = "ADDRESS", "Address Proof"
    BUSINESS_PROOF = "BUSINESS", "Business Proof"
    BANK_PROOF = "BANK", "Bank Proof"
    TAX_REGISTRATION = "TAX", "Tax Registration"
    DECLARATION = "DECLARATION", "Declaration"
    LEGAL_DOCUMENT = "LEGAL", "Legal Document"
    BUSINESS_PAN = "BUSINESS_PAN", "Business PAN"
    OTHER = "OTHER", "Other"


class DocumentType(models.TextChoices):
    PAN = "PAN", "PAN Card"
    AADHAR = "AADHAR", "Aadhaar"
    PASSPORT = "PASSPORT", "Passport"
    DRIVING_LICENSE = "DL", "Driving License"
    GST_CERTIFICATE = "GST", "GST Certificate"
    MSME_UDYAM = "MSME", "MSME / Udyam Certificate"
    INCORPORATION_CERTIFICATE = "INC", "Incorporation Certificate"
    BANK_PROOF = "BANK", "Bank Proof"
    PHOTO = "PHOTO", "Photograph"
    SIGNATURE = "SIGN", "Signature"
    OTHER = "OTHER", "Other"
    GST_DECLARATION = "GST_DECLARATION", "GST Declaration"
    PARTNERSHIP_DEED = "PARTNERSHIP_DEED", "Partnership Deed / LLP Agreement"
    SHOP_ESTABLISHMENT = "SHOP_EST", "Shop Establishment Certificate"
    OTHER_GOVT_PROOF = "OTHER_GOVT", "Other Government Proof"


DOCUMENT_RULES = {
    DocumentOwnerType.MEMBER: {
        DocumentCategory.IDENTITY_PROOF: [
            DocumentType.AADHAR,
            DocumentType.PAN,
            DocumentType.PASSPORT,
            DocumentType.DRIVING_LICENSE,
        ],
    },
    DocumentOwnerType.ORGANIZATION: {
        DocumentCategory.BANK_PROOF: [
            DocumentType.BANK_PROOF,
        ],
        DocumentCategory.TAX_REGISTRATION: [
            DocumentType.GST_CERTIFICATE,
            DocumentType.GST_DECLARATION,
        ],
        DocumentCategory.BUSINESS_PROOF: [
            DocumentType.MSME_UDYAM,
            DocumentType.SHOP_ESTABLISHMENT,
            DocumentType.OTHER_GOVT_PROOF,
        ],
        DocumentCategory.LEGAL_DOCUMENT: [
            DocumentType.INCORPORATION_CERTIFICATE,
            DocumentType.PARTNERSHIP_DEED,
        ],
        DocumentCategory.BUSINESS_PAN: [
            DocumentType.PAN,
        ],
    },
}


# ==============================
# KYC DOCUMENT REQUIREMENT MATRIX
# ==============================
class MemberBuyingPotential(BaseModel):
    name = models.CharField(max_length=255)
    description = models.TextField()
    internal_name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Member Buying Potential"
        verbose_name_plural = "Member Buying Potentials"


BUSINESS_KYC_REQUIREMENTS = {

    BusinessType.FREELANCER: {
        DocumentOwnerType.MEMBER: {
            DocumentCategory.IDENTITY_PROOF: {
                DocumentType.AADHAR: DocumentRequirementType.MANDATORY,
                DocumentType.PAN: DocumentRequirementType.MANDATORY,
            },
        },
        DocumentOwnerType.ORGANIZATION: {
            DocumentCategory.BANK_PROOF: {
                DocumentType.BANK_PROOF: DocumentRequirementType.MANDATORY,
            },
            DocumentCategory.TAX_REGISTRATION: {
                DocumentType.GST_CERTIFICATE: DocumentRequirementType.OPTIONAL,
                DocumentType.GST_DECLARATION: DocumentRequirementType.CONDITIONAL,
            },
            DocumentCategory.BUSINESS_PROOF: {
                DocumentType.MSME_UDYAM: DocumentRequirementType.OPTIONAL,
            },
        },
    },

    BusinessType.SOLE_PROPRIETORSHIP: {
        DocumentOwnerType.MEMBER: {
            DocumentCategory.IDENTITY_PROOF: {
                DocumentType.AADHAR: DocumentRequirementType.MANDATORY,
                DocumentType.PAN: DocumentRequirementType.MANDATORY,
            },
        },
        DocumentOwnerType.ORGANIZATION: {
            DocumentCategory.BANK_PROOF: {
                DocumentType.BANK_PROOF: DocumentRequirementType.MANDATORY,
            },
            DocumentCategory.TAX_REGISTRATION: {
                DocumentType.GST_CERTIFICATE: DocumentRequirementType.MANDATORY,
            },
            DocumentCategory.BUSINESS_PROOF: {
                DocumentType.MSME_UDYAM: DocumentRequirementType.CONDITIONAL,
                DocumentType.SHOP_ESTABLISHMENT: DocumentRequirementType.CONDITIONAL,
                DocumentType.OTHER_GOVT_PROOF: DocumentRequirementType.CONDITIONAL,
            },
            DocumentCategory.DECLARATION: {
                DocumentType.GST_DECLARATION: DocumentRequirementType.CONDITIONAL,
            },
        },
    },

    BusinessType.PARTNERSHIP: {
        DocumentOwnerType.MEMBER: {
            DocumentCategory.IDENTITY_PROOF: {
                DocumentType.AADHAR: DocumentRequirementType.MANDATORY,
                DocumentType.PAN: DocumentRequirementType.MANDATORY,
            },
        },
        DocumentOwnerType.ORGANIZATION: {
            DocumentCategory.BUSINESS_PAN: {
                DocumentType.PAN: DocumentRequirementType.MANDATORY,
            },
            DocumentCategory.BANK_PROOF: {
                DocumentType.BANK_PROOF: DocumentRequirementType.MANDATORY,
            },
            DocumentCategory.LEGAL_DOCUMENT: {
                DocumentType.PARTNERSHIP_DEED: DocumentRequirementType.MANDATORY,
            },
            DocumentCategory.TAX_REGISTRATION: {
                DocumentType.GST_CERTIFICATE: DocumentRequirementType.MANDATORY,
            },
            DocumentCategory.BUSINESS_PROOF: {
                DocumentType.MSME_UDYAM: DocumentRequirementType.CONDITIONAL,
                DocumentType.SHOP_ESTABLISHMENT: DocumentRequirementType.CONDITIONAL,
                DocumentType.OTHER_GOVT_PROOF: DocumentRequirementType.CONDITIONAL,
            },
            DocumentCategory.DECLARATION: {
                DocumentType.GST_DECLARATION: DocumentRequirementType.CONDITIONAL,
            },
        },
    },

    BusinessType.PRIVATE_LIMITED: {
        DocumentOwnerType.MEMBER: {
            DocumentCategory.IDENTITY_PROOF: {
                DocumentType.AADHAR: DocumentRequirementType.MANDATORY,
                DocumentType.PAN: DocumentRequirementType.MANDATORY,
            },
        },
        DocumentOwnerType.ORGANIZATION: {
            DocumentCategory.BUSINESS_PAN: {
                DocumentType.PAN: DocumentRequirementType.MANDATORY,
            },
            DocumentCategory.BANK_PROOF: {
                DocumentType.BANK_PROOF: DocumentRequirementType.MANDATORY,
            },
            DocumentCategory.LEGAL_DOCUMENT: {
                DocumentType.INCORPORATION_CERTIFICATE: DocumentRequirementType.MANDATORY,
            },
            DocumentCategory.TAX_REGISTRATION: {
                DocumentType.GST_CERTIFICATE: DocumentRequirementType.MANDATORY,
            },
            DocumentCategory.BUSINESS_PROOF: {
                DocumentType.MSME_UDYAM: DocumentRequirementType.CONDITIONAL,
                DocumentType.SHOP_ESTABLISHMENT: DocumentRequirementType.CONDITIONAL,
                DocumentType.OTHER_GOVT_PROOF: DocumentRequirementType.CONDITIONAL,
            },
            DocumentCategory.DECLARATION: {
                DocumentType.GST_DECLARATION: DocumentRequirementType.CONDITIONAL,
            },
        },
    },
}


def organization_logo_upload_path(instance, filename):
    org_id = instance.id or uuid.uuid4()
    return f"organization/logos/{org_id}/{filename}"


class Organization(CodeMixin, BaseModel):
    name = models.CharField(max_length=150)
    website = models.URLField(blank=True, null=True)
    marketing_email = models.EmailField(blank=True, null=True)
    marketing_phone = models.CharField(max_length=20, blank=True, null=True)

    company_logo = models.FileField(
        upload_to=organization_logo_upload_path,
        blank=True,
        null=True
    )

    CLASS_PREFIX = "ORG"

    @property
    def kyc_status(self):
        """
        Returns KYC status safely.
        """
        if hasattr(self, "kyc_profile") and self.kyc_profile:
            return self.kyc_profile.status
        return None

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"


class MemberSource(BaseModel):
    name = models.CharField(max_length=50)
    internal_name = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name = "Member Source"
        verbose_name_plural = "Member Sources"

    def __str__(self):
        return f"{self.name}"


class Member(CodeMixin, BaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="member_profile",
        null=True, blank=True
    )

    account_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="acm_members",
        null=True,
        blank=True
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="members",
        null=True, blank=True
    )

    buying_potential = models.ForeignKey(
        MemberBuyingPotential,
        on_delete=models.PROTECT,
        related_name="members",
        null=True, blank=True
    )

    email = models.EmailField(null=True, unique=True)

    phone_country_code = models.CharField(
        max_length=5,
        default="91",
        help_text="Country calling code without + (e.g. 91, 1, 44)",
        verbose_name="County Code"
    )

    phone = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        help_text="National phone number without country code"
    )

    phone2 = models.CharField(max_length=200, blank=True, null=True, verbose_name="Secondary Phone Numbers")

    is_owner = models.BooleanField(default=False)

    source = models.ForeignKey(
        MemberSource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Primary lead source"
    )

    CLASS_PREFIX = "MB"

    def __str__(self):
        return f"{self.user} - {self.organization}"

    def clean(self):
        super().clean()

        def normalize_number(num):
            if not num:
                return None
            return (
                num.replace("+", "")
                .replace("-", "")
                .replace(" ", "")
                .strip()
            )

        if self.phone:
            self.phone = normalize_number(self.phone)

        if self.phone_country_code:
            self.phone_country_code = normalize_number(self.phone_country_code)

        if not self.phone:
            return

        exists = (
            Member.objects
            .exclude(pk=self.pk)
            .filter(
                phone=self.phone,
                phone_country_code=self.phone_country_code
            )
            .exists()
        )

        if exists:
            raise ValidationError({
                "phone": "Phone number already exists for another member"
            })

    @property
    def full_phone(self):
        """Returns phone in +<code><number> format"""
        if not self.phone:
            return None
        return f"+{self.phone_country_code}{self.phone}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["email"],
                condition=Q(email__isnull=False),
                name="unique_member_email"
            ),
            models.UniqueConstraint(
                fields=["organization"],
                condition=Q(is_owner=True),
                name="unique_organization_owner"
            ),
            models.UniqueConstraint(
                fields=["phone_country_code", "phone"],
                condition=Q(phone__isnull=False),
                name="unique_member_phone_with_country_code"
            ),
        ]

        verbose_name = "Member"
        verbose_name_plural = "Members"


class MemberActivityLog(BaseModel):
    member = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name="activity_logs"
    )

    action = models.ForeignKey(
        Action,
        on_delete=models.PROTECT,
        related_name="logs",
        verbose_name="Actions & Result"
    )

    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="logs"
    )

    remarks = models.TextField()

    next_followup_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Next follow-up date and time"
    )

    def __str__(self):
        return f"{self.member} - Next Follow Up on {self.next_followup_at}"

    class Meta:
        verbose_name = "Member Activity Log"
        verbose_name_plural = "Member Activity Logs"


class OrganizationAddress(BaseModel):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="addresses"
    )
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, blank=True)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True)
    pincode = models.CharField(max_length=20, blank=True, null=True)

    spoc_email = models.EmailField(blank=True, null=True)
    spoc_phone = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"{self.organization} - {self.pincode}"

    class Meta:
        verbose_name = "Organization Address"
        verbose_name_plural = "Organization Addresses"


class BusinessDetails(BaseModel):
    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="business_details"
    )
    business_type = models.CharField(
        max_length=10,
        choices=BusinessType.choices
    )
    legal_name = models.CharField(max_length=255)
    trade_name = models.CharField(max_length=255, blank=True, null=True)
    incorporation_date = models.DateField(blank=True, null=True)
    employee_count = models.PositiveIntegerField(default=0)
    pan_number = models.CharField(max_length=10, blank=True, null=True)
    gstin_number = models.CharField(max_length=20, blank=True, null=True)
    annual_turnover = models.FloatField(blank=True, null=True)

    def __str__(self):
        return self.legal_name

    class Meta:
        verbose_name = "Business Details"
        verbose_name_plural = "Business Details"


class OrganizationKYC(BaseModel):
    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="kyc_profile"
    )
    status = models.CharField(
        max_length=20,
        choices=KYCStatus.choices,
        default=KYCStatus.NOT_STARTED
    )
    kyc_completed_at = models.DateTimeField(blank=True, null=True)
    kyc_expires_at = models.DateTimeField(blank=True, null=True)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="reviewed_organization_kycs"
    )
    rejection_reason = models.TextField(blank=True, null=True)
    is_compliant = models.BooleanField(default=False)

    def __str__(self):
        return f"Organization KYC - {self.organization}"

    class Meta:
        verbose_name = "Organization KYC"
        verbose_name_plural = "Organization KYCs"


class BusinessDocument(BaseModel):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="business_documents",
                                     null=True)
    category = models.CharField(
        max_length=20,
        choices=DocumentCategory.choices
    )
    document_type = models.CharField(
        max_length=20,
        choices=DocumentType.choices
    )
    document_number = models.CharField(max_length=100, blank=True, null=True)
    issued_date = models.DateField(blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.document_number} ({self.document_type})"

    class Meta:
        verbose_name = "Business Document"
        verbose_name_plural = "Business Documents"


def business_document_upload_path(instance, filename):
    document = instance.document

    return (
        f"documents/"
        f"organizations/"
        f"{document.document_type}/"
        f"pages/"
        f"{filename}"
    )


class DocumentPage(BaseModel):
    class PageType(models.TextChoices):
        FRONT = "front", "Front"
        BACK = "back", "Back"
        PAGE = "page", "Single Page"
        MULTI = "multi", "Multi-page File"

    document = models.ForeignKey(
        BusinessDocument,
        on_delete=models.CASCADE,
        related_name="pages"
    )

    page_type = models.CharField(
        max_length=20,
        choices=PageType.choices
    )

    # Use ONE of the following patterns

    # Pattern A: Single page
    page_number = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Use for single-page files"
    )

    # Pattern B: Multi-page file (PDF)
    page_start = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Start page number in the file"
    )
    page_end = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="End page number in the file"
    )

    file = models.FileField(upload_to=business_document_upload_path)

    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(blank=True, null=True)

    remarks = models.TextField(blank=True, null=True)

    # --------------------
    # VALIDATION
    # --------------------
    def clean(self):
        # cannot mix single page and page range
        if self.page_number and (self.page_start or self.page_end):
            raise ValidationError(
                "Use either page_number OR page_start/page_end, not both"
            )

        # page range must be complete
        if (self.page_start and not self.page_end) or \
                (self.page_end and not self.page_start):
            raise ValidationError(
                "Both page_start and page_end are required"
            )

        # range sanity
        if self.page_start and self.page_end:
            if self.page_start > self.page_end:
                raise ValidationError("page_start cannot be greater than page_end")

    def __str__(self):
        if self.page_number:
            return f"{self.document} - Page {self.page_number}"
        if self.page_start and self.page_end:
            return f"{self.document} - Pages {self.page_start}-{self.page_end}"
        return f"{self.document} - {self.page_type}"

    class Meta:
        ordering = ("page_number", "page_start")

class BankAccount(BaseModel):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="bank_accounts")
    bank = models.ForeignKey('dmcpesys.Bank', on_delete=models.PROTECT, null=True, blank=True)
    account_number = models.CharField(max_length=100)
    ifsc_code = models.CharField(max_length=20)
    account_holder_name = models.CharField(max_length=255)
    is_primary = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Bank Account"
        verbose_name_plural = "Bank Accounts"

    def __str__(self):
        return f"{self.account_number}"


auditlog.register(Member)
auditlog.register(Organization)
auditlog.register(BankAccount)
