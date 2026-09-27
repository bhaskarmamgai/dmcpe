from accounts.models import BankStatement
from common.libraries import read_csv_file, get_date_from_given_str_format
from accounts.serializers import BankRecordDataValidator
from accounts.enums import BANK_TRANSFER


def get_bank_statement_object_by_id(id: int):
    try:
        return BankStatement.objects.get(id=id)
    except BankStatement.DoesNotExist:
        return None


def update_bank_statement_object(id: int, **kwargs):
    qs = BankStatement.objects.filter(id=id)
    qs.update(**kwargs)
    return qs


def is_csv_file_already_imported(id:int):
    bank_statement_obj = get_bank_statement_object_by_id(id)
    if bank_statement_obj.records_imported:
        return True
    return False


def import_csv_file(created_by_id: int, bank_statement_obj_id: int):
    bank_statement_obj = get_bank_statement_object_by_id(bank_statement_obj_id)
    csv_obj = read_csv_file(bank_statement_obj.file.name)
    headers_to_be_match_with = ['date', 'description', 'reference_id', 'amount', 'credit_or_debit']
    headers_to_be_match = csv_obj.header
    error_msg = ""
    if len(headers_to_be_match_with) != len(headers_to_be_match):
        error_msg += "<li>Headers Count Mismatch.Expected {} got {}</li><br>".format(headers_to_be_match_with,
                                                                                     headers_to_be_match)
        if error_msg:
            raise Exception(error_msg)

    for head in headers_to_be_match_with:
        if head in headers_to_be_match:
            pass
        else:
            error_msg += "<li> {} is missing.Please Upload New CSV and Try Again</li><br>".format(head)
            raise Exception(error_msg)

    # Update serializer data
    updated_data = []
    for index, item in enumerate(csv_obj.obj_list):
        item.update({'statement_id': bank_statement_obj.id})
        item.update({'mode_of_payment': BANK_TRANSFER})

        # https://stackoverflow.com/questions/16870663/how-do-i-validate-a-date-string-format-in-python
        parse_date_obj = get_date_from_given_str_format(item.get('date'))
        if parse_date_obj:
            item.update({'date': parse_date_obj})
            item.update({'created_by_id': created_by_id})
        else:
            error_msg += "<li>Column Value Mismatch at row {}.Expected Date Format is dd-mm-yyyy but got {}.</li><br>".format(
                index + 2, item.get('date'))
            raise Exception(error_msg)
        updated_data.append(item)
    # create instance of serializers class
    serializer_obj = BankRecordDataValidator(data=updated_data, many=True)
    if serializer_obj.is_valid():
        serializer_obj.save()
    else:
        for index, error in enumerate(serializer_obj.errors):
            if error:
                error_msg += "<li>Invalid value for {} at row {} in Uploaded CSV</li><br>".format(*error, index + 2)
                raise Exception(error_msg)
