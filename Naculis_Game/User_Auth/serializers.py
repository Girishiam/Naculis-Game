from rest_framework import serializers
from .models import CustomUser, UserProfile
from django_countries.fields import CountryField

# -------------------
# Register Serializer
# -------------------
# serializers.py

class RegisterSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True)
    referral_code = serializers.CharField(required=False, allow_blank=True)  # Add referral_code field

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'phone', 'password', 'confirm_password', 'referral_code']
        extra_kwargs = {'password': {'write_only': True}}

    def validate(self, data):
        # Password match validation
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")

        # Password length check
        if len(data['password']) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")

        # Check if email already exists (case-insensitive)
        if CustomUser.objects.filter(email__iexact=data['email']).exists():
            raise serializers.ValidationError("A user with this email already exists.")

        # Check if username already exists (case-insensitive)
        if CustomUser.objects.filter(username__iexact=data['username']).exists():
            raise serializers.ValidationError("A user with this username already exists.")

        return data

    def create(self, validated_data):
        referral_code = validated_data.get('referral_code', None)  # Retrieve referral code
        validated_data.pop('confirm_password')  # Remove confirm_password field before creating user

        # Create the user
        user = CustomUser.objects.create_user(**validated_data)

        # Handle referral code if provided
        if referral_code:
            try:
                # Check if the referral code is valid
                referrer_profile = UserProfile.objects.get(referral_code=referral_code)

                # Link the referrer and assign rewards
                user.userprofile.referred_by = referrer_profile.user
                user.userprofile.save()

                # Reward the referrer
                referrer_profile.xp += 20
                referrer_profile.gem += 1
                referrer_profile.discount_on_next_purchase = 0.10  # 10% discount for the next purchase
                referrer_profile.save()

                # Reward the new user (receiver)
                user.userprofile.xp += 10  # New user gets 10 XP for signing up
                user.userprofile.gem += 5  # New user gets 5 gems
                user.userprofile.discount_on_next_purchase = 0.50  # 50% discount for the new user (referee)
                user.userprofile.save()

            except UserProfile.DoesNotExist:
                pass  # If referral code is invalid, silently ignore

        return user




# -------------------
# Login Serializer
# -------------------
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    name = serializers.CharField()
    password = serializers.CharField()
    remember_me = serializers.BooleanField(default=False)

    def validate(self, data):
        # Validate if the user exists with the provided email and username
        try:
            user = CustomUser.objects.get(email=data['email'], username=data['name'])
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("Invalid credentials")

        # Validate password
        if not user.check_password(data['password']):
            raise serializers.ValidationError("Invalid credentials")

        return data

# -------------------
# OTP & Auth Helpers
# -------------------
class EmailOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()

class SendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField()

class ResendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()

class OTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField()

class ResetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField()
    confirm_password = serializers.CharField()

class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

# -------------------
# Delete Account
# -------------------
class DeleteAccountSerializer(serializers.Serializer):
    email = serializers.EmailField()

# -------------------
# Message Response
# -------------------
class MessageResponseSerializer(serializers.Serializer):
    msg = serializers.CharField()

# -------------------
# User Profile Serializer
# -------------------





class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    country = serializers.CharField(source='country.name', read_only=True)  # Converts CountryField to a string
    referred_by = serializers.CharField(source='referred_by.username', read_only=True)  # Add referrer info
    
    class Meta:
        model = UserProfile
        fields = [
            'username', 'email', 'phone', 'dob', 'gender', 'country', 'profile_picture',
            'xp', 'daily_streak', 'star', 'gem', 'referred_by', 
            'referral_code', 'referral_link', 'referral_count', 'discount_used'
        ]

    
    def update(self, instance, validated_data):
        # Update fields in CustomUser (phone)
        user = instance.user
        user.phone = validated_data.get('phone', user.phone)
        user.save()

        # Update UserProfile fields
        instance.dob = validated_data.get('dob', instance.dob)
        instance.country = validated_data.get('country', instance.country)
        instance.gender = validated_data.get('gender', instance.gender)
        instance.profile_picture = validated_data.get('profile_picture', instance.profile_picture)
        instance.xp = validated_data.get('xp', instance.xp)
        instance.daily_streak = validated_data.get('daily_streak', instance.daily_streak)
        instance.star = validated_data.get('star', instance.star)
        instance.gem = validated_data.get('gem', instance.gem)

        instance.save()  # Save the updated UserProfile
        return instance
