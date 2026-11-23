import logging
import os

logger = logging.getLogger(__name__)


def run_database_bootstrap():
    """
    On cold starts or initial deployments when a persistent DATABASE_URL is provided,
    this function verifies if database migrations have been executed.
    If core tables (like auth_user) are not yet present, it automatically runs:
      1. call_command('migrate', interactive=False)
      2. Creates/updates superuser 'nikhilkhat_5976' with password 'nikhil@123'
      3. Verifies and activates profile with phone '7900781098'
      4. Seeds default Place records if places table is empty
    """
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        return

    try:
        from django.db import connection
        with connection.cursor() as cursor:
            # Query standard SQL information_schema to check if auth_user exists
            cursor.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_name='auth_user'"
            )
            tables_exist = cursor.fetchone() is not None

        if not tables_exist:
            logger.info("Fresh PostgreSQL database detected. Running initial migrations...")
            from django.core.management import call_command
            call_command('migrate', interactive=False, verbosity=0)
            logger.info("Database migrations successfully applied.")

        # Ensure superuser nikhilkhat_5976 and profile are provisioned
        from django.contrib.auth import get_user_model
        from accounts.models import Profile

        UserModel = get_user_model()
        admin_user = UserModel.objects.filter(username='nikhilkhat_5976').first()
        if not admin_user:
            admin_user = UserModel.objects.create_superuser(
                username='nikhilkhat_5976',
                email='nikhilkhatri240@gmail.com',
                password='nikhil@123',
            )
            logger.info("Created superuser nikhilkhat_5976.")
        else:
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.is_active = True
            admin_user.email = 'nikhilkhatri240@gmail.com'
            admin_user.set_password('nikhil@123')
            admin_user.save()

        profile, _ = Profile.objects.get_or_create(user=admin_user)
        if not profile.phone or not profile.email_verified:
            profile.phone = profile.phone or '7900781098'
            profile.email_verified = True
            profile.save()

        # Seed initial Places if empty so Explore page has destinations
        from places.models import Place
        if not Place.objects.exists():
            default_places = [
                Place(name="The Ridge", city="Shimla", state="Himachal Pradesh", category="sightseeing", description="Famous open space in the heart of Shimla offering panoramic views."),
                Place(name="Mall Road", city="Shimla", state="Himachal Pradesh", category="shopping", description="Main street and shopping hub lined with cafes and handicraft stores."),
                Place(name="Jakhoo Temple", city="Shimla", state="Himachal Pradesh", category="sightseeing", description="Ancient temple situated on Jakhoo Hill, the highest peak in Shimla."),
                Place(name="Solang Valley", city="Manali", state="Himachal Pradesh", category="adventure", description="Renowned adventure valley for paragliding, zorbing, and winter sports."),
                Place(name="Old Manali", city="Manali", state="Himachal Pradesh", category="food", description="Charming bohemian village with bakeries, live music, and scenic cafes."),
                Place(name="Fort Aguada", city="Goa", state="Goa", category="sightseeing", description="17th-century Portuguese fortress overlooking the Arabian Sea."),
                Place(name="Baga Beach", city="Goa", state="Goa", category="beach", description="Popular beach destination known for water sports and vibrant shacks."),
                Place(name="Taj Mahal", city="Agra", state="Uttar Pradesh", category="sightseeing", description="Iconic ivory-white marble mausoleum on the south bank of the Yamuna river."),
            ]
            Place.objects.bulk_create(default_places)
            logger.info("Seeded initial places.")

    except Exception as exc:
        logger.warning("Database bootstrap skipped or failed: %s", exc)
