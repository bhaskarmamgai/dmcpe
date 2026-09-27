from django.db import connection
from bms.models.actual_payment.actual_payment import ActualPayment
from bms.models.release_request.release_request import ReleaseRequest
from bms.models.planned_payment.planned_payment import PlannedPayment
from bms.models import Booking, SellerCostComponent
from django.db.models import Sum, F, Q
from bms.serializers.booking import PlannedPaymentSerializer
import datetime
from rest_framework import exceptions
from bms.config.base import SELLER_COST_COMPONENT_CANCELLED_ID



def get_bookings_where_collection_is_due_as_on_given_date(date, member_id):
    """This function will calculate pending amount for a
    given bookings/booking"""
    query = "select t.id as booking_id,t.amount_in_inr as amount_in_inr, " \
            "p.planned_payment, " \
            "COALESCE(a.actual_payment, 0) as actual_payment, " \
            "round((p.planned_payment - COALESCE(a.actual_payment, 0))::numeric, 2) as due_amount " \
            "from bms_booking as t " \
            "join ( " \
            "select booking_id, sum(amount) planned_payment " \
            "from bms_plannedpayment " \
            "where member_id = %s and date <= %s::date and type = %s and status != %s and (payment_type IN (%s,%s,%s))" \
            "group by booking_id " \
            ") as p " \
            "on t.id = p.booking_id " \
            "left join ( " \
            "select booking_id, sum(amount) actual_payment " \
            "from bms_actualpayment " \
            "where member_id = %s and  type = %s " \
            "group by booking_id " \
            ") as a " \
            "on t.id = a.booking_id " \
            "where (t.buyer_id = %s or t.seller_id = %s) and t.deleted = 0 " \
            "and p.planned_payment - COALESCE(a.actual_payment, 0) > 0 "

    with connection.cursor() as cursor:
        cursor.execute(query,
                       [member_id, date, PlannedPayment.DUE_ON_MEMBER, PlannedPayment.CANCELLED, PlannedPayment.TRANCHE,
                        PlannedPayment.CANCELLATION_FINAL_SETTLEMENT, PlannedPayment.REFUND, member_id,
                        ActualPayment.PAID_BY_MEMBER,
                        member_id, member_id])
        col = [col[0] for col in cursor.description]
        rows = [dict(zip(col, row)) for row in cursor.fetchall()]
        return rows


def get_bookings_where_collection_is_due_as_on_given_date_with_booking_id(date, booking_id):
    query = "select t.id as booking_id, " \
            "COALESCE(p.planned_payment, 0) as buyer_planned_payment, " \
            "COALESCE(a.actual_payment, 0) as buyer_actual_payment, " \
            "GREATEST(COALESCE(p.planned_payment, 0) - COALESCE(a.actual_payment, 0), 0) as buyer_due_amount " \
            "from bms_booking as t " \
            "left join ( " \
            "select booking_id, sum(amount) planned_payment " \
            "from bms_plannedpayment " \
            "where date <= %s::date and type = %s and status != %s and (payment_type IN (%s,%s,%s))  " \
            "group by booking_id " \
            ") as p " \
            "on t.id = p.booking_id " \
            "left join ( " \
            "select booking_id, sum(amount) actual_payment " \
            "from bms_actualpayment " \
            "where type = %s" \
            "group by booking_id " \
            ") as a " \
            "on t.id = a.booking_id " \
            "where t.id = %s and t.deleted = 0 "
    with connection.cursor() as cursor:
        cursor.execute(query,
                       [date, PlannedPayment.DUE_ON_MEMBER, PlannedPayment.CANCELLED, PlannedPayment.TRANCHE,
                        PlannedPayment.CANCELLATION_FINAL_SETTLEMENT, PlannedPayment.REFUND,
                        ActualPayment.PAID_BY_MEMBER,
                        booking_id])
        col = [col[0] for col in cursor.description]
        rows = [dict(zip(col, row)) for row in cursor.fetchall()]
        return rows


