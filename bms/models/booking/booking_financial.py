from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from auditlog.registry import auditlog
from bms.models.booking.booking import Booking
from common.models import BaseModel




class BookingFinancial(BaseModel):
    booking = models.OneToOneField(Booking, on_delete=models.PROTECT, related_name="booking_financial")
    total_net_payable = models.FloatField(validators=[MaxValueValidator(1000000), MinValueValidator(0)],
                                          verbose_name="Total Net Payable (Collection Currency)", default=0)
    total_net_receivable = models.FloatField(validators=[MaxValueValidator(1000000), MinValueValidator(0)],
                                             verbose_name="Total Net Receivable (Collection Currency)", default=0)
    total_cost_price = models.FloatField(validators=[MaxValueValidator(1000000), MinValueValidator(0)],
                                         verbose_name="Total Cost Price (Collection Currency)", default=0)
    approved_discount = models.FloatField(validators=[MaxValueValidator(1000000), MinValueValidator(0)],
                                          verbose_name="Total Approved Discount (Collection Currency)", default=0)
    tcs = models.FloatField(verbose_name="Total TCS (Collection Currency)", default=0)
    gross_profit = models.FloatField(validators=[MaxValueValidator(100000), MinValueValidator(0)],
                                     verbose_name="Gross Profit (Collection Currency)", default=0)
    net_profit = models.FloatField(validators=[MaxValueValidator(100000), MinValueValidator(0)],
                                   verbose_name="Net Profit (Collection Currency)", default=0)
    total_seller_service_charge = models.FloatField(validators=[MaxValueValidator(100000), MinValueValidator(0)],
                                                    verbose_name="Total Seller Service Charges (Collection Currency)",
                                                    default=0)
    total_tax_on_seller_service_charge = models.FloatField(validators=[MaxValueValidator(100000), MinValueValidator(0)],
                                                           verbose_name="Total Tax On Seller Service Charges (Collection Currency)",
                                                           default=0)
    total_commission_received = models.FloatField(verbose_name="Total Commission Received (Collection Currency)",
                                                  default=0, null=True)
    total_tds = models.FloatField(verbose_name="Total TDS (Collection Currency)", default=0, null=True)

    def __str__(self):
        return "{}/{}/{}".format(str(self.booking), str(self.gross_profit), str(self.net_profit))

    class Meta:
        verbose_name_plural = "Booking Financials (Summary)"



auditlog.register(BookingFinancial)
