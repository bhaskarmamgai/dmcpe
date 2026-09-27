from django.db import transaction

from dmcpesys.models import (
    Country,
    State,
    Destination,
    Area,
    LocationMaster
)

# ======================================================================
# 📌 CONFIG
# ======================================================================

COUNTRY_NAME = "Indonesia"
COUNTRY_ISO = "ID"

STATE_NAME = "Bali"
DESTINATION_NAME = "Bali"

# Area → Locations mapping
DATA = {
    "Airport": [
        {
            "name": "DPS Airport",
            "category": "airport",
            "type": "POINT"
        }
    ],

    "South Bali": [
        {"name": "Kuta", "category": "district"},
        {"name": "Seminyak", "category": "district"},
        {"name": "Legian", "category": "district"},
        {"name": "Nusa Dua", "category": "district"},
        {"name": "Uluwatu", "category": "district"},
        {"name": "Jimbaran", "category": "district"},
    ],

    "Central Bali": [
        {"name": "Canggu", "category": "district"},
        {"name": "Ubud", "category": "city_center"},
        {"name": "Gianyar", "category": "district"},
        {"name": "Bedugul", "category": "district"},
    ],

    "North & East Bali": [
        {"name": "Sidemen", "category": "district"},
        {"name": "Lovina", "category": "beach"},
    ],
}


# ======================================================================
# 🚀 MAIN SCRIPT
# ======================================================================

@transaction.atomic
def bootstrap_bali_geo():
    print("🌴 Bootstrapping Bali geographic hierarchy...\n")

    # ===========================================================
    # 1️⃣ Country
    # ===========================================================
    country, _ = Country.objects.get_or_create(
        name=COUNTRY_NAME,
        defaults={"iso_code": COUNTRY_ISO}
    )
    print(f"Country ✔ {country}")

    # ===========================================================
    # 2️⃣ State (Province)
    # ===========================================================
    state, _ = State.objects.get_or_create(
        name=STATE_NAME,
        country=country
    )
    print(f"State ✔ {state}")

    # ===========================================================
    # 3️⃣ Destination
    # ===========================================================
    destination, _ = Destination.objects.get_or_create(
        name=DESTINATION_NAME,
        country=country,
        state=state
    )
    print(f"Destination ✔ {destination}\n")

    # ===========================================================
    # 4️⃣ Areas & Locations
    # ===========================================================
    for area_name, locations in DATA.items():
        area, area_created = Area.objects.get_or_create(
            name=area_name,
            destination=destination,
            defaults={"is_default": area_name == "South Bali"}
        )

        print(f"Area {'CREATED' if area_created else 'EXISTS'} → {area.name}")

        for loc in locations:
            loc_name = loc["name"]
            loc_category = loc.get("category")
            loc_type = loc.get("type", "POINT")

            location, created = LocationMaster.objects.get_or_create(
                name=loc_name,
                destination=destination,
                area=area,
                defaults={
                    "country": country,
                    "state": state,
                    "location_type": loc_type,
                    "location_category": loc_category,
                }
            )

            print(
                f"   ↳ Location {'CREATED' if created else 'EXISTS'} "
                f"→ {location.name} ({location.location_category})"
            )

        print("")

    print("🎉 Bali geo structure created successfully!")


# Run script
bootstrap_bali_geo()