def get_bookings_where_collection_is_due_as_on_given_date_with_booking_id_v2(date, booking_id):
    query = "select t.id as booking_id, " \
            "COALESCE(p.planned_payment, 0) as buyer_planned_payment, " \
            "COALESCE(a.actual_payment, 0) as buyer_actual_payment, " \
            "GREATEST(COALESCE(p.planned_payment, 0) - COALESCE(a.actual_payment, 0), 0) as buyer_due_amount " \
            "from (select * from bms_booking t where t.id = %s and t.is_deleted = false) as t " \
            "left join ( " \
            "select booking_id, sum(amount) planned_payment " \
            "from bms_plannedpayment " \
            "where booking_id=%s and date <= %s::date and type = %s and status != %s and (payment_type IN (%s,%s,%s))  " \
            "group by booking_id " \
            ") as p " \
            "on t.id = p.booking_id " \
            "left join ( " \
            "select booking_id, sum(amount) actual_payment " \
            "from bms_actualpayment " \
            "where booking_id=%s and type = %s" \
            "group by booking_id " \
            ") as a " \
            "on t.id = a.booking_id "
    with connection.cursor() as cursor:
        cursor.execute(query,
                       [booking_id, booking_id, date, PlannedPayment.DUE_ON_MEMBER, PlannedPayment.CANCELLED, PlannedPayment.TRANCHE,
                        PlannedPayment.CANCELLATION_FINAL_SETTLEMENT, PlannedPayment.REFUND, booking_id,
                        ActualPayment.PAID_BY_MEMBER])
        col = [col[0] for col in cursor.description]
        rows = [dict(zip(col, row)) for row in cursor.fetchall()]
        return rows


def update_planned_payment_record_for_scheduled_collection(booking_ids, member_id):
    if booking_ids:
        for booking_id in booking_ids:
            actual_payment_sum_paid_by_member = ActualPayment.objects.filter(booking_id=booking_id,
                                                                             member_id=member_id,
                                                                             type=ActualPayment.PAID_BY_MEMBER).aggregate(
                Sum('amount'))




            """
                (Revised Formula For Refund Tranches)
                Old Formulae: [Sum[Collected]- Paid] - Already Marked Collected
                New Suggested Formulae: Sum[Collected] - Already Marked Collected
            """
            planned_payment_marked_collected = PlannedPayment.objects.filter(booking_id=booking_id,
                                                                             member_id=member_id,
                                                                             status=PlannedPayment.COLLECTED,
                                                                             type=PlannedPayment.DUE_ON_MEMBER).exclude(
                payment_type__in=[PlannedPayment.DIRECT_PAYMENT]).aggregate(
                Sum('amount'))

            pending_planned_payment_objects = PlannedPayment.objects.filter(booking_id=booking_id,
                                                                            member_id=member_id,
                                                                            status=PlannedPayment.PENDING,
                                                                            type=PlannedPayment.DUE_ON_MEMBER).exclude(
                payment_type__in=[PlannedPayment.DIRECT_PAYMENT]).order_by(
                'date')



            print(f"[update_planned_payment_record_for_scheduled_collection]Id: {booking_id},. Actual Amount {actual_payment_sum_paid_by_member}, "
                           f"Planned Payment Paid {planned_payment_marked_collected}")
            from bms.providers.bookings import get_booking_object_from_id
            booking_obj =get_booking_object_from_id(booking_id)
            actual_payment_collected = actual_payment_sum_paid_by_member['amount__sum'] or 0
            if actual_payment_collected:
                planned_payment_amount_to_be_mark_collected = round(
                    actual_payment_collected - (planned_payment_marked_collected['amount__sum'] or 0), 2)
                val = planned_payment_amount_to_be_mark_collected
                for obj in pending_planned_payment_objects:
                    if obj.amount <= val:
                        obj.status = PlannedPayment.COLLECTED
                        obj.actual_payment_amount = obj.amount
                        if booking_obj.buyer.id == int(member_id):
                            from bms.providers.bookings import calculate_amount_in_collection_currency_for_collection
                            obj.actual_payment_amount_in_collection_currency = calculate_amount_in_collection_currency_for_collection(
                                booking_obj.collection_currency.id, obj.member_currency.id, booking_obj.created_at, obj.amount)
                        else:
                            from bms.providers.bookings import calculate_amount_in_collection_currency_for_payment
                            seller_cost_components = SellerCostComponent.objects.filter(
                                seller_member__id=obj.member.id,
                                booking__code=obj.bookings.code).exclude(seller_status__id=SELLER_COST_COMPONENT_CANCELLED_ID)
                            obj.actual_payment_amount_in_collection_currency = calculate_amount_in_collection_currency_for_payment(
                                booking_obj.collection_currency.id, obj.amount, seller_cost_components)
                        obj.save()
                        val = val - obj.amount
                    else:
                        obj.actual_payment_amount = val
                        if booking_obj.buyer.id == int(member_id):
                            from bms.providers.bookings import calculate_amount_in_collection_currency_for_collection
                            obj.actual_payment_amount_in_collection_currency = calculate_amount_in_collection_currency_for_collection(
                                booking_obj.collection_currency.id, obj.member_currency.id, booking_obj.created_at,val)
                        else:
                            from bms.providers.bookings import calculate_amount_in_collection_currency_for_payment
                            seller_cost_components = SellerCostComponent.objects.filter(
                                seller_member__id=obj.member.id,
                                booking__code=obj.bookings.code).exclude(seller_status__id=SELLER_COST_COMPONENT_CANCELLED_ID)
                            obj.actual_payment_amount_in_collection_currency = calculate_amount_in_collection_currency_for_payment(
                                booking_obj.collection_currency.id, val, seller_cost_components)
                        obj.save()
                        break
        return True


