from rest_framework import serializers
from .models import CustomUser, UserProfile, UserDiscount,PendingRegistration
from django_countries.fields import CountryField
import cloudinary.uploader
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from django.utils.translation import gettext_lazy as _


# Register Serializer
class RegisterSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True)
    referral_code = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'phone', 'password', 'confirm_password', 'referral_code']
        extra_kwargs = {'password': {'write_only': True}}

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")
        if len(data['password']) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")
        if CustomUser.objects.filter(email__iexact=data['email']).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        if CustomUser.objects.filter(username__iexact=data['username']).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return data

    def create(self, validated_data):
        referral_code = validated_data.pop('referral_code', None)
        password = validated_data.pop('password')
        validated_data.pop('confirm_password')

        # Create user and hash password
        user = CustomUser(**validated_data)
        user.set_password(password)
        user.save()

        user_profile = user.userprofile

        if referral_code:
            try:
                referrer_profile = UserProfile.objects.get(referral_code=referral_code)
                user_profile.referred_by = referrer_profile
                user_profile.save()

                # Referrer rewards
                referrer_profile.xp += 20
                referrer_profile.gem += 1
                referrer_profile.referral_count += 1
                referrer_profile.save()

                # 50% discount to referee
                UserDiscount.objects.create(
                    user_profile=user_profile,
                    percent=50.00,
                    reason='Referral Sign-up'
                )

                # 20% discount to referrer
                UserDiscount.objects.create(
                    user_profile=referrer_profile,
                    percent=20.00,
                    reason=f'Referral Reward (for referring {user.username})'
                )

                # Extra rewards to new user
                user_profile.xp += 10
                user_profile.gem += 5
                user_profile.save()

            except UserProfile.DoesNotExist:
                pass  # Invalid referral code

        return user

        return user
    

#start registration serializer
class StartRegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    referral_code = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError("Passwords do not match.")
        return data



#verify registration serializer
class VerifyRegistrationOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

# Login Serializer



class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    username = serializers.CharField()
    password = serializers.CharField()
    remember_me = serializers.BooleanField(default=False)

    def validate(self, data):
        email = data.get('email')
        username = data.get('username')
        password = data.get('password')

        try:
            user = CustomUser.objects.get(email=email, username=username)
        except CustomUser.DoesNotExist:
           raise serializers.ValidationError({"detail": _("No User is available with that email + username.")})

        if not user.check_password(password):
            raise serializers.ValidationError("Password is incorrect")

        if not user.is_active:
            raise serializers.ValidationError("User account is disabled")

        data['user'] = user
        return data



# OTP & Auth Helpers

class EmailOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()

class SendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField()

class ResendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField()

class OTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField()

class ResetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField()
    confirm_password = serializers.CharField()


#logout serializer

class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate(self, attrs):
        self.token = attrs['refresh']
        return attrs

    def save(self, **kwargs):
        try:
            token = RefreshToken(self.token)
            token.blacklist()
        except TokenError:
            raise serializers.ValidationError("Invalid or expired token.")


# Delete Account

class DeleteAccountSerializer(serializers.Serializer):
    email = serializers.EmailField()


# Message Response

class MessageResponseSerializer(serializers.Serializer):
    msg = serializers.CharField()




    #user_discount
class UserDiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDiscount
        fields = ['id', 'percent', 'reason', 'used', 'granted_at', 'used_at']

# User Profile Serializer
class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    country = serializers.CharField(source='country.name', read_only=True)  # Converts CountryField to a string
    referred_by = serializers.CharField(source='referred_by.username', read_only=True)  # Add referrer info
    discounts = UserDiscountSerializer(many=True, read_only=True)
    
    class Meta:
        model = UserProfile
        fields = [
            'username', 'email', 'first_name', 'last_name','phone', 'dob', 'gender', 'country', 'profile_picture',
            'xp', 'daily_streak', 'level', 'hearts', 'gem', 'referred_by', 
            'referral_code', 'referral_link', 'referral_count', 'discount_used','discounts'
        ]

    
    def update(self, instance, validated_data):
        # Update fields in CustomUser (phone)
        user = instance.user
        user.phone = validated_data.get('phone', user.phone)
        user.save()

        # Update UserProfile fields
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.dob = validated_data.get('dob', instance.dob)
        instance.country = validated_data.get('country', instance.country)
        instance.gender = validated_data.get('gender', instance.gender)
        instance.profile_picture = validated_data.get('profile_picture', instance.profile_picture)
        instance.xp = validated_data.get('xp', instance.xp)
        instance.daily_streak = validated_data.get('daily_streak', instance.daily_streak)
        instance.level = validated_data.get('level', instance.level)
        instance.gem = validated_data.get('gem', instance.gem)
        instance.hearts = validated_data.get('hearts', instance.hearts)

        instance.save()  # Save the updated UserProfile
        return instance
    def get_discounts(self, obj):
        return [
            {
                'id': d.id,
                'percent': str(d.percent),
                'reason': d.reason,
                'used': d.used,
                'granted_at': d.granted_at,
                'used_at': d.used_at
            }
            for d in obj.discounts.all()
        ]
    
class UserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['phone', 'first_name', 'last_name', 'dob', 'gender', 'country', 'profile_picture', 'previous_profile_picture']
        read_only_fields = ['previous_profile_picture']

    def update(self, instance, validated_data):
        new_image = validated_data.get('profile_picture', None)
        if new_image:
            # Save current image to previous before updating
            if instance.profile_picture:
                instance.previous_profile_picture = instance.profile_picture
        return super().update(instance, validated_data)