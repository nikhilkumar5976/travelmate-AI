import os
import sys
from pathlib import Path

# Ensure the backend directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

from django.core.asgi import get_asgi_application

application = get_asgi_application()
app = application

# Automatic PostgreSQL initialization for Supabase/Neon when DATABASE_URL is set
try:
    from backend.bootstrap import run_database_bootstrap
    run_database_bootstrap()
except Exception:
    pass
