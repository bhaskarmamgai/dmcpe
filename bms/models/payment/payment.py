from django.db import models
from bms.models.booking.booking import Booking
from common.models import BaseModel


class PaymentLogs(BaseModel):
    booking = models.ForeignKey(Booking, on_delete=models.PROTECT, null=True)
    payload = models.TextField()
    response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "{} {}".format(self.booking, self.created_at)

    class Meta:
        verbose_name = "Booking Payment Log"
