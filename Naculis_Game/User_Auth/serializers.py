from rest_framework import serializers
from .models import CustomUser, UserProfile, UserDiscount
from django_countries.fields import CountryField
import cloudinary.uploader
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
        from .models import UserDiscount, UserProfile  # Local import to avoid circular

        # Remove confirm_password before user creation
        referral_code = validated_data.pop('referral_code', None)
        validated_data.pop('confirm_password')

        # Create user and UserProfile
        user = CustomUser.objects.create_user(**validated_data)
        user_profile = user.userprofile

        # If registered via referral, handle rewards and discounts
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

                # Grant a 50% discount to the **referee** (new user)
                UserDiscount.objects.create(
                    user_profile=user_profile,
                    percent=50.00,
                    reason='Referral Sign-up'
                )

                # Optionally, also grant a discount to the **referrer**
                UserDiscount.objects.create(
                    user_profile=referrer_profile,
                    percent=20.00,   # e.g., 20% for referrer; change as needed!
                    reason=f'Referral Reward (for referring {user.username})'
                )

                # Other new user rewards
                user_profile.xp += 10
                user_profile.gem += 5
                user_profile.save()
            except UserProfile.DoesNotExist:
                pass  # Invalid code, ignore

        return user



# Login Serializer

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


# OTP & Auth Helpers

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
    country = serializers.CharField(source='country.name', read_only=True)  # Converts CountryField to a string
    referred_by = serializers.CharField(source='referred_by.username', read_only=True)  # Add referrer info
    discounts = UserDiscountSerializer(many=True, read_only=True)
    class Meta:
        model = UserProfile
        fields = [
            'username', 'email', 'phone', 'dob', 'gender', 'country', 'profile_picture',
            'xp', 'daily_streak', 'star', 'gem', 'referred_by', 
            'referral_code', 'referral_link', 'referral_count', 'discount_used','discounts'
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
        fields = ['phone', 'dob', 'gender', 'country', 'profile_picture', 'previous_profile_picture']
        read_only_fields = ['previous_profile_picture']

    def update(self, instance, validated_data):
        new_image = validated_data.get('profile_picture', None)
        if new_image:
            # Save current image to previous before updating
            if instance.profile_picture:
                instance.previous_profile_picture = instance.profile_picture
        return super().update(instance, validated_data)