from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, UserProfile, UserEmailOTP


class UserProfileInline(admin.TabularInline):
    model = UserProfile
    extra = 1
    fk_name = 'user'
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')


@admin.register(User)
class UserAdmin(UserAdmin):
    model = User
    list_display = ('id', 'username', 'email', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active', 'is_superuser', 'groups', 'created_at', 'updated_at', 'created_by',
                   'updated_by')
    search_fields = ('username', 'email', 'role')
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    inlines = (UserProfileInline,)

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        # Filter for Account Manager lookups (specifically for Member admin)
        if request.GET.get('model_name') == 'member' and \
           request.GET.get('field_name') == 'account_manager':
            queryset = queryset.exclude(role='member')
        return queryset, use_distinct

    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Personal Info', {'fields': ('role',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'role', 'password1', 'password2', 'is_active', 'is_staff', 'is_superuser')}
         ),
    )


@admin.register(UserProfile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'first_name', 'last_name', 'phone', 'city', 'country')
    search_fields = ('user__username', 'first_name', 'last_name', 'phone', 'city', 'country')
    raw_id_fields = ('user',)
    list_filter = ('created_at', 'updated_at', 'created_by', 'updated_by')

    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')


@admin.register(UserEmailOTP)
class UserEmailOTPAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "email",
        "is_verified",
        "attempts",
        "expires_at",
        "is_expired",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by"
    )
    list_filter = ("is_verified", "expires_at")
    search_fields = ("email",)
    readonly_fields = ("otp_hash", "expires_at", "attempts", "is_verified")

    def is_expired(self, obj):
        return obj.is_expired

    is_expired.boolean = True
    is_expired.short_description = "Expired"
