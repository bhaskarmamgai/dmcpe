from django.db import transaction as bookings
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from common.libraries import get_round_off_amount
from common.models import generate_unique_code
from bms.providers.transaction_summary import update_fx_profit_loss_for_booking
from django.conf import settings
from bms.models import PlannedPayment, Booking, ReleaseRequest, CancellationRequest, \
    BookingCancellationProxy, BookingDocument, BookingRefundProxy, CancellationComment, SellerCostComponent, \
    BookingFinancial, ApprovedDiscount, BookingCharges, BookingSummary, ReleaseRequestPayments
from bms.services import  bookings as booking_services, release_request, \
    booking_history as booking_history_services, booking_cancellation as cancellation_services, seller_cost_component
from bms.enums import CANCELLATION_REQUEST_STATUS_TYPE, DEFAULT_SELLER_FX_MARKUP, DEFAULT_SELLER_FX
from common.decorators import skip_signal
from dmcpesys.services import get_travel_supply_configuration_by_app_and_key, get_currency_by_symbol, \
    get_roe_and_markup_by_currency
from members.services import OrganizationServices as organization
from wallets.services import WalletServices as wallet


@receiver(pre_save, sender=Booking)
def pre_save_transaction(sender, instance, **kwargs):
    try:
        old_instance = sender.objects.get(id=instance.id)
        if old_instance.status in [sender.PENDING, sender.HOLD] and instance.status == sender.CONFIRMED:
            instance.create_latest_booking_financial = True
        if old_instance.status == sender.PENDING and instance.status == sender.CONFIRMED and not instance.created_by_id in [
            settings.INTERNAL_API_USER_FLIGHT, settings.INTERNAL_API_USER_HOTEL]:
            instance.initiate_manual_invoice_generation = True
        if old_instance.status in [sender.PENDING,
                                   sender.HOLD] and instance.status == sender.CONFIRMED and instance.created_by_id in [
            settings.INTERNAL_API_USER_FLIGHT, settings.INTERNAL_API_USER_HOTEL]:
            instance.send_booking_confirmation_mail = True
        elif old_instance.code != None and instance.status == sender.PENDING and instance.created_by_id in [
            settings.INTERNAL_API_USER_FLIGHT]:
            instance.send_booking_pending_mail = True
        elif old_instance.status in [sender.PENDING, sender.HOLD] and instance.status == sender.FAILED:
            instance.send_booking_failure_mail = True
        elif old_instance.status == sender.PENDING and instance.status == sender.HOLD:
            instance.send_hold_booking_mail = True
        if old_instance.status != instance.status:
            booking_history_services.create_booking_status_history(instance.id, status=instance.status)
        if old_instance.code == None and instance.status in [Booking.CONFIRMED]:
            instance.initiate_manual_booking_actions = True
    except sender.DoesNotExist:
        instance.initiate_manual_invoice_generation = False
        instance.send_booking_confirmation_mail = False
        instance.send_booking_pending_mail = False
        instance.send_booking_failure_mail = False
        instance.send_hold_booking_mail = False
        instance.initiate_manual_booking_actions = False
        return None


@receiver(post_save, sender=Booking)
@skip_signal()
def confirmed_transaction_post_save(sender, instance, created, **kwargs):
    """
    Booking Post Save Actions
    """
    if created:
        instance.buyer_organization = organization.get_member_organization_by_member_id(instance.buyer.id)
        organization_obj = organization.get_member_organization_by_member_id(instance.buyer.id)
        wallet_obj = wallet.get_wallet_obj_by_organization_id(organization_obj.id)
        instance.collection_currency = wallet_obj.currency
        current_roe, currency_charges = get_roe_and_markup_by_currency(instance.collection_currency.id,
                                                                       instance.currency.id, instance.created_at)
        instance.amount_in_collection_currency = get_round_off_amount(
            (float(instance.amount) + currency_charges.bank_charges) * (
                    current_roe.roe + currency_charges.selling_mark_up),
            instance.collection_currency.id if instance.collection_currency else None, True)
        booking_services.booking_charges_v2_save(instance.id, current_roe.roe, currency_charges.selling_mark_up,
                                                 currency_charges.bank_charges)
        instance.save()
        booking_history_services.create_booking_status_history(instance.id, status=instance.status)

    # if not (not hasattr(instance,
    #                     "initiate_manual_invoice_generation") or not instance.initiate_manual_invoice_generation):
    #     bookings.on_commit(lambda: invoice_provider.create_transaction_invoice_for_manual_booking(instance))
    bookings.on_commit(lambda: booking_services.update_booking_financial_v2(instance.id))


