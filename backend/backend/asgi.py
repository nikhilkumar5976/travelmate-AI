import os
import sys
from pathlib import Path

from django.core.asgi import get_asgi_application

# Ensure the project/backend root directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

application = get_asgi_application()
app = application

# On Vercel without DATABASE_URL, create tables in /tmp/db.sqlite3 on cold start
if os.environ.get("VERCEL") and not os.environ.get("DATABASE_URL"):
    try:
        from django.core.management import call_command
        from django.db import connection

        with connection.cursor() as cursor:
            tables = connection.introspection.table_names(cursor)

        if "auth_user" not in tables:
            call_command("migrate", interactive=False, verbosity=0)
    except Exception as exc:
        print(f"Startup migration skipped/failed: {exc}")