def update_planned_payment_record_for_scheduled_payment(booking_ids, member_id):
    if booking_ids:
        for booking_id in booking_ids:
            from bms.providers.bookings import get_booking_object_from_id
            booking_obj = get_booking_object_from_id(booking_id)
            actual_payment_paid_to_member = ActualPayment.objects.filter(Q(booking_id=booking_id,
                                                                           member_id=member_id,
                                                                           type=ActualPayment.PAID_TO_MEMBER) & (Q(
                release_request__status=ReleaseRequest.RELEASED) | Q(record__isnull=False))).aggregate(
                Sum('amount'))
            planned_payment_sum_marked_paid = PlannedPayment.objects.filter(booking_id=booking_id,
                                                                            member_id=member_id,
                                                                            status=PlannedPayment.PAID,
                                                                            type=PlannedPayment.DUE_TO_MEMBER).exclude(
                payment_type__in=[PlannedPayment.DIRECT_PAYMENT]).aggregate(
                Sum('amount'))

            pending_planned_payment_objects = PlannedPayment.objects.filter(booking_id=booking_id,
                                                                            member_id=member_id,
                                                                            status=PlannedPayment.PENDING,
                                                                            type=PlannedPayment.DUE_TO_MEMBER).exclude(
                payment_type__in=[PlannedPayment.DIRECT_PAYMENT]).order_by(
                'date')
            print(f"[update_planned_payment_record_for_scheduled_payment]Id: {booking_id},. Actual Amount {actual_payment_paid_to_member}, "
                           f"Planned Payment Paid {planned_payment_sum_marked_paid}")
            if actual_payment_paid_to_member['amount__sum'] or 0:
                planned_payment_amount_to_be_mark_paid = round(
                    (actual_payment_paid_to_member['amount__sum'] or 0) - (
                            planned_payment_sum_marked_paid['amount__sum'] or 0),
                    2)
                val = planned_payment_amount_to_be_mark_paid
                for obj in pending_planned_payment_objects:
                    seller_cost_components = None
                    if obj.amount <= val:
                        obj.status = PlannedPayment.PAID
                        obj.actual_payment_amount = obj.amount
                        if booking_obj.buyer.id == int(member_id):
                            obj.actual_payment_amount_in_collection_currency = calculate_amount_in_collection_currency_for_collection(
                                obj.booking.collection_currency.id, obj.member_currency.id,
                                booking_obj.created_at, obj.actual_payment_amount
                            )

                            obj.save()
                            val = val - obj.amount
                    else:
                        obj.actual_payment_amount = val
                        if booking_obj.buyer.id == int(member_id):
                            from bms.providers.bookings import calculate_amount_in_collection_currency_for_collection
                            obj.actual_payment_amount_in_collection_currency = calculate_amount_in_collection_currency_for_collection(
                                obj.booking.collection_currency.id, obj.member_currency.id,
                                booking_obj.created_at, obj.actual_payment_amount
                            )
                        else:
                            from bms.providers.bookings import calculate_amount_in_collection_currency_for_payment
                            seller_cost_components = SellerCostComponent.objects.filter(
                                seller_member__id=obj.member.id,
                                booking__code=obj.booking.code).exclude(seller_status__id=SELLER_COST_COMPONENT_CANCELLED_ID)
                            obj.actual_payment_amount_in_collection_currency = calculate_amount_in_collection_currency_for_payment(
                                obj.booking.collection_currency.id, obj.actual_payment_amount,
                                    seller_cost_components)
                        obj.save()
                        break
        return True