@receiver(post_save, sender=CancellationRequest)
@skip_signal()
def cancellation_request_post_save(sender, instance, created, **kwargs):
    if not created:
        if kwargs.get('update_fields') and (
                'status' in tuple(kwargs.get('update_fields')) or 'cancellation_status' in tuple(
            kwargs.get('update_fields'))
                or 'service_request_status' in tuple(kwargs.get('update_fields'))):
            cancellation_services.update_cancellation_request(instance.id,
                                                              status_type=CANCELLATION_REQUEST_STATUS_TYPE.get(
                                                                  instance.status))
            cancellation_services.create_cancellation_status_history(instance)
        return
    if instance.request_type_id == settings.REQUEST_TYPE_MANUAL_ID:
        code = generate_unique_code(instance.id, instance.__class__.__name__)
        instance.cancellation_code = code
        instance.skip_signal = True
        instance.save()
    cancellation_services.create_cancellation_status_history(instance)


@receiver(pre_save, sender=ReleaseRequest)
def pre_save_release_request(sender, instance, **kwargs):
    try:
        old_instance = sender.objects.get(id=instance.id)
        if old_instance.status != instance.status:
            instance.log_release_request_status_history = True
    except sender.DoesNotExist:
        instance.log_release_request_status_history = True
        return None


@receiver(post_save, sender=ReleaseRequest)
def post_save_release_request(sender, instance, **kwargs):
    if hasattr(instance, 'log_release_request_status_history') and instance.log_release_request_status_history:
        release_request.record_release_request_status_history(instance.id, instance.status)


@receiver(post_save, sender=BookingCancellationProxy)
def booking_cancellation_proxy_post_save(sender, instance, created, **kwargs):
    booking_history_services.create_booking_status_history(instance.id, status=instance.status)


@receiver(pre_save, sender=BookingDocument)
def booking_document_pre_booking_save(sender, instance, **kwargs):
    try:
        old_instance = sender.objects.get(id=instance.id)
        new_instance = instance
        if old_instance.file != new_instance.file:
            instance.send_booking_document_notification = True
        else:
            instance.send_booking_document_notification = False
    except sender.DoesNotExist:
        instance.send_booking_document_notification = False


@receiver(pre_save, sender=SellerCostComponent)
def seller_cost_component_pre_save(sender, instance, **kwargs):
    if instance.pk:
        prev_instance = SellerCostComponent.objects.get(pk=instance.pk)
        instance._prev_version = prev_instance


