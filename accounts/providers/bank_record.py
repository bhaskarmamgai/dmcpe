import datetime
from accounts.models import BankRecord


# Todo : Update this by Bhaskar
def update_bank_record_line(record_id, claimed_by, service_id, **kwargs):
    record_obj = BankRecord.objects.get(id=record_id)
    record_obj.claimed = True
    record_obj.service_id = service_id
    record_obj.claimed_by = claimed_by
    if kwargs.get('member_id'):
        record_obj.member_id = kwargs.get('member_id')
    if kwargs.get('organization_id'):
        record_obj.organization_id = kwargs.get('organization_id')
    if kwargs.get('posting_id'):
        record_obj.posting_id = kwargs.get('posting_id')
    record_obj.claimed_at = datetime.datetime.now()
    record_obj.save()


def update_bank_record_by_id(record_id, **kwargs):
    BankRecord.objects.filter(id=record_id).update(**kwargs.get('kwargs'))


def bank_record_by_id(record_id):
    return BankRecord.objects.get(id=record_id)


def create_bank_record(date, description, reference_id, credit_or_debit, amount, created_by_id, remark, member_id,
                       source):
    params = {
        'date': date,
        'description': description,
        'reference_id': reference_id,
        'credit_or_debit': credit_or_debit,
        'amount': amount,
        'created_by_id': created_by_id,
        'remark': remark,
        'member_id': member_id,
        'source': source
    }
    obj = BankRecord(**params)
    obj.save()
    return obj
