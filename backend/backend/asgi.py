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
# ensure migrations are applied to the ephemeral /tmp/db.sqlite3 on container boot.
if os.environ.get('VERCEL') and not os.environ.get('DATABASE_URL'):
    marker = Path('/tmp/.migrated')
    if not marker.exists():
        try:
            from django.core.management import call_command
            call_command('migrate', interactive=False, verbosity=0)
            marker.touch()
        except Exception:
            pass

