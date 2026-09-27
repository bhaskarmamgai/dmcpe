from rest_framework import serializers
from .models import BankRecord
from accounts.enums import CREDIT_OR_DEBIT, MODE_OF_PAYMENT


# https://tinyendian.com/articles/parsing-query-parameters-in-rest-framework/
class BankRecordDataValidator(serializers.Serializer):
    date = serializers.DateField()
    description = serializers.CharField()
    reference_id = serializers.CharField()
    amount = serializers.FloatField()
    statement_id = serializers.IntegerField()
    credit_or_debit = serializers.ChoiceField(CREDIT_OR_DEBIT)
    created_by_id = serializers.IntegerField()
    mode_of_payment = serializers.ChoiceField(MODE_OF_PAYMENT)

    class Meta:
        model = BankRecord
        fields = ("date", "description", "reference_id", "amount", "statement", "credit_or_debit", "mode_of_payment",
                  "created_by")

    def create(self, validated_data):
        record = BankRecord.objects.create(**validated_data)
        return record
