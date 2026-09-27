from django.db import connection
from django.conf import settings
import datetime
from bms.models.actual_payment.actual_payment import ActualPayment
from bms.models.release_request.release_request import ReleaseRequest
from bms.models.planned_payment.planned_payment import PlannedPayment
from bms.serializers.booking import ReleaseRequestSerializer
from dmcpesys.models import CurrencyConfiguration
from django.core.exceptions import ValidationError


def get_bookings_where_payment_release_is_due_in_given_date_range(date, member_id, organization_id, booking_start_date,
                                                                  booking_end_date, **kwargs):
    destination_id = kwargs.get('destination_id')
    transaction_type_id = kwargs.get('type_id')
    category_id = kwargs.get('category_id')
    booking_id = kwargs.get('booking_id')
    vendor_organization_id = kwargs.get('vendor_organization')

    query1 = "SELECT t.id as booking_id,t.amount_in_inr as amount_in_inr, " \
             "p.planned_payment, " \
             "COALESCE(act.actual_payment, 0) as actual_payment, COALESCE(req.requested_payment,0) as requested_payment, " \
             "p.planned_payment - COALESCE(act.actual_payment, 0) as due_amount " \
             "FROM bms_booking as t "
    b_join = "JOIN(SELECT booking_id, vendor_organization_id from bms_bookingfinancial where vendor_organization_id=%s) " \
             "as b on t.id=b.booking_id " if vendor_organization_id and vendor_organization_id > 0 else ""

    query2 = "JOIN(SELECT booking_id, sum(amount) planned_payment " \
             "FROM bms_plannedpayment " \
             "WHERE member_id = %s and organization_id = %s and date <= %s::date and type = %s and status != %s and  (payment_type IN (%s,%s)) " \
             "group by booking_id " \
             ") as p on t.id = p.booking_id " \
             "LEFT JOIN ( " \
             "SELECT ap.booking_id, sum(ap.amount) as actual_payment " \
             "FROM bms_actualpayment as ap JOIN bms_releaserequest as rr on ap.release_request_id = rr.id " \
             "WHERE ap.member_id = %s and ap.organization_id = %s and ap.type = %s " \
             "and rr.status= %s " \
             "group by booking_id " \
             ") as act on t.id = act.booking_id " \
             "LEFT JOIN ( " \
             "SELECT ap.booking_id, sum(ap.amount) as requested_payment " \
             "FROM bms_actualpayment as ap JOIN bms_releaserequest as rr on ap.release_request_id = rr.id " \
             "WHERE ap.member_id = %s and ap.organization_id = %s and ap.type = %s " \
             "and rr.status= %s " \
             "group by booking_id " \
             ") as req on t.id = req.booking_id " \
             "WHERE (t.seller_id = %s or t.buyer_id = %s) and (t.buyer_organization_id = %s or " \
             "t.seller_organization_id = %s) and t.deleted = 0 " \
             "and p.planned_payment - COALESCE(act.actual_payment, 0) > 0 " \
             "and t.booking_date between %s and %s "

    query = query1 + b_join + query2
    filter1 = "and t.destination_id = %s " if (destination_id and destination_id > 0) else ""
    filter2 = "and t.type_id = %s " if transaction_type_id and transaction_type_id > 0 else ""
    filter3 = "and t.category_id = %s " if category_id and category_id > 0 else ""
    filter4 = "and t.id = %s " if booking_id and booking_id > 0 else ""

    final_query = query + filter1 + filter2 + filter3 + filter4 + "order by t.id desc limit %s; "

    with connection.cursor() as cursor:
        variable_list = []
        if vendor_organization_id:
            variable_list.append(vendor_organization_id)
        variable_list = variable_list + [member_id, organization_id, date, PlannedPayment.DUE_TO_MEMBER,
                                         PlannedPayment.CANCELLED,
                                         PlannedPayment.TRANCHE, PlannedPayment.CANCELLATION_FINAL_SETTLEMENT,
                                         member_id,
                                         organization_id, ActualPayment.PAID_TO_MEMBER, ReleaseRequest.RELEASED,
                                         member_id,
                                         organization_id, ActualPayment.PAID_TO_MEMBER, ReleaseRequest.PENDING,
                                         member_id, member_id,
                                         organization_id, organization_id, booking_start_date, booking_end_date]
        if destination_id:
            variable_list.append(destination_id)
        if transaction_type_id:
            variable_list.append(transaction_type_id)
        if category_id:
            variable_list.append(category_id)
        if booking_id:
            variable_list.append(booking_id)
        variable_list.append(1000)
        cursor.execute(final_query, variable_list)
        col = [col[0] for col in cursor.description]
        rows = [dict(zip(col, row)) for row in cursor.fetchall()]
        return rows


