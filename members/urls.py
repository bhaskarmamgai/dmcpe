from django.urls import path
from members.views import profile_view, BusinessDocumentUploadAPIView, signup_view

urlpatterns = [
    path('members/auth/profile/', profile_view, name='profile'),
    path('members/auth/sign-up/', signup_view, name='member-sign-up'),
    path("organizations/kyc/documents/", BusinessDocumentUploadAPIView.as_view(), name="upload_kyc_documents"),
]
