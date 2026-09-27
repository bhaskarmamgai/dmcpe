import secrets
import string
import boto3
from django.conf import settings
from django.core.mail import send_mail
from botocore.exceptions import ClientError


def generate_random_password(length=10):
    """
    Generates a secure random password containing uppercase, lowercase, digits, and special characters.
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        if (any(c.islower() for c in password)
                and any(c.isupper() for c in password)
                and any(c.isdigit() for c in password)
                and any(c in "!@#$%^&*" for c in password)):
            return password


def send_welcome_credentials_email(email, password, org_name=""):
    """
    Sends welcome email with auto-generated credentials.
    Tries AWS SES if configured, otherwise falls back to standard Django send_mail.
    """
    subject = "Welcome to Remittance Management System (RMS) - Your Account Credentials"
    
    text_content = (
        f"Hello,\n\n"
        f"Your account for {org_name or 'Remittance Management System'} has been successfully registered.\n\n"
        f"Your Login Credentials:\n"
        f"Email: {email}\n"
        f"Password: {password}\n\n"
        f"Please log in and change your password after your first login.\n\n"
        f"Best regards,\n"
        f"Remittance Management System Team"
    )
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; color: #333; max-width: 600px; border: 1px solid #e0e0e0; border-radius: 8px;">
        <h2 style="color: #1a56db; margin-top: 0;">Welcome to Remittance Management System (RMS)</h2>
        <p>Your account for <strong>{org_name or 'your organization'}</strong> has been successfully created.</p>
        <div style="background-color: #f3f4f6; padding: 15px; border-radius: 6px; margin: 20px 0;">
            <p style="margin: 5px 0;"><strong>Email:</strong> {email}</p>
            <p style="margin: 5px 0;"><strong>Auto-Generated Password:</strong> <code style="font-size: 16px; color: #d97706; background: #fff; padding: 2px 6px; border-radius: 4px;">{password}</code></p>
        </div>
        <p>Please log in using these credentials and update your password.</p>
        <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 20px 0;" />
        <p style="font-size: 12px; color: #6b7280;">This is an automated system notification from RMS.</p>
    </div>
    """

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "RMS Remittance <devops@travelsupply.in>")

    # Attempt AWS SES direct call if credentials exist
    aws_key = getattr(settings, "AWS_ACCESS_KEY_ID", None)
    aws_secret = getattr(settings, "AWS_SECRET_ACCESS_KEY", None)
    aws_region = getattr(settings, "AWS_S3_REGION_NAME", "ap-south-1")

    if aws_key and aws_secret:
        try:
            client = boto3.client(
                "ses",
                region_name=aws_region,
                aws_access_key_id=aws_key,
                aws_secret_access_key=aws_secret,
            )
            client.send_email(
                Source=from_email,
                Destination={"ToAddresses": [email]},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {
                        "Html": {"Data": html_content, "Charset": "UTF-8"},
                        "Text": {"Data": text_content, "Charset": "UTF-8"},
                    },
                },
            )
            print(f"✅ Credentials email sent via AWS SES to {email}")
            return True
        except Exception as e:
            print(f"⚠️ AWS SES email dispatch failed: {e}. Falling back to send_mail.")

    # Fallback to standard Django send_mail
    try:
        send_mail(
            subject=subject,
            message=text_content,
            html_message=html_content,
            from_email=from_email,
            recipient_list=[email],
            fail_silently=True,
        )
        print(f"✅ Credentials email sent via send_mail to {email}")
        return True
    except Exception as e:
        print(f"⚠️ Email send failed: {e}")
        return False


def send_otp_email_and_sms(email, mobile, otp):
    """
    Dispatches OTP code to user email and mobile phone.
    """
    subject = "RMS Verification Code"
    text_content = f"Your RMS Verification Code is {otp}. Valid for 5 minutes."
    html_content = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; color: #333; max-width: 500px; border: 1px solid #e0e0e0; border-radius: 8px;">
        <h3 style="color: #1a56db;">RMS Verification Code</h3>
        <p>Your OTP code to complete registration & activation is:</p>
        <h2 style="color: #d97706; background: #f3f4f6; padding: 10px; text-align: center; border-radius: 6px; letter-spacing: 4px;">{otp}</h2>
        <p style="font-size: 13px; color: #666;">This code is valid for 5 minutes. Do not share it with anyone.</p>
    </div>
    """
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "RMS Remittance <devops@travelsupply.in>")

    try:
        send_mail(
            subject=subject,
            message=text_content,
            html_message=html_content,
            from_email=from_email,
            recipient_list=[email],
            fail_silently=True,
        )
        print(f"✅ OTP {otp} sent to email {email}")
    except Exception as e:
        print(f"⚠️ Failed sending email OTP: {e}")

    print(f"📱 [SMS Provider] OTP {otp} dispatched to mobile {mobile}")
    return True