def get_bookings_where_payment_release_is_due_in_given_date_range_v2_for_bmsv2(
        date, member_id, organization_id,
        booking_start_date, booking_end_date, **kwargs):

    print("\n========= FUNCTION START =========")

    destination_id = kwargs.get('destination_id')
    transaction_type_id = kwargs.get('type_id')
    category_id = kwargs.get('category_id')
    booking_id = kwargs.get('booking_id')
    vendor_organization_id = kwargs.get('vendor_organization')

    print("INPUT PARAMS:")
    print("booking_id:", booking_id)
    print("member_id:", member_id)
    print("organization_id:", organization_id)
    print("date:", date)
    print("booking_start_date:", booking_start_date)
    print("booking_end_date:", booking_end_date)
    print("destination_id:", destination_id)
    print("transaction_type_id:", transaction_type_id)
    print("category_id:", category_id)
    print("vendor_organization_id:", vendor_organization_id)

    query1 = (
        "SELECT t.id as booking_id, t.amount as amount, p.planned_payment, "
        "c.symbol as member_currency_symbol, "
        "COALESCE(act.actual_payment, 0) as actual_payment, "
        "COALESCE(req.requested_payment,0) as requested_payment, "
        "p.planned_payment - COALESCE(act.actual_payment, 0) as due_amount "
        "FROM (SELECT * FROM bms_booking t WHERE t.id=%s) as t "
    )

    b_join = ""
    if vendor_organization_id and vendor_organization_id > 0:
        b_join = (
            "JOIN (SELECT booking_id, vendor_organization_id "
            "FROM bms_bookingfinancial WHERE vendor_organization_id=%s) as b "
            "ON t.id = b.booking_id "
        )

    query2 = (
        "JOIN (SELECT booking_id, member_currency_id, ROUND(sum(amount)::numeric,2) planned_payment "
        "FROM bms_plannedpayment "
        "WHERE booking_id=%s AND member_id=%s AND organization_id=%s AND date <= %s::date "
        "AND type=%s AND status != %s AND (payment_type IN (%s,%s)) "
        "GROUP BY booking_id, member_currency_id "
        ") as p ON t.id = p.booking_id "
        "JOIN dmcpesys_currency as c ON p.member_currency_id = c.id "

        # 🔥 FIXED GROUP BY
        "LEFT JOIN ( "
        "SELECT ap.booking_id, ROUND(sum(ap.amount)::numeric,2) as actual_payment "
        "FROM bms_actualpayment as ap "
        "JOIN bms_releaserequest as rr ON ap.release_request_id = rr.id "
        "WHERE ap.booking_id=%s AND ap.member_id=%s AND ap.organization_id=%s AND ap.type=%s "
        "AND rr.status=%s "
        "GROUP BY ap.booking_id "
        ") as act ON t.id = act.booking_id "

        # 🔥 FIXED GROUP BY
        "LEFT JOIN ( "
        "SELECT ap.booking_id, sum(ap.amount) as requested_payment "
        "FROM bms_actualpayment as ap "
        "JOIN bms_releaserequest as rr ON ap.release_request_id = rr.id "
        "WHERE ap.booking_id=%s AND ap.member_id=%s AND ap.organization_id=%s AND ap.type=%s "
        "AND rr.status=%s "
        "GROUP BY ap.booking_id "
        ") as req ON t.id = req.booking_id "

        "WHERE (EXISTS (SELECT 1 FROM bms_sellercostcomponent as scc "
        "WHERE scc.booking_id = t.id AND scc.seller_member_id = %s) "
        "OR t.buyer_id = %s) "

        "AND (EXISTS (SELECT 1 FROM bms_sellercostcomponent as scc "
        "WHERE scc.booking_id = t.id AND scc.seller_organization_id = %s) "
        "OR t.buyer_organization_id = %s) "

        # 🔥 FIXED BOOLEAN
        "AND NOT t.is_deleted "

        "AND p.planned_payment - COALESCE(act.actual_payment, 0) > 0 "
        "AND t.booking_date BETWEEN %s AND %s "
    )

    query = query1 + b_join + query2

    filter1 = "AND t.destination_id = %s " if destination_id and destination_id > 0 else ""
    filter2 = "AND t.type_id = %s " if transaction_type_id and transaction_type_id > 0 else ""
    filter3 = "AND t.category_id = %s " if category_id and category_id > 0 else ""

    final_query = query + filter1 + filter2 + filter3 + "ORDER BY t.id DESC LIMIT %s;"

    # ================= DEBUG =================
    print("\n===== FINAL QUERY =====")
    print(final_query)

    print("\n===== PLACEHOLDER COUNT =====")
    print("Total %s:", final_query.count("%s"))

    variable_list = []
    variable_list.append(booking_id)

    if vendor_organization_id:
        variable_list.append(vendor_organization_id)

    variable_list += [
        booking_id, member_id, organization_id, date,
        PlannedPayment.DUE_TO_MEMBER, PlannedPayment.CANCELLED,
        PlannedPayment.TRANCHE, PlannedPayment.CANCELLATION_FINAL_SETTLEMENT,

        booking_id, member_id, organization_id,
        ActualPayment.PAID_TO_MEMBER, ReleaseRequest.RELEASED,

        booking_id, member_id, organization_id,
        ActualPayment.PAID_TO_MEMBER, ReleaseRequest.PENDING,

        member_id, member_id,
        organization_id, organization_id,
        booking_start_date, booking_end_date
    ]

    if destination_id:
        variable_list.append(destination_id)
    if transaction_type_id:
        variable_list.append(transaction_type_id)
    if category_id:
        variable_list.append(category_id)

    variable_list.append(1000)

    print("\n===== VARIABLES =====")
    for i, val in enumerate(variable_list):
        print(f"{i}: {val}")

    print("Total variables:", len(variable_list))

    # ================= EXECUTION =================
    with connection.cursor() as cursor:
        try:
            cursor.execute(final_query, variable_list)
            print("✅ Query executed successfully")
        except Exception as e:
            print("❌ QUERY FAILED:", str(e))
            raise

        col = [col[0] for col in cursor.description]
        rows = [dict(zip(col, row)) for row in cursor.fetchall()]

        print("\n===== RESULT =====")
        print(rows)

        print("========= FUNCTION END =========\n")

        return rows
