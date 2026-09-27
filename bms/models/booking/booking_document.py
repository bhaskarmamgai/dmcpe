from bms.models.booking.booking import Booking
from dmcpesys.models import Category
from django.db import models
from common.models import BaseModel

class BookingDocument(BaseModel):
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    STATUS_TYPE = (
        (ACTIVE, ACTIVE),
        (INACTIVE, INACTIVE)
    )
    BOOKING_VOUCHER = 'booking_voucher'
    TICKET = 'ticket'
    CREDIT_NOTE = 'cn'
    DEBIT_NOTE = 'dn'
    CANCELLATION_INVOICE = 'cancellation_invoice'
    DOCUMENT_TYPE = (
        (BOOKING_VOUCHER, 'Booking Voucher'),
        (TICKET, 'Ticket'),
        (CREDIT_NOTE, 'Credit Note'),
        (DEBIT_NOTE, 'Debit Note'),
        (CANCELLATION_INVOICE, 'Cancellation Invoice')
    )
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE)
    booking = models.ForeignKey(Booking, on_delete=models.PROTECT, related_name="booking_documents", )
    name = models.CharField(max_length=100)
    delivery_date = models.DateTimeField(null=True, blank=True)
    file = models.FileField(null=True, blank=True, max_length=255)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    status = models.CharField(max_length=30, choices=STATUS_TYPE)

    def __str__(self):
        return str(self.booking.id) + "|" + self.status

    class Meta:
        verbose_name_plural = "Booking Document"
