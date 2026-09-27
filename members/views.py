from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from members.models import Member
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from django.shortcuts import get_object_or_404

from .models import Organization
from .serializers import BusinessDocumentUploadSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction

from .models import (
    BusinessDocument,
    DocumentPage,
    KYCStatus,
)
from .serializers import SignupSerializer
from rest_framework_simplejwt.tokens import RefreshToken


@api_view(["POST"])
@permission_classes([AllowAny])
@transaction.atomic
def signup_view(request):
    print("---- RAW REQUEST.DATA ----")
    print(request.data)
    print("---- RAW REQUEST.FILES ----")
    print(request.FILES)

    serializer = SignupSerializer(data=request.data)

    if not serializer.is_valid():
        print("Serializer errors:", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    result = serializer.save()
    user = result["user"]
    organization = result["organization"]
    member = result["member"]

    # ---------------------------
    # DOCUMENT EXTRACTION
    # ---------------------------
    def extract_documents(request):
        documents = []
        index = 0

        while True:
            prefix = f"documents[{index}]"

            category = request.data.get(f"{prefix}[category]")
            document_type = request.data.get(f"{prefix}[document_type]")
            document_number = request.data.get(f"{prefix}[document_number]")

            page_type = request.data.get(f"{prefix}[page_type]", "page")
            page_number = request.data.get(f"{prefix}[page_number]")
            page_start = request.data.get(f"{prefix}[page_start]")
            page_end = request.data.get(f"{prefix}[page_end]")

            file = request.FILES.get(f"{prefix}[file]")

            # stop when nothing found
            if not any([category, document_type, file]):
                break

            documents.append({
                "category": category,
                "document_type": document_type,
                "document_number": document_number,
                "page_type": page_type,
                "page_number": page_number,
                "page_start": page_start,
                "page_end": page_end,
                "file": file,
            })

            index += 1

        return documents

    documents = extract_documents(request)

    uploaded_docs_count = 0

    for doc in documents:
        print("📄 Processing document:", doc)

        # Create BusinessDocument (1 per category + type)
        business_doc, created = BusinessDocument.objects.get_or_create(
            organization=organization,
            category=doc["category"],
            document_type=doc["document_type"],
            defaults={
                "document_number": doc.get("document_number"),
            }
        )

        # Create DocumentPage (file stored here)
        page = DocumentPage.objects.create(
            document=business_doc,
            page_type=doc.get("page_type"),
            page_number=doc.get("page_number") or None,
            page_start=doc.get("page_start") or None,
            page_end=doc.get("page_end") or None,
            file=doc.get("file"),
        )

        print("✅ Document saved:", business_doc.id, "Page:", page.id)
        uploaded_docs_count += 1

    # ---------------------------
    # KYC STATUS (INITIAL)
    # ---------------------------
    org_kyc_status = (
        KYCStatus.PENDING if uploaded_docs_count > 0 else KYCStatus.NOT_STARTED
    )

    if hasattr(organization, "kyc_profile"):
        organization.kyc_profile.status = org_kyc_status
        organization.kyc_profile.save(update_fields=["status"])

    # ---------------------------
    # JWT TOKENS
    # ---------------------------
    refresh = RefreshToken.for_user(user)
    refresh["user_id"] = str(user.id)
    refresh["member_id"] = str(member.id)
    refresh["organization_id"] = str(organization.id)
    refresh["organization_name"] = organization.name
    refresh["is_owner"] = member.is_owner

    return Response(
        {
            "success": True,
            "message": "Registration successful",
            "user": {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
            },
            "organization": {
                "id": str(organization.id),
                "name": organization.name,
                "code": organization.code,
                "kyc_status": org_kyc_status,
            },
            "member": {
                "id": str(member.id),
                "code": member.code,
                "is_owner": member.is_owner,
            },
            "documents_uploaded": uploaded_docs_count,
            "tokens": {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def profile_view(request):
    """
    Returns authenticated user's profile,
    member, and organization details.
    """
    user = request.user

    member = get_object_or_404(
        Member.objects.select_related("organization"),
        user=user,
    )
    organization = member.organization
    return Response(
        {
            "success": True,
            "user": {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": getattr(user, "role", None),
                "is_active": user.is_active,
                "date_joined": user.date_joined,
            },
            "member": {
                "id": str(member.id),
                "code": member.code,
                "email": member.email,
                "phone": member.phone,
                "is_owner": member.is_owner,
                "created_at": member.created_at,
                "updated_at": member.updated_at,
            },
            "organization": {
                "id": str(organization.id),
                "name": organization.name,
                "code": organization.code,
                "website": organization.website,
                "created_at": organization.created_at,
                "kyc_status": organization.kyc_status
            },
        },
        status=status.HTTP_200_OK,
    )


class BusinessDocumentUploadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BusinessDocumentUploadSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        organization = get_object_or_404(
            Organization, id=data["organization_id"]
        )

        # TODO (optional): check user belongs to organization
        # if not organization.members.filter(user=request.user).exists():
        #     return Response({"detail": "Unauthorized"}, status=403)

        # Create or fetch BusinessDocument
        document, created = BusinessDocument.objects.get_or_create(
            organization=organization,
            category=data["category"],
            document_type=data["document_type"],
            defaults={
                "document_number": data.get("document_number"),
                "issued_date": data.get("issued_date"),
                "expiry_date": data.get("expiry_date"),
            }
        )

        # Upload page
        page = DocumentPage.objects.create(
            document=document,
            page_type=data["page_type"],
            page_number=data.get("page_number"),
            page_start=data.get("page_start"),
            page_end=data.get("page_end"),
            file=data["file"],
        )

        return Response(
            {
                "success": True,
                "document_id": document.id,
                "page_id": page.id,
                "message": "Business document uploaded successfully",
            },
            status=status.HTTP_201_CREATED,
        )
