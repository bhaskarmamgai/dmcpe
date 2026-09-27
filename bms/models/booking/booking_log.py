from django.db import models
from bms.models.booking.booking import Booking
from common.models import BaseModel

class BookingLog(BaseModel):
    booking = models.ForeignKey(Booking, related_name="booking_log", on_delete=models.PROTECT)
    column_name = models.CharField(max_length=50, blank=False, null=False)
    old_value = models.CharField(max_length=250, blank=True, null=True)
    new_value = models.CharField(max_length=250, blank=True, null=False)

    class Meta:
        verbose_name_plural = "Logs"


