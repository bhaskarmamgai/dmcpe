from rest_framework import serializers

from bms.models.actual_payment.actual_payment import ActualPayment
from bms.models.release_request.release_request import ReleaseRequest
from bms.models.planned_payment.planned_payment import PlannedPayment
from bms.models import BookingInvoices
from bms.enums import RELEASE_REQUEST_RELEASE_OPTION, BANK_TRANSFER, RefundMode


class PlannedPaymentSerializer(serializers.Serializer):
    member_id = serializers.IntegerField()
    booking_id = serializers.IntegerField()
    amount = serializers.FloatField()
    amount_in_collection_currency = serializers.FloatField(allow_null=True)
    member_currency_id = serializers.IntegerField(allow_null=True)
    date = serializers.DateField()
    type = serializers.ChoiceField(choices=PlannedPayment.DUE_TYPE)
    status = serializers.ChoiceField(choices=PlannedPayment.STATUS)
    payment_type = serializers.ChoiceField(choices=PlannedPayment.PAYMENT_TYPE)
    created_by_id = serializers.IntegerField()

    organization_id = serializers.IntegerField()

    class Meta:
        model = PlannedPayment

    def create(self, validated_data):
        record = PlannedPayment.objects.create(**validated_data)
        return record


class ActualPaymentSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField()
    amount = serializers.FloatField()
    member_id = serializers.IntegerField()
    date = serializers.DateField()
    type = serializers.ChoiceField(ActualPayment.ACTUAL_PAYMENT_TYPE)
    record_id = serializers.IntegerField(allow_null=True)
    created_by_id = serializers.IntegerField()
    release_request_id = serializers.IntegerField(allow_null=True)
    amount_in_member_currency = serializers.FloatField(allow_null=True)

    organization_id = serializers.FloatField(allow_null=True)
    status = serializers.CharField(allow_null=True)
    amount_in_collection_currency = serializers.FloatField(allow_null=True)
    member_currency_id = serializers.IntegerField(allow_null=True)

    class Meta:
        model = ActualPayment

    def create(self, validated_data):
        record = ActualPayment.objects.create(**validated_data)
        return record


class ReleaseRequestSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField(allow_null=True)
    member_id = serializers.IntegerField(allow_null=False)
    description = serializers.CharField(allow_null=False)
    requested_currency_id = serializers.IntegerField(allow_null=True)
    requested_amount = serializers.FloatField(allow_null=False)
    created_by_id = serializers.IntegerField()
    to_be_released_on = serializers.DateField()
    organization_bank_account_id = serializers.IntegerField(allow_null=True)

    organization_id = serializers.IntegerField(allow_null=True)
    mode = serializers.ChoiceField(choices=RELEASE_REQUEST_RELEASE_OPTION, default=BANK_TRANSFER)
    proof = serializers.FileField(allow_null=True)
    remark = serializers.CharField(allow_null=True)
    refund_mode = serializers.CharField(default=RefundMode.BLANK.value)

    class Meta:
        model = ReleaseRequest

    def create(self, validated_data):
        record = ReleaseRequest.objects.create(**validated_data)
        return record


class BookingInvoiceSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField()
    created_by_id = serializers.IntegerField()
    document_path = serializers.FileField(allow_null=True, required=False)
    description_of_reimbursement = serializers.CharField()
    description_of_service_charges = serializers.CharField()
    sac_code_service = serializers.CharField(allow_blank=True)

    tax_invoice_number = serializers.CharField(allow_null=True)
    service_charges = serializers.FloatField()
    reimbursement_amount = serializers.FloatField()
    igst_percentage_on_service_charges = serializers.FloatField(default=0)
    igst_amount_on_service_charges = serializers.FloatField(default=0)
    cgst_percentage_on_service_charges = serializers.FloatField(default=0)
    cgst_amount_on_service_charges = serializers.FloatField(default=0)
    sgst_percentage_on_service_charges = serializers.FloatField(default=0)
    sgst_amount_on_service_charges = serializers.FloatField(default=0)
    total_service_charges_with_tax = serializers.FloatField()
    invoice_amount = serializers.FloatField()
    invoice_reference_number = serializers.CharField(default=None)
    qr_code = serializers.FileField(default=None)
    is_einvoice = serializers.BooleanField(default=False)
    ack_date = serializers.DateTimeField(default=None)
    ack_no = serializers.CharField(default=None)
    approved_discount = serializers.FloatField(default=0)
    scratch_card_amount = serializers.FloatField(default=0)
    invoice_type = serializers.CharField(allow_null=True)

    class Meta:
        model = BookingInvoices

    def create(self, validated_data):
        record = BookingInvoices.objects.create(**validated_data)
        return record
