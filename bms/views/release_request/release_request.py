from django.shortcuts import render, redirect, reverse, HttpResponse
from django.utils.safestring import mark_safe
from bms.services import actual_payment, release_request
from bms.models.actual_payment.actual_payment import ActualPayment
from bms.models.release_request.release_request import ReleaseRequest
from django.contrib import messages
from bms.forms import RejectReleaseRequestForm
from bms.services.wallet import actual_payment as wallet_actual_payment_services
from bms.validators.release_request import validate_release_request


def reject_release_request(request, release_request_id):
    release_request_obj = release_request.get_release_request_obj(release_request_id)

    is_valid, error_msg = validate_release_request(request, release_request_id)
    if not is_valid:
        return HttpResponse(error_msg)

    if request.method == "GET":
        reject_release_request_form_obj = RejectReleaseRequestForm()
        return render(request, 'release_request/release/reject_release_request.html',
                      {"reject_release_request_form_obj": reject_release_request_form_obj})
    if request.method == "POST":
        reject_release_request_form_obj = RejectReleaseRequestForm(request.POST, instance=release_request_obj)
        if reject_release_request_form_obj.is_valid():
            release_request_obj.action_by = request.user
            release_request_obj.save()
            reject_release_request_form_obj.save()
            messages.add_message(request, messages.SUCCESS,
                                 mark_safe(
                                     'Release Request {} has been Rejected'.format(mark_safe("<a href='%s'>%s</a>" % (
                                         reverse('admin:bms_releaserequest_change', args=[release_request_obj.id]),
                                         release_request_obj)))))
            release_request.update_release_request_status(release_request_id, ReleaseRequest.REJECTED)
            wallet_actual_payment_services.update_actual_payment_objects(ids=[i.id for i in
                                                                              actual_payment.get_actual_payment_objects_from_release_id(
                                                                                  release_request_obj.id)],
                                                                         update_params={
                                                                             'status': ActualPayment.REJECTED})
            return redirect(reverse('admin:bms_releaserequest_changelist'))
    return redirect(reverse('admin:bms_releaserequest_changelist'))
