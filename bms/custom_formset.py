from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.forms import BaseInlineFormSet
from common.libraries import get_round_off_amount
from dmcpesys.services import get_roe_and_markup_by_currency
from bms.models import PlannedPayment, Booking, SellerCostComponent
from wallets.models import Wallet
from members.services import OrganizationServices
from bms.config.base import SELLER_COST_COMPONENT_CANCELLED_ID
from bms.services import bookings


class FlightDetailInlineFormset(BaseInlineFormSet):
    def clean(self):
        super(FlightDetailInlineFormset, self).clean()
        if hasattr(self.instance, 'type') and getattr(self.instance, 'category'):
            if self.instance.type.id == settings.BOOKING_TYPE_FLIGHT_ID and self.instance.category.id == settings.CATEGORY_FLIGHT_ID:
                non_empty_form = 0
                for form in self:
                    if form.cleaned_data:
                        non_empty_form += 1
                if non_empty_form - len(self.deleted_forms) < 1:
                    raise ValidationError("Please Fill These Details.")


class PlannedPaymentScheduleInlineFormset(BaseInlineFormSet):
    def clean(self):
        super(PlannedPaymentScheduleInlineFormset, self).clean()
        self._check_schedule_collection_sum()

    def _check_schedule_collection_sum(self):
        non_empty_form = 0
        total_schedule_collection_amount = 0
        for form in self:
            if form.cleaned_data:
                if form.cleaned_data.get('id') is not None and form.cleaned_data.get('id').payment_type in [
                    PlannedPayment.TRANCHE, PlannedPayment.DIRECT_PAYMENT] and form.cleaned_data.get('id').status in [
                    PlannedPayment.PENDING,
                    PlannedPayment.COLLECTED]:
                    non_empty_form += 1
                    total_schedule_collection_amount += form.cleaned_data.get('id').amount
                elif form.cleaned_data.get('payment_type') is not None and form.cleaned_data.get('payment_type') in [
                    PlannedPayment.TRANCHE, PlannedPayment.DIRECT_PAYMENT]:
                    non_empty_form += 1
                    total_schedule_collection_amount += form.cleaned_data.get('amount')
        if self.instance.status == Booking.CONFIRMED and non_empty_form - len(self.deleted_forms) < 1:
            raise ValidationError("Please fill Schedule Collection")

        if self.instance.status == Booking.CONFIRMED and hasattr(self.instance,
                                                                 'booking_financial') and total_schedule_collection_amount > 0 and total_schedule_collection_amount != self.instance.booking_financial.total_net_receivable:
            raise ValidationError(
                "Sum of all Schedule collections- Tranche and Direct Payment should be equal to Total Net Receivable (Collection Currency)")

    def get_safe_fee_from_booking_object(self):
        return self.instance.booking_charges.safe_fee if hasattr(self.instance, 'booking_charges') else 0

    def get_booking_financial_v2_obj(self):
        return self.instance.booking_financial if hasattr(self.instance, 'booking_financial') else None

    def get_service_charge_collected_from_buyer(self):
        return self.instance.booking_charges.service_charge_collected_from_buyer if hasattr(self.instance,
                                                                                            'booking_charges') else 0

    def get_roe_on_booking_date(self):
        return self.instance.booking_charges.roe_on_booking_date if hasattr(self.instance, 'booking_charges') else 1

    def get_convenience_charges_on_roe(self):
        return self.instance.booking_charges.convenience_charges_on_roe if hasattr(self.instance,
                                                                                   'booking_charges') else 0


