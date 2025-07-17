from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, UserProfile, UserDiscount

# Custom filter for SuperUsers
class SuperUserFilter(admin.SimpleListFilter):
    title = 'User Type'
    parameter_name = 'is_superuser'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Superusers'),
            ('no', 'Regular Users'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(is_superuser=True)
        elif self.value() == 'no':
            return queryset.filter(is_superuser=False)
        return queryset


# Custom UserAdmin for managing CustomUser in Admin
class CustomUserAdmin(UserAdmin):
    list_display = ['email', 'username', 'is_superuser']
    list_filter = ['is_superuser', SuperUserFilter]
    search_fields = ['email', 'username']
    ordering = ['email']
    fieldsets = (
        (None, {'fields': ('email', 'username', 'password','role')}),
        ('Permissions', {'fields': ('is_superuser', 'is_staff', 'is_active')}),
    )
    add_fieldsets = (
        (None, {
            'fields': ('email', 'username', 'password1', 'password2'),
        }),
    )

# Register the CustomUser model with the admin panel
admin.site.register(CustomUser, CustomUserAdmin)

#discount
class UserDiscountInline(admin.TabularInline):
    model = UserDiscount
    extra = 0  # Don’t show empty extra forms by default
    readonly_fields = ('percent', 'reason', 'used', 'granted_at', 'used_at')
    can_delete = False

# UserProfileAdmin for managing UserProfile in Admin
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'referral_code', 'referral_link', 'referred_by', 'gender', 'country', 'is_fully_filled']
    list_filter = ['gender', 'country']
    search_fields = ['user__email', 'user__username']

    def referral_code(self, obj):
        """Return the referral code of the user"""
        return obj.referral_code

    def referral_link(self, obj):
        """Return the referral link of the user"""
        return obj.referral_link
    inlines = [UserDiscountInline]


@admin.register(UserDiscount)
class UserDiscountAdmin(admin.ModelAdmin):
    list_display = ['username', 'percent', 'reason', 'used', 'granted_at', 'used_at']
    list_filter = ['used']
    search_fields = ['user_profile__user__email', 'user_profile__user__username', 'reason']

    def username(self, obj):
        """Return the username of the user associated with the discount"""
        return obj.user_profile.user.username
    username.short_description = "User"

