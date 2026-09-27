from accounts.providers import bank_record


def update_bank_record(record_id, claimed_by, service_id, **kwargs):
    return bank_record.update_bank_record_line(record_id, claimed_by, service_id, **kwargs)


def get_bank_record_obj_by_id(record_id):
    return bank_record.bank_record_by_id(record_id)


def create_bank_record(date, description, reference_id, credit_or_debit, amount, created_by_id, remark,
                       member_id, source):
    return bank_record.create_bank_record(date, description, reference_id, credit_or_debit, amount, created_by_id,
                                          remark, member_id, source)


def update_bank_record_by_id(record_id, **kwargs):
    return bank_record.update_bank_record_by_id(record_id, **kwargs)
