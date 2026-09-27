from django.db import models
from common.models import BaseModel, CodeMixin
from django.core.validators import MinValueValidator, MaxValueValidator
from .models_manager import StatsDailyManager

class Country(CodeMixin, BaseModel):
    name = models.CharField(max_length=100, unique=True)
    iso_code = models.CharField(max_length=10, unique=True, null=True, blank=True)

    CLASS_PREFIX = 'CO'  # Short prefix for country

    class Meta:
        verbose_name = "Country"
        verbose_name_plural = "Countries"

    def __str__(self):
        return f"{self.code}-{self.name}-{self.iso_code}"


class Currency(CodeMixin, BaseModel):
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=100, unique=True)

    CLASS_PREFIX = 'CUR'

    class Meta:
        verbose_name = "Currency"
        verbose_name_plural = "Currency's"

    def __str__(self):
        return f"{self.code}-{self.name}-{self.symbol}"


class State(CodeMixin, BaseModel):
    name = models.CharField(max_length=100)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='states')

    CLASS_PREFIX = 'ST'

    class Meta:
        verbose_name = "State"
        verbose_name_plural = "States"
        unique_together = ('name', 'country')

    def __str__(self):
        return f"{self.name} ({self.country})"


class Destination(CodeMixin, BaseModel):
    name = models.CharField(max_length=150)
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='destinations', null=True, blank=True)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='destinations', null=True, blank=True)

    CLASS_PREFIX = 'DE'

    class Meta:
        verbose_name = "Destination"
        verbose_name_plural = "Destinations"

    def __str__(self):
        return f"{self.name}"


class Area(CodeMixin, BaseModel):
    name = models.CharField(max_length=150)
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE, related_name='areas')
    is_default = models.BooleanField(
        default=False,
        help_text="Marks this area as the default or representative area for the destination."
    )

    CLASS_PREFIX = 'AR'

    class Meta:
        verbose_name = "Area"
        verbose_name_plural = "Areas"
        unique_together = ('name', 'destination')

    def __str__(self):
        return f"{self.code}-{self.name}-{self.destination}"


# Unified Location model for geo points or polygons
"""
Country: Indonesia
    └─ Destination: Bali
          └─ Area: Utta Kubud
                └─ LocationMaster: (specific geo coordinates around Utta Kubud)
"""


