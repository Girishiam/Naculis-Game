from django.contrib.auth.models import AbstractUser
from django.db import models
from django_countries.fields import CountryField
import uuid


class CustomUser(AbstractUser):
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
    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='N')
    country = CountryField(blank_label='Select Country', null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    xp = models.IntegerField(default=5)
    daily_streak = models.IntegerField(default=0)
    star = models.IntegerField(default=0)
    gem = models.IntegerField(default=0)
    phone = models.CharField(max_length=15, blank=True, null=True)
    referral_code = models.CharField(max_length=20, unique=True, blank=True, null=True)
    referral_link = models.URLField(max_length=200, blank=True, null=True)
    referred_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals')
    discount_used = models.BooleanField(default=False)  # Track if discount has been used
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
            self.referral_code = self.generate_referral_code()  # Generate referral code if not set
        
        # Ensure referral link is based on the same referral code
        if not self.referral_link:
            self.referral_link = self.generate_referral_link()  # Generate referral link
        
        super().save(*args, **kwargs)  # Save to the database