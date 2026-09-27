import datetime
from django.conf import settings
from django.contrib import admin
from django.db import models
from django.forms import Textarea
from django.urls import reverse
from django.utils.safestring import mark_safe
from common.libraries import get_numbers_formatted_to_indian_locale
from members.services import OrganizationServices as organization
from bms.config.base import SELLER_COST_COMPONENT_CANCELLED_ID
from bms.custom_formset import PlannedPaymentScheduleInlineFormset, PlannedPaymentCollectionInlineFormset, \
    PlannedPaymentEditAllFieldsFormset
from bms.models import Booking, BookingCancellationProxy, BookingRefundProxy, PlannedPayment
from bms.models.seller_cost_component.seller_cost_component import SellerCostComponent
from bms.services import member, bookings as bookings
from bms.forms import PlannedPaymentEditAllFieldsForm


class PlannedPaymentInline(admin.TabularInline):
    model = PlannedPayment
    readonly_fields = ['id', 'get_actual_payment_amount', 'member_currency', 'amount_in_collection_currency',
                       'actual_payment_amount_in_collection_currency', 'created_at', 'created_by']
    list_display = [field.name for field in PlannedPayment._meta.get_fields()]
    fields = ['member', 'organization', 'member_currency', 'amount', 'amount_in_collection_currency',
              'get_actual_payment_amount', 'actual_payment_amount_in_collection_currency', 'date', 'status',
              'payment_type', 'type',
              'remark']
    autocomplete_fields = ['member', 'organization', 'member_currency']

    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 1, 'cols': 20})},
    }

    def get_fields(self, request, obj=None):
        return ['member', 'organization', 'member_currency', 'amount', 'amount_in_collection_currency',
                'get_actual_payment_amount', 'actual_payment_amount_in_collection_currency', 'date', 'status',
                'payment_type', 'type',
                'remark', 'created_at', 'created_by']

    def get_pending_amount(self, obj):
        return get_numbers_formatted_to_indian_locale(obj.amount - obj.actual_payment_amount)

    def get_actual_payment_amount(self, obj):
        return get_numbers_formatted_to_indian_locale(obj.actual_payment_amount)

    def cancel_tranche(self, obj):
        if obj.id and obj.status == PlannedPayment.PENDING and obj.payment_type in [PlannedPayment.TRANCHE]:
            return mark_safe("<a href='{}'>Cancel Now</a>".format(
                reverse('bms:booking_cancellation_cancel_planned_tranche',
                        args=[obj.booking.id, obj.id, BookingRefundProxy.__name__
                              ])))
        else:
            return "NA"

    get_pending_amount.short_description = "Amount Pending (Member Currency)"
    get_actual_payment_amount.short_description = 'Actual Payment Amount'

    def initiate_refund_process(self, obj):
        if obj.id and obj.status == PlannedPayment.PENDING and obj.payment_type in [
            PlannedPayment.REFUND] and obj.type == PlannedPayment.DUE_TO_MEMBER:
            return mark_safe(
                "<a href='{}'>Initiate Refund</a>".format(
                    reverse('bms:booking_refund_select_refund_options', args=[obj.id])))
        else:
            return "NA"

    def get_queryset(self, request):
        qs = super(PlannedPaymentInline, self).get_queryset(request).select_related('organization', 'member',
                                                                                    'booking', 'booking__type',
                                                                                    'booking__buyer',)
        return qs