class PlannedPaymentEditAllFieldsFormset(BaseInlineFormSet):
    def save_existing_objects(self, commit=True):
        saved_instances = super(PlannedPaymentEditAllFieldsFormset, self).save_existing_objects(commit)
        if commit:
            for index, saved_instance in enumerate(saved_instances):
                if saved_instance.bookings.booking_version_type == Booking.V2:
                    if saved_instance.payment_type == PlannedPayment.REFUND:
                        if saved_instance.type == PlannedPayment.DUE_ON_MEMBER:
                            seller_cost_components = SellerCostComponent.objects.filter(
                                seller_member__id=saved_instance.member.id,
                                booking__code=saved_instance.bookings.code).exclude(
                                seller_status__id=SELLER_COST_COMPONENT_CANCELLED_ID)
                            saved_instance.member_currency = seller_cost_components.last().seller_currency if seller_cost_components.last() else None
                            saved_instance.amount_in_collection_currency = bookings.calculate_amount_in_collection_currency_for_payment(
                                saved_instance.bookings.collection_currency.id, saved_instance.amount,
                                seller_cost_components)
                        elif saved_instance.type == PlannedPayment.DUE_TO_MEMBER:
                            saved_instance.member_currency = saved_instance.bookings.collection_currency
                            saved_instance.amount_in_collection_currency = bookings.calculate_amount_in_collection_currency_for_collection(
                                saved_instance.bookings.collection_currency.id,
                                saved_instance.member_currency_id, saved_instance.bookings.created_at,
                                saved_instance.amount)
                    else:
                        if saved_instance.type == PlannedPayment.DUE_ON_MEMBER:
                            saved_instance.member_currency = saved_instance.bookings.collection_currency
                            saved_instance.amount_in_collection_currency = bookings.calculate_amount_in_collection_currency_for_collection(
                                saved_instance.bookings.collection_currency.id,
                                saved_instance.member_currency_id, saved_instance.bookings.created_at,
                                saved_instance.amount)
                        elif saved_instance.type == PlannedPayment.DUE_TO_MEMBER:
                            seller_cost_components = SellerCostComponent.objects.filter(
                                seller_member__id=saved_instance.member.id,
                                booking__code=saved_instance.bookings.code).exclude(
                                seller_status__id=SELLER_COST_COMPONENT_CANCELLED_ID)
                            saved_instance.member_currency = seller_cost_components.last().seller_currency if seller_cost_components.last() else None
                            saved_instance.amount_in_collection_currency = bookings.calculate_amount_in_collection_currency_for_payment(
                                saved_instance.bookings.collection_currency.id, saved_instance.amount,
                                seller_cost_components)
                saved_instance.save()
                saved_instances[index] = saved_instance
        return saved_instances

    def save_new_objects(self, commit=True):
        saved_instances = super(PlannedPaymentEditAllFieldsFormset, self).save_new_objects(commit)
        if commit:
            for index, saved_instance in enumerate(saved_instances):
                if saved_instance.bookings.booking_version_type == Booking.V2:
                    if saved_instance.payment_type == PlannedPayment.REFUND:
                        if saved_instance.type == PlannedPayment.DUE_ON_MEMBER:
                            seller_cost_components = SellerCostComponent.objects.filter(
                                seller_member__id=saved_instance.member.id,
                                booking__code=saved_instance.bookings.code).exclude(
                                seller_status__id=SELLER_COST_COMPONENT_CANCELLED_ID)
                            saved_instance.member_currency = seller_cost_components.last().seller_currency if seller_cost_components.last() else None
                            saved_instance.amount_in_collection_currency = bookings.calculate_amount_in_collection_currency_for_payment(
                                saved_instance.bookings.collection_currency.id, saved_instance.amount,
                                seller_cost_components)
                        elif saved_instance.type == PlannedPayment.DUE_TO_MEMBER:
                            saved_instance.member_currency = saved_instance.bookings.collection_currency
                            saved_instance.amount_in_collection_currency = bookings.calculate_amount_in_collection_currency_for_collection(
                                saved_instance.bookings.collection_currency.id, saved_instance.member_currency_id,
                                saved_instance.bookings.created_at, saved_instance.amount)
                    else:
                        if saved_instance.type == PlannedPayment.DUE_ON_MEMBER:
                            saved_instance.member_currency = saved_instance.bookings.collection_currency
                            saved_instance.amount_in_collection_currency = bookings.calculate_amount_in_collection_currency_for_collection(
                                saved_instance.bookings.collection_currency.id,
                                saved_instance.member_currency_id, saved_instance.bookings.created_at,
                                saved_instance.amount)
                        elif saved_instance.type == PlannedPayment.DUE_TO_MEMBER:
                            seller_cost_components = SellerCostComponent.objects.filter(
                                seller_member__id=saved_instance.member.id,
                                booking__code=saved_instance.bookings.code).exclude(
                                seller_status__id=SELLER_COST_COMPONENT_CANCELLED_ID)
                            saved_instance.member_currency = seller_cost_components.last().seller_currency if seller_cost_components.last() else None
                            saved_instance.amount_in_collection_currency = bookings.calculate_amount_in_collection_currency_for_payment(
                                saved_instance.bookings.collection_currency.id, saved_instance.amount,
                                seller_cost_components)
                saved_instance.save()
                saved_instances[index] = saved_instance
        return saved_instances


