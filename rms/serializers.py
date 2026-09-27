import re
from django.db import transaction
from django.contrib.auth import get_user_model, authenticate
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from members.models import (
    Member,
    Organization,
    BusinessDetails,
    OrganizationAddress,
    OrganizationKYC,
    KYCStatus,
    BusinessType,
)
from users.models import UserProfile, UserEmailOTP
from users.utils.otp import generate_otp, hash_otp, otp_expiry_time
from dmcpesys.models import State, Country, Currency
from .models import (
    RMSProfile,
    Beneficiary,
    RemittanceRequest,
    RemittancePassenger,
    RemittanceStageChoices,
    RemittanceStatusChoices,
    RemittancePurposeChoices,
)
from .utils import generate_random_password, send_welcome_credentials_email, send_otp_email_and_sms

User = get_user_model()


class RMSSignupSerializer(serializers.Serializer):
    org = serializers.CharField(
        required=False,
        max_length=150,
        help_text="Organization legal name"
    )
    organization_name = serializers.CharField(
        required=False,
        max_length=150,
        help_text="Alternative alias for organization name"
    )
    pan = serializers.CharField(
        required=True,
        max_length=10,
        min_length=10,
        help_text="10-character Indian Business PAN number (e.g. ABCDE1234F)"
    )
    mobile = serializers.CharField(
        required=False,
        max_length=20,
        help_text="Mobile phone number"
    )
    phone = serializers.CharField(
        required=False,
        max_length=20,
        help_text="Alternative alias for mobile phone number"
    )
    phone_country_code = serializers.CharField(
        required=False,
        default="91",
        max_length=5
    )
    email = serializers.EmailField(required=True)
    state = serializers.CharField(
        required=True,
        help_text="State ID or State Name of India"
    )

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("A user with this email address already exists.")
        if Member.objects.filter(email=email).exists():
            raise serializers.ValidationError("A member with this email address already exists.")
        return email

    def validate_pan(self, value):
        pan = value.strip().upper()
        pan_regex = r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$'
        if not re.match(pan_regex, pan):
            raise serializers.ValidationError("Invalid PAN format. Must be 5 uppercase letters, 4 digits, and 1 uppercase letter (e.g., ABCDE1234F).")
        return pan

    def validate(self, attrs):
        # Resolve org name
        org_name = attrs.get("org") or attrs.get("organization_name")
        if not org_name:
            raise serializers.ValidationError({"org": "Organization name ('org') is required."})
        attrs["org_name"] = org_name.strip()

        # Resolve mobile number
        mobile = attrs.get("mobile") or attrs.get("phone")
        if not mobile:
            raise serializers.ValidationError({"mobile": "Mobile phone number is required."})

        # Normalize mobile
        normalized_mobile = re.sub(r'[^0-9]', '', mobile)
        if len(normalized_mobile) < 10:
            raise serializers.ValidationError({"mobile": "Please enter a valid 10-digit mobile number."})

        # Check mobile uniqueness
        country_code = attrs.get("phone_country_code", "91").replace("+", "")
        if Member.objects.filter(phone=normalized_mobile, phone_country_code=country_code).exists():
            raise serializers.ValidationError({"mobile": "This mobile number is already registered for another member."})

        attrs["normalized_mobile"] = normalized_mobile
        attrs["country_code"] = country_code

        # Resolve State (India)
        state_input = attrs.get("state")
        state_obj = None

        if str(state_input).isdigit():
            state_obj = State.objects.filter(pk=int(state_input)).first()
        else:
            state_obj = State.objects.filter(name__iexact=str(state_input).strip()).first()

        if not state_obj:
            raise serializers.ValidationError({"state": f"State '{state_input}' not found in dmspesys database."})

        attrs["state_obj"] = state_obj
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        email = validated_data["email"]
        org_name = validated_data["org_name"]
        pan = validated_data["pan"]
        mobile = validated_data["normalized_mobile"]
        country_code = validated_data["country_code"]
        state_obj = validated_data["state_obj"]

        # 1. Auto-generate password
        auto_password = generate_random_password(10)

        # 2. Create User with REMIT_ONLY role (inactive until OTP verified)
        username = email
        user = User.objects.create_user(
            email=email,
            username=username,
            password=auto_password,
            role="REMIT_ONLY",
            is_active=False
        )

        # 3. Create UserProfile
        UserProfile.objects.create(
            user=user,
            first_name=org_name,
            last_name="(RMS)",
            phone=mobile,
            state=state_obj.name if state_obj else None,
            country=state_obj.country.name if state_obj and state_obj.country else "India"
        )

        # 4. Create Organization
        organization = Organization.objects.create(
            name=org_name,
            marketing_email=email,
            marketing_phone=f"+{country_code}{mobile}"
        )

        # 5. Create BusinessDetails (with PAN)
        BusinessDetails.objects.create(
            organization=organization,
            legal_name=org_name,
            pan_number=pan,
            business_type=BusinessType.OTHER
        )

        # 6. Create OrganizationAddress
        OrganizationAddress.objects.create(
            organization=organization,
            address_line1="Not provided",
            state=state_obj,
            country=state_obj.country if state_obj else None
        )

        # 7. Create OrganizationKYC
        OrganizationKYC.objects.create(
            organization=organization,
            status=KYCStatus.NOT_STARTED
        )

        # 8. Create Member
        member = Member.objects.create(
            user=user,
            organization=organization,
            email=email,
            phone=mobile,
            phone_country_code=country_code,
            is_owner=True
        )

        # 9. Create RMSProfile
        rms_profile = RMSProfile.objects.create(
            organization=organization,
            is_active_remitter=True
        )

        # 10. Generate and Send Email & Mobile OTP
        otp_code = generate_otp()
        UserEmailOTP.objects.filter(email=email, is_verified=False).update(is_active=False, is_deleted=True)
        UserEmailOTP.objects.create(
            email=email,
            otp_hash=hash_otp(otp_code),
            expires_at=otp_expiry_time()
        )
        send_otp_email_and_sms(email, mobile, otp_code)

        return {
            "user": user,
            "member": member,
            "organization": organization,
            "rms_profile": rms_profile,
            "auto_password": auto_password,
            "otp_code": otp_code,
        }


class RMSVerifyOTPRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    otp = serializers.CharField(required=True, max_length=10)

    def validate(self, attrs):
        email = attrs.get("email").strip().lower()
        otp = attrs.get("otp").strip()

        user = User.objects.filter(email=email).first()
        if not user:
            raise serializers.ValidationError({"email": "User with this email does not exist."})

        try:
            otp_obj = UserEmailOTP.objects.filter(
                email=email,
                is_verified=False
            ).latest("created_at")
        except UserEmailOTP.DoesNotExist:
            raise serializers.ValidationError({"otp": "No valid OTP request found. Please request a new OTP."})

        if otp_obj.is_expired:
            otp_obj.is_active = False
            otp_obj.is_deleted = True
            otp_obj.save(update_fields=["is_active", "is_deleted"])
            raise serializers.ValidationError({"otp": "The OTP code has expired."})

        if otp_obj.otp_hash != hash_otp(otp):
            otp_obj.attempts += 1
            otp_obj.save(update_fields=["attempts"])
            raise serializers.ValidationError({"otp": "Invalid OTP code."})

        otp_obj.is_verified = True
        otp_obj.save(update_fields=["is_verified"])

        # Activate User and confirm role REMIT_ONLY
        user.is_active = True
        user.role = "REMIT_ONLY"
        user.save(update_fields=["is_active", "role"])

        member = Member.objects.select_related("organization").filter(user=user).first()
        organization = member.organization if member else None

        attrs["user"] = user
        attrs["member"] = member
        attrs["organization"] = organization
        return attrs



class RMSLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        email = attrs.get("email").strip().lower()
        password = attrs.get("password")

        user = User.objects.filter(email=email).first()
        if not user:
            raise serializers.ValidationError({"email": "Invalid email or password."})

        if not user.check_password(password):
            raise serializers.ValidationError({"password": "Invalid email or password."})

        if not user.is_active:
            raise serializers.ValidationError({"email": "This user account is inactive."})

        member = Member.objects.select_related("organization").filter(user=user).first()
        if not member:
            raise serializers.ValidationError({"user": "Member profile not found for this user."})

        attrs["user"] = user
        attrs["member"] = member
        attrs["organization"] = member.organization
        return attrs


# =========================================================
# BENEFICIARY SERIALIZERS
# =========================================================

class BeneficiarySerializer(serializers.ModelSerializer):
    bank_country_id = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.all(), source='bank_country', required=False, allow_null=True
    )
    beneficiary_country_id = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.all(), source='beneficiary_country', required=False, allow_null=True
    )
    currency_id = serializers.PrimaryKeyRelatedField(
        queryset=Currency.objects.all(), source='currency', required=False, allow_null=True
    )

    bank_country_name = serializers.CharField(source='bank_country.name', read_only=True)
    beneficiary_country_name = serializers.CharField(source='beneficiary_country.name', read_only=True)
    currency_code = serializers.CharField(source='currency.code', read_only=True)

    class Meta:
        model = Beneficiary
        fields = [
            'id', 'code', 'organization',
            'account_number', 'swift_code', 'iban',
            'bank_name', 'bank_address', 'bank_city', 'bank_country_id', 'bank_country_name',
            'currency_id', 'currency_code',
            'beneficiary_name', 'beneficiary_address',
            'beneficiary_country_id', 'beneficiary_country_name', 'beneficiary_city',
            'zone', 'beneficiary_email', 'beneficiary_mobile',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'code', 'organization', 'created_at', 'updated_at']

    def validate_account_number(self, value):
        return value.strip()

    def validate_swift_code(self, value):
        return value.strip().upper()


# =========================================================
# REMITTANCE WORKFLOW SERIALIZERS (4 STAGES & RESUME)
# =========================================================

class RemittancePassengerSerializer(serializers.ModelSerializer):
    class Meta:
        model = RemittancePassenger
        fields = [
            'id', 'pan_number', 'passenger_name', 'passenger_mobile', 'amount',
            'date_of_journey', 'is_pan_verified', 'pan_verified_at'
        ]
        read_only_fields = ['id', 'is_pan_verified', 'pan_verified_at']

    def validate_pan_number(self, value):
        pan = value.strip().upper()
        if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', pan):
            raise serializers.ValidationError("Invalid PAN format (e.g. ABCDE1234F).")
        return pan


class RemittanceStage1Serializer(serializers.ModelSerializer):
    """
    Stage 1: Create Invoice API Serializer
    """
    beneficiary_id = serializers.PrimaryKeyRelatedField(
        queryset=Beneficiary.objects.all(),
        source='beneficiary',
        required=False,
        allow_null=True
    )
    currency_id = serializers.PrimaryKeyRelatedField(
        queryset=Currency.objects.all(),
        source='currency',
        required=False,
        allow_null=True
    )

    class Meta:
        model = RemittanceRequest
        fields = [
            'id', 'code', 'purpose', 'beneficiary_id',
            'beneficiary_name', 'beneficiary_email', 'beneficiary_mobile',
            'invoice_reference_number', 'invoice_date', 'invoice_amount',
            'is_part_payment', 'remittance_amount', 'currency_id',
            'intermediary_bank_charges', 'no_of_travellers', 'invoice_document',
            'current_stage', 'status'
        ]
        read_only_fields = ['id', 'code', 'current_stage', 'status']

    def validate(self, attrs):
        invoice_amt = attrs.get('invoice_amount', 0)
        is_part = attrs.get('is_part_payment', False)
        remit_amt = attrs.get('remittance_amount', invoice_amt)

        if is_part:
            if not remit_amt or remit_amt <= 0:
                raise serializers.ValidationError({"remittance_amount": "Remittance amount must be greater than 0 for part payment."})
            if remit_amt > invoice_amt:
                raise serializers.ValidationError({"remittance_amount": "Remittance amount cannot exceed total invoice amount."})
        else:
            attrs['remittance_amount'] = invoice_amt

        # Populate beneficiary contact info if beneficiary_id provided
        beneficiary = attrs.get('beneficiary')
        if beneficiary:
            if not attrs.get('beneficiary_name'):
                attrs['beneficiary_name'] = beneficiary.beneficiary_name
            if not attrs.get('beneficiary_email'):
                attrs['beneficiary_email'] = beneficiary.beneficiary_email
            if not attrs.get('beneficiary_mobile'):
                attrs['beneficiary_mobile'] = beneficiary.beneficiary_mobile
            if not attrs.get('currency') and beneficiary.currency:
                attrs['currency'] = beneficiary.currency

        return attrs

    def create(self, validated_data):
        validated_data['current_stage'] = RemittanceStageChoices.STAGE_2_KYC
        validated_data['status'] = RemittanceStatusChoices.INVOICE_SUBMITTED
        return super().create(validated_data)


