from django.shortcuts import redirect
from django.http import HttpResponse
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from accounts.services import bank_statement


@login_required
def import_records(request, statement_id):
    if bank_statement.is_csv_file_already_imported(statement_id):
        return HttpResponse("This Bank Statement Is Already Imported")
    try:
        bank_statement.import_csv_file(request.user.id, statement_id)
        # https://stackoverflow.com/questions/3712814/how-to-show-a-message-to-a-django-admin-after-saving-a-model
        messages.add_message(request, messages.SUCCESS, 'Bank Records Have Been Imported Successfully')
        # https://stackoverflow.com/questions/694477/getting-django-admin-url-for-an-object
        return redirect(reverse('admin:accounts_bankstatement_change', args=[statement_id]))
    except Exception as e:
        return HttpResponse("Parsing Error : {}".format(e))
