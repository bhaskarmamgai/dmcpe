from bms.models import BookingDocument
from django.contrib import admin
from django.utils.safestring import mark_safe


class BookingDocumentAdmin(admin.ModelAdmin):
    model = BookingDocument
    fields = ['booking', 'document_type', 'name', 'delivery_date', 'category', 'status', 'created_by', 'created_at']
    list_display = ['booking', 'document_type', 'name', 'delivery_date', 'category', 'status', 'created_by', 'created_at']
    search_fields = ['booking__code']
    list_filter = ['status', 'document_type']
    list_per_page = 5

    def document_link(self, instance):
        if instance and instance.file:
            return mark_safe(
                "<a href='{}'>Link</a>".format(instance.file.name)) if instance.file.name else 'NA'

admin.site.register(BookingDocument, BookingDocumentAdmin)