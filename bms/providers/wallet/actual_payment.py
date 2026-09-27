
from bms.serializers.booking import ActualPaymentSerializer
from bms.models.actual_payment.actual_payment import ActualPayment



def record_actual_payments(actual_payment_data):
    error_msg = ""
    if actual_payment_data:
        actual_payment_objs = ActualPaymentSerializer(many=True, data=actual_payment_data)
        if actual_payment_objs.is_valid():
            print("Actual Payment Recorded Successfully")
            return actual_payment_objs.save()
        else:
            error_msg += "<li>{}</li>".format(actual_payment_objs.errors)
            raise Exception(error_msg)

def update_actual_payment(id=None, ids=None, update_params=None):
    if id:
        print("Updating Single Actual Payments for ID : {}".format(id))
        return ActualPayment.objects.filter(id=id).update(**update_params)
    elif ids:
        print("Updating Multiple Actual Payments for IDS : {}".format(ids))
        return ActualPayment.objects.filter(id__in=ids).update(**update_params)
