from django.db import models
from auditlog.registry import auditlog
from bms.enums import BOOKING_STATUS_CHOICES
from bms.models.booking import Booking
from common.models import BaseModel

class BookingStatusHistory(BaseModel):

    booking = models.ForeignKey(Booking, related_name="booking_status_history", on_delete=models.PROTECT)
    status = models.CharField(max_length=50, choices=BOOKING_STATUS_CHOICES, null=False)

    def __str__(self):
        return "{}-{}".format(str(self.booking), self.status)

    class Meta:
        verbose_name_plural = "Booking Status History"

auditlog.register(BookingStatusHistory)