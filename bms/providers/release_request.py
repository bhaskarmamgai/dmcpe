from django.db import connection
import datetime
from django.shortcuts import reverse
from django.utils.safestring import mark_safe
from common.libraries import get_round_off_amount
from bms.models import ActualPayment, ReleaseRequest, ReleaseRequestStatusHistory, PlannedPayment, Booking,    ReleaseRequestPayments
from bms.serializers.booking import ReleaseRequestSerializer
from bms.enums import BANK_TRANSFER, RefundMode
from django.db.models import Sum
from bms.services.bookings import get_seller_cost_components_by_booking_code, get_weighted_seller_fx_and_markup
from bms.services import transaction_summary,seller_cost_component


def get_bookings_where_payment_release_is_due_as_on_given_date(date, member_id):
    """This function will calculate pending amount for a
    given bookings/booking"""
    query = "SELECT t.id as booking_id,t.amount_in_inr as amount_in_inr, " \
            "p.planned_payment, " \
            "COALESCE(act.actual_payment, 0) as actual_payment, COALESCE(req.requested_payment,0) as requested_payment, " \
            "p.planned_payment - COALESCE(act.actual_payment, 0) as due_amount " \
            "FROM bms_booking as t " \
            "JOIN ( " \
            "SELECT booking_id, sum(amount) planned_payment " \
            "FROM bms_plannedpayment " \
            "WHERE member_id = %s and date <= %s::date and type = %s and status != %s and  (payment_type IN (%s,%s)) " \
            "group by booking_id " \
            ") as p on t.id = p.booking_id " \
            "LEFT JOIN ( " \
            "SELECT ap.booking_id, sum(ap.amount) as actual_payment " \
            "FROM bms_actualpayment as ap JOIN bms_releaserequest as rr on ap.release_request_id = rr.id " \
            "WHERE ap.member_id = %s and ap.type = %s " \
            "and rr.status= %s " \
            "group by booking_id " \
            ") as act on t.id = act.booking_id " \
            "LEFT JOIN ( " \
            "SELECT ap.booking_id, sum(ap.amount) as requested_payment " \
            "FROM bms_actualpayment as ap JOIN bms_releaserequest as rr on ap.release_request_id = rr.id " \
            "WHERE ap.member_id = %s and ap.type = %s " \
            "and rr.status= %s " \
            "group by booking_id " \
            ") as req on t.id = req.booking_id " \
            "WHERE (t.seller_id = %s or t.buyer_id = %s) and t.deleted = 0 " \
            "and p.planned_payment - COALESCE(act.actual_payment, 0) > 0; "
    with connection.cursor() as cursor:
        cursor.execute(query,
                       [member_id, date, PlannedPayment.DUE_TO_MEMBER, PlannedPayment.CANCELLED, PlannedPayment.TRANCHE,
                        PlannedPayment.CANCELLATION_FINAL_SETTLEMENT, member_id,
                        ActualPayment.PAID_TO_MEMBER,
                        ReleaseRequest.RELEASED, member_id, ActualPayment.PAID_TO_MEMBER, ReleaseRequest.PENDING,
                        member_id, member_id])


        col = [col[0] for col in cursor.description]
        rows = [dict(zip(col, row)) for row in cursor.fetchall()]
        return rows

def filter_booking_ids_whose_collection_is_due_before_today_by_member_id(seller_id: int, booking_ids: []):
    """This function will filter bookings whose collect tranche is due as on today for a
    a particular seller against multiple bookings"""

    print("\n====== FUNCTION START ======")
    print("seller_id:", seller_id)
    print("booking_ids:", booking_ids)

    if not booking_ids:
        print("❌ No booking_ids provided")
        return []

    booking_ids_str = ','.join(map(str, booking_ids))
    print("booking_ids_str:", booking_ids_str)

    today_date = datetime.datetime.now().date()
    print("today_date:", today_date)

    payment_types = (
        PlannedPayment.TRANCHE,
        PlannedPayment.REFUND,
        PlannedPayment.CANCELLATION_FINAL_SETTLEMENT
    )
    print("payment_types:", payment_types)

    print("PlannedPayment.PENDING:", PlannedPayment.PENDING)
    print("PlannedPayment.DUE_ON_MEMBER:", PlannedPayment.DUE_ON_MEMBER)

    query = "SELECT booking.id FROM bms_booking booking where id in " \
            "( " \
            "select booking_id from bms_plannedpayment pp " \
            "where booking.id in ({booking_ids}) " \
            "and pp.member_id = booking.buyer_id " \
            "and pp.status='{planned_payment_status}' " \
            "and pp.payment_type in {payment_types} " \
            "and pp.type = '{due_type}' " \
            "and pp.date <= '{today_date}'::date " \
            "); ".format(
                booking_ids=booking_ids_str,
                planned_payment_status=PlannedPayment.PENDING,
                payment_types=payment_types,
                due_type=PlannedPayment.DUE_ON_MEMBER,
                today_date=today_date
            )

    print("\n===== FINAL QUERY =====")
    print(query)

    with connection.cursor() as cursor:
        try:
            cursor.execute(query)
            print("✅ Query executed successfully")
        except Exception as e:
            print("❌ Query execution failed:", str(e))
            raise

        col = [col[0] for col in cursor.description]
        print("Columns:", col)

        raw_rows = cursor.fetchall()
        print("Raw rows:", raw_rows)

        rows = [dict(zip(col, row)) for row in raw_rows]

        print("Formatted rows:", rows)
        print("====== FUNCTION END ======\n")

        return rows