def create_planned_payment_record(booking_id, members_ids: list, organization_ids: list, amounts: list,
                                  payment_types: list, **kwargs):
    data = []
    for member_id, organization_id, amount, payment_type in zip(members_ids, organization_ids, amounts, payment_types):
        if amount and float(amount):
            from bms.providers.bookings import get_booking_object_from_id
            booking_obj = get_booking_object_from_id(booking_id)
            amount_in_collection_currency = None
            if booking_obj.booking_version_type == "v2":
                if booking_obj.buyer.id == int(member_id):
                    from bms.providers.bookings import calculate_amount_in_collection_currency_for_collection
                    amount_in_collection_currency = calculate_amount_in_collection_currency_for_collection(
                        booking_obj.collection_currency.id, int(kwargs.get('currency_id')),
                        booking_obj.created_at, float(amount)) if kwargs.get('currency_id') and booking_obj.collection_currency else 0
                else:
                    from bms.providers.bookings import get_seller_cost_components_by_booking_code, calculate_amount_in_collection_currency_for_payment
                    seller_cost_components = get_seller_cost_components_by_booking_code(booking_obj.code,
                                                                                        seller_member__id=member_id)
                    amount_in_collection_currency = calculate_amount_in_collection_currency_for_payment(
                        booking_obj.collection_currency.id, amount, seller_cost_components)
            data.append({
                'member_id': member_id,
                'organization_id': organization_id,
                'booking_id': booking_id,
                'amount': amount,
                'amount_in_collection_currency': amount_in_collection_currency if booking_obj.booking_version_type == Booking.V2 and kwargs.get('currency_id') else 0,
                'member_currency_id': kwargs.get('currency_id'),
                'date': kwargs.get('date') if kwargs.get('date') else datetime.datetime.now().date(),
                'type': payment_type,
                'status': PlannedPayment.PENDING,
                'payment_type': kwargs.get('payment_type', PlannedPayment.TRANCHE),
                'created_by_id': kwargs.get('created_by_id')
            })
    if data:
        planned_payment_serializer_obj = PlannedPaymentSerializer(many=True, data=data)
        if planned_payment_serializer_obj.is_valid():
            return planned_payment_serializer_obj.save()
        else:
            raise Exception(planned_payment_serializer_obj.errors)
    return None


