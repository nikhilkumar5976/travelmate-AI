"""
Standalone Supabase Migration & Seeding Tool for TravelMate AI
Usage:
    python migrate_supabase.py
    python migrate_supabase.py --url "postgresql://..."
"""

import argparse
import os
import sys
from pathlib import Path

# Setup Django environment
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

parser = argparse.ArgumentParser(description="Migrate and seed Supabase database.")
parser.add_argument("--url", help="Database URL", default=None)
args = parser.parse_args()

if args.url:
    os.environ["DATABASE_URL"] = args.url

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

import django
django.setup()

from django.core.management import call_command
from django.contrib.auth import get_user_model
from accounts.models import Profile
from places.models import Place


def main():
    db_url = os.environ.get("DATABASE_URL", "")
    print(f"Connecting to database...")

    try:
        print("Running migrations...")
        call_command("migrate", interactive=False, verbosity=1)
        print("Migrations complete.")
    except Exception as exc:
        print(f"\nMigration failed: {exc}")
        if "timeout expired" in str(exc).lower() or "2406:" in str(exc):
            print("\n[DIAGNOSTIC NOTICE]")
            print("Your network appears to be IPv4-only and cannot reach Supabase direct IPv6.")
            print("To run migrations locally, use the Supabase IPv4 Pooler URL from your Supabase Dashboard:")
            print("Dashboard -> Project Settings -> Database -> Connection string -> Session tab (port 5432 or 6543).\n")
        sys.exit(1)

    print("\nEnsuring superuser 'nikhilkhat_5976' exists...")
    User = get_user_model()
    admin_user = User.objects.filter(username="nikhilkhat_5976").first()
    if not admin_user:
        admin_user = User.objects.create_superuser(
            username="nikhilkhat_5976",
            email="nikhilkhatri240@gmail.com",
            password="nikhil@123",
        )
        print("Superuser nikhilkhat_5976 created.")
    else:
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.is_active = True
        admin_user.email = "nikhilkhatri240@gmail.com"
        admin_user.set_password("nikhil@123")
        admin_user.save()
        print("Superuser nikhilkhat_5976 updated.")

    profile, _ = Profile.objects.get_or_create(user=admin_user)
    profile.phone = profile.phone or "7900781098"
    profile.email_verified = True
    profile.save()
    print("Superuser profile verified with phone 7900781098.")

    if not Place.objects.exists():
        print("Seeding default places...")
        places = [
            Place(name="The Ridge", city="Shimla", state="Himachal Pradesh", category="sightseeing", description="Famous open space in the heart of Shimla offering panoramic views."),
            Place(name="Mall Road", city="Shimla", state="Himachal Pradesh", category="shopping", description="Main street and shopping hub lined with cafes and handicraft stores."),
            Place(name="Jakhoo Temple", city="Shimla", state="Himachal Pradesh", category="sightseeing", description="Ancient temple situated on Jakhoo Hill, the highest peak in Shimla."),
            Place(name="Solang Valley", city="Manali", state="Himachal Pradesh", category="adventure", description="Renowned adventure valley for paragliding, zorbing, and winter sports."),
            Place(name="Old Manali", city="Manali", state="Himachal Pradesh", category="food", description="Charming bohemian village with bakeries, live music, and scenic cafes."),
            Place(name="Fort Aguada", city="Goa", state="Goa", category="sightseeing", description="17th-century Portuguese fortress overlooking the Arabian Sea."),
            Place(name="Baga Beach", city="Goa", state="Goa", category="beach", description="Popular beach destination known for water sports and vibrant shacks."),
            Place(name="Taj Mahal", city="Agra", state="Uttar Pradesh", category="sightseeing", description="Iconic ivory-white marble mausoleum on the south bank of the Yamuna river."),
        ]
        Place.objects.bulk_create(places)
        print(f"Seeded {len(places)} places.")

    print("\nSUCCESS: Supabase database is fully initialized and ready for production!")


if __name__ == "__main__":
    main()