class PlannedPaymentCollectionInlineFormset(BaseInlineFormSet):
    def clean(self):
        super(PlannedPaymentCollectionInlineFormset, self).clean()
        self._check_schedule_payment_sum()

    def _check_schedule_payment_sum(self):
        non_empty_form = 0
        total_schedule_payment_amount = 0
        schedule_payment_member_id = 0
        scheduled_payments_member_ids_with_amounts = dict()
        for form in self:
            if form.cleaned_data:
                schedule_payment_member_id = form.instance.member_id
                if form.instance.booking.status == Booking.PENDING:
                    raise ValidationError("Schedule Payment is not applicable in case of Pending Booking")

                elif form.cleaned_data.get('id') is not None and form.cleaned_data.get('id').payment_type in [
                    PlannedPayment.TRANCHE, PlannedPayment.DIRECT_PAYMENT] and form.cleaned_data.get('id').status in [
                    PlannedPayment.PENDING,
                    PlannedPayment.PAID]:
                    if schedule_payment_member_id in scheduled_payments_member_ids_with_amounts:
                        scheduled_payments_member_ids_with_amounts[schedule_payment_member_id] += form.cleaned_data.get(
                            'id').amount
                    else:
                        scheduled_payments_member_ids_with_amounts[schedule_payment_member_id] = form.cleaned_data.get(
                            'id').amount
                    total_schedule_payment_amount += form.cleaned_data.get('id').amount
                elif form.cleaned_data.get('payment_type') is not None and form.cleaned_data.get('payment_type') in [
                    PlannedPayment.TRANCHE, PlannedPayment.DIRECT_PAYMENT]:
                    if schedule_payment_member_id in scheduled_payments_member_ids_with_amounts:
                        scheduled_payments_member_ids_with_amounts[schedule_payment_member_id] += form.cleaned_data.get(
                            'amount')
                    else:
                        scheduled_payments_member_ids_with_amounts[schedule_payment_member_id] = form.cleaned_data.get(
                            'amount')
                    total_schedule_payment_amount += form.cleaned_data.get('amount')
                non_empty_form += 1
        if self.instance.status == Booking.CONFIRMED and non_empty_form - len(self.deleted_forms) < 1:
            raise ValidationError("Please fill Schedule Payment")

        for member_id, amount in scheduled_payments_member_ids_with_amounts.items():
            schedule_payment_member_id = member_id
            calculated_total_amount = get_total_amount_of_seller_cost_component_member(schedule_payment_member_id,
                                                                                       self.instance.code)
            if self.instance.status == Booking.CONFIRMED and get_round_off_amount(
                    calculated_total_amount) != get_round_off_amount(amount):
                raise ValidationError(
                    "Sum of all Schedule Payments- Tranche and Direct Payment should be equal to the respective seller's sum of Net Payable to Seller (Seller Currency) ")

    def get_booking_loss_from_booking_object(self):
        return self.instance.booking_charges.booking_loss if hasattr(self.instance, 'booking_charges') else 0

    def get_safe_collect_fee_from_booking_object(self):
        return self.instance.booking_charges.safe_collect_fee if hasattr(self.instance, 'booking_charges') else 0


def get_total_amount_of_seller_cost_component_member(member_id, code):
    return SellerCostComponent.objects.filter(seller_member__id=member_id, booking__code=code).exclude(
        seller_status__id=SELLER_COST_COMPONENT_CANCELLED_ID).aggregate(
        total=Sum('seller_net_payable_in_seller_currency'))['total'] or 0


class ApprovedDiscountInlineFormset(BaseInlineFormSet):
    def clean(self):
        super(ApprovedDiscountInlineFormset, self).clean()
        self._check_approved_discount()

    def _check_approved_discount(self):
        total_approved_discount = 0
        booking_amount = 0
        for form in self:
            if form.cleaned_data:
                if not booking_amount:
                    booking_amount = form.cleaned_data.get('booking').amount_in_collection_currency
                total_approved_discount += form.cleaned_data.get('amount', 0)
        if booking_amount < total_approved_discount:
            raise ValidationError("Net Approved Discount should be less than Booking Amount")


class SellerCostComponentInlineFormset(BaseInlineFormSet):
    def clean(self):
        super(SellerCostComponentInlineFormset, self).clean()
        self._check_seller_cost_component()

    def _get_wallet_currency(self, member_id):
        try:
            organization_obj = OrganizationServices.get_member_organization_by_member_id(member_id)
            wallet = Wallet.objects.get(organization_id=organization_obj.id)
            return wallet.currency
        except:
            import traceback
            traceback.print_exc()
            return None

    def _check_if_seller_roe_and_markup_exists(self, booking_obj, seller_currency_id):
        try:
            get_roe_and_markup_by_currency(booking_obj.collection_currency.id,
                                           seller_currency_id,
                                           booking_obj.created_at)
            return True
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False

    def _check_seller_cost_component(self):
        if self.instance.status == Booking.CONFIRMED and len(self) == 0:
            raise ValidationError("Seller Cost Component cannot be empty for confirmed bookings")

        for form in self:
            if form.cleaned_data:
                seller_currency = form.cleaned_data.get('seller_currency')
                if seller_currency:
                    if not form.cleaned_data.get('seller_fx') or not form.cleaned_data.get('seller_fx_markup'):
                        is_exist_roe_or_markup = self._check_if_seller_roe_and_markup_exists(self.instance,
                                                                                             seller_currency.id)
                        if not is_exist_roe_or_markup:
                            raise ValidationError("Please check if ROE And Markup are Present.")
                    if form.cleaned_data.get('seller_member'):
                        wallet_currency_of_seller = self._get_wallet_currency(form.cleaned_data.get('seller_member').id)
                        if seller_currency != wallet_currency_of_seller:
                            raise ValidationError("Seller Currency is not matching with Wallet Currency")
