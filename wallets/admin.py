from django.contrib import admin
from wallets.models import Wallet


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "code",
        "organization",
        "currency",
        "current_balance",
        "created_at",
        "updated_at",
        "is_active",
    )

    list_filter = (
        "currency",
        "is_active",
        "created_at",
        "updated_at",
    )

    search_fields = (
        "organization__name",
        "currency__code",
        "code",
    )

    readonly_fields = (
        "code",
        "current_balance",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    )

    autocomplete_fields = (
        "organization",
        "currency",
    )

    fieldsets = (
        (None, {
            "fields": (
                "organization",
                "currency",
                "current_balance",
            )
        }),
        ("Audit Info", {
            "fields": (
                "code",
                "is_active",
                "is_deleted",
                "created_at",
                "updated_at",
                "created_by",
                "updated_by",
            ),
            "classes": ("collapse",),
        }),
    )


class WalletInline(admin.TabularInline):
    model = Wallet
    extra = 0

    fields = (
        "code",
        "currency",
        "current_balance",
        "is_active",
    )

    readonly_fields = (
        "code",
        "current_balance",
    )

    autocomplete_fields = (
        "currency",
    )
