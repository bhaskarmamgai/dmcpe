from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from users.models import UserEmailOTP
from users.utils.otp import generate_otp, otp_expiry_time
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from members.models import Member
from users.utils.otp import hash_otp, MAX_OTP_ATTEMPTS
from django.template.loader import render_to_string
from django.utils.timezone import now
import boto3
from django.conf import settings
from botocore.exceptions import ClientError

User = get_user_model()


def send_email_ses(from_email, to_email, subject, html_body, text_body=None):
    client = boto3.client(
        "ses",
        region_name=settings.AWS_S3_REGION_NAME,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )

    try:
        client.send_email(
            Source=from_email,
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {
                    "Html": {"Data": html_body, "Charset": "UTF-8"},
                    "Text": {"Data": text_body or "", "Charset": "UTF-8"},
                },
            },
        )

    except ClientError as e:
        raise RuntimeError(
            f"SES send failed: {e.response['Error']['Message']}"
        )


def send_otp_email(email, otp, expiry_minutes=10):
    """
    Sends OTP email using AWS SES
    """
    print(f"Sending OTP {otp} to {email}")

    # Only allow emails ending with travelsupply.in or bhaskar90196@gmail.com
    if not (email.endswith("@travelsupply.in") or email == "bhaskar90196@gmail.com"):
        print(f"Email restricted: {email} is not in the allowed list.")
        return None

    subject = "Your TravelSupply Verification Code"
    DEFAULT_FROM_EMAIL = "TravelSupply <devops@travelsupply.in>"

    context = {
        "OTP_CODE": otp,
        "OTP_EXPIRY_MINUTES": expiry_minutes,
        "CURRENT_YEAR": now().year,
    }
    html_body = render_to_string("email_login_otp.html", context)
    return send_email_ses(
        DEFAULT_FROM_EMAIL,
        to_email=email,
        subject=subject,
        html_body=html_body,
    )

@api_view(["POST"])
@permission_classes([AllowAny])
def request_otp_view(request):
    email = request.data.get("email")

    if not email:
        return Response(
            {"error": "Email is Required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    UserEmailOTP.objects.filter(
        email=email,
        is_verified=False
    ).update(is_active=False, is_deleted=True)

    otp = generate_otp()

    UserEmailOTP.objects.create(
        email=email,
        otp_hash=hash_otp(otp),
        expires_at=otp_expiry_time()
    )

    send_otp_email(email, otp)

    return Response(
        {"success": True, "message": "OTP Sent Successfully."},
        status=status.HTTP_200_OK
    )


def error_response(code, message, http_status=status.HTTP_400_BAD_REQUEST):
    return Response(
        {
            "success": False,
            "error_code": code,
            "message": message,
        },
        status=http_status,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def verify_otp_view(request):
    email = request.data.get("email")
    otp = request.data.get("otp")

    if not email:
        return error_response(
            "OTP_EMAIL_REQUIRED",
            "Email is required to verify OTP."
        )

    if not otp:
        return error_response(
            "OTP_CODE_REQUIRED",
            "OTP is required to continue."
        )

    try:
        otp_obj = UserEmailOTP.objects.filter(
            email=email,
            is_verified=False
        ).latest("created_at")

    except UserEmailOTP.DoesNotExist:
        return error_response(
            "OTP_NOT_FOUND",
            "OTP not found or already used. Please request a new OTP."
        )

    # Expired OTP
    if otp_obj.is_expired:
        otp_obj.is_active = False
        otp_obj.is_deleted = True
        otp_obj.save(update_fields=["is_active", "is_deleted"])
        return error_response(
            "OTP_EXPIRED",
            "The OTP has expired. Please request a new one."
        )

    # Too many attempts
    if otp_obj.attempts >= MAX_OTP_ATTEMPTS:
        otp_obj.is_active = False
        otp_obj.is_deleted = True
        otp_obj.save(update_fields=["is_active", "is_deleted"])
        return error_response(
            "OTP_MAX_ATTEMPTS",
            "Maximum OTP attempts exceeded. Please request a new OTP."
        )

    # Wrong OTP
    if otp_obj.otp_hash != hash_otp(otp):
        otp_obj.attempts += 1
        otp_obj.save(update_fields=["attempts"])
        return error_response(
            "OTP_INVALID",
            "Invalid OTP. Please try again."
        )

    # OTP success
    otp_obj.is_verified = True
    otp_obj.save(update_fields=["is_verified"])

    # -------------------------
    # LOGIN vs SIGNUP DECISION
    # -------------------------
    try:
        user = User.objects.get(email=email)
        member = Member.objects.select_related(
            "organization", "organization__kyc_profile"
        ).get(user=user)

        refresh = RefreshToken.for_user(user)

        org_kyc_status = (
            member.organization.kyc_profile.status
            if hasattr(member.organization, "kyc_profile")
            else None
        )

        next_screen = "HOME" if org_kyc_status == "APPROVED" else "KYC"

        return Response(
            {
                "success": True,
                "status": "LOGIN",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "next_screen": next_screen,
            },
            status=status.HTTP_200_OK,
        )

    except User.DoesNotExist:
        return Response(
            {
                "success": True,
                "status": "SIGNUP_REQUIRED",
                "next_screen": "SIGNUP",
                "email": email,
            },
            status=status.HTTP_200_OK,
        )