def get_bookings_where_payment_release_is_due_in_given_date_range_v2(date, member_id, organization_id,
                                                                     booking_start_date,
                                                                     booking_end_date, **kwargs):
    destination_id = kwargs.get('destination_id')
    transaction_type_id = kwargs.get('type_id')
    category_id = kwargs.get('category_id')
    booking_id = kwargs.get('booking_id')
    vendor_organization_id = kwargs.get('vendor_organization')

    query1 = "SELECT t.id as booking_id,t.amount_in_inr as amount_in_inr, " \
             "p.planned_payment, " \
             "COALESCE(act.actual_payment, 0) as actual_payment, COALESCE(req.requested_payment,0) as requested_payment, " \
             "p.planned_payment - COALESCE(act.actual_payment, 0) as due_amount " \
             "FROM(select * from bms_booking t where t.id=%s) as t "
    b_join = "JOIN(SELECT booking_id, vendor_organization_id from bms_bookingfinancial where vendor_organization_id=%s) " \
             "as b on t.id=b.booking_id " if vendor_organization_id and vendor_organization_id > 0 else ""

    query2 = "JOIN(SELECT booking_id, sum(amount) planned_payment " \
             "FROM bms_plannedpayment " \
             "WHERE booking_id=%s and member_id = %s and organization_id = %s and date <= %s::date and type = %s and status != %s and  (payment_type IN (%s,%s)) " \
             "group by booking_id " \
             ") as p on t.id = p.booking_id " \
             "LEFT JOIN ( " \
             "SELECT ap.booking_id, sum(ap.amount) as actual_payment " \
             "FROM bms_actualpayment as ap JOIN bms_releaserequest as rr on ap.release_request_id = rr.id " \
             "WHERE ap.booking_id=%s and ap.member_id = %s and ap.organization_id = %s and ap.type = %s " \
             "and rr.status= %s " \
             "group by booking_id " \
             ") as act on t.id = act.booking_id " \
             "LEFT JOIN ( " \
             "SELECT ap.booking_id, sum(ap.amount) as requested_payment " \
             "FROM bms_actualpayment as ap JOIN bms_releaserequest as rr on ap.release_request_id = rr.id " \
             "WHERE ap.booking_id=%s and ap.member_id = %s and ap.organization_id = %s and ap.type = %s " \
             "and rr.status= %s " \
             "group by booking_id " \
             ") as req on t.id = req.booking_id " \
             "WHERE(t.seller_id = %s or t.buyer_id = %s) and (t.buyer_organization_id = %s or " \
             "t.seller_organization_id = %s) and t.deleted = 0 " \
             "and p.planned_payment - COALESCE(act.actual_payment, 0) > 0 " \
             "and t.booking_date between %s and %s "

    query = query1 + b_join + query2
    filter1 = "and t.destination_id = %s " if (destination_id and destination_id > 0) else ""
    filter2 = "and t.type_id = %s " if transaction_type_id and transaction_type_id > 0 else ""
    filter3 = "and t.category_id = %s " if category_id and category_id > 0 else ""

    final_query = query + filter1 + filter2 + filter3 + "order by t.id desc limit %s; "

    with connection.cursor() as cursor:
        variable_list = []
        variable_list.append(booking_id)
        if vendor_organization_id:
            variable_list.append(vendor_organization_id)
        variable_list = variable_list + [booking_id, member_id, organization_id, date, PlannedPayment.DUE_TO_MEMBER,
                                         PlannedPayment.CANCELLED,
                                         PlannedPayment.TRANCHE, PlannedPayment.CANCELLATION_FINAL_SETTLEMENT,
                                         booking_id, member_id,
                                         organization_id, ActualPayment.PAID_TO_MEMBER, ReleaseRequest.RELEASED,
                                         booking_id, member_id,
                                         organization_id, ActualPayment.PAID_TO_MEMBER, ReleaseRequest.PENDING,
                                         member_id, member_id,
                                         organization_id, organization_id, booking_start_date, booking_end_date]
        if destination_id:
            variable_list.append(destination_id)
        if transaction_type_id:
            variable_list.append(transaction_type_id)
        if category_id:
            variable_list.append(category_id)
        variable_list.append(100)
        cursor.execute(final_query, variable_list)
        col = [col[0] for col in cursor.description]
        rows = [dict(zip(col, row)) for row in cursor.fetchall()]
        return rows


