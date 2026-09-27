from django.shortcuts import render, redirect, reverse
from dmcpesys.services import get_enabled_categories, get_category_obj_by_id
from bms.services.booking_document import get_booking_document_by_booking_document_id, create_booking_document
from datetime import datetime
from bms.services import bookings
from members.services import MemberServices
from bms.enums import BOOKING_DOCUMENT_STATUS_TYPE, BOOKING_DOCUMENT_TYPE


def create_booking_document_manually(request, booking_id):
    saved_document_obj = {}
    categories = get_enabled_categories()

    if request.method == 'GET' and 'document_id' in request.GET:
        saved_document_obj = get_booking_document_by_booking_document_id(int(request.GET['document_id']))

    elif request.method == 'POST':
        name = request.POST['name']
        if 'document_id' in request.GET:
            booking_doc_obj = get_booking_document_by_booking_document_id(int(request.GET['document_id']))
            booking_doc_obj.name = name
            booking_doc_obj.category = get_category_obj_by_id(int(request.POST['category']))
            booking_doc_obj.status = request.POST['status']
            booking_doc_obj.document_type = request.POST['document_type']
            booking_doc_obj.save()
        else:
            datetime_object = None
            if request.POST['delivery_date']:
                datetime_object = datetime.strptime(request.POST['delivery_date'], '%Y-%m-%dT%H:%M')
            create_booking_document(
                booking_id=booking_id,
                created_by=request.user,
                name=name,
                delivery_date=datetime_object,
                category=get_category_obj_by_id(int(request.POST['category'])),
                status=request.POST['status'],
                document_type=request.POST['document_type'],
            )
        return redirect(reverse('admin:bms_booking_change', args=[booking_id]))

    return render(request, 'booking_document/edit.html',
                  context={"status_type": BOOKING_DOCUMENT_STATUS_TYPE, "document_type": BOOKING_DOCUMENT_TYPE,
                           "category": categories, "saved_data": saved_document_obj})


def get_buyer_info(booking_id):
    booking_obj = bookings.get_booking_object_from_id(booking_id)
    members_data = {}
    if booking_obj.buyer_id:
        members_data = MemberServices.get_member_data_from_member_id(booking_obj.buyer_id)
    return {
        "member_id": members_data.id,
        "brand_name": members_data.company_name2,
        "logo_url": members_data.logo_url,
        "mobile": members_data.phone2,
        "email": members_data.email2,
    }
