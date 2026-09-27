from django.db import models
from auditlog.registry import auditlog
from dmcpesys.enums import TripType
from dmcpesys.models import Airport, Airline
from bms.models.booking.booking import Booking
from common.models import BaseModel

class FlightDetail(BaseModel):
    booking = models.OneToOneField(Booking, on_delete=models.PROTECT, related_name="flight_detail")
    from_airport = models.ForeignKey(Airport, on_delete=models.PROTECT, related_name="from_airport",
                                     verbose_name="From Airport")
    to_airport = models.ForeignKey(Airport, on_delete=models.PROTECT, related_name="to_airport",
                                   verbose_name="To Airport")
    airline = models.ForeignKey(Airline, on_delete=models.PROTECT, verbose_name="Airline")
    trip_type = models.CharField(max_length=255, choices=TripType.choices())
    airline_code = models.CharField(max_length=255, verbose_name="Airline Code")
    flight_number = models.CharField(max_length=255, verbose_name="Flight Number")

    def __str__(self):
        return "{}/{}/{}".format(str(self.booking), str(self.from_airport), str(self.to_airport))

    class Meta:
        verbose_name_plural = "Flight Details"


auditlog.register(FlightDetail)
