from django.urls import path
from .views import (
    rms_signup_view,
    rms_verify_otp_view,
    rms_login_view,
    rms_indian_states_view,
    beneficiary_list_create_view,
    beneficiary_detail_view,
    remittance_stage1_create_invoice_view,
    remittance_stage2_kyc_pan_view,
    passenger_excel_template_download_view,
    remittance_calculate_breakup_view,
    remittance_stage3_payment_view,
    remittance_stage4_confirmation_view,
    remittance_list_view,
    remittance_stagewise_summary_view,
    remittance_detail_view,
)

app_name = "rms"

urlpatterns = [
    # Auth & States
    path("auth/signup/", rms_signup_view, name="rms-signup"),
    path("auth/verify-otp/", rms_verify_otp_view, name="rms-verify-otp"),
    path("auth/login/", rms_login_view, name="rms-login"),
    path("states/", rms_indian_states_view, name="rms-indian-states"),

    # Beneficiary APIs
    path("beneficiaries/", beneficiary_list_create_view, name="beneficiary-list-create"),
    path("beneficiaries/<int:pk>/", beneficiary_detail_view, name="beneficiary-detail"),

    # 4-Stage Remittance Workflow & Resume APIs
    path("remittances/stage1-create-invoice/", remittance_stage1_create_invoice_view, name="remittance-stage1"),
    path("remittances/passenger-excel-template/", passenger_excel_template_download_view, name="passenger-excel-template"),
    path("remittances/<int:pk>/stage2-kyc-pan/", remittance_stage2_kyc_pan_view, name="remittance-stage2"),
    path("remittances/calculate-breakup/", remittance_calculate_breakup_view, name="remittance-calculate-breakup-standalone"),
    path("remittances/<int:pk>/calculate-breakup/", remittance_calculate_breakup_view, name="remittance-calculate-breakup"),
    path("remittances/<int:pk>/stage3-payment/", remittance_stage3_payment_view, name="remittance-stage3"),
    path("remittances/<int:pk>/stage4-confirmation/", remittance_stage4_confirmation_view, name="remittance-stage4"),

    # Query & Detail APIs
    path("remittances/stagewise/", remittance_stagewise_summary_view, name="remittance-stagewise-summary"),
    path("remittances/", remittance_list_view, name="remittance-list"),
    path("remittances/<int:pk>/", remittance_detail_view, name="remittance-detail"),
]
