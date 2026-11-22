import os
import sys
from pathlib import Path

# Ensure backend directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

application = get_asgi_application()
app = application

# On Vercel serverless functions without an external DATABASE_URL,
# ensure all database tables exist on the ephemeral /tmp/db.sqlite3 on boot.
if os.environ.get('VERCEL') and not os.environ.get('DATABASE_URL'):
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            tables = connection.introspection.table_names(cursor)
        if 'auth_user' not in tables:
            from django.core.management import call_command
            call_command('migrate', interactive=False, verbosity=0)
    except Exception:
        pass

