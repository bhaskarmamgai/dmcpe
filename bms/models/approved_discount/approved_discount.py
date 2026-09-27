from django.db import models
from auditlog.registry import auditlog
from common.models import BaseModel

class DiscountType(BaseModel):
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return '{}'.format(self.name)

    class Meta:
        verbose_name_plural = "Discount Type"


class ApprovedDiscount(BaseModel):
    discount_type = models.ForeignKey('bms.DiscountType', on_delete=models.PROTECT, null=True)
    collection_currency = models.ForeignKey('dmcpesys.Currency', on_delete=models.PROTECT, null=True,
                                            verbose_name='Collection Currency')
    amount = models.FloatField(default=0, verbose_name='Amount (Collection Currency)')
    booking = models.ForeignKey('bms.Booking', related_name="approved_discounts", on_delete=models.PROTECT,
                                null=True)
    remark = models.TextField(null=True, blank=False, verbose_name="Remarks")
    attachment = models.FileField(blank=False, null=True, max_length=255)

    class Meta:
        verbose_name = "Approved Discount"


auditlog.register(ApprovedDiscount, include_fields=["amount"])
