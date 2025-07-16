from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.conf import settings
from datetime import timedelta
from django.contrib.auth import authenticate
import random
import uuid
from .models import CustomUser, UserProfile
from .serializers import (
    RegisterSerializer, LoginSerializer, EmailOTPSerializer,
    UserProfileSerializer
)

User = get_user_model()
otp_storage = {}         # Temporary in-memory OTP store
verified_email = {}      # Temporary email verification store

# -------------------------------
#           Register
# -------------------------------
# views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model
from .models import UserProfile
from .serializers import RegisterSerializer
import uuid

User = get_user_model()

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        referral_code = request.data.get('referral_code')  # Promo code entered manually
        referral_code_from_url = request.query_params.get('ref')  # Referral code from the URL query parameter
        
        # Get the referral code, prioritizing the one in the body or query params
        referral_code_to_use = referral_code or referral_code_from_url

        # Serialize the request data to create the user
        serializer = RegisterSerializer(data=request.data)

        if serializer.is_valid():
            try:
                # Create the user
                user = serializer.save()

                # Ensure a user profile is created automatically
                user_profile = user.userprofile
                # Generate and save the referral code and referral link if not already set
                if not user_profile.referral_code:
                    user_profile.referral_code = user_profile.generate_referral_code()
                    user_profile.referral_link = user_profile.generate_referral_link()
                    user_profile.save()

                # Handle referral logic if referral code/link is provided
                if referral_code_to_use:
                    try:
                        # Check if the referral code exists
                        referrer_profile = UserProfile.objects.get(referral_code=referral_code_to_use)

                        # Link the new user to the referrer
                        user_profile.referred_by = referrer_profile  # Assign the UserProfile instance
                        user_profile.save()

                        # Reward the referrer
                        referrer_profile.xp += 20  # Reward referrer with 20 XP
                        referrer_profile.gem += 1  # Reward referrer with 1 gem
                        referrer_profile.referral_count += 1  # Increment the referral count
                        referrer_profile.save()

                        # Reward the new user (referee)
                        user_profile.discount_on_next_purchase = 0.50  # 50% discount for the new user
                        user_profile.xp += 10  # New user gets 10 XP for signing up
                        user_profile.gem += 5  # New user gets 5 gems
                        user_profile.save()

                    except UserProfile.DoesNotExist:
                        return Response({"error": "Invalid referral code."}, status=400)  # Return error if referral code is invalid

                # Return the response with referral details (if applicable)
                return Response({
                    "msg": "User registered successfully",
                    "referral_code": user_profile.referral_code,
                    "referral_link": user_profile.referral_link,
                    "referred_by": user.userprofile.referred_by.user.username if user.userprofile.referred_by else None
                }, status=201)

            except Exception as e:
                print(f"Error during registration: {str(e)}")  # Print the error message for debugging
                return Response({"error": f"Registration failed. Please try again. Error: {str(e)}"}, status=500)

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
        if serializer.is_valid():
            email = serializer.validated_data['email']
            name = serializer.validated_data['name']
            password = serializer.validated_data['password']
            remember_me = serializer.validated_data['remember_me']

            try:
                user = User.objects.get(email=email, username=name)
                if not user.check_password(password):
                    raise ValueError
            except (User.DoesNotExist, ValueError):
                return Response({"error": "Invalid credentials"}, status=401)

            # Generate Refresh Token
            refresh = RefreshToken.for_user(user)
            if remember_me:
                refresh.set_exp(lifetime=timedelta(days=30))  # Remember me logic (longer expiration)

            # Return both access and refresh tokens
            return Response({
                "access": str(refresh.access_token),
                "refresh": str(refresh)
            })
        return Response(serializer.errors, status=400)


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
            otp_storage[email] = otp

            subject = 'Your OTP for Password Reset'
            message = f'Your OTP is: {otp}'
            from_email = settings.DEFAULT_FROM_EMAIL

            try:
                send_mail(subject, message, from_email, [email])
                return Response({"msg": "OTP sent to email"}, status=200)
            except Exception as e:
                return Response({"error": "Failed to send email"}, status=500)
        return Response(serializer.errors, status=400)

class ResendOTPView(SendOTPView):
    pass


# -------------------------------
#         Verify OTP
# -------------------------------


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        otp = request.data.get("otp")

        if not email or not otp:
            return Response({"error": "Email and OTP are required"}, status=400)

        if otp_storage.get(email) == otp:
            verified_email["user"] = email
            otp_storage.pop(email, None)  # Clear OTP after verification
            return Response({"msg": "OTP verified"}, status=200)
        return Response({"error": "Invalid OTP"}, status=400)



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
        # Extract the refresh token from the request body
        refresh_token = request.data.get("refresh")
        print(refresh_token)
        if not refresh_token:
            return Response({"error": "Refresh token missing"}, status=400)

        try:
            # Blacklist the refresh token to invalidate it
            token = RefreshToken(refresh_token)
            token.blacklist()  # Blacklist the refresh token
            
            return Response({"msg": "Logged out successfully"}, status=205)

        except Exception as e:
            return Response({"error": str(e)}, status=400)


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