def get_release_request_obj(release_request_id):
    return ReleaseRequest.objects.get(id=release_request_id)


def update_release_request_status(release_request_id, status):
    release_req_obj = ReleaseRequest.objects.get(id=release_request_id)
    release_req_obj.status = status
    return release_req_obj.save()


def check_if_release_request_exist_for_booking(booking_id: int, released_request_status: str, **kwargs):
    obj = ActualPayment.objects.filter(bookings=booking_id, release_request__status=released_request_status, **kwargs)
    if obj:
        msg_header = "Following Released Request Already Exist for this booking id <a href='{}'>{}</a><br>".format(
            reverse("admin:trs_booking_change", args=[booking_id]), booking_id)
        msg_body = [mark_safe('Release request <a href="%s">#%s</a><br>' % (
            reverse('admin:trs_releaserequest_change', args=[i.release_request.id]), i.release_request.id)) for
                    i in obj]
        msg_footer = "<br>Please Contact Finance Team for any Help"
        response_message = msg_header + "\n".join(msg_body) + msg_footer
        return {'status': True, 'response_message': response_message}
    return {'status': False, 'response_message': ''}


def create_release_request(member_id, requested_amounts, created_by, **kwargs):
    error_msg = ""
    total_requested_amount = 0
    for amount in requested_amounts:
        total_requested_amount += float(amount)

    data_for_request_release = {
        'booking_id': kwargs.get('booking_id'),
        'member_id': member_id,
        'requested_amount': total_requested_amount,
        'to_be_released_on': kwargs.get('to_be_released_on') if kwargs.get(
            'to_be_released_on') else datetime.datetime.now().date(),
        'description': kwargs.get('description') if kwargs.get('description') else 'NA',
        'created_by_id': kwargs.get('created_by_id') if kwargs.get('created_by_id') else created_by.id,
        'bank_account_id': kwargs.get('selected_bank_account'),
        'organization_id': kwargs.get('organization_id'),
        'mode': kwargs.get('release_mode', BANK_TRANSFER),
        'organization_bank_account_id': kwargs.get('organization_bank_account'),
        'proof': kwargs.get('proof') if kwargs.get('proof') else None,
        'remark': kwargs.get('remark') if kwargs.get('remark') else None,
        'refund_mode': kwargs.get('refund_mode') if kwargs.get('refund_mode') else RefundMode.BLANK.value,
        'requested_currency_id': kwargs.get('currency_id') if kwargs.get('currency_id') else None
    }

    release_obj = ReleaseRequestSerializer(data=data_for_request_release)
    if release_obj.is_valid():
        release_request_objs = release_obj.save()
        return release_request_objs
    else:
        error_msg += "<li>{}</li>".format(release_obj.errors)
        raise Exception(error_msg)


def record_release_request_status_history(release_request_id: int, status: str, **kwargs):
    return ReleaseRequestStatusHistory.objects.create(
        **{'release_request_id': release_request_id, 'status': status})


def get_pending_release_requests_by_organization_id_and_mode_of_release(organization_id, mode_of_release):
    release_requests = ReleaseRequest.objects.filter(status=ReleaseRequest.PENDING,
                                                     organization__id=organization_id,
                                                     mode=mode_of_release,
                                                     booking__booking_version_type=Booking.V2)
    return release_requests


def create_release_request_payment(release_request_obj, **request_data):
    total_transaction_cost = request_data.get('transaction_cost')
    total_remit_type_cost = request_data.get('remit_type_cost')
    total_amount_released_in_member_currency = request_data.get('amount_released_in_member_currency')
    request_data['transaction_cost'] = get_round_off_amount((float(total_transaction_cost) + float(total_remit_type_cost)) * (float(release_request_obj.requested_amount) / float(total_amount_released_in_member_currency)))
    del request_data['amount_released_in_member_currency']

    return ReleaseRequestPayments.objects.create(release_request_id=release_request_obj.id,
                                                 booking_id=release_request_obj.booking.id if release_request_obj.booking else None,
                                                 organization_id=release_request_obj.organization.id if release_request_obj.organization else None,
                                                 amount_released_in_member_currency=release_request_obj.requested_amount,
                                                 **request_data)


def get_total_requested_amount_by_release_request_ids(release_request_ids):
    return ReleaseRequest.objects.filter(id__in=release_request_ids).aggregate(amount=Sum('requested_amount'))


def get_remittance_amount_for_release_request_payment(release_request_payment_obj):
    roe = release_request_payment_obj.roe_on_date_of_payment
    bid_ask_spread = release_request_payment_obj.bid_ask_spread
    return get_round_off_amount(release_request_payment_obj.transaction_cost * (roe + bid_ask_spread))


