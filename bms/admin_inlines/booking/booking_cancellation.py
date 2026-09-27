from django.contrib import admin
from django.utils.safestring import mark_safe
from bms.models import BookingCancellation, CancellationStatusHistory
from django.db import models
from django.forms import Textarea
from django.urls import reverse



class BookingCancellationInline(admin.TabularInline):
    model = BookingCancellation
    readonly_fields = ['created_by', 'get_proof_link']
    extra=0

    def get_proof_link(self, obj):
        return mark_safe("<a href='{}'>Link</a>".format(obj.get_proof_url())) if obj.proof else 'NA'

    def has_change_permission(self, request, obj=None):
        """
        The 'obj' parameter represents the parent object being edited in the inline.
        """
        if obj and obj and hasattr(obj, 'booking_details') and obj.booking_details.is_completed:
            return False
        return True

    def has_add_permission(self, request, obj=None):
        """
        The 'obj' parameter represents the parent object being edited in the inline.
        """
        if obj and  hasattr(obj, 'booking_details') and obj.booking_details.is_completed:
            return False
        return True

    verbose_name_plural = "Cancellation Details"



class CancellationStatusHistoryReadOnlyInline( admin.TabularInline):
    model = CancellationStatusHistory
    readonly_fields = ['service_request_status', 'remarks', 'updated_by', 'updated_at']
    verbose_name_plural = "Cancellation Status History"




