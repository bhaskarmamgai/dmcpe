from django.shortcuts import redirect, render
from django.urls import reverse
from django.contrib import messages

from bms.services import planned_payment
from bms.models.planned_payment.planned_payment import PlannedPayment
from bms.forms import CancelTrancheForm


def cancel_planned_payment_tranche(request, booking_id: int, planned_payment_id: int, model_name: str):
    planned_payment_obj = planned_payment.get_planned_payment_object_by_planned_payment_id(planned_payment_id)
    if request.method == "POST":
        print("Cancel Planned Payment ID {}".format(planned_payment_id))
        cancel_tranche_form = CancelTrancheForm(request.POST, instance=planned_payment_obj)
        if cancel_tranche_form.is_valid():
            cancel_tranche_form.save()
        planned_payment.update_planned_payment_status(PlannedPayment.CANCELLED, planned_payment_id)
        messages.add_message(request, messages.SUCCESS,
                             'Planned Payment Status with ID {} has been Marked Cancelled Successfully'.format(
                                 planned_payment_id))
        return redirect(reverse('admin:trs_{}_change'.format(model_name.lower()), args=[booking_id]))
    if request.method == "GET":
        cancel_tranche_form = CancelTrancheForm()
        return render(request, "tranche/cancel_tranche.html",
                      {'cancel_tranche_form': cancel_tranche_form, 'planned_payment_obj': planned_payment_obj})
