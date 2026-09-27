from django.conf import settings
from django.db import models
from auditlog.registry import auditlog
from common.models import BaseModel

class BookingInvoiceConfig(BaseModel):
    next_sequence = models.IntegerField()
    invoice_type = models.CharField(max_length=10, choices=settings.INVOICE_TYPE)
    booking_type = models.CharField(max_length=10, choices=settings.BOOKING_TYPE, null=True)
    financial_year = models.CharField(max_length=10, choices=settings.FINANCIAL_YEARS)
    company_initial = models.CharField(max_length=10, choices=settings.COMPANY_INITIALS)

    def __str__(self):
        return "{}/{}/{}/{}/{}".format(str(self.invoice_type), str(self.booking_type), str(self.financial_year), str(
            self.company_initial), str(self.next_sequence))

    class Meta:
        verbose_name_plural = "Booking Invoice Config"


auditlog.register(BookingInvoiceConfig)
