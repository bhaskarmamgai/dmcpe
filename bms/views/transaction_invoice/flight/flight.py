from django.http import HttpResponse
from django.shortcuts import redirect, reverse, render
from django.contrib.auth.decorators import user_passes_test, login_required
from bms.services import flight,bookings

@user_passes_test(lambda user: user.has_perm('bms.view_transactioninvoices'))
@user_passes_test(lambda user: user.has_perm('bms.add_transactioninvoices'))
@login_required
def create_invoice(request, booking_id):
    booking_obj = bookings.get_booking_object_from_id(booking_id)
    if request.method == "POST":
        error_message, invoice_id = flight.handle_flight_booking_invoice_request(booking_id,
                                                                                         request.user.id)
        if error_message:
            return HttpResponse(error_message)
        return redirect(reverse('admin:bms_bookinginvoices_change', args=[invoice_id]))
    return render(request, 'tax_invoice/flight/edit.html', {'booking_obj': booking_obj})
