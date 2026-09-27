from django.urls import path
from accounts.views.bank_statement import import_records

urlpatterns = [
    path('bank_statement/import_records/<int:statement_id>', import_records, name='bank_statement_import_record'),
]
