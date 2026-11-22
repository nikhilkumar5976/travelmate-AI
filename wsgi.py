"""
Root WSGI entrypoint for Vercel deployment.
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent / 'backend'
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

from backend.wsgi import application, app  # noqa: F401, E402
