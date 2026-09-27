import nested_admin
from django.contrib import admin
from django.db.models import OuterRef, Subquery
from common.admin import OrganizationFilter, MemberSourceFilter, MemberBuyingPotentialFilter, \
    AccountManagerAutocompleteFilter, CreatedAtFilter, UpdatedAtFilter, NextFollowupFilter, \
    OrganizationKYCStatusFilterForMember, AuditAdminMixin, OrganizationKYCStatusFilterForOrganization
from .models import (
    Organization,
    Member,
    OrganizationAddress,
    BusinessDetails,
    OrganizationKYC,
    BusinessDocument,
    MemberActivityLog,
    Action,
    Campaign,
    MemberSource,
    DocumentPage,
    MemberBuyingPotential,
    BankAccount
)
from wallets.admin import WalletInline


@admin.register(MemberBuyingPotential)
class MemberBuyingPotentialAdmin(admin.ModelAdmin):
    search_fields = ("name", "internal_name")
    list_display = ("id", "name", "internal_name", "is_active")
    list_filter = ("is_active",)
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')


class MemberBuyingPotentialInline(admin.TabularInline):
    model = MemberBuyingPotential
    extra = 1
    fields = (
        'name',
        'internal_name',
        'description',
    )
    show_change_link = True


class BankAccountInline(admin.TabularInline):
    model = BankAccount
    extra = 1
    show_change_link = True


@admin.register(MemberSource)
class MemberSourceAdmin(admin.ModelAdmin):
    search_fields = ("name", "internal_name")
    list_display = ("id", "name", "internal_name", "is_active")
    list_filter = ("is_active",)


@admin.register(Action)
class ActionAdmin(admin.ModelAdmin):
    search_fields = ("name", "internal_name",)
    list_display = ("name", "internal_name", "is_active")
    list_filter = ("is_active",)


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    search_fields = ("name", "internal_name")
    list_display = ("name", "internal_name", "is_active")
    list_filter = ("is_active",)


class MemberActivityLogInline(admin.TabularInline):
    model = MemberActivityLog
    extra = 1
    fields = (
        "campaign",
        "action",
        "remarks",
        "next_followup_at",
        'created_at',
        'updated_at',
        'created_by',
        'updated_by'
    )
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    autocomplete_fields = ("action", "campaign")
    show_change_link = True


class DocumentPageInline(nested_admin.NestedTabularInline):
    model = DocumentPage
    extra = 0
    fields = (
        "page_type",
        "page_number",
        "page_start",
        "page_end",
        "file",
        "is_verified",
        "verified_at",
        "remarks",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    )

    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')


class BusinessDocumentInline(nested_admin.NestedTabularInline):
    model = BusinessDocument
    extra = 1
    fields = (
        'category',
        'document_type',
        'document_number',
        'is_verified',
        'created_at',
        'updated_at',
        'created_by',
        'updated_by',
    )
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    inlines = [DocumentPageInline]


class OrganizationAddressInline(admin.TabularInline):
    model = OrganizationAddress
    extra = 1
    fields = (
        'address_line1',
        'address_line2',
        'state',
        'country',
        'pincode',
        'spoc_email',
        'spoc_phone',
    )
    autocomplete_fields = ('state', 'country')
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')


class BusinessDetailsInline(admin.TabularInline):
    model = BusinessDetails
    extra = 0
    max_num = 1
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')


class OrganizationKYCInline(admin.TabularInline):
    model = OrganizationKYC
    extra = 0
    max_num = 1
    autocomplete_fields = ('reviewer',)
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')


class MemberInline(admin.TabularInline):
    model = Member
    extra = 0
    fields = (
        'user',
        'email',
        'phone',
        'is_owner',
        'created_at',
        'updated_at',
        'created_by',
        'updated_by'
    )
    autocomplete_fields = ('user',)
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    show_change_link = True


