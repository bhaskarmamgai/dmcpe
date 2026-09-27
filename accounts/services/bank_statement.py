from django.db import transaction
from accounts.providers import bank_statement


def get_bank_statement_object_by_id(bank_statement_id: int):
    return bank_statement.get_bank_statement_object_by_id(bank_statement_id)


def update_bank_statement_object(bank_statement_id: int, **kwargs):
    return bank_statement.update_bank_statement_object(bank_statement_id, **kwargs)


@transaction.atomic
def import_csv_file(created_by_id, bank_statement_object_id):
    bank_statement.import_csv_file(created_by_id, bank_statement_object_id)
    bank_statement.update_bank_statement_object(bank_statement_object_id, records_imported=True)
    return True


def is_csv_file_already_imported(bank_statement_id: int):
    return bank_statement.is_csv_file_already_imported(bank_statement_id)
