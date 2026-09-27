from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from bms.validators.claim import validate_claim_bank_record_request
from accounts.services.bank_record import update_bank_record, update_bank_record_by_id
from django.conf import settings


def block_bank_record(request, **kwargs):
    claim_check, error_msg = validate_claim_bank_record_request(
        request.user.id, kwargs.get('record_id'))
    if not claim_check:
        return HttpResponse("Claim Error: {} ".format(error_msg))
    record_id = kwargs.get('record_id')
    update_bank_record_by_id(
        record_id, kwargs={'comment': 'Block Bank Record for Others'})
    update_bank_record(record_id, request.user, settings.SERVICE_OTHERS_ID)
    return redirect(reverse('admin:accounts_bankrecord_change', args=[record_id]))