@admin.register(Organization)
class OrganizationAdmin(AuditAdminMixin, nested_admin.NestedModelAdmin):
    list_display = (
        'id',
        'code',
        'name',
        'website',
        'marketing_email',
        'marketing_phone',
        'kyc_status',
        'is_active',
        'created_at',
        'updated_at',
    )
    fieldsets = (
        (None, {
            "fields": (
                "code",
                "name",
                "website",
                "marketing_email",
                "marketing_phone",
                "company_logo",
                "is_active",
                "is_deleted",
                "created_at",
                "updated_at",
                "created_by",
                "updated_by"
            )
        }),
    )
    search_fields = (
        'name',
        'website',
        'marketing_email',
    )
    list_filter = (OrganizationKYCStatusFilterForOrganization, 'is_active', 'created_at', 'updated_at',)
    readonly_fields = (
        'code',
        'created_at',
        'updated_at',
        'created_by',
        'updated_by',
        'kyc_status'
    )
    inlines = (
        WalletInline,
        MemberInline,
        BusinessDetailsInline,
        OrganizationAddressInline,
        OrganizationKYCInline,
        BusinessDocumentInline,
        BankAccountInline
    )
    list_per_page = 25

    def kyc_status(self, obj):
        return obj.kyc_status


@admin.register(Member)
class MemberAdmin(AuditAdminMixin, nested_admin.NestedModelAdmin):
    list_per_page = 25
    list_select_related = ('organization', 'account_manager', 'user', 'organization__kyc_profile')
    list_display = (
        'id',
        'code',
        'organization',
        'is_owner',
        'account_manager',
        'kyc_status',
        'last_remark',
        'is_active',
        'created_at',
        'updated_at',
        'created_by',
        'updated_by'
    )
    search_fields = (
        'organization__name',
        'email',
        'phone',
        'organization__name',
    )
    list_filter = (
        OrganizationFilter,
        MemberSourceFilter,
        MemberBuyingPotentialFilter,
        AccountManagerAutocompleteFilter,
        NextFollowupFilter,
        OrganizationKYCStatusFilterForMember,
        'is_owner',
        'is_active',
        CreatedAtFilter,
        UpdatedAtFilter,
    )
    autocomplete_fields = ['organization']
    readonly_fields = (
        'code',
        'user',
        'created_at',
        'updated_at',
        'created_by',
        'updated_by',
    )
    inlines = (
        MemberActivityLogInline,
    )

    fieldsets = (
        ("Basic Information", {
            "fields": (
                "code",
                "user",
                "organization",
                "account_manager",
                "is_owner",
            )
        }),
        ("Contact Details", {
            "fields": (
                "email",
                ("phone_country_code",
                 "phone"),
                "phone2",
            )
        }),
        ("Other Details", {
            "fields": (
                "buying_potential",
                "source",
                "is_active",
            )
        }),
        ("Audit Info", {
            "fields": (
                "created_at",
                "updated_at",
                "created_by",
                "updated_by",
            )
        }),
    )

    def kyc_status(self, obj):
        if obj and obj.organization:
            return obj.organization.kyc_status
        return "NA"

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        last_remark_subquery = MemberActivityLog.objects.filter(
            member=OuterRef('pk')
        ).order_by('-created_at').values('remarks')[:1]
        queryset = queryset.annotate(last_remark_annotated=Subquery(last_remark_subquery))
        return queryset

    @admin.display(description="Last Remark", ordering="last_remark_annotated")
    def last_remark(self, obj):
        return obj.last_remark_annotated or "-"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        from users.models import User
        if db_field.name == "account_manager":
            kwargs["queryset"] = User.objects.exclude(role='member')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(OrganizationAddress)
class OrganizationAddressAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'organization',
        'state',
        'country',
        'pincode',
        'spoc_email',
        'spoc_phone',
        'is_active',
        'created_at',
        'updated_at',
    )
    search_fields = (
        'organization__name',
        'pincode',
        'spoc_email',
    )
    list_filter = (
        'country',
        'state',
        'organization',
        'created_at',
    )
    ordering = ('organization', 'state', 'pincode')
    autocomplete_fields = ('organization', 'state', 'country')
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')


@admin.register(OrganizationKYC)
class OrganizationKYCAdmin(admin.ModelAdmin):
    list_display = (
        'organization',
        'status',
        'is_compliant',
        'kyc_completed_at',
        'kyc_expires_at',
        'is_active',
        'created_at',
        'updated_at',
    )
    list_filter = ('status', 'is_compliant')
    search_fields = ('organization__name',)
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')


@admin.register(BusinessDocument)
class BusinessDocumentAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'category',
        'document_type',
        'is_verified',
        'is_active',
        'created_at',
        'updated_at',
    )
    list_filter = (
        'category',
        'document_type',
        'is_verified',
    )
    search_fields = ('document_number',)
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    inlines = (DocumentPageInline,)
