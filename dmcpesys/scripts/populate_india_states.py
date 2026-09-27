import os
import sys
import django

# Setup Django Environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "traventic_core.settings")
django.setup()

from django.db import transaction
from dmcpesys.models import Country, State

INDIAN_STATES_AND_UTS = [
    # 28 States
    "Andhra Pradesh",
    "Arunachal Pradesh",
    "Assam",
    "Bihar",
    "Chhattisgarh",
    "Goa",
    "Gujarat",
    "Haryana",
    "Himachal Pradesh",
    "Jharkhand",
    "Karnataka",
    "Kerala",
    "Madhya Pradesh",
    "Maharashtra",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Odisha",
    "Punjab",
    "Rajasthan",
    "Sikkim",
    "Tamil Nadu",
    "Telangana",
    "Tripura",
    "Uttar Pradesh",
    "Uttarakhand",
    "West Bengal",

    # 8 Union Territories
    "Andaman and Nicobar Islands",
    "Chandigarh",
    "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi",
    "Jammu and Kashmir",
    "Ladakh",
    "Lakshadweep",
    "Puducherry"
]


@transaction.atomic
def run():
    print("🇮🇳 Starting population of Country 'India' and 36 States/UTs in dmcpesys...")

    # 1. Ensure Country India exists
    country, created = Country.objects.get_or_create(
        name="India",
        defaults={
            "iso_code": "IN",
            "code": "CO_IN"
        }
    )
    if created:
        print(f"✅ Created Country: {country.name} (ISO: {country.iso_code})")
    else:
        if not country.iso_code:
            country.iso_code = "IN"
            country.save(update_fields=["iso_code"])
        print(f"ℹ️ Country India already exists (ID: {country.id}, ISO: {country.iso_code})")

    # 2. Populate States & UTs
    created_count = 0
    existing_count = 0

    for idx, state_name in enumerate(INDIAN_STATES_AND_UTS, start=1):
        state_obj, is_new = State.objects.get_or_create(
            name=state_name,
            country=country,
            defaults={
                "code": f"ST_IN_{idx:02d}"
            }
        )
        if is_new:
            created_count += 1
            print(f"  + Added State/UT [{idx:02d}]: {state_name}")
        else:
            existing_count += 1
            print(f"  • Existing State/UT [{idx:02d}]: {state_name}")

    print("\n🎉 POPULATION COMPLETE!")
    print(f"Total States & UTs Processed: {len(INDIAN_STATES_AND_UTS)}")
    print(f"New States Created: {created_count}")
    print(f"Existing States Preserved: {existing_count}")


if __name__ == "__main__":
    run()
