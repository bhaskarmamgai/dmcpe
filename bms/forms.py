from datetime import datetime
from django import forms
from members.models import Member, Organization

from dmcpesys.services import  check_if_roe_and_markup_exists
from bms.models.release_request.release_request import ReleaseRequest, ReleaseRequestProxy, ReleaseRequestPayments
from bms.models.planned_payment.planned_payment import PlannedPayment
from bms.models.booking.booking_invoice import BookingInvoices
from bms.models import ApprovedDiscount, SellerCostComponent
from bms.models.booking import BookingType, Booking
from dmcpesys.models import Service, Destination, Category, TravelSupplyGroupEntities, Currency, RemitType
from django.conf import settings
from bms.enums import RELEASE_REQUEST_RELEASE_OPTION
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
from members.services import OrganizationServices
from wallets.services import WalletServices as wallet


class addInvoice(forms.ModelForm):
    company_name = forms.ChoiceField(choices=settings.COMPANY_LIST)

    def __init__(self, *args, **kwargs):
        super(addInvoice, self).__init__(*args, **kwargs)
        self.fields['igst_amount_on_service_charges'].widget.attrs['readonly'] = True
        self.fields['cgst_amount_on_service_charges'].widget.attrs['readonly'] = True
        self.fields['sgst_amount_on_service_charges'].widget.attrs['readonly'] = True
        self.fields['company_name'].widget.attrs['class'] = 'form-control'

    class Meta:
        model = BookingInvoices
        fields = ['tax_invoice_number', 'description_of_service_charges', 'description_of_reimbursement',
                  'service_charges', 'igst_percentage_on_service_charges', 'cgst_percentage_on_service_charges',
                  'sgst_percentage_on_service_charges',
                  'sac_code_service', 'igst_amount_on_service_charges', 'cgst_amount_on_service_charges',
                  'sgst_amount_on_service_charges', 'booking', 'total_service_charges_with_tax', 'invoice_amount',
                  'reimbursement_amount', ]
        exclude = ['created_by']

    def clean(self):
        service_charges = round(float(self.cleaned_data.get('service_charges')), 2)
        igst_amount_on_service_charges = round(float(self.cleaned_data.get('igst_amount_on_service_charges')), 2)
        cgst_amount_on_service_charges = round(float(self.cleaned_data.get('cgst_amount_on_service_charges')), 2)
        sgst_amount_on_service_charges = round(float(self.cleaned_data.get('sgst_amount_on_service_charges')), 2)
        calculated_service_charges_with_tax = round(
            service_charges + igst_amount_on_service_charges + cgst_amount_on_service_charges + sgst_amount_on_service_charges,
            2)

        total_service_charges_with_tax = round(float(self.cleaned_data.get('total_service_charges_with_tax')), 2)
        reimbursement_amount = round(float(self.cleaned_data.get('reimbursement_amount')), 2)
        invoice_amount = round(float(self.cleaned_data.get('invoice_amount')), 2)

        if abs(total_service_charges_with_tax - calculated_service_charges_with_tax) > 1:
            self._errors['total_service_charges_with_tax'] = self.error_class(
                ['Service charges %s, taxes (%s, %s, %s) and total service charges with tax (%s) does not match' % (
                    service_charges, igst_amount_on_service_charges, cgst_amount_on_service_charges,
                    sgst_amount_on_service_charges, total_service_charges_with_tax)])

        if abs(invoice_amount - (reimbursement_amount + total_service_charges_with_tax)) > 1:
            self._errors['invoice_amount'] = self.error_class(
                ['Invoice amount %s, Reimbursement amount %s, Total service charges and tax %s does not match' % (
                    invoice_amount, reimbursement_amount, total_service_charges_with_tax)])


class SelectMember(forms.Form):
    member = forms.ModelChoiceField(queryset=Member.objects.all())


class SelectPlannedTransactions(forms.Form):
    member_id = forms.IntegerField()
    record_id = forms.IntegerField()

    def __init__(self, *args, **kwargs):
        super(SelectPlannedTransactions, self).__init__(*args, **kwargs)
        self.fields['member_id'].widget.attrs['readonly'] = True
        self.fields['record_id'].widget.attrs['readonly'] = True


class SelectSellerTransactions(forms.Form):
    member_id = forms.IntegerField()

    def __init__(self, *args, **kwargs):
        super(SelectSellerTransactions, self).__init__(*args, **kwargs)
        self.fields['member_id'].widget.attrs['readonly'] = True


class SelectService(forms.Form):
    service = forms.ModelChoiceField(queryset=Service.objects.all())


