from django.db import models
from common.models import BaseModel

class BookingType(BaseModel):
    name = models.CharField(max_length=30, unique=True, blank=False, null=False)
    description = models.CharField(max_length=2048, blank=True, null=True)
    deleted = models.BooleanField(default=False)
    enabled = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Types"