from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from auditlog.registry import auditlog
from members.enums import BUYER_OR_SELLER, BUYER, SELLER
from bms.models.booking.booking import Booking
from dmcpesys.models import Category
from bms.enums import CancellationStatus,CANCELLATION_REQUEST_STATUS_TYPE_CHOICES, FILE_TYPE_CHOICES, FILE_TYPE__IMAGE,    CancellationRequestTypeVersion, CANCELLATION_REQUEST_STATUS_CHOICES, CANCELLATION_STATUS_INT_ENUM_MAPPING,    SERVICE_REQUEST_INTERNAL_SYSTEM_STATUS_CHOICES, BACKGROUND_SYNC_PROVIDER_STATUS_CHOICES
from members.models import Member
from django.core.exceptions import ValidationError
from members.services import MemberServices as member_services
from dmcpesys.constants import CATEGORY_FLIGHT_ID, CATEGORY_HOTEL_ID
from tinymce.models import HTMLField
from common.models import BaseModel


def cancellation_proof_file_path(instance, filename):

    return 'trs/booking/cancellation/proof/{0}/{1}'.format(instance.booking.id, filename.replace(" ", "-").lower())


class BookingCancellation(BaseModel):
    booking = models.OneToOneField(Booking, related_name="cancelled_booking", on_delete=models.PROTECT)
    charged_to = models.CharField(max_length=10, choices=BUYER_OR_SELLER, default=BUYER)
    charged_amount = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(10000000)],
        verbose_name="Charged Amount", default=0)
    owed_to = models.CharField(max_length=10, choices=BUYER_OR_SELLER, default=SELLER)
    owed_amount = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(10000000)],
        verbose_name="Owed Amount", default=0)

    proof = models.FileField(blank=True, null=True, max_length=255)
    description = models.TextField(null=True, blank=True, verbose_name="Cancellation Charges Details")

    class Meta:
        verbose_name_plural = "Booking Cancellations"

    def get_proof_url(self):
        if self and self.proof:
            return '%s' % self.proof.name if self.id else ''

    def get_old_proof_url(self):
        return '%s/%s/%s' % (settings.AWS_S3_ENDPOINT_URL, settings.AWS_S3_BOOKING_CANCELLATION_PROOF_BUCKET_NAME,
                             self.proof) if self.id else ''


class CancellationRequestType(BaseModel):
    request_type = models.CharField(max_length=50)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, null=True, blank=True)
    version = models.CharField(max_length=10, choices=CancellationRequestTypeVersion.choices(),
                               default=CancellationRequestTypeVersion.CANCELLATION_REQUEST_TYPE_VERSION_V1.value)
    is_direct_cancellation = models.BooleanField(default=False)
    request_type_details = HTMLField(null=True)
    product_details = HTMLField(null=True)
    additional_remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.request_type

    class Meta:
        verbose_name_plural = "Cancellation Request Types"

class ServiceRequestTypeAndStatusMapping(BaseModel):
    request_type = models.ForeignKey(CancellationRequestType,related_name="service_requests_type", on_delete=models.PROTECT, null=True, blank=True)
    status = models.CharField(max_length=50, null=True, blank=True)
    status_order =  models.IntegerField( null=True, blank=True)
    state = models.IntegerField( null=True, blank=True)

    def __str__(self):
        if self.request_type:
            return "{} | {} ".format(self.request_type, self.status)
        else:
            return self.status
    class Meta:
        verbose_name_plural = "Service Requests Type And Status Mapping"

