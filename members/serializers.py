from django.contrib.auth import get_user_model

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from members.models import  DocumentPage, DocumentCategory, DocumentType
from rest_framework import serializers
from django.db import transaction
from django.contrib.auth import get_user_model
from .models import (
    Organization,
    Member,
    OrganizationKYC,
    KYCStatus,
)
from users.models import UserProfile, TitleChoices

User = get_user_model()


class SignupSerializer(serializers.Serializer):
    # -------------------
    # AUTH / USER
    # -------------------
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, min_length=8)

    # Username is optional (email-based login)
    username = serializers.CharField(required=False, allow_blank=True)

    # -------------------
    # USER PROFILE
    # -------------------
    title = serializers.ChoiceField(
        choices=TitleChoices.choices,
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    first_name = serializers.CharField(required=True, max_length=100)
    middle_name = serializers.CharField(required=False, allow_blank=True, max_length=100)
    last_name = serializers.CharField(required=True, max_length=100)

    phone_country_code = serializers.CharField(
        required=False, allow_blank=True, max_length=5, default="91"
    )
    phone = serializers.CharField(required=False, allow_blank=True, max_length=20)

    # -------------------
    # ORGANIZATION
    # -------------------
    organization_name = serializers.CharField(required=True, max_length=150)
    website = serializers.URLField(required=False, allow_blank=True)

    # -------------------
    # VALIDATIONS
    # -------------------
    def validate(self, attrs):
        phone = attrs.get("phone")
        phone_country_code = attrs.get("phone_country_code") or "91"

        if phone:
            phone = (
                phone.replace("+", "")
                .replace("-", "")
                .replace(" ", "")
                .strip()
            )

            exists = Member.objects.filter(
                phone=phone,
                phone_country_code=phone_country_code,
            ).exists()

            if exists:
                raise serializers.ValidationError({
                    "phone": (
                        "This phone number is already registered. "
                        "Please use a different number."
                    )
                })

            # normalize back
            attrs["phone"] = phone
            attrs["phone_country_code"] = phone_country_code

        return attrs
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "A user with this email already exists."
            )
        return value

    def validate_username(self, value):
        if value and User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                "A user with this username already exists."
            )
        return value

    # -------------------
    # CREATE
    # -------------------
    @transaction.atomic
    def create(self, validated_data):
        # -------------------
        # USER
        # -------------------
        email = validated_data["email"]
        password = validated_data["password"]

        username = validated_data.get("username")
        if not username:
            username = email.split("@")[0]

        user = User.objects.create_user(
            email=email,
            username=username,
            password=password,
            role="member",
        )

        # -------------------
        # USER PROFILE
        # -------------------
        UserProfile.objects.create(
            user=user,
            title=validated_data.get("title"),
            first_name=validated_data["first_name"],
            middle_name=validated_data.get("middle_name") or None,
            last_name=validated_data["last_name"],
            phone=validated_data.get("phone") or None,
        )

        # -------------------
        # ORGANIZATION
        # -------------------
        organization = Organization.objects.create(
            name=validated_data["organization_name"],
            website=validated_data.get("website") or None,
        )

        # -------------------
        # MEMBER (OWNER)
        # -------------------
        member = Member.objects.create(
            user=user,
            organization=organization,
            email=email,
            phone_country_code=validated_data.get("phone_country_code") or "91",
            phone=validated_data.get("phone") or None,
            is_owner=True,
        )

        # -------------------
        # KYC INITIAL STATE
        # -------------------
        OrganizationKYC.objects.create(
            organization=organization,
            status=KYCStatus.NOT_STARTED,
        )

        return {
            "user": user,
            "organization": organization,
            "member": member,
        }

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        try:
            member = Member.objects.select_related("organization").get(user=user)
        except Member.DoesNotExist:
            raise serializers.ValidationError(
                "User does not have an associated Member profile."
            )

        token["user_id"] = str(user.id)
        token["member_id"] = str(member.id)
        token["organization_id"] = str(member.organization.id)
        token["organization_name"] = member.organization.name
        token["is_owner"] = member.is_owner
        token["role"] = getattr(user, "role", None)

        return token


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class BusinessDocumentUploadSerializer(serializers.Serializer):
    # Document-level fields
    organization_id = serializers.IntegerField()
    category = serializers.ChoiceField(choices=DocumentCategory.choices)
    document_type = serializers.ChoiceField(choices=DocumentType.choices)
    document_number = serializers.CharField(required=False, allow_blank=True)
    issued_date = serializers.DateField(required=False)
    expiry_date = serializers.DateField(required=False)

    # Page-level fields
    page_type = serializers.ChoiceField(choices=DocumentPage.PageType.choices)
    page_number = serializers.IntegerField(required=False)
    page_start = serializers.IntegerField(required=False)
    page_end = serializers.IntegerField(required=False)
    file = serializers.FileField()

    def validate(self, attrs):
        page_number = attrs.get("page_number")
        page_start = attrs.get("page_start")
        page_end = attrs.get("page_end")

        # Cannot mix single page and page range
        if page_number and (page_start or page_end):
            raise serializers.ValidationError(
                "Use either page_number OR page_start/page_end, not both"
            )

        # Page range must be complete
        if (page_start and not page_end) or (page_end and not page_start):
            raise serializers.ValidationError(
                "Both page_start and page_end are required"
            )

        # Page range sanity
        if page_start and page_end and page_start > page_end:
            raise serializers.ValidationError(
                "page_start cannot be greater than page_end"
            )

        return attrs
