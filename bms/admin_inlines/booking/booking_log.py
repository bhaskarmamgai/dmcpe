from django.contrib import admin

from bms.models import BookingLog


class BookingLogInline(admin.TabularInline):
    model = BookingLog

    list_display = [field.name for field in BookingLog._meta.get_fields()]

    def has_delete_permission(self, request, obj=None):
        return False



    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]


class BookingLogViewOnlyInline( BookingLogInline):
    pass
