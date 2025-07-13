from django.urls import path
from .views import *

urlpatterns = [
    path("signup/", RegisterView.as_view(), name="signup"),
    path("signin/", LoginView.as_view(), name="signin"),
    path("send-otp/", SendOTPView.as_view(), name="send-otp"),
    path("verify-otp/", VerifyOTPView.as_view(), name="verify-otp"),
    path("reset-password/", ResetPasswordView.as_view(), name="reset-password"),
]