class PlannedPaymentScheduleInline(PlannedPaymentInline):
    readonly_fields = ['id', 'type', 'status', 'initiate_refund_process', 'remark',
                       'amount_in_collection_currency',
                       'get_actual_collected_amount_in_member_currency',
                       'get_actual_collected_amount_in_collection_currency',
                       'get_pending_amount', 'claim_via_wallet', 'organization',
                       'member_currency', 'created_at', 'created_by']

    autocomplete_fields = ['member_currency']

    formset = PlannedPaymentScheduleInlineFormset

    def get_fields(self, request, obj=None):
        if obj:
            return ['id', 'member', 'member_currency', 'amount', 'date', 'amount_in_collection_currency',
                    'get_actual_collected_amount_in_member_currency',
                    'get_actual_collected_amount_in_collection_currency', 'get_pending_amount', 'status',
                    'payment_type', 'initiate_refund_process', 'remark', 'claim_via_wallet', 'organization',
                    'created_at', 'created_by']


    def claim_via_wallet(self, obj):
        if obj and obj.id and obj.organization.id and obj.status == PlannedPayment.PENDING and obj.payment_type in [
            PlannedPayment.TRANCHE, PlannedPayment.REFUND,
            PlannedPayment.CANCELLATION_FINAL_SETTLEMENT]:
            return mark_safe("<a href='{}?booking_id={}' target='_booking'>Claim Payment</a>".format(
                reverse('bms:wallet__claim__select__bookings',
                        args=[obj.organization.id, obj.member.id,
                              settings.SERVICE_BOOKING_ID,
                              max(obj.date, datetime.datetime.now().date())]),
                obj.booking.id))
        else:
            return "--------"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "member":
            if request.resolver_match.kwargs:
                try:
                    object_id = int(request.resolver_match.kwargs['object_id'])
                    booking_obj = Booking.objects.get(id=object_id)
                except:
                    booking_obj = Booking.objects.get(code=request.resolver_match.kwargs['object_id'])
                kwargs["queryset"] = member.get_member_queryset_from_member_ids(
                    [booking_obj.buyer.id])
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == "status":
            kwargs['choices'] = (
                (PlannedPayment.PENDING, PlannedPayment.PENDING),
                (PlannedPayment.COLLECTED, PlannedPayment.COLLECTED),
            )
        if db_field.name == 'payment_type':
            kwargs['choices'] = (
                (PlannedPayment.TRANCHE, 'Tranche'),
                (PlannedPayment.DIRECT_PAYMENT, 'Direct payment'),
            )
        return super(PlannedPaymentScheduleInline, self).formfield_for_choice_field(db_field, request, **kwargs)

    def get_queryset(self, request):
        qs = super(PlannedPaymentScheduleInline, self).get_queryset(request)
        return qs.filter(type=PlannedPayment.DUE_ON_MEMBER).order_by('date')

    def has_change_permission(self, request, obj=None):
        return False

    def get_actual_collected_amount_in_member_currency(self, obj):
        return get_numbers_formatted_to_indian_locale(obj.actual_payment_amount)

    def get_actual_collected_amount_in_collection_currency(self, obj):
        return get_numbers_formatted_to_indian_locale(obj.actual_payment_amount_in_collection_currency)

    get_actual_collected_amount_in_member_currency.short_description = 'Actual Collected Amount (Member Currency)'
    get_actual_collected_amount_in_collection_currency.short_description = 'Actual Collected Amount (Collection Currency)'

    verbose_name_plural = "Scheduled Collection"




