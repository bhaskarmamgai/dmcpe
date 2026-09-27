from bms.models import BookingDocument
from django.contrib import admin
from django.utils.safestring import mark_safe


class BookingDocumentInline(admin.TabularInline):
    model = BookingDocument
    fields = ['name', 'delivery_date', 'file', 'create_new', 'booking_document_link', 'category', 'status',
              'document_type', 'created_by', 'created_at']
    readonly_fields = ('booking_document_link', 'create_new', 'created_by', 'created_at')
    autocomplete_fields = ['booking']

    def booking_document_link(self, instance):
        if instance:
            return mark_safe(
                "<a href='{}'>Link</a>".format(instance.file.name)) if instance.file.name else 'NA'

    def create_new(self, instance):
        if instance.file:
            return 'NA'
        return mark_safe(
            '<a href="/bms/booking/{}/booking_document/create_manually{}">Create New</a>'.format(
                 instance.booking_id, '?document_id={}'.format(instance.id) if instance.id else ''))
