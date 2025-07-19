from django.contrib.auth.models import AbstractUser
from django.db import models
from django_countries.fields import CountryField
import uuid
from cloudinary.models import CloudinaryField
from django.utils import timezone
class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('staff', 'Staff'),
        ('moderator', 'Moderator'),
        ('user', 'User'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email


# models.py

class UserProfile(models.Model):
    GENDER_CHOICES = [
        ("M", "Male"),
        ("F", "Female"),
        ("O", "Other"),
        ("N", "Prefer not to say"),
    ]

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50, blank=True, null=True)

    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='N')
    country = CountryField(blank_label='Select Country', null=True, blank=True)
    profile_picture = CloudinaryField('image', blank=True, null=True)
    previous_profile_picture = CloudinaryField('image', blank=True, null=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    xp = models.IntegerField(default=0)
    daily_streak = models.IntegerField(default=0)
    level = models.IntegerField(default=0)
    hearts = models.IntegerField(default=5)
    gem = models.IntegerField(default=0)
    phone = models.CharField(max_length=15, blank=True, null=True)
    referral_code = models.CharField(max_length=20, unique=True, blank=True, null=True)
    referral_link = models.URLField(max_length=200, blank=True, null=True)
    referred_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals')
    discount_used = models.BooleanField(default=False)  
    referral_count = models.IntegerField(default=0)
    date_joined = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username + "'s Profile"

    def is_fully_filled(self):
        for field in self._meta.fields:
            if getattr(self, field.name) in [None, ''] and field.name not in ['id', 'profile_picture', 'dob']:
                return False
        return True
    
    def generate_referral_code(self):
        """Generate a unique referral code for the user."""
        return str(uuid.uuid4())[:8]  # First 8 characters of UUID



    def generate_referral_link(self):
        """Generate a referral link using the referral code."""
        return f"http://127.0.0.1:8000/api/register/?ref={self.referral_code}"
    

      # Link will use the referral code
    def save(self, *args, **kwargs):
        """Override save to generate referral code and link if not already set."""
        if not self.referral_code:
            self.referral_code = self.generate_referral_code()
        

        if not self.referral_link:
            self.referral_link = self.generate_referral_link() 
        
        super().save(*args, **kwargs)  


class UserDiscount(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='discounts')
    percent = models.DecimalField(max_digits=5, decimal_places=2)  # e.g., 50.00 for 50%
    reason = models.CharField(max_length=64, blank=True, null=True)  # e.g., 'referral'
    used = models.BooleanField(default=False)
    granted_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.user_profile.user.username}: {self.percent}% ({'used' if self.used else 'unused'})"
    

class PendingRegistration(models.Model):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150)
    raw_password = models.CharField(max_length=128, blank=True, null=True)  # ✅ Add this
    password = models.CharField(max_length=128)
    otp = models.CharField(max_length=6)
    expires_at = models.DateTimeField()
    referral_code = models.CharField(max_length=20, blank=True, null=True)
    referral_link = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.expires_at