class PlannedPaymentCollectionInline(PlannedPaymentInline):
    fields = ['id', 'member', 'member_currency', 'amount', 'amount_in_collection_currency',
              'get_actual_payment_amount_in_member_currency', 'get_actual_payment_amount_in_collection_currency',
              'get_pending_amount', 'date', 'status',
              'payment_type', 'initiate_refund_process', 'remark', 'release_request_via_wallet', 'organization']

    readonly_fields = ['id', 'type', 'status', 'initiate_refund_process', 'remark', 'amount_in_collection_currency',
                       'get_actual_payment_amount_in_member_currency',
                       'get_actual_payment_amount_in_collection_currency', 'get_pending_amount',
                       'release_request_via_wallet', 'organization',
                       'member_currency', 'created_at', 'created_by']

    autocomplete_fields = ['member_currency']
    formset = PlannedPaymentCollectionInlineFormset

    def get_fields(self, request, obj=None):
        if obj:
            return ['id', 'member', 'member_currency', 'amount', 'date', 'amount_in_collection_currency',
                    'get_actual_payment_amount_in_member_currency',
                    'get_actual_payment_amount_in_collection_currency', 'get_pending_amount', 'status',
                    'payment_type', 'initiate_refund_process', 'remark', 'release_request_via_wallet',
                    'organization', 'created_at', 'created_by']

    def release_request_via_wallet(self, obj):
        if obj and obj.id and obj.organization.id and obj.payment_type in [PlannedPayment.TRANCHE,
                                                                           PlannedPayment.CANCELLATION_FINAL_SETTLEMENT] and obj.status in [
            PlannedPayment.PENDING]:
            return mark_safe(
                "<a href='{}?booking_id={}&planned_payment_id={}' target='_booking'>Create Release Request</a>".format(
                    reverse('bms:wallet_release_request_select_booking',
                            args=[settings.SERVICE_BOOKING_ID, obj.member.id,
                                  obj.organization.id,
                                  max(obj.date, datetime.datetime.now().date()),
                                  obj.booking.booking_date, obj.booking.booking_date]),
                    obj.booking.id, obj.id))
        else:
            return "-bbc"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "member":
            if request.resolver_match.kwargs:
                try:
                    object_id = int(request.resolver_match.kwargs['object_id'])
                    booking_obj = Booking.objects.get(id=object_id)
                except:
                    booking_obj = Booking.objects.get(code=request.resolver_match.kwargs['object_id'])
                objects = SellerCostComponent.objects.filter(booking__code=booking_obj.code).exclude(
                    seller_status__id=SELLER_COST_COMPONENT_CANCELLED_ID)
                member_ids = []
                for obj in objects:
                    if obj.seller_member:
                        member_ids.append(obj.seller_member.id)
                kwargs["queryset"] = member.get_member_queryset_from_member_ids(member_ids)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == "status":
            kwargs['choices'] = (
                (PlannedPayment.PENDING, PlannedPayment.PENDING),
                (PlannedPayment.PAID, PlannedPayment.PAID),
            )
        if db_field.name == 'payment_type':
            kwargs['choices'] = (
                (PlannedPayment.TRANCHE, 'Tranche'),
                (PlannedPayment.DIRECT_PAYMENT, 'Direct payment'),
            )
        return super(PlannedPaymentCollectionInline, self).formfield_for_choice_field(db_field, request, **kwargs)

    def get_queryset(self, request):
        qs = super(PlannedPaymentCollectionInline, self).get_queryset(request)
        return qs.filter(type=PlannedPayment.DUE_TO_MEMBER).order_by('date')

    def get_actual_payment_amount_in_member_currency(self, obj):
        return get_numbers_formatted_to_indian_locale(obj.actual_payment_amount)

    def get_actual_payment_amount_in_collection_currency(self, obj):
        return get_numbers_formatted_to_indian_locale(obj.actual_payment_amount_in_collection_currency)

    get_actual_payment_amount_in_member_currency.short_description = 'Actual Payment in Member Currency'
    get_actual_payment_amount_in_collection_currency.short_description = 'Actual Payment in Collection Currency'

    verbose_name_plural = "Scheduled Payment"


class CancellationPlannedPaymentInline(admin.TabularInline):
    model = PlannedPayment

    list_display = [field.name for field in PlannedPayment._meta.get_fields()]
    fields = ['id', 'member', 'amount', 'date', 'status', 'payment_type', 'cancel_tranche', 'organization']
    readonly_fields = ['id', 'cancel_tranche']
    extra = 0

    def cancel_tranche(self, obj):
        if obj.status == PlannedPayment.PENDING and obj.payment_type in [PlannedPayment.TRANCHE,
                                                                         PlannedPayment.DIRECT_PAYMENT,
                                                                         PlannedPayment.CANCELLATION_FINAL_SETTLEMENT]:
            return mark_safe("<a href='{}'>Cancel Now</a>".format(
                reverse('trs:booking_cancellation_cancel_planned_tranche',
                        args=[obj.booking.id, obj.id, BookingCancellationProxy.__name__])))
        else:
            return "NA"



