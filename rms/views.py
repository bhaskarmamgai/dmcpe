from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from dmcpesys.models import State
from dmcpesys.serializers import StateSerializer
from .models import (
    Beneficiary,
    RemittanceRequest,
    RemittancePassenger,
    RemittanceStageChoices,
    RemittanceStatusChoices,
)
from .serializers import (
    RMSSignupSerializer,
    RMSLoginSerializer,
    RMSVerifyOTPRequestSerializer,
    BeneficiarySerializer,
    RemittanceStage1Serializer,
    RemittanceStage2Serializer,
    RemittanceStage3Serializer,
    RemittanceStage4Serializer,
    RemittanceDetailSerializer,
)
from .utils import send_welcome_credentials_email


@api_view(["POST"])
@permission_classes([AllowAny])
def rms_signup_view(request):
    """
    API 1 (RMS Signup Step 1)
    Inputs required:
    - org / organization_name: Legal Organization Name
    - pan: Business PAN number (10 chars, e.g. ABCDE1234F)
    - mobile / phone: 10-digit mobile number
    - email: Email address
    - state: State ID or State Name (State of India)

    Creates Member and Organization, generates auto-password & OTP, dispatches OTP to Email & Mobile.
    User remains inactive until OTP is verified.
    """
    serializer = RMSSignupSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(
            {
                "success": False,
                "errors": serializer.errors,
                "message": "Validation failed for RMS Signup."
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    result = serializer.save()

    user = result["user"]
    member = result["member"]
    organization = result["organization"]

    return Response(
        {
            "success": True,
            "status": "OTP_VERIFICATION_REQUIRED",
            "message": "RMS Signup created. OTP code has been dispatched to your email and mobile phone.",
            "data": {
                "user_id": str(user.id),
                "member_id": str(member.id),
                "organization_id": str(organization.id),
                "org_name": organization.name,
                "email": user.email,
                "mobile": member.phone,
                "role": user.role,
                "is_active": user.is_active,
            }
        },
        status=status.HTTP_201_CREATED
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def rms_verify_otp_view(request):
    """
    API 1 (RMS Verify OTP - Step 2)
    Validates Email/Mobile OTP. Upon verification:
    1. User is marked as activated (is_active = True).
    2. User role is confirmed as REMIT_ONLY.
    3. Credentials email with auto-generated password is sent.
    4. SimpleJWT tokens are returned.
    """
    serializer = RMSVerifyOTPRequestSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(
            {
                "success": False,
                "errors": serializer.errors,
                "message": "OTP verification failed."
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    user = serializer.validated_data["user"]
    member = serializer.validated_data["member"]
    organization = serializer.validated_data["organization"]

    # Generate SimpleJWT tokens
    refresh = RefreshToken.for_user(user)
    refresh["user_id"] = str(user.id)
    if member:
        refresh["member_id"] = str(member.id)
        refresh["is_owner"] = member.is_owner
    if organization:
        refresh["organization_id"] = str(organization.id)
        refresh["organization_name"] = organization.name

    return Response(
        {
            "success": True,
            "status": "ACTIVATED",
            "message": "OTP verified successfully. Member activated with role REMIT_ONLY.",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active,
            },
            "organization": {
                "id": str(organization.id) if organization else None,
                "name": organization.name if organization else None,
            },
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        },
        status=status.HTTP_200_OK
    )



@api_view(["POST"])
@permission_classes([AllowAny])
def rms_login_view(request):
    """
    API 1 (RMS Login)
    Inputs required:
    - email
    - password

    Authenticates user and returns simplejwt access and refresh tokens.
    """
    serializer = RMSLoginSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(
            {
                "success": False,
                "errors": serializer.errors,
                "message": "Invalid login credentials."
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    user = serializer.validated_data["user"]
    member = serializer.validated_data["member"]
    organization = serializer.validated_data["organization"]

    refresh = RefreshToken.for_user(user)
    refresh["user_id"] = str(user.id)
    refresh["member_id"] = str(member.id)
    refresh["organization_id"] = str(organization.id)
    refresh["organization_name"] = organization.name
    refresh["is_owner"] = member.is_owner

    return Response(
        {
            "success": True,
            "message": "RMS Login successful.",
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": str(user.id),
                "email": user.email,
                "role": user.role,
            },
            "organization": {
                "id": str(organization.id),
                "name": organization.name,
            }
        },
        status=status.HTTP_200_OK
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def rms_indian_states_view(request):
    """
    Returns list of states belonging to India for RMS forms.
    """
    states = State.objects.filter(
        Q(country__name__iexact="India") | Q(country__iso_code__iexact="IN")
    ).order_by("name")

    if not states.exists():
        states = State.objects.all().order_by("name")

    serializer = StateSerializer(states, many=True)
    return Response(
        {
            "success": True,
            "states": serializer.data,
            "count": len(serializer.data)
        },
        status=status.HTTP_200_OK
    )


# =========================================================
# BENEFICIARY API (CREATE & GET LIST / DETAIL)
# =========================================================

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def beneficiary_list_create_view(request):
    """
    GET: Returns all beneficiaries for the authenticated organization.
    POST: Creates a new Beneficiary account.
    """
    organization = getattr(request.user, 'organization', None) or getattr(getattr(request.user, 'member', None), 'organization', None)

    if request.method == "GET":
        if organization:
            beneficiaries = Beneficiary.objects.filter(organization=organization, is_active=True)
        else:
            beneficiaries = Beneficiary.objects.filter(is_active=True)

        serializer = BeneficiarySerializer(beneficiaries, many=True)
        return Response(
            {
                "success": True,
                "beneficiaries": serializer.data,
                "count": len(serializer.data)
            },
            status=status.HTTP_200_OK
        )

    elif request.method == "POST":
        if not organization:
            return Response(
                {"success": False, "message": "User organization profile required to create beneficiary."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = BeneficiarySerializer(data=request.data)
        if serializer.is_valid():
            beneficiary = serializer.save(organization=organization)
            return Response(
                {
                    "success": True,
                    "message": "Beneficiary created successfully.",
                    "beneficiary": BeneficiarySerializer(beneficiary).data
                },
                status=status.HTTP_201_CREATED
            )
        return Response(
            {"success": False, "errors": serializer.errors, "message": "Validation failed for Beneficiary creation."},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def beneficiary_detail_view(request, pk):
    """
    GET, PUT, DELETE for specific Beneficiary.
    """
    organization = getattr(request.user, 'organization', None) or getattr(getattr(request.user, 'member', None), 'organization', None)
    
    if organization:
        beneficiary = get_object_or_404(Beneficiary, pk=pk, organization=organization, is_active=True)
    else:
        beneficiary = get_object_or_404(Beneficiary, pk=pk, is_active=True)

    if request.method == "GET":
        serializer = BeneficiarySerializer(beneficiary)
        return Response({"success": True, "beneficiary": serializer.data}, status=status.HTTP_200_OK)

    elif request.method in ["PUT", "PATCH"]:
        partial = (request.method == "PATCH")
        serializer = BeneficiarySerializer(beneficiary, data=request.data, partial=partial)
        if serializer.is_valid():
            updated_beneficiary = serializer.save()
            return Response({"success": True, "message": "Beneficiary updated successfully.", "beneficiary": BeneficiarySerializer(updated_beneficiary).data}, status=status.HTTP_200_OK)
        return Response({"success": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "DELETE":
        beneficiary.is_active = False
        beneficiary.is_deleted = True
        beneficiary.save(update_fields=["is_active", "is_deleted"])
        return Response({"success": True, "message": "Beneficiary deleted successfully."}, status=status.HTTP_200_OK)


# =========================================================
# REMITTANCE WORKFLOW APIs (4 STAGES & RESUME JOURNEY)
# =========================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def remittance_stage1_create_invoice_view(request):
    """
    Stage 1: Create Invoice API
    Records invoice details, beneficiary contact info, invoice amount, part-payment choices, and document.
    Advances journey to STAGE_2_KYC.
    """
    organization = getattr(request.user, 'organization', None) or getattr(getattr(request.user, 'member', None), 'organization', None)
    member = getattr(request.user, 'member', None)

    if not organization:
        return Response(
            {"success": False, "message": "Organization profile required to initiate remittance."},
            status=status.HTTP_400_BAD_REQUEST
        )

    serializer = RemittanceStage1Serializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"success": False, "errors": serializer.errors, "message": "Validation failed for Stage 1 (Create Invoice)."},
            status=status.HTTP_400_BAD_REQUEST
        )

    remittance = serializer.save(organization=organization, member=member)
    detail_serializer = RemittanceDetailSerializer(remittance)

    return Response(
        {
            "success": True,
            "message": "Stage 1 (Invoice Creation) saved successfully. Next stage is Stage 2 (KYC & Passengers).",
            "remittance_id": str(remittance.id),
            "code": remittance.code,
            "current_stage": remittance.current_stage,
            "next_step": detail_serializer.data.get("next_step"),
            "data": detail_serializer.data
        },
        status=status.HTTP_201_CREATED
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def remittance_stage2_kyc_pan_view(request, pk):
    """
    Stage 2: KYC & Passenger PAN Verification API
    Records passenger PAN numbers, amounts, dates of journey, and accepts LRS Declaration.
    Advances journey to STAGE_3_PAYMENT.
    """
    organization = getattr(request.user, 'organization', None) or getattr(getattr(request.user, 'member', None), 'organization', None)
    remittance = get_object_or_404(RemittanceRequest, pk=pk, organization=organization)

    serializer = RemittanceStage2Serializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"success": False, "errors": serializer.errors, "message": "Validation failed for Stage 2 (KYC/Passengers)."},
            status=status.HTTP_400_BAD_REQUEST
        )

    passengers_data = serializer.validated_data["parsed_passengers"]
    lrs_accepted = serializer.validated_data["lrs_declaration_accepted"]
    lrs_text = serializer.validated_data.get("lrs_declaration_text", "")
    tcs_accepted = serializer.validated_data.get("tcs_declaration_accepted", True)
    tcs_liability_accepted = serializer.validated_data.get("tcs_liability_declaration_accepted", True)

    with transaction.atomic():
        # Clear existing passengers if re-submitting Stage 2
        remittance.passengers.all().delete()

        # Create Passengers
        for p_data in passengers_data:
            RemittancePassenger.objects.create(
                remittance_request=remittance,
                pan_number=p_data["pan_number"],
                passenger_name=p_data.get("passenger_name", ""),
                passenger_mobile=p_data.get("passenger_mobile", ""),
                amount=p_data["amount"],
                date_of_journey=p_data["date_of_journey"],
                is_pan_verified=True,
                pan_verified_at=timezone.now()
            )

        now_ts = timezone.now()
        remittance.lrs_declaration_accepted = lrs_accepted
        remittance.lrs_declaration_accepted_at = now_ts
        remittance.lrs_declaration_text = lrs_text

        remittance.tcs_declaration_accepted = tcs_accepted
        if tcs_accepted:
            remittance.tcs_declaration_accepted_at = now_ts

        remittance.tcs_liability_declaration_accepted = tcs_liability_accepted
        if tcs_liability_accepted:
            remittance.tcs_liability_declaration_accepted_at = now_ts

        remittance.current_stage = RemittanceStageChoices.STAGE_3_PAYMENT
        remittance.status = RemittanceStatusChoices.PAN_VERIFIED
        remittance.save(update_fields=[
            "lrs_declaration_accepted", "lrs_declaration_accepted_at", "lrs_declaration_text",
            "tcs_declaration_accepted", "tcs_declaration_accepted_at",
            "tcs_liability_declaration_accepted", "tcs_liability_declaration_accepted_at",
            "current_stage", "status"
        ])

    detail_serializer = RemittanceDetailSerializer(remittance)
    return Response(
        {
            "success": True,
            "message": f"Stage 2 (KYC & Passenger PAN Verification) completed. Processed {len(passengers_data)} passenger records.",
            "passenger_count": len(passengers_data),
            "remittance_id": str(remittance.id),
            "current_stage": remittance.current_stage,
            "next_step": detail_serializer.data.get("next_step"),
            "data": detail_serializer.data
        },
        status=status.HTTP_200_OK
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def passenger_excel_template_download_view(request):
    """
    Returns a downloadable sample Excel file (.xlsx) formatted for Stage 2 bulk passenger PAN upload.
    Headers: PAN No, Amount, Date of Journey, Passenger Name
    """
    from django.http import HttpResponse
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Passenger Details"

    # Header Row
    headers = ["PAN No*", "Amount*", "Date of Journey*", "Passenger Name"]
    ws.append(headers)

    # Sample Rows
    ws.append(["ABCDE1234F", 1500.00, "2026-10-15", "John Doe"])
    ws.append(["XYZPB9876K", 2500.00, "2026-10-18", "Jane Smith"])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="RMS_Passenger_Bulk_Upload_Template.xlsx"'
    wb.save(response)
    return response



@api_view(["POST"])
@permission_classes([IsAuthenticated])
def remittance_calculate_breakup_view(request, pk=None):
    """
    Calculates Transaction Breakup (Deal Value, Processing Fee, GST, Final INR Amount)
    for a Remittance Request or standalone parameters.
    """
    organization = getattr(request.user, 'organization', None) or getattr(getattr(request.user, 'member', None), 'organization', None)
    
    if pk:
        remittance = get_object_or_404(RemittanceRequest, pk=pk, organization=organization)
        remit_amt = float(remittance.remittance_amount)
        bank_charges = float(remittance.intermediary_bank_charges)
        currency_code = remittance.currency.code if remittance.currency else "SGD"
    else:
        remit_amt = float(request.data.get("remittance_amount", 0.0))
        bank_charges = float(request.data.get("intermediary_bank_charges", 0.0))
        currency_code = request.data.get("currency_code", "SGD")

    rate = float(request.data.get("exchange_rate", 75.1697))
    proc_fee = float(request.data.get("processing_fee_inr", 300.00))
    gst = float(request.data.get("gst_amount_inr", 3549.00))

    total_forex = remit_amt + bank_charges
    deal_val = round(total_forex * rate, 2)
    final_amt = round(deal_val + proc_fee + gst, 2)

    return Response(
        {
            "success": True,
            "transaction_breakup": {
                "remittance_amount": remit_amt,
                "intermediary_bank_charges": bank_charges,
                "total_forex": total_forex,
                "currency": currency_code,
                "exchange_rate": rate,
                "deal_value_inr": deal_val,
                "processing_fee_inr": proc_fee,
                "gst_amount_inr": gst,
                "final_amount_inr": final_amt
            }
        },
        status=status.HTTP_200_OK
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def remittance_stage3_payment_view(request, pk):
    """
    Stage 3: Payment Process API (Rate Blocking or Pay 100% Online)
    Records payment option type, exchange rate, payment disclaimer consent, reference number, and payment proof.
    Advances journey to STAGE_4_CONFIRMATION.
    """
    organization = getattr(request.user, 'organization', None) or getattr(getattr(request.user, 'member', None), 'organization', None)
    remittance = get_object_or_404(RemittanceRequest, pk=pk, organization=organization)

    serializer = RemittanceStage3Serializer(remittance, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(
            {"success": False, "errors": serializer.errors, "message": "Validation failed for Stage 3 (Payment)."},
            status=status.HTTP_400_BAD_REQUEST
        )

    remittance = serializer.save()
    now_ts = timezone.now()
    remittance.payment_date = now_ts
    remittance.payment_disclaimer_accepted_at = now_ts
    remittance.current_stage = RemittanceStageChoices.STAGE_4_CONFIRMATION
    remittance.status = RemittanceStatusChoices.PAYMENT_PENDING
    remittance.save(update_fields=["payment_date", "payment_disclaimer_accepted_at", "current_stage", "status"])

    detail_serializer = RemittanceDetailSerializer(remittance)
    return Response(
        {
            "success": True,
            "message": "Stage 3 (Payment Process) recorded successfully. Next stage is Stage 4 (Remittance Confirmation).",
            "remittance_id": str(remittance.id),
            "current_stage": remittance.current_stage,
            "next_step": detail_serializer.data.get("next_step"),
            "data": detail_serializer.data
        },
        status=status.HTTP_200_OK
    )



@api_view(["POST"])
@permission_classes([IsAuthenticated])
def remittance_stage4_confirmation_view(request, pk):
    """
    Stage 4: Remittance Confirmation & SWIFT Copy Upload API
    Records bank reference number, SWIFT copy upload, and completes the remittance.
    """
    organization = getattr(request.user, 'organization', None) or getattr(getattr(request.user, 'member', None), 'organization', None)
    remittance = get_object_or_404(RemittanceRequest, pk=pk, organization=organization)

    serializer = RemittanceStage4Serializer(remittance, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(
            {"success": False, "errors": serializer.errors, "message": "Validation failed for Stage 4 (Confirmation)."},
            status=status.HTTP_400_BAD_REQUEST
        )

    remittance = serializer.save()
    remittance.current_stage = RemittanceStageChoices.COMPLETED
    remittance.status = RemittanceStatusChoices.COMPLETED
    remittance.completed_at = timezone.now()
    remittance.save(update_fields=["current_stage", "status", "completed_at"])

    detail_serializer = RemittanceDetailSerializer(remittance)
    return Response(
        {
            "success": True,
            "message": "Stage 4 (Remittance Confirmation) completed successfully. Transaction finalized.",
            "remittance_id": str(remittance.id),
            "current_stage": remittance.current_stage,
            "next_step": detail_serializer.data.get("next_step"),
            "data": detail_serializer.data
        },
        status=status.HTTP_200_OK
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def remittance_list_view(request):
    """
    Lists Remittance Requests filtered by the logged-in Agent / Organization.
    Supported Query Filters:
    - stage: STAGE_1_INVOICE | STAGE_2_KYC | STAGE_3_PAYMENT | STAGE_4_CONFIRMATION | COMPLETED
    - status: DRAFT | INVOICE_SUBMITTED | PAN_VERIFIED | PAYMENT_PENDING | PAYMENT_RECEIVED | COMPLETED
    - purpose: TOUR_COST | EDUCATION | MEDICAL | etc.
    - search: Search code, invoice_reference_number, beneficiary_name, bank_reference_number
    - my_remittances_only: boolean (if true, filters strictly by logged-in member)
    """
    member = getattr(request.user, 'member', None)
    organization = getattr(request.user, 'organization', None) or getattr(member, 'organization', None)

    my_only = request.query_params.get("my_remittances_only", "false").lower() == "true"

    if my_only and member:
        queryset = RemittanceRequest.objects.filter(member=member, is_active=True)
    elif organization:
        queryset = RemittanceRequest.objects.filter(organization=organization, is_active=True)
    elif member:
        queryset = RemittanceRequest.objects.filter(member=member, is_active=True)
    else:
        queryset = RemittanceRequest.objects.filter(created_by=request.user, is_active=True)

    # Filter by Stage
    stage = request.query_params.get("stage")
    if stage:
        queryset = queryset.filter(current_stage=stage)

    # Filter by Status
    status_param = request.query_params.get("status")
    if status_param:
        queryset = queryset.filter(status=status_param)

    # Filter by Purpose
    purpose = request.query_params.get("purpose")
    if purpose:
        queryset = queryset.filter(purpose=purpose)

    # Search filter
    search = request.query_params.get("search")
    if search:
        search = search.strip()
        queryset = queryset.filter(
            Q(code__icontains=search) |
            Q(invoice_reference_number__icontains=search) |
            Q(beneficiary_name__icontains=search) |
            Q(bank_reference_number__icontains=search)
        )

    serializer = RemittanceDetailSerializer(queryset, many=True)
    return Response(
        {
            "success": True,
            "remittances": serializer.data,
            "count": len(serializer.data)
        },
        status=status.HTTP_200_OK
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def remittance_stagewise_summary_view(request):
    """
    Returns Stage-Wise summary counts and grouped remittances for the logged-in Agent / Organization.
    Stage Buckets:
    - STAGE_1_INVOICE
    - STAGE_2_KYC
    - STAGE_3_PAYMENT
    - STAGE_4_CONFIRMATION
    - COMPLETED
    """
    member = getattr(request.user, 'member', None)
    organization = getattr(request.user, 'organization', None) or getattr(member, 'organization', None)

    my_only = request.query_params.get("my_remittances_only", "false").lower() == "true"

    if my_only and member:
        queryset = RemittanceRequest.objects.filter(member=member, is_active=True)
    elif organization:
        queryset = RemittanceRequest.objects.filter(organization=organization, is_active=True)
    elif member:
        queryset = RemittanceRequest.objects.filter(member=member, is_active=True)
    else:
        queryset = RemittanceRequest.objects.filter(created_by=request.user, is_active=True)

    stages = [
        RemittanceStageChoices.STAGE_1_INVOICE,
        RemittanceStageChoices.STAGE_2_KYC,
        RemittanceStageChoices.STAGE_3_PAYMENT,
        RemittanceStageChoices.STAGE_4_CONFIRMATION,
        RemittanceStageChoices.COMPLETED,
    ]

    stage_counts = {}
    grouped_remittances = {}

    for stage_code in stages:
        stage_qs = queryset.filter(current_stage=stage_code)
        stage_counts[stage_code] = stage_qs.count()
        grouped_remittances[stage_code] = RemittanceDetailSerializer(stage_qs, many=True).data

    stage_counts["TOTAL"] = queryset.count()

    return Response(
        {
            "success": True,
            "agent": {
                "user_id": str(request.user.id),
                "email": request.user.email,
                "organization": organization.name if organization else None,
            },
            "summary_counts": stage_counts,
            "remittances_by_stage": grouped_remittances
        },
        status=status.HTTP_200_OK
    )



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def remittance_detail_view(request, pk):
    """
    Detail view for a specific Remittance Request.
    Includes current stage, next step endpoint, and full payload to resume user's journey.
    """
    organization = getattr(request.user, 'organization', None) or getattr(getattr(request.user, 'member', None), 'organization', None)

    if organization:
        remittance = get_object_or_404(RemittanceRequest, pk=pk, organization=organization, is_active=True)
    else:
        remittance = get_object_or_404(RemittanceRequest, pk=pk, is_active=True)

    serializer = RemittanceDetailSerializer(remittance)
    return Response(
        {
            "success": True,
            "remittance": serializer.data
        },
        status=status.HTTP_200_OK
    )

