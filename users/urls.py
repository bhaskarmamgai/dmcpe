from django.urls import path

from users.views import request_otp_view,verify_otp_view

app_name = "users"

urlpatterns = [
    path("request-otp/", request_otp_view, name="request-otp"),
    path("verify-otp/", verify_otp_view, name="verify-otp"),
]
