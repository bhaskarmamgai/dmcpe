from admin_auto_filters.filters import AutocompleteFilter
from datetime import timedelta
from django.contrib.admin import SimpleListFilter
from django.utils import timezone
from django.contrib import admin
from django.utils import timezone


class ExtendedDateFilter(SimpleListFilter):
    title = "Date"
    parameter_name = "date_range"
    field_path = None  # set in subclass

    def lookups(self, request, model_admin):
        return (
            ("today", "Today"),
            ("past_7_days", "Past 7 days"),
            ("past_45_days", "Past 45 days"),
            ("this_month", "This month"),
            ("this_quarter", "This quarter"),
            ("past_6_months", "Past 6 months"),
            ("this_year", "This year"),
        )

    def queryset(self, request, queryset):
        if not self.value():
            return queryset

        now = timezone.now()
        field = self.field_path

        if self.value() == "today":
            return queryset.filter(**{f"{field}__date": now.date()})

        if self.value() == "past_7_days":
            return queryset.filter(**{f"{field}__gte": now - timedelta(days=7)})

        if self.value() == "past_45_days":
            return queryset.filter(**{f"{field}__gte": now - timedelta(days=45)})

        if self.value() == "this_month":
            return queryset.filter(
                **{
                    f"{field}__year": now.year,
                    f"{field}__month": now.month,
                }
            )

        if self.value() == "this_quarter":
            quarter = (now.month - 1) // 3 + 1
            start_month = 3 * (quarter - 1) + 1
            start_date = now.replace(
                month=start_month, day=1, hour=0, minute=0, second=0
            )
            return queryset.filter(**{f"{field}__gte": start_date})

        if self.value() == "past_6_months":
            return queryset.filter(**{f"{field}__gte": now - timedelta(days=182)})

        if self.value() == "this_year":
            return queryset.filter(**{f"{field}__year": now.year})

        return queryset


class MemberFilter(AutocompleteFilter):
    title = "Member"
    field_name = "member"


class OrganizationFilter(AutocompleteFilter):
    title = "Organization"
    field_name = "organization"


class RequirementStatusFilter(AutocompleteFilter):
    title = "Status"
    field_name = "status"


class DestinationFilter(AutocompleteFilter):
    title = "Destination"
    field_name = "destination"


class AreaFilter(AutocompleteFilter):
    title = "Area"
    field_name = "areas"


class MemberSourceFilter(AutocompleteFilter):
    title = "Member Source"
    field_name = "source"


class MemberBuyingPotentialFilter(AutocompleteFilter):
    title = "Member Buying Potential"
    field_name = "buying_potential"


class AccountManagerAutocompleteFilter(AutocompleteFilter):
    title = "Account Manager"
    field_name = "account_manager"


class CreatedAtFilter(ExtendedDateFilter):
    title = "Created At"
    parameter_name = "created_at_range"
    field_path = "created_at"


class UpdatedAtFilter(ExtendedDateFilter):
    title = "Last Updated At"
    parameter_name = "updated_at_range"
    field_path = "updated_at"


class MemberAccountManagerFilter(SimpleListFilter):
    title = "Account Manager"
    parameter_name = "account_manager"

    def lookups(self, request, model_admin):
        from users.models import User
        qs = User.objects.exclude(role="member")
        return [(u.id, u.get_full_name() or u.username) for u in qs]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(account_manager_id=self.value())
        return queryset


class NextFollowupFilter(admin.SimpleListFilter):
    title = "Next Follow-up"
    parameter_name = "next_followup"

    def lookups(self, request, model_admin):
        return (
            ("today", "Today"),
            ("tomorrow", "Tomorrow"),
            ("upcoming", "Upcoming"),
            ("overdue", "Overdue"),
            ("none", "No Follow-up"),
        )

    def queryset(self, request, queryset):
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        tomorrow_end = today_end + timedelta(days=1)

        if self.value() == "today":
            return queryset.filter(
                activity_logs__next_followup_at__range=(today_start, today_end)
            ).distinct()

        if self.value() == "tomorrow":
            return queryset.filter(
                activity_logs__next_followup_at__range=(today_end, tomorrow_end)
            ).distinct()

        if self.value() == "upcoming":
            return queryset.filter(
                activity_logs__next_followup_at__gt=now
            ).distinct()

        if self.value() == "overdue":
            return queryset.filter(
                activity_logs__next_followup_at__lt=now
            ).distinct()

        if self.value() == "none":
            return queryset.exclude(
                activity_logs__next_followup_at__isnull=False
            )

        return queryset


class OrganizationKYCStatusFilterForMember(admin.SimpleListFilter):
    title = "Organization KYC Status"
    parameter_name = "org_kyc_status"

    def lookups(self, request, model_admin):
        from members.models import KYCStatus
        return KYCStatus.choices

    def queryset(self, request, queryset):
        value = self.value()

        if value == "NA":
            return queryset.filter(
                organization__kyc_profile__isnull=True
            )

        if value:
            return queryset.filter(
                organization__kyc_profile__status=value
            )

        return queryset


class AuditAdminMixin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        if obj.pk is None and hasattr(obj, "created_by"):
            obj.created_by = request.user
        if hasattr(obj, "updated_by"):
            obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in instances:
            if obj.pk is None and hasattr(obj, "created_by"):
                obj.created_by = request.user
            if hasattr(obj, "updated_by"):
                obj.updated_by = request.user
            obj.save()
        for obj in formset.deleted_objects:
            obj.delete()

        formset.save_m2m()

class OrganizationKYCStatusFilterForOrganization(admin.SimpleListFilter):
    title = "Organization KYC Status"
    parameter_name = "org_kyc_status"

    def lookups(self, request, model_admin):
        from members.models import KYCStatus
        return KYCStatus.choices

    def queryset(self, request, queryset):
        value = self.value()

        if value == "NA":
            return queryset.filter(
                kyc_profile__isnull=True
            )

        if value:
            return queryset.filter(
                kyc_profile__status=value
            )

        return queryset

class RequirementAccountManagerFilter(SimpleListFilter):
    title = "Account Manager"
    parameter_name = "account_manager"

    def lookups(self, request, model_admin):
        from users.models import User
        qs = User.objects.exclude(role="member")
        return [(u.id, u.get_full_name() or u.username) for u in qs]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(member__account_manager_id=self.value())
        return queryset