def get_amount_changed_due_to_fx_for_release_request_payment(release_request_payment_obj):
    roe = release_request_payment_obj.roe_on_date_of_payment
    bid_ask_spread = release_request_payment_obj.bid_ask_spread
    seller_cost_components = get_seller_cost_components_by_booking_code(release_request_payment_obj.booking.code,
                                                                        seller_member_id=release_request_payment_obj.release_request.member_id)
    weighted_seller_fx, weighted_seller_fx_markup = get_weighted_seller_fx_and_markup(seller_cost_components)
    return get_round_off_amount(release_request_payment_obj.amount_released_in_member_currency * ((roe + bid_ask_spread) - (weighted_seller_fx + weighted_seller_fx_markup)))


def check_if_release_request_can_be_created(booking_obj, member_id, amount_in_collection_currency):

    print("\n====== START check_if_release_request_can_be_created ======")

    print("booking_id:", booking_obj.id)
    print("member_id:", member_id)
    print("input amount_in_collection_currency:", amount_in_collection_currency)

    booking_summary_obj = transaction_summary.get_booking_summary_object_by_booking_id(booking_obj.id)
    print("booking_summary_obj:", booking_summary_obj)

    pending_amount = get_amount_in_collection_currency_for_pending_release_request_of_a_booking(booking_obj.id)
    print("pending_amount (all pending RR):", pending_amount)

    net_amount = float(amount_in_collection_currency) + (float(pending_amount) if pending_amount else 0.0)
    print("net_amount (new + pending):", net_amount)

    total_booking_loss = booking_obj.booking_losses.aggregate(total=Sum('amount')).get('total') or 0
    print("total_booking_loss:", total_booking_loss)

    print("net_hold:", booking_summary_obj.net_hold)
    print("net_hold + total_booking_loss:", booking_summary_obj.net_hold + total_booking_loss)

    # 🔥 MAIN CHECK (THIS IS YOUR ERROR SOURCE)
    if net_amount > booking_summary_obj.net_hold + total_booking_loss:
        print("❌ FAILED: net_amount exceeds net_hold + total_booking_loss")

        msg_header = "Release Request cannot be created for the amount (collection currency)" \
                     " if the sum of amount (collection currency) of all the pending Release Requests" \
                     " (and new one) is exceeding Net Hold + Total Booking Loss for the booking<br>"

        msg_footer = "<br>Please Contact Finance Team for any Help"
        response_message = msg_header + msg_footer

        print("Returning error message:", response_message)

        return {'status': True, 'response_message': response_message}

    print("✅ Passed first validation (Net Hold check)")

    # 🔁 SELLER FLOW CHECK
    if booking_obj.buyer.id != member_id:
        print("\n--- SELLER FLOW ---")

        pending_amount_for_a_member = get_amount_in_collection_currency_for_pending_paid_release_request_of_a_booking(
            booking_obj.id, member_id=member_id
        )
        print("pending_amount_for_member:", pending_amount_for_a_member)

        net_amount_for_member = float(amount_in_collection_currency) + \
            float(pending_amount_for_a_member) if pending_amount_for_a_member else 0.0

        print("net_amount_for_member:", net_amount_for_member)

        amount_in_collection_currency_for_seller = seller_cost_component.get_amount_in_collection_currency_for_seller_of_a_booking(
            booking_obj.id, seller_member_id=member_id
        )
        print("seller_limit (collection currency):", amount_in_collection_currency_for_seller)

        # 🔥 SECOND CHECK
        if net_amount_for_member > amount_in_collection_currency_for_seller:
            print("❌ FAILED: net_amount_for_member exceeds seller limit")

            msg_header = "Release Request cannot be created for the amount (collection currency)" \
                         " if the sum of amount (collection currency) of all the pending Release Requests" \
                         " (and new one) is exceeding net seller cost component amount for the seller.<br>"

            msg_footer = "<br>Please Contact Finance Team for any Help"
            response_message = msg_header + msg_footer

            print("Returning seller error:", response_message)

            return {'status': True, 'response_message': response_message}

        print("✅ Passed seller validation")

    else:
        print("\n--- BUYER FLOW --- (seller validation skipped)")

    print("✅ ALL CHECKS PASSED")

    print("====== END FUNCTION ======\n")

    return {'status': False, 'response_message': ''}


def get_amount_in_collection_currency_for_pending_release_request_of_a_booking(booking_id, **kwargs):
    return ActualPayment.objects.filter(booking_id=booking_id, status=ActualPayment.PENDING,
                                        release_request__status=ReleaseRequest.PENDING, **kwargs).aggregate(amount=Sum('amount_in_collection_currency'))['amount']


def get_amount_in_collection_currency_for_pending_paid_release_request_of_a_booking(booking_id, **kwargs):
    return ActualPayment.objects.filter(booking_id=booking_id, status__in=[ActualPayment.PENDING, ActualPayment.PAID],
                                        release_request__status__in=[ReleaseRequest.PENDING, ReleaseRequest.RELEASED], **kwargs).aggregate(amount=Sum('amount_in_collection_currency'))['amount']
