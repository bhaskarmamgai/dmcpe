import random
import hashlib
from datetime import timedelta
from django.utils import timezone

OTP_EXPIRY_MINUTES = 5
MAX_OTP_ATTEMPTS = 5

def generate_otp():
    return f"{random.randint(100000, 999999)}"

def hash_otp(otp: str) -> str:
    return hashlib.sha256(otp.encode()).hexdigest()

def otp_expiry_time():
    return timezone.now() + timedelta(minutes=OTP_EXPIRY_MINUTES)
