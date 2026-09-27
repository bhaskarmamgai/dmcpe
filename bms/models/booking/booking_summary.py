from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from bms.models.booking.booking import Booking
from common.models import BaseModel

class BookingSummary(BaseModel):
    booking = models.OneToOneField(Booking, related_name="booking_summary", on_delete=models.PROTECT)
    net_hold = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(500000000)],
                                 verbose_name="Net Hold", default=0)

    amount_pending_for_collection_from_buyer = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(500000000)],
        verbose_name="Amount Pending for Collection from Buyer", default=0)
    amount_pending_for_collection_from_seller = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(500000000)],
        verbose_name="Amount Pending for Collection from Seller", default=0)
    amount_pending_for_payment_to_buyer = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(10000000)],
        verbose_name="Amount Pending for Payment to Buyer", default=0)
    amount_pending_for_payment_to_seller = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(500000000)],
        verbose_name="Amount Pending for Payment to Seller", default=0)
    amount_paid_to_buyer = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(500000000)],
                                             verbose_name="Amount Paid To Buyer", default=0)
    amount_paid_to_seller = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(500000000)],
                                              verbose_name="Amount Paid To Seller", default=0)

    amount_collected_from_buyer = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(500000000)],
                                                    verbose_name="Amount Collected From Buyer", default=0)
    amount_collected_from_seller = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(500000000)],
                                                     verbose_name="Amount Collected From Seller", default=0)
    has_buyer_given_review = models.BooleanField(default=False, verbose_name="Buyer Has Given Review ?")
    has_seller_given_review = models.BooleanField(default=False, verbose_name="Seller Has Given Review ?")
    net_hold_in_member_currency = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(500000000)],
                                                    verbose_name="Net Hold in Member Currency", default=0)
    remit_profit_loss_ratio = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(10000000)],
                                                verbose_name="Remit P/L (Realised)", default=0)
    fx_profit_loss = models.FloatField(verbose_name="FX P/L", null=True)