@receiver(post_save, sender=SellerCostComponent)
@skip_signal()
def seller_cost_component_save(sender, instance, created, **kwargs):
    prev_version_instance = getattr(instance, '_prev_version', None)
    try:
        if not instance.serial_number:
            serial_no = instance.booking.code + "-" + str(
                seller_cost_component.count_no_of_seller_cost_components_for_a_booking(
                    instance.booking.id))
            instance.serial_number = serial_no
        if not instance.seller_fx or not instance.seller_fx_markup:
            """
            Ex: base currency (quote currency in admin) -> INR, currency (base currency in admin) -> SGD
            and we want to convert SGD -> INR, so we will pass INR in base currency and SGD in currency
            """
            current_roe, current_markup = get_roe_and_markup_by_currency(instance.booking.collection_currency.id,
                                                                         instance.seller_currency.id,
                                                                         instance.booking.created_at)
            if not instance.seller_fx:
                if instance.seller_fx != 0:
                    instance.seller_fx = current_roe.roe if current_roe else DEFAULT_SELLER_FX
            if not instance.seller_fx_markup:
                instance.seller_fx_markup = DEFAULT_SELLER_FX_MARKUP
        if instance.seller_member:
            instance.seller_organization = organization.get_member_organization_by_member_id(instance.seller_member.id)
        tcs_amount = get_round_off_amount(float(instance.tcs) / float(instance.seller_fx + instance.seller_fx_markup))
        instance.seller_net_payable_in_seller_currency = get_round_off_amount(
            instance.cost_in_seller_currency - instance.commission_received + instance.tds + instance.tax + tcs_amount + instance.seller_service_charge)
        instance.seller_net_payable_in_collection_currency = seller_cost_component.seller_net_payable_in_collection_currency(
            instance)
        instance.cost_in_collection_currency = seller_cost_component.get_cost_in_collection_currency(instance)
        instance.skip_signal = True
        instance.save()

        bookings.on_commit(lambda: booking_services.update_booking_financial_v2(instance.booking.id))

        if instance.booking.status == Booking.CONFIRMED and prev_version_instance and prev_version_instance.seller_net_payable_in_collection_currency != instance.seller_net_payable_in_collection_currency:
            booking_services.update_latest_booking_financials(instance.booking.id,
                                                              alteration_effect_in_total_cost_price=instance.seller_net_payable_in_collection_currency - prev_version_instance.seller_net_payable_in_collection_currency,
                                                              alteration_effect_in_gross_profit=prev_version_instance.seller_net_payable_in_collection_currency - instance.seller_net_payable_in_collection_currency)
        if created:
            booking_services.update_latest_booking_financials(instance.booking.id,
                                                              alteration_effect_in_total_cost_price=instance.seller_net_payable_in_collection_currency,
                                                              alteration_effect_in_gross_profit=(
                                                                                                    -1) * instance.seller_net_payable_in_collection_currency)
        bookings.on_commit(lambda: booking_services.update_booking_financial_v2(instance.booking.id))

    except Exception as e:
        return True


@receiver(pre_save, sender=ApprovedDiscount)
def approved_discount_pre_save(sender, instance, **kwargs):
    if instance.pk:
        prev_instance = ApprovedDiscount.objects.get(pk=instance.pk)
        instance._prev_version = prev_instance


@receiver(post_save, sender=ApprovedDiscount)
@skip_signal()
def approved_discount_post_save(sender, instance, created, **kwargs):
    try:
        if instance and instance.booking:
            instance.skip_signal = True
            booking_services.update_booking_financial_v2(instance.booking.id)
            if instance.booking.status == Booking.CONFIRMED and hasattr(instance,
                                                                        '_prev_version') and instance._prev_version.amount != instance.amount:
                booking_services.update_latest_booking_financials(instance.booking.id,
                                                                  alteration_effect_in_approved_discount=instance.amount - instance._prev_version.amount)
            if created:
                if instance.booking.status == Booking.CONFIRMED:
                    booking_services.update_latest_booking_financials(instance.booking.id,
                                                                      alteration_effect_in_approved_discount=instance.amount)
                instance.collection_currency = instance.booking.collection_currency
                instance.save()
            bookings.on_commit(lambda: booking_services.update_booking_financial_v2(instance.booking.id))

    except Exception as e:
        return True


@receiver(post_save, sender=BookingCharges)
@skip_signal()
def booking_charges_post_save(sender, instance, created, **kwargs):
    try:
        if instance and instance.booking:
            instance.skip_signal = True
            amount_in_collection_currency = get_round_off_amount(
                (float(instance.booking.amount) + instance.service_charge_collected_from_buyer) * (
                        instance.roe_on_booking_date + instance.convenience_charges_on_roe),
                instance.booking.collection_currency.id if instance.booking.collection_currency else None, True)
            booking_services.update_booking(instance.booking.id,
                                            amount_in_collection_currency=amount_in_collection_currency,
                                            amount_in_inr=amount_in_collection_currency)
            instance.save()
            booking_services.update_booking_financial_v2(instance.booking.id)
    except Exception as e:
        return True


@receiver(pre_save, sender=ReleaseRequestPayments)
def release_request_payments_pre_save(sender, instance, **kwargs):
    if instance.pk:
        prev_instance = ReleaseRequestPayments.objects.get(pk=instance.pk)
        instance._prev_version = prev_instance


@receiver(post_save, sender=ReleaseRequestPayments)
def release_request_payments_post_save(sender, instance, created, **kwargs):
    prev_version_instance = getattr(instance, '_prev_version', None)
    update_fx_profit_loss_for_booking(instance, prev_version_instance)
