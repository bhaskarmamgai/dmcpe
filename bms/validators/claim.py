import datetime, pytz
from accounts.providers.bank_record import bank_record_by_id

UTC_TIMEZONE = pytz.UTC

def validate_claim_bank_record_request(user_id, bank_record_id):
    claim_check, error_msg = True, None
    if user_id:
        claim_check = True if bank_record_by_id(
            bank_record_id).created_at >= UTC_TIMEZONE.localize(
            datetime.datetime.now() - datetime.timedelta(
                days=10)) else False
        error_msg = "Bank Record Cannot be claimed After {} days of creation. Please contact admin".format(
            10) if not claim_check else None
    return claim_check, error_msg
