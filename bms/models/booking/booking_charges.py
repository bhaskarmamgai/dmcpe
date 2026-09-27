from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from auditlog.registry import auditlog
from bms.models.booking.booking import Booking
from common.models import BaseModel

class BookingCharges(BaseModel):
    booking = models.OneToOneField(Booking, related_name="booking_charges", on_delete=models.PROTECT)
    roe_on_booking_date = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(10000000)], default=1,
                                            verbose_name="xe.com RoE on Booking Date")

    service_charge_collected_from_buyer = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(10000000)],
        verbose_name="Bank Charges in Booking Currency", default=0)
    convenience_charges_on_roe = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(5)], default=0,
                                                   verbose_name="Convenience Charges On RoE")
    booking_loss = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(10000000)],
                                     default=0, verbose_name="Booking Loss",null=True,blank=True)

    class Meta:
        verbose_name_plural = "Booking Charges"


auditlog.register(BookingCharges)