import io
import datetime
import openpyxl


def parse_passenger_excel(file_obj):
    """
    Parses an uploaded Excel (.xlsx, .xls) file for passenger PAN, Amount, Date of Journey.
    Expected headers: PAN No, Amount, Date of Journey, Passenger Name (optional)
    """
    try:
        wb = openpyxl.load_workbook(file_obj, data_only=True)
        sheet = wb.active
        rows = list(sheet.iter_rows(values_only=True))
    except Exception as e:
        raise serializers.ValidationError({"excel_file": f"Invalid excel file format: {str(e)}"})

    if not rows or len(rows) < 2:
        raise serializers.ValidationError({"excel_file": "Uploaded excel file is empty or missing data rows."})

    # Find header indices
    pan_idx = None
    amt_idx = None
    date_idx = None
    name_idx = None

    for idx, cell in enumerate(rows[0]):
        if cell is None:
            continue
        val = str(cell).strip().lower()
        if "pan" in val:
            pan_idx = idx
        elif "amount" in val:
            amt_idx = idx
        elif "journey" in val or "date" in val:
            date_idx = idx
        elif "name" in val or "passenger" in val:
            name_idx = idx

    if pan_idx is None or amt_idx is None or date_idx is None:
        raise serializers.ValidationError({
            "excel_file": "Excel file must contain header columns: 'PAN No', 'Amount', and 'Date of Journey'."
        })

    parsed_passengers = []

    for row_idx, row in enumerate(rows[1:], start=2):
        if not row or all(c is None for c in row):
            continue

        pan_val = str(row[pan_idx]).strip().upper() if len(row) > pan_idx and row[pan_idx] else None
        amt_val = row[amt_idx] if len(row) > amt_idx else None
        date_val = row[date_idx] if len(row) > date_idx else None
        name_val = str(row[name_idx]).strip() if name_idx is not None and len(row) > name_idx and row[name_idx] else ""

        if not pan_val or not amt_val or not date_val:
            continue

        # Validate PAN
        if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', pan_val):
            raise serializers.ValidationError({
                "excel_file": f"Row {row_idx}: Invalid PAN format '{pan_val}'. Must be 10-char alphanumeric (e.g. ABCDE1234F)."
            })

        # Parse Amount
        try:
            amt_float = float(amt_val)
            if amt_float <= 0:
                raise ValueError()
        except ValueError:
            raise serializers.ValidationError({
                "excel_file": f"Row {row_idx}: Amount must be a positive number."
            })

        # Parse Date of Journey
        formatted_date = None
        if isinstance(date_val, (datetime.date, datetime.datetime)):
            formatted_date = date_val.strftime("%Y-%m-%d")
        else:
            date_str = str(date_val).strip()
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"):
                try:
                    dt = datetime.datetime.strptime(date_str, fmt)
                    formatted_date = dt.strftime("%Y-%m-%d")
                    break
                except ValueError:
                    continue

        if not formatted_date:
            raise serializers.ValidationError({
                "excel_file": f"Row {row_idx}: Invalid Date of Journey format '{date_val}'. Use YYYY-MM-DD or DD/MM/YYYY."
            })

        parsed_passengers.append({
            "pan_number": pan_val,
            "passenger_name": name_val,
            "amount": amt_float,
            "date_of_journey": formatted_date
        })

    if not parsed_passengers:
        raise serializers.ValidationError({"excel_file": "No valid passenger records found in uploaded excel file."})

    return parsed_passengers


