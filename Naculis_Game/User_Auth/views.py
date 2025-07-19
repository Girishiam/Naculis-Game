from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.conf import settings
from datetime import timedelta
from django.contrib.auth import authenticate
import random
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils.translation import gettext_lazy as _

from django.utils import translation
from django.conf import settings
from django.utils.translation import gettext as _
from rest_framework import generics, permissions, status
from django.utils import timezone


from .models import CustomUser, UserProfile, UserDiscount,PendingRegistration





from .serializers import (
   RegisterSerializer, StartRegistrationSerializer, VerifyRegistrationOTPSerializer, LoginSerializer, EmailOTPSerializer,
    UserProfileSerializer, UserProfileUpdateSerializer, UserDiscountSerializer, LogoutSerializer
)


User = get_user_model()
otp_storage = {}         # Temporary in-memory OTP store
verified_email = {}      # Temporary email verification store

#language set



# -------------------------------
#           Register
# -------------------------------


User = get_user_model()
class StartRegistrationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        referral_code = request.data.get("referral_code") or request.query_params.get("ref", "")
        data = request.data.copy()
        data["referral_code"] = referral_code

        serializer = StartRegistrationSerializer(data=data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        email = data["email"]
        username = data["username"]

        # Don't register if user already exists
        if User.objects.filter(email=email).exists():
            return Response({"error": "Email already registered."}, status=400)
        if User.objects.filter(username=username).exists():
            return Response({"error": "Username already taken."}, status=400)

        # Generate OTP
        otp = str(random.randint(100000, 999999))
        expires_at = timezone.now() + timedelta(minutes=5)

        # Delete previous attempt
        PendingRegistration.objects.filter(email=email).delete()

        # Save to temporary registration
        PendingRegistration.objects.create(
            email=email,
            username=username,
            raw_password=data["password"],  # Not hashed yet
            password=data["password"],      # Same here
            otp=otp,
            expires_at=expires_at,
            referral_code=referral_code,
            referral_link=f"http://127.0.0.1:8000/api/register/?ref={referral_code}" if referral_code else None
        )

        # Send OTP
        try:
            send_mail(
                subject="Verify your email",
                message=f"Your OTP is: {otp}. It expires in 5 minutes.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
            )
        except Exception as e:
            return Response({"error": f"Failed to send OTP: {str(e)}"}, status=500)

        return Response({"msg": "OTP sent to your email. Please verify to complete registration."}, status=200)



#start registration OTP verification view
class VerifyRegistrationOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyRegistrationOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        data = serializer.validated_data
        try:
            pending = PendingRegistration.objects.get(email=data["email"])
        except PendingRegistration.DoesNotExist:
            return Response({"error": "No pending registration found."}, status=404)

        if pending.is_expired():
            pending.delete()
            return Response({"error": "OTP has expired."}, status=400)

        if data["otp"] != pending.otp:
            return Response({"error": "Invalid OTP."}, status=400)

        # All checks passed – create the user
        payload = {
            "username": pending.username,
            "email": pending.email,
            "password": pending.password,
            "confirm_password": pending.password,
            "referral_code": pending.referral_code,
        }

        serializer = RegisterSerializer(data=payload)
        if serializer.is_valid():
            user = serializer.save()

            profile = user.userprofile
            profile.referral_code = profile.generate_referral_code()
            profile.referral_link = profile.generate_referral_link()
            profile.save()

            # Cleanup pending
            pending.delete()

            refresh = RefreshToken.for_user(user)
            return Response({
                "msg": "User registered successfully",
                "referral_code": profile.referral_code,
                "referral_link": profile.referral_link,
                "referred_by": profile.referred_by.user.username if profile.referred_by else None,
            }, status=201)

        return Response(serializer.errors, status=400)



#Referral Link View
class ReferralLinkView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get the user's profile
        user_profile = request.user.userprofile

        # Generate the referral link using the referral code
        referral_link = user_profile.generate_referral_link()

        return Response({"referral_link": referral_link}, status=200)


#Referral Code View
class ReferralCodeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get the user's referral code
        referral_code = request.user.userprofile.referral_code

        return Response({"referral_code": referral_code}, status=200)
# -------------------------------
#             Login
# -------------------------------
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        user = serializer.validated_data['user']
        remember_me = serializer.validated_data.get('remember_me', False)

        refresh = RefreshToken.for_user(user)
        if remember_me:
            refresh.set_exp(lifetime=timedelta(days=30))

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        })


