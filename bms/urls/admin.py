from django.urls import path

import bms.views.bank_record.wallet.add
import bms.views.bank_record.claim
from bms.views.wallet.claim import claim as wallet_claim
from bms.views.wallet.release import release as wallet_release
from bms.views.transaction_invoice.flight import flight
from bms.views.transaction_invoice.own_supply import own_supply
from bms.views.release_request import release_request
from bms.views.bms import fetch_booking_financials
from bms.views.booking_document.booking_document import create_booking_document_manually
from bms.views.booking_cancellation import booking_cancellation
from bms.views.booking_cancellation import planned_payment
from bms.views.booking_refund import refund
from bms.services import refund as refund_services
from bms.services.booking_alteration import initiate_booking_alteration

app_name = 'bms'
urlpatterns = [
    path('booking/<int:booking_id>/booking_document/create_manually/', create_booking_document_manually,
         name='create_booking_document_manually'),
    path('bookings/fetch-latest-booking-financials/<int:booking_id>', fetch_booking_financials,
         name='fetch-latest-booking-financials-manually'),
    path('bank_record/claim/block_bank_record/<int:record_id>', bms.views.bank_record.claim.block_bank_record,
         name='bank_record__claim__block_bank_record'),
    path('create_invoice/own-supply/<int:booking_id>/',
         own_supply.create_invoice, name='create_invoice_own_supply'),
    path('booking_cancellation/cancel_booking/<int:booking_id>', booking_cancellation.cancel_booking,
         name="booking_cancellation_cancel_booking"),
    path('booking_cancellation/cancellation_final_settlement/<int:booking_id>',
         booking_cancellation.cancellation_final_settlement,
         name="booking_cancellation_cancellation_final_settlement"),
    path(
        'booking_cancellation/cancel_planned_payment_tranche/<int:booking_id>/<int:planned_payment_id>/<str:model_name>',
        planned_payment.cancel_planned_payment_tranche, name='booking_cancellation_cancel_planned_tranche'),
    path('release_request/reject_release_request/<int:release_request_id>',
         release_request.reject_release_request,
         name="release_request_reject_release_request"),

    path('booking_refund/select_refund_options/<int:planned_payment_id>', refund.select_booking_refund_options,
         name='booking_refund_select_refund_options'),

    path('booking_refund/release_request/bank_transfer/<int:planned_payment_id>', refund.create_refund_as_bank_transfer,
         name='booking_refund_bank_transfer'),

    path('booking_refund/release_request/add_to_wallet/<int:planned_payment_id>',
         refund.create_refund_as_add_to_wallet,
         name='booking_refund_add_to_wallet'),

    path('create_invoice/flight/<int:booking_id>/',
         flight.create_invoice, name='create_invoice_flight'),


    path('wallet/claim/select_service/', wallet_claim.select_service,
         name='wallet__payment__select__service'),

    # Claims - Select Booking
    path(
        'wallet/claim/select_bookings/<int:organization_id>/<int:member_id>/<int:service_id>/<str:selected_due_date>',
        wallet_claim.select_bookings, name='wallet__claim__select__bookings'),

    path('bank_record/claim/add_to_wallet/<int:member_id>/<int:organization_id>/<int:bank_record_id>',
         bms.views.bank_record.wallet.add.add,
         name='bank_record__claim__add_to_wallet'),

    path('wallet/release_request/edit', wallet_release.edit, name="wallet_release_request"),
    path(
        'wallet/release_request/select_booking/<int:service_id>/<int:member_id>/<int:organization_id>/'
        '<str:selected_due_date>/<str:booking_start_date>/<str:booking_end_date>',
        wallet_release.select_bookings, name="wallet_release_request_select_booking"),

    # Release Request
    path(
        'wallet/release_request/select_booking/<int:service_id>/<int:member_id>/<int:organization_id>/<str'
        ':selected_due_date>/<str:booking_start_date>/<str:booking_end_date>?destination_id=<int:destination_id>'
        '&category_id=<int:category_id>&type_id=<int:type_id>&vendor_organization=<int:vendor_organization>/',
        wallet_release.select_bookings, name="wallet_release_request_select_booking_v2"),


    path('wallet/release_request/approve/<int:release_request_id>',
         wallet_release.approve_release_request,
         name="wallet_release_request_approve_release_request"),

    path('wallet/release_request/approve/add_to_wallet/<int:release_request_id>',
         wallet_release.add_to_wallet, name="wallet_release_request_approve_add_to_wallet"),

    path('wallet/release_request/approve/bank_transfer/<int:release_request_id>',
         wallet_release.bank_transfer, name="wallet_release_request_approve_bank_transfer"),
    path('wallet/release_request/bulk_release/select_organization',
         wallet_release.fetch_release_request_for_organization, name="select_bulk_release_organization"),
    path("wallet/release_request/bulk_release/<int:organization_id>/<str:mode_of_release>",
         wallet_release.select_release_requests_for_bulk_release, name="select_release_requests_for_bulk_release"),
    path("wallet/release_request/bulk_reject/<str:release_request_ids_str>",
         wallet_release.reject_bulk_release_requests, name="wallet_reject_release_request"),

    path('<str:code>/manual_refund_to_wallet', refund_services.manual_refund_to_wallet, name="manual-refund-to-wallet"),
    path('booking/cancellation_process_v2/select_cancellation_type/<int:booking_id>',
         booking_cancellation.cancellation_process_v2_type_selection, name="select_cancellation_process_v2_type"),
    path('booking/cancellation_process_v2/fill_cancellation_details/<int:booking_id>/<str:cancellation_type>',
         booking_cancellation.cancellation_process_v2_fill_cancellation_details,
         name="cancellation_process_v2_fill_cancellation_details"),
    path('alteration/<int:booking_id>/', initiate_booking_alteration, name='booking_alteration'),
]
