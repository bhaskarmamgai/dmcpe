from bms.models.payment.payment import PaymentLogs


def record_payment_logs(payload, response, **kwargs):
    return PaymentLogs(
        booking_id=kwargs.get('booking_id'),
        payload=payload,
        response=response.data
    ).save()
