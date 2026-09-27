from django.contrib import admin
from bms.models import BookingStatement
from django.utils.safestring import mark_safe


class BookingStatementAdmin(admin.ModelAdmin):
    model = BookingStatement
    list_display = ['get_organization', 'get_member_name', 'start_date', 'end_date', "created_at"]
    search_fields = ['organization__code', 'request_from_member']
    list_filter = ['start_date', 'end_date']
    list_per_page = 5

    def get_document_url(self, obj=None):
        return mark_safe("<a href='{}'>{}</a>".format(obj.document_url, obj.document_url)) if obj else 'NA'

    def get_member_name(self, obj):
        return obj.request_from_member if obj else '-'

    def get_organization(self, obj):
        return obj.organization.code if obj and obj.organization else '-'

    get_document_url.short_description = "Document Url"
    get_member_name.short_description = "Request From Member"
    get_organization.short_description = "Organization"



admin.site.register(BookingStatement, BookingStatementAdmin)