class ReleaseRequestProxyForm(forms.ModelForm):
    class Meta:
        model = ReleaseRequestProxy
        fields = ['proof', 'amount_released_including_charges', 'release_notes']



class CancellationFinalSettlementForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(CancellationFinalSettlementForm, self).__init__(*args, **kwargs)
        self.fields['amount'].required = False

    COLLECT = PlannedPayment.DUE_ON_MEMBER
    PAY = PlannedPayment.DUE_TO_MEMBER
    COLLECT_OR_PAY = (
        (COLLECT, 'COLLECT'),
        (PAY, 'PAY')
    )
    amount = forms.FloatField(min_value=0)
    collect_or_pay = forms.ChoiceField(choices=COLLECT_OR_PAY)


class RejectReleaseRequestForm(forms.ModelForm):
    remark = forms.CharField(widget=forms.Textarea(attrs={'rows': 4, 'cols': 50}))

    class Meta:
        model = ReleaseRequest
        fields = ('remark',)


class CancelTrancheForm(forms.ModelForm):
    remark = forms.CharField(widget=forms.Textarea(attrs={'rows': 4, 'cols': 50}))

    class Meta:
        model = PlannedPayment
        fields = ('remark',)


class PlannedPaymentEditAllFieldsForm(forms.ModelForm):
    class Meta:
        model = PlannedPayment
        fields = '__all__'

    def clean(self):
        if self.has_changed() and not self.cleaned_data.get('remark'):
            raise ValidationError({'remark': mark_safe("This Field is Required")})


class BookingRefundOptionsForm(forms.Form):
    RELEASE_REQUEST_AS_ADD_TO_WALLET = "add_to_wallet"
    RELEASE_REQUEST_AS_BANK_TRANSFER = "bank_transfer"
    BOOKING_REFUND_OPTIONS = (
        (RELEASE_REQUEST_AS_ADD_TO_WALLET, "Release Request[Add To Wallet]"),
        (RELEASE_REQUEST_AS_BANK_TRANSFER, "Release Request[Bank Transfer]")
    )
    booking_refund_option = forms.ChoiceField(choices=BOOKING_REFUND_OPTIONS,
                                              widget=forms.Select(attrs={'class': "form-control"}))


class ModeOfReleaseRequestForm(forms.Form):
    RELEASE_REQUEST_AS_ADD_TO_WALLET = "add_to_wallet"
    RELEASE_REQUEST_AS_BANK_TRANSFER = "bank_transfer"
    MODE_OF_RELEASE_REQUEST_OPTIONS = (
        (RELEASE_REQUEST_AS_BANK_TRANSFER, "Release Request [Bank Transfer]"),
        (RELEASE_REQUEST_AS_ADD_TO_WALLET, "Release Request [Add To Wallet]")
    )
    mode_of_release = forms.ChoiceField(choices=MODE_OF_RELEASE_REQUEST_OPTIONS,
                                        widget=forms.Select(attrs={'class': "form-control"}))


class TypeOfCancellationRequestForm(forms.Form):
    CANCELLATION_REQUEST_FOR_FULL_CANCELLATION = "full_cancellation"
    CANCELLATION_REQUEST_FOR_PARTIAL_CANCELLATION = "partial_cancellation"
    CANCELLATION_REQUEST_OPTIONS = (
        (CANCELLATION_REQUEST_FOR_FULL_CANCELLATION, "Cancellation Request [Full Cancellation]"),
        (CANCELLATION_REQUEST_FOR_PARTIAL_CANCELLATION, "Cancellation Request [Partial Cancellation]")
    )
    cancellation_type = forms.ChoiceField(choices=CANCELLATION_REQUEST_OPTIONS,
                                          widget=forms.Select(attrs={'class': "form-control"}))


class TravelSupplyGroupEntityForm(forms.Form):
    travel_supply_group_entity = forms.ModelChoiceField(
        queryset=TravelSupplyGroupEntities.objects.filter(is_active=True, is_deleted=False),
        widget=forms.Select(attrs={'class': "form-control"}))


class CurrencyForm(forms.Form):
    currency = forms.ModelChoiceField(queryset=Currency.objects.filter(is_active=True, is_deleted=False),
                                      widget=forms.Select(attrs={'class': "form-control"}))


class RemitTypeForm(forms.Form):
    remit_type = forms.ModelChoiceField(queryset=RemitType.objects.filter(is_active=True),
                                        widget=forms.Select(attrs={'class': "form-control"}))