def create_planned_payment_record_v2(booking_id, members_ids: list, organization_ids: list, amounts: list,
                                     payment_types: list, **kwargs):
    data = []
    due_dates = kwargs.get('due_dates')
    currencies = kwargs.get('currencies')
    for member_id, organization_id, amount, payment_type, due_date, currency_id in zip(members_ids, organization_ids, amounts, payment_types, due_dates, currencies):
        from bms.providers.bookings import get_booking_object_from_id
        booking_obj = get_booking_object_from_id(booking_id)
        if amount and float(amount):
            amount_in_collection_currency = None
            seller_currency = currency_id
            collection_currency_id = booking_obj.collection_currency.id
            booking_date = booking_obj.created_at
            if booking_obj.buyer.id == int(member_id):
                from bms.providers.bookings import calculate_amount_in_collection_currency_for_collection
                amount_in_collection_currency = calculate_amount_in_collection_currency_for_collection(
                    collection_currency_id, int(currency_id),
                    booking_date, float(amount)) if currency_id and collection_currency_id else 0
            else:
                from bms.providers.bookings import get_seller_cost_components_by_booking_code, calculate_amount_in_collection_currency_for_payment
                seller_cost_components = get_seller_cost_components_by_booking_code(booking_obj.code,
                                                                                    seller_member__id=member_id)
                seller_currency = seller_cost_components[0].seller_currency_id
                amount_in_collection_currency = calculate_amount_in_collection_currency_for_payment(
                    collection_currency_id, float(amount), seller_cost_components)
            data.append({
                'member_id': member_id,
                'organization_id': organization_id,
                'booking_id': booking_id,
                'amount': amount,
                'amount_in_collection_currency': amount_in_collection_currency,
                'date': due_date,
                'type': payment_type,
                'member_currency_id': seller_currency,
                'status': PlannedPayment.PENDING,
                'payment_type': kwargs.get('payment_type', PlannedPayment.TRANCHE),
                'created_by_id': kwargs.get('created_by_id')
            })
    if data:
        planned_payment_serializer_obj = PlannedPaymentSerializer(many=True, data=data)
        if planned_payment_serializer_obj.is_valid():
            return planned_payment_serializer_obj.save()
        else:
            raise Exception(planned_payment_serializer_obj.errors)
    return None


def update_planned_payment_status(status: str, planned_payment_id: int):
    planned_payment_obj = PlannedPayment.objects.get(id=planned_payment_id)
    planned_payment_obj.status = status
    return planned_payment_obj.save()


def get_planned_payments_with_status_and_booking_id(status: str, booking_id: int):
    return PlannedPayment.objects.filter(booking_id=booking_id, status=status)


def get_planned_payment_objects(**kwargs):
    filters = {
        'transaction__deleted': False
    }

    fields = ['booking_id', 'member_id', 'type', 'payment_type', 'status', 'date', 'date__lt',
              'transaction__booking_date__gte']
    for field in fields:
        if field in kwargs and kwargs.get(field) is not None:
            if isinstance(kwargs.get(field), list):
                filters['{0}__{1}'.format(field, 'in')] = kwargs.get(field)
            else:
                filters[field] = kwargs.get(field)
    qs = PlannedPayment.objects.filter(**filters)
    if len(filters) > 0:
        return qs
    else:

        return qs[0:100]


def get_total_amount_scheduled_for_collection_for_given_booking_from_given_member(booking, member):
    qs = get_planned_payment_objects(booking_id=booking.id, member_id=member.id, type=PlannedPayment.DUE_ON_MEMBER,
                                     payment_type=[PlannedPayment.TRANCHE,
                                                   PlannedPayment.CANCELLATION_FINAL_SETTLEMENT],
                                     status=[PlannedPayment.PENDING, PlannedPayment.PAID])

    amount_scheduled_for_collection = qs.aggregate(Sum('amount'))
    return amount_scheduled_for_collection['amount__sum'] or 0


