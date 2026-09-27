import datetime
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.safestring import mark_safe

from auditlog.registry import auditlog
from common.models import CodeMixin, BaseModel

from dmcpesys.models import Category, Currency, Destination, Inclusion

from members.models import Organization

from members.services import MemberServices


class Booking(CodeMixin, BaseModel):
    BLANK = ''
    BLANK_LABEL = '-'
    NA = 'na'
    RECEIVED = 'received'
    PENDING = 'pending'
    PARTIALLY_RECEIVED = 'partially_received'
    APPROVED = 'approved'

    DOCUMENT_STATUS_CHOICES = (
        (BLANK, BLANK_LABEL),
        (RECEIVED, RECEIVED),
        (PENDING, PENDING),
        (PARTIALLY_RECEIVED, PARTIALLY_RECEIVED),
        (APPROVED, APPROVED),
        (NA, NA),
    )
    CONFIRMED = "confirmed"
    CANCELLATION_INITIATED = "cancellation_initiated"
    CANCELLATION_SETTLED = "cancellation_settled"
    CANCELLED = "cancelled"
    FAILED = "failed"
    HOLD = 'hold'
    RELEASED = 'released'

    STATUS = (
        (CONFIRMED, CONFIRMED),
        (CANCELLATION_INITIATED, CANCELLATION_INITIATED),
        (CANCELLED, CANCELLED),
        (FAILED, FAILED),
        (RELEASED, RELEASED),
        (HOLD, HOLD),
        (PENDING, PENDING)
    )
    CLASS_PREFIX = 'BG'

    status = models.CharField(max_length=50, choices=STATUS, default=CONFIRMED)
    code = models.CharField(max_length=7, unique=True, blank=True, null=True)
    booking_date = models.DateField(verbose_name='Booking Date', default=datetime.date.today)
    type = models.ForeignKey('bms.BookingType', on_delete=models.PROTECT)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, blank=False, null=True)
    buyer = models.ForeignKey('members.Member', related_name="purchase_transactions", on_delete=models.PROTECT)
    buyer_organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="buyer_bookings",
                                           null=True,
                                           blank=False, verbose_name="Buyer Organization")
    agent_collection_entity = models.ForeignKey('dmcpesys.TravelSupplyGroupEntities', on_delete=models.PROTECT,
                                                related_name="agent_collection_entity",
                                                null=True, blank=False,
                                                verbose_name="TACE")
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, verbose_name="Booking Currency")
    amount = models.FloatField(validators=[MinValueValidator(1), MaxValueValidator(10000000)],
                               verbose_name="Amount in Booking Currency (Excluding Bank Charges)")
    collection_currency = models.ForeignKey(Currency, on_delete=models.PROTECT, verbose_name="Collection Currency",
                                            related_name="bookings", null=True)
    amount_in_collection_currency = models.FloatField(validators=[MinValueValidator(1), MaxValueValidator(10000000)],
                                                      verbose_name="Amount in Collection Currency", null=True)
    amount_in_inr = models.FloatField(validators=[MinValueValidator(1), MaxValueValidator(10000000)],
                                      verbose_name="Amount in INR", default=0)
    original_deal_amount = models.FloatField(validators=[MaxValueValidator(10000000)],
                                             verbose_name="Original Deal Amount", null=True, blank=True)
    departure_at = models.DateField(verbose_name="Date of Travel")
    destination = models.ForeignKey(Destination, blank=False, on_delete=models.PROTECT, null=True,
                                    verbose_name="Destination")
    nights_count = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(30)],
                                       verbose_name="Nights #")
    adults_count = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(500)],
                                       verbose_name="Adults #", blank=True, null=True)
    children_count = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(200)],
                                         verbose_name="Children #", blank=True, null=True)
    document_status = models.CharField(max_length=20, choices=DOCUMENT_STATUS_CHOICES, default=BLANK, )

    proof = models.FileField(blank=True, null=True, max_length=255, help_text='Booking Proof')

    inclusions = models.ManyToManyField(Inclusion, blank=True, related_name='transactions')

    description = models.CharField(max_length=1024, blank=True, null=True)
    parent_booking_id = models.IntegerField(verbose_name="Parent Booking ID", blank=True, null=True)
    parent_booking_code = models.CharField(max_length=7, blank=True, null=True, verbose_name="Parent Booking Code")
    invoice_number = models.CharField(max_length=7, blank=True, null=True, verbose_name="Booking Invoice Number")

    def clean(self):
        created = self.pk or None
        if not created:
            if hasattr(self, 'buyer'):
                error_message, admin_field_ids = MemberServices.validate_members_organization_mandatory_fields_for_booking(
                    self.buyer.organization)
                if error_message and admin_field_ids:
                    raise ValidationError(
                        mark_safe("{}-{}".format("Following Details of Buyer Organization Are Missing:<br/>",
                                                 error_message)))
            if self.booking_date and self.booking_date > datetime.datetime.today().date():
                raise ValidationError(
                    {'booking_date': mark_safe("Booking Date Can't Be Greater Than Today's Date")})

    def __str__(self):
        return "#%s | %s | %s | %s" % (
            self.id, self.code, self.type.name, self.buyer)

    class Meta:
        verbose_name_plural = "Bookings"


class BookingCancellationProxy(Booking):
    class Meta:
        proxy = True
        verbose_name_plural = "Cancellation"


class BookingRefundProxy(Booking):
    class Meta:
        proxy = True
        verbose_name_plural = "Refunds"


class PendingBookingFlightProxy(Booking):
    class Meta:
        proxy = True
        verbose_name_plural = "Flight Pending Bookings"


auditlog.register(Booking)
auditlog.register(PendingBookingFlightProxy)
