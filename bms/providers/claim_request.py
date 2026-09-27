from bms.models.claim_request.claim_request import ClaimRequestLogs


def record_claim_request_logs(booking_id, payload, **kwargs):
    claim_request_log = ClaimRequestLogs(
        booking_id=booking_id,
        payload=payload,
        status=kwargs.get('status'),
        amount=payload.get('amount'),
        source=kwargs.get('claim_source')
    )
    claim_request_log.save()
    return claim_request_log


def update_claim_request_log_object(claim_request_log_id: int, **kwargs):
    qs = ClaimRequestLogs.objects.filter(id=claim_request_log_id)
    qs.update(**kwargs)
    return qs