class LocationMaster(CodeMixin, BaseModel):
    LOCATION_TYPE_CHOICES = [
        ('POINT', 'Point'),
        ('POLYGON', 'Polygon'),
        ('MULTIPOLYGON', 'MultiPolygon'),
    ]

    # Location category for better classification
    LOCATION_CATEGORY_CHOICES = [
        ('airport', 'Airport'),
        ('hotel_area', 'Hotel Area'),
        ('areas', 'Area'),
        ('state', 'State'),
        ('attraction', 'Attraction'),
        ('beach', 'Beach'),
        ('temple', 'Temple'),
        ('city_center', 'City Center'),
        ('port', 'Port/Harbor'),
        ('island', 'Island'),  # For ferries
        ('mainland', 'Mainland'),  # For ferries
        ('station', 'Train/Bus Station'),
        ('landmark', 'Landmark'),
        ('district', 'District/Area'),
    ]

    name = models.CharField(max_length=150)

    location_type = models.CharField(
        max_length=12,
        choices=LOCATION_TYPE_CHOICES,
        help_text="Geometric representation type"
    )

    location_category = models.CharField(
        max_length=50,
        choices=LOCATION_CATEGORY_CHOICES,
        null=True,
        blank=True,
        help_text="Functional category of the location"
    )

    # Geometry fields
    # point = geomodels.PointField(null=True, blank=True)
    # polygon = geomodels.PolygonField(null=True, blank=True)
    # multipolygon = geomodels.MultiPolygonField(null=True, blank=True)

    # geom = geomodels.GeometryField(null=True, blank=True)
    # Optional hierarchical reference
    country = models.ForeignKey(
        Country,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    state = models.ForeignKey(
        State,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    destination = models.ForeignKey(
        Destination,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    area = models.ForeignKey(
        'Area',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # Island-specific fields
    is_island = models.BooleanField(
        default=False,
        help_text="Mark as True if this location is an island"
    )
    mainland_connection = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='connected_islands',
        help_text="Reference to mainland or main island this connects to"
    )

    CLASS_PREFIX = 'LC'

    class Meta:
        verbose_name = "Location"
        verbose_name_plural = "Locations"

    def __str__(self):
        return f"{self.name} ({self.location_category})"


class Bank(BaseModel):
    name = models.CharField(max_length=300, null=True, blank=True, verbose_name="Bank Name")

    def __str__(self):
        return self.name


class Service(BaseModel):
    name = models.CharField(max_length=50, null=False, blank=False)
    description = models.CharField(max_length=500, null=True, blank=True)

    def __str__(self):
        return self.name


class Category(BaseModel):
    name = models.CharField(max_length=255, unique=True, blank=False, null=False)
    description = models.CharField(max_length=500, null=True, blank=True)

    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["id"]


class Inclusion(BaseModel):
    name = models.CharField(max_length=255, unique=True, blank=False, null=False)
    deleted = models.BooleanField(default=False)
    enabled_icon = models.URLField(max_length=255, null=True, blank=True)
    disable_icon = models.URLField(max_length=255, null=True, blank=True)

    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        verbose_name_plural = "Inclusions"
        ordering = ["id"]


class StatsDaily(BaseModel):
    date = models.DateField(unique=True, blank=False, null=False)
    requirements_status_update_count = models.IntegerField(blank=True, null=True, default=0)
    requirements_match_count = models.IntegerField(blank=True, null=True, default=0)

    objects = StatsDailyManager()

    class Meta:
        verbose_name_plural = "Stats - Daily"


class Airport(BaseModel):
    name = models.CharField(max_length=255, unique=True, blank=False, null=False)
    code = models.CharField(max_length=255, unique=True, blank=False, null=False)
    city = models.ForeignKey(LocationMaster, on_delete=models.PROTECT, null=False)

    def __str__(self):
        return "({})-{}-{}".format(self.code, self.name, self.city.name)


class Airline(BaseModel):
    name = models.CharField(max_length=255, unique=True, blank=False, null=False)

    def __str__(self):
        return self.name


class TravelSupplyConfiguration(BaseModel):
    environment_choices = (
        ('PROD', 'PROD'),
        ('STAGING', 'STAGING'),
        ('DEV', 'DEV'),
        ('QA', 'QA'),
    )
    key = models.CharField(max_length=255)
    value = models.TextField()
    environment = models.CharField(max_length=255, choices=environment_choices)
    description = models.CharField(max_length=255, default="specifies possible values for this key")
    category = models.CharField(max_length=255, default="tech")

    def __str__(self):
        return "#{} | {} | {}".format(self.id, self.key, self.value)


class AcmRatingFeedbackOptions(BaseModel):
    text = models.CharField(max_length=255)

    class Meta:
        verbose_name_plural = "Acm Rating Feedback Options"

    def __str__(self):
        return "{}".format(self.text)


class AcquisitionChannel(BaseModel):
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255, null=True)

    def __str__(self):
        return '{}'.format(self.name)

    class Meta:
        verbose_name_plural = "Acquisition Channels"


class RateOfExchange(BaseModel):
    date = models.DateTimeField()
    currency = models.ForeignKey(Currency, verbose_name='Base Currency', on_delete=models.PROTECT)
    roe = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(50000)],
                            verbose_name="Rate of exchange", default=1)
    base_currency = models.ForeignKey(Currency, on_delete=models.PROTECT, verbose_name='Base/Quote Currency',
                                      related_name="base_currency")

    def __str__(self):
        return '{} - {}'.format(self.currency, self.roe)

    class Meta:
        unique_together = ['currency', 'date']
        verbose_name_plural = "Rate of Exchanges"


class BaseCurrencyCharge(models.Model):
    currency = models.ForeignKey(Currency, verbose_name='Base Currency', on_delete=models.PROTECT)
    base_currency = models.ForeignKey(Currency, verbose_name='Quote Currency', on_delete=models.PROTECT,
                                      related_name="base_currency_currency_base_charges")
    bank_charges = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(1000)],
                                     verbose_name="Bank Charges", default=0, null=False, blank=False)
    selling_mark_up = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(1000)],
                                        verbose_name="Selling Markup", default=0, null=False, blank=False)
    buying_mark_up = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(1000)],
                                       verbose_name="Buying Markup", default=0, null=False, blank=False)

    class Meta:
        unique_together = ['currency', 'base_currency']
        verbose_name_plural = "Markup and Bank Charges"


class TravelSupplyGroupEntities(CodeMixin, BaseModel):
    name = models.CharField(max_length=100, verbose_name="TS Group Entity Name")
    country = models.ForeignKey(Country, on_delete=models.PROTECT, verbose_name="TC Group Entity Country")
    notes = models.TextField(max_length=1000, null=True, blank=True)

    CLASS_PREFIX = "TSGE"

    def __str__(self):
        return str(self.name)

    class Meta:
        verbose_name_plural = "Travel Supply Group Entities"


class RemitType(BaseModel):
    name = models.CharField(max_length=100, null=True)

    def __str__(self):
        return '{}'.format(self.name)

    class Meta:
        verbose_name_plural = "Remit Types"


class CurrencyConfiguration(BaseModel):
    currency = models.OneToOneField(Currency, verbose_name='Currency', on_delete=models.PROTECT)
    release_limit = models.FloatField(verbose_name="Release Limit", default=0, null=False, blank=False)

    def __str__(self):
        return '{} | {}'.format(self.currency, self.release_limit)