class CancellationPlannedPaymentCollectionInline(CancellationPlannedPaymentInline):
    readonly_fields = ['id', 'cancel_tranche', 'remark', 'created_at', 'created_by']
    extra = 0

    def get_fields(self, request, obj=None):
        if obj:
            return ['id', 'member', 'organization', 'amount', 'amount_in_collection_currency', 'date', 'status',
                    'payment_type', 'cancel_tranche', 'remark', 'created_at', 'created_by']

    def get_queryset(self, request):
        qs = super(CancellationPlannedPaymentCollectionInline, self).get_queryset(request)
        return qs.filter(type=PlannedPayment.DUE_TO_MEMBER).order_by('date')

    verbose_name_plural = "Scheduled Payment"


class CancellationPlannedPaymentScheduleInline(CancellationPlannedPaymentInline):
    readonly_fields = ['id', 'cancel_tranche', 'claim', 'remark', 'created_at', 'created_by']
    extra = 0

    def claim(self, obj):
        if obj and obj.id and obj.status not in [PlannedPayment.COLLECTED,
                                                 PlannedPayment.CANCELLED] and obj.payment_type in [
            PlannedPayment.TRANCHE,
            PlannedPayment.CANCELLATION_FINAL_SETTLEMENT]:
            return mark_safe("<a href='{}' target='_booking'>Claim</a>".format(
                reverse('admin:accounts_bankrecord_changelist')))
        else:
            return "-"

    def get_fields(self, request, obj=None):
        if obj:
            return ['id', 'member', 'member_currency', 'amount', 'amount_in_collection_currency', 'date', 'status',
                    'payment_type', 'claim', 'remark', 'created_at', 'created_by']

    def get_queryset(self, request):
        qs = super(CancellationPlannedPaymentScheduleInline, self).get_queryset(request)
        return qs.filter(type=PlannedPayment.DUE_ON_MEMBER).order_by('date')

    verbose_name_plural = "Scheduled Collection"


class RefundPlannedPaymentToCollectInline(PlannedPaymentInline):
    fields = ['id', 'member', 'organization', 'amount', 'date', 'status', 'cancel_tranche', 'payment_type', 'type', ]
    autocomplete_fields = []
    readonly_fields = ['id', 'status', 'cancel_tranche', 'member_currency', 'amount_in_collection_currency',
                       'created_at', 'created_by']
    extra = 0

    def get_fields(self, request, obj=None):
        return ['id', 'member', 'organization', 'member_currency', 'amount', 'amount_in_collection_currency',
                'date', 'status', 'cancel_tranche', 'payment_type', 'type', 'created_at', 'created_by']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "member":
            if request.resolver_match.kwargs:
                try:
                    object_id = int(request.resolver_match.kwargs['object_id'])
                    booking_obj = Booking.objects.get(id=object_id)
                except:
                    booking_obj = Booking.objects.get(code=request.resolver_match.kwargs['object_id'])
                kwargs["queryset"] = member.get_member_queryset_from_member_ids([booking_obj.buyer.id]
                                                                                + [
                                                                                    cost_component.seller_member.id if cost_component.seller_member else None
                                                                                    for cost_component in
                                                                                    bookings.get_seller_cost_components_by_booking_code(
                                                                                        booking_obj.code)])

        if db_field.name == "organization":
            if request.resolver_match.kwargs:
                booking_obj = Booking.objects.get(id=request.resolver_match.kwargs['object_id'])
                kwargs["queryset"] = organization.get_organization_queryset_from_organization_ids(
                    [booking_obj.buyer_organization.id] + [
                        cost_component.seller_organization.id if cost_component.seller_organization else None for
                        cost_component in bookings.get_seller_cost_components_by_booking_code(booking_obj.code)])
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == 'payment_type':
            kwargs['choices'] = (
                (PlannedPayment.REFUND, 'Refund'),
            )
        if db_field.name == 'type':
            kwargs['choices'] = (
                (PlannedPayment.DUE_ON_MEMBER, 'To Collect'),
            )
        return super(RefundPlannedPaymentToCollectInline, self).formfield_for_choice_field(db_field, request, **kwargs)

    def cancel_tranche(self, obj):
        if obj.id and obj.status == PlannedPayment.PENDING and obj.payment_type in [PlannedPayment.TRANCHE,
                                                                                    PlannedPayment.REFUND]:
            return mark_safe("<a href='{}'>Cancel Now</a>".format(
                reverse('bms:booking_cancellation_cancel_planned_tranche',
                        args=[obj.booking.id, obj.id, BookingRefundProxy.__name__
                              ])))
        else:
            return "NA"

    def get_queryset(self, request):
        qs = super(RefundPlannedPaymentToCollectInline, self).get_queryset(request)
        return qs.filter(type=PlannedPayment.DUE_ON_MEMBER).order_by('date')

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj):
        if obj and hasattr(obj, 'booking_details') and obj.booking_details.is_completed:
            return False
        return True

    verbose_name_plural = "Scheduled Collection"