# -------------------------------
#         Send / Resend OTP
# -------------------------------


class SendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = EmailOTPSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp = str(random.randint(100000, 999999))

            # Set OTP and expiry (5 minutes from now)
            otp_storage[email] = {
                "otp": otp,
                "expires_at": timezone.now() + timedelta(minutes=5)
            }

            subject = 'Your OTP for Registration / Password Reset'
            message = f'Your OTP is: {otp} (valid for 5 minutes)'
            from_email = settings.DEFAULT_FROM_EMAIL

            try:
                send_mail(subject, message, from_email, [email])
                return Response({"msg": "OTP sent to email"}, status=200)
            except Exception:
                return Response({"error": "Failed to send OTP"}, status=500)

        return Response(serializer.errors, status=400)


# -------------------------------
#         Resend OTP
class ResendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"error": "Email is required."}, status=400)

        try:
            pending = PendingRegistration.objects.get(email=email)
        except PendingRegistration.DoesNotExist:
            return Response({"error": "No registration found."}, status=404)

        # Generate new OTP
        otp = str(random.randint(100000, 999999))
        pending.otp = otp
        pending.expires_at = timezone.now() + timedelta(minutes=5)
        pending.save()

        try:
            send_mail(
                subject="Resend OTP",
                message=f"Your new OTP is: {otp}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
            )
            return Response({"msg": "OTP resent successfully."}, status=200)
        except Exception as e:
            return Response({"error": f"Failed to send OTP: {str(e)}"}, status=500)


# -------------------------------
#         Verify OTP
# -------------------------------

class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        otp = request.data.get("otp")

        if not email or not otp:
            return Response({"error": "Email and OTP are required."}, status=400)

        otp_data = otp_storage.get(email)
        if not otp_data:
            return Response({"error": "OTP not sent or expired."}, status=400)

        if timezone.now() > otp_data["expires_at"]:
            otp_storage.pop(email, None)
            return Response({"error": "OTP has expired."}, status=400)

        if otp != otp_data["otp"]:
            return Response({"error": "Invalid OTP."}, status=400)

        # ✅ Mark email as verified
        verified_email["user"] = email
        otp_storage.pop(email, None)

        return Response({"msg": "OTP verified successfully."}, status=200)

        return Response({"msg": "OTP verified successfully"}, status=200)


# -------------------------------
#       Reset Password
# -------------------------------


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = verified_email.get("user")
        new_password = request.data.get("new_password")
        confirm_password = request.data.get("confirm_password")

        if not email:
            return Response({"error": "OTP not verified"}, status=400)
        if not new_password or not confirm_password:
            return Response({"error": "Both passwords are required"}, status=400)
        if new_password != confirm_password:
            return Response({"error": "Passwords do not match"}, status=400)
        if len(new_password) < 8:
            return Response({"error": "Password too short"}, status=400)

        try:
            user = CustomUser.objects.get(email=email)
            user.set_password(new_password)
            user.save()

            # Remove verified marker
            verified_email.pop("user", None)

            return Response({"msg": "Password updated successfully"}, status=200)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found"}, status=404)


# -------------------------------
#            Logout
# -------------------------------

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"msg": "Successfully logged out."}, status=status.HTTP_205_RESET_CONTENT)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# -------------------------------
#       Delete Account
# -------------------------------
class DeleteAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user = request.user
        user.delete()
        return Response({"msg": "Account deleted"}, status=204)

