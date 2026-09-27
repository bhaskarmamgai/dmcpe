from django.db import models
from common.models import BaseModel

class BookingLoss(BaseModel):
    currency = models.ForeignKey('dmcpesys.Currency', on_delete=models.PROTECT, null=True,
                                 verbose_name='Currency')
    amount = models.FloatField(default=0, verbose_name='Loss (Collection Currency)')
    booking = models.ForeignKey('bms.Booking', related_name="booking_losses", on_delete=models.PROTECT,
                                null=True)
    remark = models.CharField(max_length=200, verbose_name="Remarks")

    class Meta:
        verbose_name = "Booking Losses"
