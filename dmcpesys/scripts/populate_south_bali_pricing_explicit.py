from decimal import Decimal
from django.db import transaction

from transfers.models import TransferRoute, TransferPrice, VehicleType, LuggageVan,RouteLocation
from dmcpesys.models import Destination, Area, Currency, LocationMaster


# ======================================================================
# CONFIG (EXPLICIT FROM MAP)
# ======================================================================

DESTINATION_NAME = "Bali"
AREA_NAME = "Bali"
AIRPORT_NAME = "Ngurah Rai International Airport (DPS)"

SOUTH_BALI_LOCATIONS = [
    "Canggu",
    "Ubud",
    "Uluwatu",
]

AVANZA_PRICE = Decimal("15.00")
HIACE_PRICE = Decimal("50.00")
LUGGAGE_VAN_PRICE = Decimal("10.00")

CURRENCY_CODE = "USD"


# ======================================================================
# MAIN
# ======================================================================

@transaction.atomic
def populate_south_bali_pricing_explicit():
    print("💰 Populating South Bali pricing (explicit map-based)...\n")

    destination = Destination.objects.get(name=DESTINATION_NAME)
    currency = Currency.objects.get(name=CURRENCY_CODE)

    airport = LocationMaster.objects.get(
        name=AIRPORT_NAME,
        location_category="airport",
        destination=destination
    )

    # --------------------------------------------------------------
    # LOOP THROUGH EACH SOUTH BALI LOCATION EXPLICITLY
    # --------------------------------------------------------------
    for loc_name in SOUTH_BALI_LOCATIONS:
        location = LocationMaster.objects.get(
            name=loc_name,
            destination=destination
        )

        route_name = f"{airport.name} → {location.name}"

        route = TransferRoute.objects.create(
            name=route_name,
            destination=destination,
            service_type_id=5,
            route_type='one_way',
            from_location=airport,
            to_location=location,
        )
        RouteLocation.objects.create(
            route=route,
            from_location=airport,
            to_location=location,
            sequence=1
        )
        print(f"Route ✔ {route.name}")

        # ----------------------------------------------------------
        # Transfer Prices (Per Vehicle)
        # ----------------------------------------------------------
        for vehicle_name, price in {
            "Avanza": AVANZA_PRICE,
            "Hiace": HIACE_PRICE,
        }.items():
            vehicle = VehicleType.objects.get(name=vehicle_name)

            obj, created = TransferPrice.objects.update_or_create(
                route=route,
                vehicle_type=vehicle,
                transfer_type="private",
                defaults={
                    "price": price,
                    "currency": currency,
                    "price_per": "vehicle",
                    "is_available": True,
                }
            )

            print(
                f"   ↳ {'CREATED' if created else 'UPDATED'} "
                f"{vehicle.name}: {price} {currency.code}"
            )

        # --------------------------------------------------------------
        # Luggage Van Pricing (Explicit South Bali Area)
        # --------------------------------------------------------------
        luggage_van = LuggageVan.objects.update_or_create(
            destination=destination,
            direction="one_way",
            from_location=airport,
            to_location=location,
            defaults={
                "price": LUGGAGE_VAN_PRICE,
                "currency": currency,
                "price_per": "vehicle",
                "from_location": airport,
                "to_location": location,
            }
        )

    print("\n🎉 South Bali pricing populated successfully!")


# Run
populate_south_bali_pricing_explicit()
