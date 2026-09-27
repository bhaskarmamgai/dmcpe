from django.db import models
from common.models import BaseModel

class SellerStatus(BaseModel):
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return '{}'.format(self.name)

    class Meta:
        verbose_name_plural = "Seller Const Component Status's"