class RemittanceStage2Serializer(serializers.Serializer):
    """
    Stage 2: KYC / Passenger PAN & LRS Declaration Serializer
    Supports BOTH manual passengers array AND excel file upload.
    """
    passengers = RemittancePassengerSerializer(many=True, required=False)
    excel_file = serializers.FileField(required=False, allow_null=True)
    lrs_declaration_accepted = serializers.BooleanField(required=True)
    lrs_declaration_text = serializers.CharField(required=False, allow_blank=True)
    tcs_declaration_accepted = serializers.BooleanField(required=False, default=True)
    tcs_liability_declaration_accepted = serializers.BooleanField(required=False, default=True)

    def validate_lrs_declaration_accepted(self, value):
        if not value:
            raise serializers.ValidationError("LRS Declaration consent must be accepted to proceed.")
        return value

    def validate(self, attrs):
        passengers = attrs.get("passengers")
        excel_file = attrs.get("excel_file")

        if not passengers and not excel_file:
            raise serializers.ValidationError("Please provide passenger details either manually via 'passengers' or upload an 'excel_file'.")

        if excel_file:
            try:
                parsed = parse_passenger_excel(excel_file)
                attrs["parsed_passengers"] = parsed
            except serializers.ValidationError:
                raise
            except Exception as e:
                raise serializers.ValidationError({"excel_file": f"Failed to parse excel file: {str(e)}"})
        else:
            cleaned = []
            for p in passengers:
                cleaned.append({
                    "pan_number": p["pan_number"],
                    "passenger_name": p.get("passenger_name", ""),
                    "passenger_mobile": p.get("passenger_mobile", ""),
                    "amount": p["amount"],
                    "date_of_journey": str(p["date_of_journey"])
                })
            attrs["parsed_passengers"] = cleaned

        return attrs




class RemittanceStage3Serializer(serializers.ModelSerializer):
    """
    Stage 3: Payment Process Serializer (Rate Blocking or Pay 100% Online)
    """
    class Meta:
        model = RemittanceRequest
        fields = [
            'payment_option_type', 'exchange_rate',
            'deal_value_inr', 'processing_fee_inr', 'gst_amount_inr', 'final_amount_inr',
            'payment_method', 'payment_reference_number', 'payment_proof_document',
            'paid_amount', 'payment_disclaimer_accepted'
        ]
        read_only_fields = ['deal_value_inr', 'final_amount_inr']

    def validate(self, attrs):
        instance = self.instance
        disclaimer = attrs.get('payment_disclaimer_accepted', False)
        
        if not disclaimer:
            raise serializers.ValidationError({"payment_disclaimer_accepted": "Payment disclaimer consent must be accepted to proceed."})

        # Calculate transaction breakup
        remit_amt = float(instance.remittance_amount) if instance else 0.0
        bank_charges = float(instance.intermediary_bank_charges) if instance else 0.0
        total_forex = remit_amt + bank_charges
        
        rate = float(attrs.get('exchange_rate') or (instance.exchange_rate if instance else 75.1697))
        proc_fee = float(attrs.get('processing_fee_inr') or 300.00)
        gst = float(attrs.get('gst_amount_inr') or 3549.00)

        deal_val = round(total_forex * rate, 2)
        final_amt = round(deal_val + proc_fee + gst, 2)

        attrs['deal_value_inr'] = deal_val
        attrs['processing_fee_inr'] = proc_fee
        attrs['gst_amount_inr'] = gst
        attrs['final_amount_inr'] = final_amt
        if not attrs.get('paid_amount'):
            attrs['paid_amount'] = final_amt

        return attrs