class CancellationRequest(BaseModel):
    cancellation_code = models.CharField(max_length=7, unique=True, null=True,  blank=True)
    booking = models.ForeignKey('bms.Booking', related_name="cancellation_requests", on_delete=models.PROTECT)
    request_type = models.ForeignKey(CancellationRequestType,related_name="cancellation_requests_type", on_delete=models.PROTECT)
    cancellation_status = models.IntegerField(choices=CancellationStatus.choices(),
                                              default=CancellationStatus.CANCELLATION_STATUS__REQUEST_RECEIVED.value)
    service_request_status = models.ForeignKey(ServiceRequestTypeAndStatusMapping, related_name="service_request_status_cancellation",
                                            on_delete=models.PROTECT, null=True, blank=True)
    status = models.CharField(max_length=50,choices=SERVICE_REQUEST_INTERNAL_SYSTEM_STATUS_CHOICES, null=True, blank=True)
    status_type = models.IntegerField(choices= CANCELLATION_REQUEST_STATUS_TYPE_CHOICES, null=True, blank=True)
    document = models.URLField(blank=True, null=True, max_length=512)
    member_remarks = models.TextField(null=True, blank=True)

    def __str__(self):
        return "{} | {} | {}".format(self.id, self.cancellation_code, self.service_request_status.status            if self.service_request_status else None)

    class Meta:
        verbose_name_plural = "Cancellation Requests"

    def save(self, *args, **kwargs):
        if self.service_request_status is None:
            if self.request_type_id == settings.REQUEST_TYPE_MANUAL_ID:
                self.service_request_status = None
            else:
                service_status = ServiceRequestTypeAndStatusMapping.objects.get(request_type=self.request_type, status_order=CancellationStatus.CANCELLATION_STATUS__REQUEST_RECEIVED.value,is_active=True)
                self.service_request_status = service_status
        if self.service_request_status and self.service_request_status.status_order == CancellationStatus.CANCELLATION_STATUS__REQUEST_RECEIVED.value:
            self.is_abort_allowed = True
        else:
            self.is_abort_allowed = False
        super(CancellationRequest, self).save(*args, **kwargs)


class CancellationStatusHistory(BaseModel):
    cancellation_request = models.ForeignKey(CancellationRequest, related_name='cancellation_status_history',
                                             on_delete=models.PROTECT, null=True)
    cancellation_status = models.IntegerField(choices=CancellationStatus.choices(),
                                              default=CancellationStatus.CANCELLATION_STATUS__REQUEST_RECEIVED.value)
    service_request_status = models.ForeignKey(ServiceRequestTypeAndStatusMapping, related_name="service_request_status_history",
                                       on_delete=models.PROTECT, null=True, blank=True)
    booking = models.ForeignKey('bms.Booking', related_name="cancellation_status_history", on_delete=models.PROTECT)
    status = models.CharField(max_length=50,choices=CANCELLATION_REQUEST_STATUS_CHOICES, null=True, blank=True)
    status_type = models.IntegerField(choices=CANCELLATION_REQUEST_STATUS_TYPE_CHOICES, null=True, blank=True)
    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return "{} {} {}".format(self.id, self.booking, self.status)

    class Meta:
        verbose_name_plural = "Cancellation Status History"


class CancellationComment(BaseModel):
    message = models.TextField(blank=True, null=True)
    file = models.FileField(null=True, blank=True, max_length=255)
    file_type = models.CharField(max_length=50, choices=FILE_TYPE_CHOICES, default=FILE_TYPE__IMAGE)
    service_request_status = models.ForeignKey(ServiceRequestTypeAndStatusMapping, related_name="service_request_status_comments",
                                       on_delete=models.PROTECT ,null=True, blank=True)
    cancellation_status = models.IntegerField(choices=CancellationStatus.choices(),
                                              default=CancellationStatus.CANCELLATION_STATUS__REQUEST_RECEIVED.value)
    cancellation_request = models.ForeignKey(CancellationRequest, related_name="cancellation_comments", on_delete=models.PROTECT)

    def __str__(self):
        return "Comment - {}".format(self.id)

    class Meta:
        verbose_name_plural = "Cancellation Comments"


class CancellationRequestFeedback(BaseModel):
    cancellation_request = models.ForeignKey(CancellationRequest, related_name="cancellation_request_feedbacks", on_delete=models.PROTECT)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    remarks = models.TextField(null=True, blank=True)


    def __str__(self):
        return "{} {}".format(self.rating, self.cancellation_request.cancellation_code)
    class Meta:
        verbose_name_plural = "Cancellation Request Feedbacks"


auditlog.register(CancellationRequestType)
auditlog.register(CancellationRequest)
auditlog.register(BookingCancellation)
auditlog.register(CancellationStatusHistory)
auditlog.register(CancellationComment)
auditlog.register(CancellationRequestFeedback)
