from django.db import connection
from bms.models.actual_payment.actual_payment import ActualPayment
from bms.models.planned_payment.planned_payment import PlannedPayment


def get_bookings_where_collection_is_due_as_on_given_date(date, organization_id, member_id):
    """

    This function will calculate pending amount for a
    given bookings/booking against Organization

    """
    query = "select t.id as booking_id, t.collection_currency_id as collection_currency_id, t.created_at as booking_date, t.amount_in_inr as amount_in_inr," \
            "p.planned_payment, p.currency as currency_id, c.symbol as currency," \
            "round(COALESCE(a.actual_payment, 0)::numeric, 2) as actual_payment, " \
            "round((p.planned_payment - COALESCE(a.actual_payment, 0))::numeric, 2) as due_amount " \
            "from bms_booking as t " \
            "join ( " \
            "select booking_id, sum(amount) planned_payment, MAX(member_currency_id) currency " \
            "from bms_plannedpayment " \
            "where organization_id = %s and member_id = %s and date <= %s::date and type = %s and status != %s and (payment_type IN (%s,%s,%s))" \
            "group by booking_id " \
            ") as p " \
            "on t.id = p.booking_id " \
            "left join ( select id, symbol from dmcpesys_currency ) as c on p.currency = c.id " \
            "left join ( " \
            "select booking_id, sum(amount) actual_payment " \
            "from bms_actualpayment " \
            "where organization_id = %s and member_id = %s and type = %s " \
            "group by booking_id " \
            ") as a " \
            "on t.id = a.booking_id " \
            "where (exists(select 1 from bms_sellercostcomponent as scc where scc.booking_id = t.id and " \
            "scc.seller_organization_id = %s) or t.buyer_organization_id = %s) and (exists(select 1 from bms_sellercostcomponent as scc where scc.booking_id = t.id " \
            "and scc.seller_member_id = %s) or t.buyer_id = %s) and t.is_deleted = false " \
            "and p.planned_payment - COALESCE(a.actual_payment, 0) > 0 "

    with connection.cursor() as cursor:
        cursor.execute(query,
                       [organization_id, member_id, date, PlannedPayment.DUE_ON_MEMBER, PlannedPayment.CANCELLED,
                        PlannedPayment.TRANCHE, PlannedPayment.REFUND,
                        PlannedPayment.CANCELLATION_FINAL_SETTLEMENT, organization_id, member_id,
                        ActualPayment.PAID_BY_MEMBER,
                        organization_id, organization_id, member_id, member_id])
        col = [col[0] for col in cursor.description]
        rows = [dict(zip(col, row)) for row in cursor.fetchall()]
        return rows