class RemittanceStage4Serializer(serializers.ModelSerializer):
    """
    Stage 4: Remittance Confirmation & SWIFT Copy Serializer
    """
    class Meta:
        model = RemittanceRequest
        fields = [
            'bank_reference_number', 'swift_copy_document', 'remarks'
        ]


class RemittanceDetailSerializer(serializers.ModelSerializer):
    """
    Comprehensive Remittance Detail Serializer supporting Journey Resume
    """
    beneficiary = BeneficiarySerializer(read_only=True)
    passengers = RemittancePassengerSerializer(many=True, read_only=True)

    current_stage_display = serializers.CharField(source='get_current_stage_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    purpose_display = serializers.CharField(source='get_purpose_display', read_only=True)

    currency_code = serializers.CharField(source='currency.code', read_only=True)

    next_step = serializers.SerializerMethodField()

    class Meta:
        model = RemittanceRequest
        fields = [
            'id', 'code', 'organization', 'member', 'beneficiary',
            'current_stage', 'current_stage_display', 'status', 'status_display', 'next_step',
            'purpose', 'purpose_display', 'beneficiary_name', 'beneficiary_email', 'beneficiary_mobile',
            'invoice_reference_number', 'invoice_date', 'invoice_amount',
            'is_part_payment', 'remittance_amount', 'currency_code',
            'intermediary_bank_charges', 'no_of_travellers', 'invoice_document',
            'lrs_declaration_accepted', 'lrs_declaration_accepted_at', 'lrs_declaration_text',
            'tcs_declaration_accepted', 'tcs_declaration_accepted_at',
            'tcs_liability_declaration_accepted', 'tcs_liability_declaration_accepted_at',
            'passengers',
            'payment_option_type', 'exchange_rate', 'deal_value_inr', 'processing_fee_inr', 'gst_amount_inr', 'final_amount_inr',
            'payment_method', 'payment_reference_number', 'payment_proof_document', 'paid_amount', 'payment_date',
            'payment_disclaimer_accepted', 'payment_disclaimer_accepted_at',
            'bank_reference_number', 'swift_copy_document', 'completed_at', 'remarks',
            'created_at', 'updated_at'
        ]

    def get_next_step(self, obj):
        stage_map = {
            RemittanceStageChoices.STAGE_1_INVOICE: {
                "stage": "STAGE_1_INVOICE",
                "action": "Create Invoice",
                "endpoint": f"/api/v1/rms/remittances/stage1-create-invoice/"
            },
            RemittanceStageChoices.STAGE_2_KYC: {
                "stage": "STAGE_2_KYC",
                "action": "Submit Passenger PAN & Accept LRS Declaration",
                "endpoint": f"/api/v1/rms/remittances/{obj.id}/stage2-kyc-pan/"
            },
            RemittanceStageChoices.STAGE_3_PAYMENT: {
                "stage": "STAGE_3_PAYMENT",
                "action": "Submit Payment Proof & Reference",
                "endpoint": f"/api/v1/rms/remittances/{obj.id}/stage3-payment/"
            },
            RemittanceStageChoices.STAGE_4_CONFIRMATION: {
                "stage": "STAGE_4_CONFIRMATION",
                "action": "Upload SWIFT Copy & Confirm Remittance",
                "endpoint": f"/api/v1/rms/remittances/{obj.id}/stage4-confirmation/"
            },
            RemittanceStageChoices.COMPLETED: {
                "stage": "COMPLETED",
                "action": "Remittance Completed",
                "endpoint": None
            }
        }
        return stage_map.get(obj.current_stage, None)

