from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import timedelta
import random
from django.core.mail import send_mail
from .serializers import *
from django.conf import settings
from rest_framework.permissions import IsAuthenticated




User = get_user_model()
otp_storage = {}

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"msg": "User registered successfully"}, status=201)
        return Response(serializer.errors, status=400)

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
            except User.DoesNotExist:
                return Response({"error": "Invalid credentials"}, status=401)

            if not user.check_password(password):
                return Response({"error": "Invalid credentials"}, status=401)

            refresh = RefreshToken.for_user(user)
            if remember_me:
                refresh.set_exp(lifetime=timedelta(days=30))

            return Response({
                "access": str(refresh.access_token),
                "refresh": str(refresh)
            })
        return Response(serializer.errors, status=400)

from django.core.mail import send_mail

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
            recipient_list = [email]

            try:
                send_mail(subject, message, from_email, recipient_list)
                return Response({"msg": "OTP sent to email"}, status=200)
            except Exception as e:
                print(e)
                return Response({"error": "Failed to send email"}, status=500)
        return Response(serializer.errors, status=400)


verified_email = {}  # email: True

class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        otp = request.data.get("otp")

        if not email or not otp:
            return Response({"error": "Email and OTP are required"}, status=400)

        if otp_storage.get(email) == otp:
            verified_email["user"] = email
            return Response({"msg": "OTP verified"})
        return Response({"error": "Invalid OTP"}, status=400)


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = verified_email.get("user")  # Fetch from memory
        new_password = request.data.get("new_password")
        confirm_password = request.data.get("confirm_password")

        if not email:
            return Response({"error": "OTP not verified for any email"}, status=400)

        if not new_password or not confirm_password:
            return Response({"error": "New password and confirm password are required"}, status=400)

        if new_password != confirm_password:
            return Response({"error": "Passwords do not match"}, status=400)

        if len(new_password) < 8:
            return Response({"error": "Password too short"}, status=400)

        try:
            user = CustomUser.objects.get(email=email)
            user.set_password(new_password)
            user.save()
            verified_email.pop("user", None)  # Clear after use
            return Response({"msg": "Password updated"}, status=200)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"msg": "Logged out successfully"}, status=205)
        except Exception as e:
            return Response({"error": "Invalid token"}, status=400)


class DeleteAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user = request.user
        user.delete()
        return Response({"msg": "Account deleted"}, status=204)