class CommonFormClaimAndRelease(forms.Form):
    service = forms.ModelChoiceField(queryset=Service.objects.all())
    member = forms.ModelChoiceField(queryset=Member.objects.all())
    organization = forms.ModelChoiceField(queryset=Organization.objects.all())


class ClaimFromWalletForm(CommonFormClaimAndRelease):
    pass


class ReleaseFromWalletForm(CommonFormClaimAndRelease):
    destination = forms.ModelChoiceField(queryset=Destination.objects.all())
    category = forms.ModelChoiceField(queryset=Category.objects.all())
    type = forms.ModelChoiceField(queryset=BookingType.objects.all())
    vendor_organization = forms.ModelChoiceField(queryset=Organization.objects.all())


class SelectPlannedTransactionsV2(forms.Form):
    organization_id = forms.IntegerField()
    wallet_id = forms.IntegerField()

    def __init__(self, *args, **kwargs):
        super(SelectPlannedTransactionsV2, self).__init__(*args, **kwargs)
        self.fields['organization_id'].widget.attrs['readonly'] = True
        self.fields['wallet_id'].widget.attrs['readonly'] = True


class ReleaseRequestReleaseOptions(forms.Form):
    release_option = forms.ChoiceField(choices=RELEASE_REQUEST_RELEASE_OPTION,
                                       widget=forms.Select(attrs={'class': "form-control"}))


class BookingCancellationMandatoryCommentsInlineFormSet(forms.BaseInlineFormSet):

    def clean(self):
        super(BookingCancellationMandatoryCommentsInlineFormSet, self).clean()
        non_empty_forms = 0
        for form in self:
            if form.cleaned_data:
                non_empty_forms += 1
        if non_empty_forms - len(self.deleted_forms) < 1:
            raise ValidationError("Please add a Comment while changing Cancellation Status or Charges.")


class ApprovedDiscountAdminForm(forms.ModelForm):
    class Meta:
        model = ApprovedDiscount
        fields = "__all__"

    def clean(self):
        form_cleaned_data = super().clean()
        booking = form_cleaned_data.get('booking')
        if hasattr(booking, 'booking_financial'):
            net_discount_till_now = form_cleaned_data.get('booking').booking_financial.approved_discount
            if booking.amount_in_collection_currency < net_discount_till_now + form_cleaned_data.get('amount'):
                raise ValidationError('Net Approved Discount should be less than Booking Amount')
        if booking.status == Booking.CONFIRMED:
            raise ValidationError('Approved Discount cannot be added for confirmed bookings')
        if booking and hasattr(booking, 'booking_details') and booking.booking_details.is_completed:
            raise ValidationError('Approved Discount Cannot Be Added For Complete Booking')
        return form_cleaned_data


class ReleaseRequestPaymentsForm(forms.ModelForm):
    class Meta:
        model = ReleaseRequestPayments
        fields = "__all__"

    def clean(self):
        form_cleaned_data = super().clean()
        instance = getattr(self, 'instance')
        booking = form_cleaned_data.get('booking')
        if booking and hasattr(booking, 'booking_details') and booking.booking_details.is_completed:
            raise ValidationError('Release Request Payment Cannot Be Added For Complete Booking')
        if not instance.id:
            release_request = form_cleaned_data.get('release_request')
            if ReleaseRequestPayments.objects.filter(booking=booking, release_request=release_request).exists():
                raise ValidationError('Release Request Payment already exists with this Booking and Release Request')
        return form_cleaned_data


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = "__all__"

    def clean(self):
        form_cleaned_data = super().clean()
        if form_cleaned_data.get('buyer') and form_cleaned_data.get('currency'):
            organization_obj = OrganizationServices.get_member_organization_by_member_id(form_cleaned_data['buyer'].id)
            wallet_obj = wallet.get_wallet_obj_by_organization_id(organization_obj.id)
            is_valid, error_message = check_if_roe_and_markup_exists(wallet_obj.currency.id,
                                                                     form_cleaned_data['currency'].id, datetime.now())
            if not is_valid:
                raise ValidationError(error_message)
        return form_cleaned_data


class SellerCostComponentAdminForm(forms.ModelForm):
    class Meta:
        model = SellerCostComponent
        fields = "__all__"

    def clean(self):
        form_cleaned_data = super().clean()
        booking = form_cleaned_data.get('booking')
        if booking and hasattr(booking, 'booking_details') and booking.booking_details.is_completed:
            raise ValidationError('Seller Cost Component Cannot Be Added For Complete Booking')
        return form_cleaned_data
