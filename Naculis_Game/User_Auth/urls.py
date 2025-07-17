from django.urls import path
from .views import *

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),

    path('send-otp/', SendOTPView.as_view(), name='send_otp'),
    path('resend-otp/', ResendOTPView.as_view(), name='resend_otp'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),

    path('reset-password/', ResetPasswordView.as_view(), name='reset_password'),

    path('logout/', LogoutView.as_view(), name='logout'),
    path('delete-account/', DeleteAccountView.as_view(), name='delete_account'),

    path('profile/', UserProfileView.as_view(), name='user_profile'),
    path('profile/update/', UserProfileUpdateView.as_view(), name='update_profile'),
    path('profile/delete-picture/', DeleteProfilePictureView.as_view(), name='delete_profile_picture'),

    path('referral-link/', ReferralLinkView.as_view(), name='referral-link'),
    path('referral-code/', ReferralCodeView.as_view(), name='referral-code'),

    #discount
    path('discounts/', UserDiscountListView.as_view(), name='user-discount-list'),
    path('discounts/<int:pk>/', UserDiscountDetailView.as_view(), name='user-discount-detail'),
    path('discounts/create/', AdminCreateDiscountView.as_view(), name='admin-create-discount'),
    path('discounts/<int:pk>/use/', UseDiscountView.as_view(), name='use-discount'),
    path('discounts/<int:pk>/delete/', AdminDeleteDiscountView.as_view(), name='admin-delete-discount'),

]