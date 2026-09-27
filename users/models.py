import uuid
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from django.db import models
from common.models import BaseModel


class TitleChoices(models.TextChoices):
    MR = 'Mr', 'Mr.'
    MRS = 'Mrs', 'Mrs.'
    MS = 'Ms', 'Ms.'
    DR = 'Dr', 'Dr.'
    PROF = 'Prof', 'Prof.'


def user_picture_upload_path(instance, filename):
    user_id = instance.id or uuid.uuid4()
    return f"users/profile-picture/{user_id}/{filename}"


class User(AbstractUser, BaseModel):
    email = models.EmailField(
        unique=True,
        null=True,
        blank=True
    )
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('employee', 'Employee (Travel Supply Team)'),
        ('member', 'Member (Travel Agent)'),
        ('REMIT_ONLY', 'Remittance Only (RMS)'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')

    # Avoid reverse accessor clashes with Django's default auth.User
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_set',
        blank=True,
        help_text='The groups this user belongs to.',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_permissions',
        blank=True,
        help_text='Specific permissions for this user.',
    )
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username",]

    def __str__(self):
        return f"{self.username}"


class UserProfile(BaseModel):
    """
    Additional user information.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    title = models.CharField(max_length=5, choices=TitleChoices.choices, blank=True, null=True)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)  # Added state field
    country = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)  # Added postal code
    date_of_birth = models.DateField(blank=True, null=True)  # Added DOB
    gender = models.CharField(max_length=10, blank=True, null=True, choices=[
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ])
    picture = models.FileField(upload_to=user_picture_upload_path, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)  # Short biography or description
    website = models.URLField(blank=True, null=True)  # User personal/portfolio website

    def __str__(self):
        return f"{self.title + ' ' if self.title else ''}{self.first_name} {self.last_name}".strip() or self.user.username


class UserEmailOTP(BaseModel):
    email = models.EmailField()
    otp_hash = models.CharField(max_length=255)
    expires_at = models.DateTimeField()
    is_verified = models.BooleanField(default=False)
    attempts = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "User Email OTP"
        verbose_name_plural = "User Email OTPs"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