class RefundPlannedPaymentToPayInline(PlannedPaymentInline):
    fields = ['id', 'member', 'organization', 'amount', 'date', 'status', 'cancel_tranche', 'payment_type', 'type', ]
    readonly_fields = ['id', 'status', 'cancel_tranche', 'member_currency', 'amount_in_collection_currency',
                       'created_at', 'created_by']
    autocomplete_fields = []
    extra = 0

    def get_fields(self, request, obj=None):
        return ['id', 'member', 'organization', 'member_currency', 'amount', 'amount_in_collection_currency',
                'date', 'status', 'cancel_tranche', 'payment_type', 'type', 'created_at', 'created_by']

    def cancel_tranche(self, obj):
        if obj.id and obj.status == PlannedPayment.PENDING and obj.payment_type in [PlannedPayment.TRANCHE,
                                                                                    PlannedPayment.REFUND]:
            return mark_safe("<a href='{}'>Cancel Now</a>".format(
                reverse('bms:booking_cancellation_cancel_planned_tranche',
                        args=[obj.booking.id, obj.id, BookingRefundProxy.__name__
                              ])))
        else:
            return "NA"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "member":
            if request.resolver_match.kwargs:
                try:
                    object_id = int(request.resolver_match.kwargs['object_id'])
                    booking_obj = Booking.objects.get(id=object_id)
                except:
                    booking_obj = Booking.objects.get(code=request.resolver_match.kwargs['object_id'])
                kwargs["queryset"] = member.get_member_queryset_from_member_ids([booking_obj.buyer.id]
                                                                                + [
                                                                                    cost_component.seller_member.id if cost_component.seller_member else None
                                                                                    for cost_component in
                                                                                    bookings.get_seller_cost_components_by_booking_code(
                                                                                        booking_obj.code)])

        if db_field.name == "organization":
            if request.resolver_match.kwargs:
                booking_obj = Booking.objects.get(id=request.resolver_match.kwargs['object_id'])
                kwargs["queryset"] = organization.get_organization_queryset_from_organization_ids(
                    [booking_obj.buyer_organization.id] + [
                        cost_component.seller_organization.id if cost_component.seller_organization else None for
                        cost_component in
                        bookings.get_seller_cost_components_by_booking_code(booking_obj.code)])

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == 'payment_type':
            kwargs['choices'] = (
                (PlannedPayment.REFUND, 'Refund'),
            )
        if db_field.name == 'type':
            kwargs['choices'] = (
                (PlannedPayment.DUE_TO_MEMBER, 'To Pay'),
            )
        return super(RefundPlannedPaymentToPayInline, self).formfield_for_choice_field(db_field, request, **kwargs)

    def get_queryset(self, request):
        qs = super(RefundPlannedPaymentToPayInline, self).get_queryset(request)
        return qs.filter(type=PlannedPayment.DUE_TO_MEMBER).order_by('date')

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj):
        if obj and hasattr(obj, 'booking_details') and obj.booking_details.is_completed:
            return False
        return True

    verbose_name_plural = "Scheduled Payment"