def get_bookings_where_payment_release_is_due_in_given_date_range_for_version_2(date, member_id, organization_id,
                                                                                booking_start_date, booking_end_date,
                                                                                **kwargs):
    destination_id = kwargs.get('destination_id')
    transaction_type_id = kwargs.get('type_id')
    category_id = kwargs.get('category_id')
    booking_id = kwargs.get('booking_id')
    vendor_organization_id = kwargs.get('vendor_organization')

    query1 = "SELECT t.id as booking_id, t.amount as amount, p.planned_payment, c.symbol as member_currency_symbol," \
             " ROUND(COALESCE(act.actual_payment, 0)::numeric, 2) as actual_payment, COALESCE(req.requested_payment,0) as requested_payment," \
             " p.planned_payment - COALESCE(act.actual_payment, 0) as due_amount FROM bms_booking as t "

    query2 = "JOIN(SELECT booking_id, member_currency_id, ROUND(sum(amount)::numeric, 2) planned_payment " \
             "FROM bms_plannedpayment " \
             "WHERE member_id = %s and organization_id = %s and date <= %s::date and type = %s and status != %s and  (payment_type IN (%s,%s)) " \
             "group by booking_id, member_currency_id " \
             ") as p on t.id = p.booking_id " \
             "JOIN dmcpesys_currency as c on p.member_currency_id = c.id " \
             "LEFT JOIN ( " \
             "SELECT ap.booking_id, sum(ap.amount) as actual_payment " \
             "FROM bms_actualpayment as ap JOIN bms_releaserequest as rr on ap.release_request_id = rr.id " \
             "WHERE ap.member_id = %s and ap.organization_id = %s and ap.type = %s " \
             "and rr.status= %s " \
             "group by booking_id " \
             ") as act on t.id = act.booking_id " \
             "LEFT JOIN ( " \
             "SELECT ap.booking_id, sum(ap.amount) as requested_payment " \
             "FROM bms_actualpayment as ap JOIN bms_releaserequest as rr on ap.release_request_id = rr.id " \
             "WHERE ap.member_id = %s and ap.organization_id = %s and ap.type = %s " \
             "and rr.status= %s " \
             "group by booking_id " \
             ") as req on t.id = req.booking_id " \
             "WHERE (exists (select 1 from bms_sellercostcomponent as scc where scc.booking_id = t.id " \
             "and scc.seller_member_id = %s) or t.buyer_id = %s) " \
             "and (exists (select 1 from bms_sellercostcomponent as scc where scc.booking_id = t.id and " \
             "scc.seller_organization_id = %s) or t.buyer_organization_id = %s) and t.deleted = 0 " \
             "and p.planned_payment - COALESCE(act.actual_payment, 0) > 0 " \
             "and t.booking_date between %s and %s "

    query = query1 + query2
    filter1 = "and t.destination_id = %s " if (destination_id and destination_id > 0) else ""
    filter2 = "and t.type_id = %s " if transaction_type_id and transaction_type_id > 0 else ""
    filter3 = "and t.category_id = %s " if category_id and category_id > 0 else ""
    filter4 = "and t.id = %s " if booking_id and booking_id > 0 else ""

    final_query = query + filter1 + filter2 + filter3 + filter4 + "order by t.id desc limit %s; "

    with connection.cursor() as cursor:
        variable_list = []
        if vendor_organization_id:
            variable_list.append(vendor_organization_id)
        variable_list = variable_list + [member_id, organization_id, date, PlannedPayment.DUE_TO_MEMBER,
                                         PlannedPayment.CANCELLED,
                                         PlannedPayment.TRANCHE, PlannedPayment.CANCELLATION_FINAL_SETTLEMENT,
                                         member_id,
                                         organization_id, ActualPayment.PAID_TO_MEMBER, ReleaseRequest.RELEASED,
                                         member_id,
                                         organization_id, ActualPayment.PAID_TO_MEMBER, ReleaseRequest.PENDING,
                                         member_id, member_id,
                                         organization_id, organization_id, booking_start_date, booking_end_date]
        if destination_id:
            variable_list.append(destination_id)
        if transaction_type_id:
            variable_list.append(transaction_type_id)
        if category_id:
            variable_list.append(category_id)
        if booking_id:
            variable_list.append(booking_id)
        variable_list.append(1000)
        cursor.execute(final_query, variable_list)
        col = [col[0] for col in cursor.description]
        rows = [dict(zip(col, row)) for row in cursor.fetchall()]
        return rows


