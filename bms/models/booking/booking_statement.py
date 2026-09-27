from django.db import models
from auditlog.registry import auditlog
from members.models import Organization
from members.models import Member
from common.models import BaseModel

class BookingStatement(BaseModel):
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT,related_name="booking_statements")
    request_from_member = models.ForeignKey(Member, on_delete=models.PROTECT, related_name="member_booking_statements")
    document_url = models.URLField(null=True)
    start_date = models.DateField(verbose_name = "Start Date")
    end_date = models.DateField(verbose_name = "End Date")

    class Meta:
        verbose_name_plural = "Booking Statements"

auditlog.register(BookingStatement)