def get_tranches_pending_for_collection_on_given_due_date(due_date, **kwargs):
    qs = get_planned_payment_objects(type=PlannedPayment.DUE_ON_MEMBER,
                                     payment_type=[PlannedPayment.TRANCHE,
                                                   PlannedPayment.CANCELLATION_FINAL_SETTLEMENT],
                                     status=[PlannedPayment.PENDING], date=due_date)

    print("[get_tranches_pending_for_collection_on_given_due_date]Pending Tranches Before Filtration : {}".format(len(qs)))
    qs = apply_amount_tolerance_filter_in_pending_payment_objects_for_email_remainder(qs, tolerance_amount=kwargs.get(
        'tolerance_amount', 0))
    print("[get_tranches_pending_for_collection_on_given_due_date]Pending Tranches After Filtration : {}".format(len(qs)))
    return qs[:kwargs.get('max_count')]


def get_tranches_pending_for_collection_before_given_due_date(due_date, **kwargs):
    qs = get_planned_payment_objects(type=PlannedPayment.DUE_ON_MEMBER,
                                     payment_type=[PlannedPayment.TRANCHE,
                                                   PlannedPayment.CANCELLATION_FINAL_SETTLEMENT],
                                     status=[PlannedPayment.PENDING], date__lt=due_date,
                                     transaction__booking_date__gte=kwargs.get("transaction_cut_off_date")
                                     )
    print("[get_tranches_pending_for_collection_before_given_due_date]Pending Tranches Before Filtration : {}".format(len(qs)))
    qs = apply_amount_tolerance_filter_in_pending_payment_objects_for_email_remainder(qs, tolerance_amount=kwargs.get(
        'tolerance_amount', 0))
    print("[get_tranches_pending_for_collection_before_given_due_date]Pending Tranches After Filtration : {}".format(len(qs)))
    return qs[:kwargs.get('max_count')]


def get_planned_payment_object_by_planned_payment_id(planned_payment_id: int):
    return PlannedPayment.objects.get(id=planned_payment_id)


def apply_amount_tolerance_filter_in_pending_payment_objects_for_email_remainder(planned_payment_queryset, **kwargs):
    qs = planned_payment_queryset.annotate(pending_amount=F('amount') - F('actual_payment_amount')).filter(
        pending_amount__gt=kwargs.get('tolerance_amount'))
    return qs


def add__due_amount__for_each_planned_payment__in_response(response):
    amount_due_on_member = 0.0
    amount_due_to_member = 0.0
    try:
        for i in range(len(response['planned_payments'])):
            if response['planned_payments'][i]['type'] == "due_on_member":
                if response['planned_payments'][i]['status'] == "pending":
                    amount_due_on_member += response['planned_payments'][i]['pending_amount']
                response['planned_payments'][i]['due_amount'] = amount_due_on_member
            else:
                if response['planned_payments'][i]['status'] == "pending":
                    amount_due_to_member += response['planned_payments'][i]['pending_amount']
                response['planned_payments'][i]['due_amount'] = amount_due_to_member

        return response
    except Exception as e:
        print(f"Something Went Wrong while adding Amount. {str(e)}")
        exceptions.APIException("Something went wrong. {}".format(e))


def get_date_of__last_tranche__due_on_member__by_booking_id(booking_id):
    try:
        qs = PlannedPayment.objects.filter(booking_id=booking_id).filter(type='due_on_member').order_by('-date').first()
        date = qs.date
        return date
    except Exception as e:
        exceptions.APIException("Something went wrong. {}".format(e))


def get_planned_payment_obj_by_booking_id(booking_id: int, **kwargs):
    try:
        return PlannedPayment.objects.filter(booking_id=booking_id, type=kwargs.get('type'),
                                             status=kwargs.get('status'))
    except PlannedPayment.DoesNotExist:
        print(f"Planned Payment Does Not Exist.")
        return None


def get_planned_payments_by_booking_id_and_type(booking_id, type):
    try:
        return PlannedPayment.objects.filter(booking_id=booking_id, type=type)
    except PlannedPayment.DoesNotExist:
        print(f"Planned Payment Does Not Exist.")
        return None