def create_release_request(organization_id, member_id, requested_amounts, created_by, **kwargs):
    error_msg = ""
    total_requested_amount = 0
    for amount in requested_amounts:
        total_requested_amount += float(amount)

    data_for_request_release = {
        'booking_id': kwargs.get('booking_id'),
        'member_id': member_id,
        'organization_id': organization_id,
        'requested_amount': total_requested_amount,
        'to_be_released_on': kwargs.get('to_be_released_on') if kwargs.get(
            'to_be_released_on') else datetime.datetime.now().date(),
        'description': kwargs.get('description') if kwargs.get('description') else 'NA',
        'created_by_id': created_by.id,
        'organization_bank_account_id': kwargs.get('organization_bank_account'),
        'mode': kwargs.get('release_option'),
        'proof': kwargs.get('proof') if kwargs.get('proof') else None,
        'remark': kwargs.get('remark') if kwargs.get('remark') else None,
        'requested_currency_id': kwargs.get('currency_id') if kwargs.get('currency_id') else None
    }

    currency_config = CurrencyConfiguration.objects.filter(currency_id=kwargs.get('currency_id'))
    if currency_config and total_requested_amount > currency_config.last().release_limit:
        raise ValidationError(
            f"Exceeding the limit set in Currency Config for currency {currency_config.last().currency}, current limit => {currency_config.last().release_limit}")
    release_obj = ReleaseRequestSerializer(data=data_for_request_release)
    if release_obj.is_valid():
        release_request_objs = release_obj.save()
        return release_request_objs
    else:
        error_msg += "<li>{}</li>".format(release_obj.errors)
        raise Exception(error_msg)
