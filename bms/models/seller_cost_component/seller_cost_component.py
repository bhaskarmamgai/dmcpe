from auditlog.registry import auditlog
from django.db import models
from common.models import BaseModel

class SellerCostComponent(BaseModel):
    serial_number = models.CharField(max_length=255, null=True, blank=True)
    seller_member = models.ForeignKey('members.Member', on_delete=models.PROTECT, null=True)
    seller_organization = models.ForeignKey('members.Organization', on_delete=models.PROTECT, null=True)
    component = models.CharField(max_length=500, null=True, blank=True)
    booking = models.ForeignKey('bms.Booking', related_name="booking_seller_cost_components",
                                on_delete=models.PROTECT, null=True)
    categories = models.ManyToManyField('dmcpesys.Category', related_name='categories_seller_cost_components')
    seller_status = models.ForeignKey('bms.SellerStatus', verbose_name="Seller Status",
                                      on_delete=models.PROTECT, null=True)
    sce = models.ForeignKey('dmcpesys.TravelSupplyGroupEntities', on_delete=models.PROTECT, null=True,
                            related_name="seller_contracting_entity")
    seller_booking_code = models.CharField(max_length=255, null=True, blank=True,
                                           verbose_name="Seller Booking Code / PNR Number")
    seller_reference_number = models.CharField(max_length=150, null=True, blank=True,
                                               verbose_name="Seller Reference Number / Trace Id")
    seller_invoice_code = models.CharField(max_length=250, null=True, blank=True,
                                           verbose_name="Seller Invoice Code")
    seller_currency = models.ForeignKey('dmcpesys.Currency', on_delete=models.PROTECT, null=True, default=1)
    cost_in_seller_currency = models.FloatField(default=0, verbose_name="Cost in Seller Currency")
    tax = models.FloatField(default=0, verbose_name="Tax on Seller Service Charge")
    seller_service_charge = models.FloatField(default=0, verbose_name="Seller Service Charge")
    commission_received = models.FloatField(default=0)
    tds = models.FloatField(default=0, verbose_name="TDS")
    tcs = models.FloatField(default=0, verbose_name="TCS (Collection Currency)")
    seller_net_payable_in_seller_currency = models.FloatField(null=True,
                                                              verbose_name="Net Payable to Seller (Seller Currency)")
    seller_net_payable_in_collection_currency = models.FloatField(null=True,
                                                                  verbose_name="Net Payable to Seller (Collection Currency)")
    component_markup = models.FloatField(null=True, default=0, verbose_name="Component Markup (Seller Currency)")
    seller_fx = models.FloatField(null=True, blank=True)
    seller_fx_markup = models.FloatField(null=True, blank=True)
    cost_in_collection_currency = models.FloatField(null=True, verbose_name="Cost in Collection Currency")
    seller_performa_invoice = models.FileField(blank=True, null=True, max_length=255,
                                               verbose_name="Seller Performa Invoice")

    class Meta:
        verbose_name = "Seller Cost Component"

    def __str__(self):
        return "{}".format(self.serial_number)


auditlog.register(SellerCostComponent, include_fields=["cost_in_seller_currency", "seller_service_charge", "tax",
                                                       "commission_received", "tcs", "tds", "seller_fx",
                                                       "seller_fx_markup"])