# -------------------------------
#      User Profile (Get/Put)
# -------------------------------
class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = request.user.userprofile
            serializer = UserProfileSerializer(profile)
            return Response({
                "username": profile.user.username,
                "referral_code": profile.referral_code,
                "referral_link": profile.generate_referral_link(),
                "referred_by": profile.referred_by.user.username if profile.referred_by else None,
                **serializer.data  # Include other profile details from UserProfileSerializer
            }, status=200)
        except UserProfile.DoesNotExist:
            return Response({"error": "Profile not found"}, status=404)

    def put(self, request):
        try:
            profile = request.user.userprofile
            serializer = UserProfileSerializer(profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=200)
            return Response(serializer.errors, status=400)
        except UserProfile.DoesNotExist:
            return Response({"error": "Profile not found"}, status=404)



# class UserProfileUpdateView(APIView):
#     permission_classes = [IsAuthenticated]
#     parser_classes = [MultiPartParser, FormParser]

#     def put(self, request):
#         user_profile = request.user.userprofile

#         # If new profile_picture is uploaded, move old one to previous_profile_picture
#         if 'profile_picture' in request.data and user_profile.profile_picture:
#             user_profile.previous_profile_picture = user_profile.profile_picture

#         serializer = UserProfileUpdateSerializer(
#             user_profile,
#             data=request.data,
#             partial=True
#         )
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data, status=200)
#         return Response(serializer.errors, status=400)

class UserProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def put(self, request):
        user_profile = request.user.userprofile
        serializer = UserProfileUpdateSerializer(user_profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    def get(self, request):
        user_profile = request.user.userprofile
        serializer = UserProfileUpdateSerializer(user_profile)
        return Response(serializer.data, status=200)


class DeleteProfilePictureView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user_profile = request.user.userprofile
        if user_profile.profile_picture:
            # Optional: Actually delete the image from Cloudinary storage
            # You need to store the public_id of the image to do this (CloudinaryField stores it)
            import cloudinary
            try:
                cloudinary.uploader.destroy(user_profile.profile_picture.public_id)
            except Exception:
                pass  # Ignore if delete fails

            user_profile.profile_picture = None
            user_profile.save()
            return Response({"msg": "Profile picture deleted."}, status=status.HTTP_200_OK)
        else:
            return Response({"msg": "No profile picture to delete."}, status=status.HTTP_400_BAD_REQUEST)



#discount
# List all your own discounts
class UserDiscountListView(generics.ListAPIView):
    serializer_class = UserDiscountSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserDiscount.objects.filter(user_profile=self.request.user.userprofile)

# Retrieve a specific discount (must be your own)
class UserDiscountDetailView(generics.RetrieveAPIView):
    serializer_class = UserDiscountSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserDiscount.objects.filter(user_profile=self.request.user.userprofile)

# Admin/staff: Create a discount for any user
class AdminCreateDiscountView(generics.CreateAPIView):
    serializer_class = UserDiscountSerializer
    permission_classes = [permissions.IsAdminUser]

    def perform_create(self, serializer):
        user_profile_id = self.request.data.get('user_profile_id')
        try:
            user_profile = UserProfile.objects.get(id=user_profile_id)
        except UserProfile.DoesNotExist:
            raise serializer.ValidationError("UserProfile not found.")
        serializer.save(user_profile=user_profile)

# Mark a discount as used (apply a discount)

class UseDiscountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            discount = UserDiscount.objects.get(pk=pk, user_profile=request.user.userprofile)
        except UserDiscount.DoesNotExist:
            return Response({"detail": "Discount not found."}, status=404)

        if discount.used:
            return Response({"detail": "Discount already used."}, status=400)

        discount.used = True
        discount.used_at = timezone.now()
        discount.save()
        return Response({"detail": "Discount applied successfully."}, status=200)

# (Optional) Delete a discount (admin only)
class AdminDeleteDiscountView(generics.DestroyAPIView):
    queryset = UserDiscount.objects.all()
    serializer_class = UserDiscountSerializer
    permission_classes = [permissions.IsAdminUser]