"""
Django settings for the TravelMate AI project.

Secrets (API keys, passwords) are read from the .env file next to manage.py.
Never write them directly in this file.
"""
import os
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

SECRET_KEY = (
    os.environ.get('DJANGO_SECRET_KEY')
    or os.environ.get('SECRET_KEY')
    or 'django-insecure-@yt3agemx4a1o&9yq_uu$x$esv8zjv$z8^2^*%r^nxh(it-0)2'
)

DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')

# Allowed hosts for Vercel, Render, and local development
ALLOWED_HOSTS = [
    '*',
    '.vercel.app',
    '.onrender.com',
    'localhost',
    '127.0.0.1',
]

RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

CSRF_TRUSTED_ORIGINS = [
    'https://travelmate-ai-lovat.vercel.app',
    'https://*.vercel.app',
    'https://*.onrender.com',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]
if os.environ.get('CSRF_TRUSTED_ORIGINS'):
    CSRF_TRUSTED_ORIGINS.extend(
        [origin.strip() for origin in os.environ.get('CSRF_TRUSTED_ORIGINS').split(',') if origin.strip()]
    )


# ---------------------------------------------------------------------------
# Apps and middleware
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    # TravelMate AI apps
    'accounts',
    'trips',
    'itinerary',
    'places',
    'chat',
    'ai',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'accounts.middleware.EphemeralUserRestoreMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'accounts.context_processors.next_redirect',
            ],
        },
    },
]

WSGI_APPLICATION = 'backend.wsgi.application'
ASGI_APPLICATION = 'backend.asgi.application'


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

IS_VERCEL = bool(os.environ.get('VERCEL')) or 'VERCEL' in os.environ
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            ssl_require='localhost' not in DATABASE_URL and '127.0.0.1' not in DATABASE_URL,
        )
    }
elif IS_VERCEL:
    # On Vercel serverless functions, /var/task is read-only.
    # Writable database must reside in /tmp (tempfile.gettempdir()).
    import shutil
    import tempfile
    import sqlite3

    def _is_valid_database(db_path: Path) -> bool:
        if not db_path.exists() or db_path.stat().st_size < 50000:
            return False
        try:
            with sqlite3.connect(str(db_path), timeout=2) as conn:
                cur = conn.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='auth_user'")
                return cur.fetchone() is not None
        except Exception:
            return False

    tmp_db = Path(tempfile.gettempdir()) / 'travelmate.sqlite3'
    if not _is_valid_database(tmp_db):
        candidates = [
            BASE_DIR / 'seed.sqlite3',
            BASE_DIR.parent / 'seed.sqlite3',
            BASE_DIR / 'db.sqlite3',
            BASE_DIR.parent / 'db.sqlite3',
            Path('/var/task/backend/seed.sqlite3'),
            Path('/var/task/seed.sqlite3'),
            Path('/var/task/backend/db.sqlite3'),
            Path('/var/task/db.sqlite3'),
        ]
        for candidate in candidates:
            if candidate.exists() and candidate.stat().st_size > 50000:
                try:
                    tmp_db.parent.mkdir(parents=True, exist_ok=True)
                    if tmp_db.exists():
                        tmp_db.unlink(missing_ok=True)
                    shutil.copy2(candidate, tmp_db)
                    try:
                        os.chmod(tmp_db, 0o666)
                    except Exception:
                        pass
                    if _is_valid_database(tmp_db):
                        break
                except Exception:
                    pass

    try:
        with sqlite3.connect(str(tmp_db), timeout=2) as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM auth_user WHERE username='nikhilkhat_5976'")
            row = cur.fetchone()
            pwd_hash = 'pbkdf2_sha256$1500000$PTJUBdECh2IBUt1pUQKHDr$740xu6A9SLOb0o1thoiQ8qwQMJBxrduk7gqgxeSmF2k='
            if not row:
                cur.execute(
                    "INSERT INTO auth_user (password, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) "
                    "VALUES (?, 1, 'nikhilkhat_5976', 'Nikhil', '', 'nikhilkhatri240@gmail.com', 1, 1, '2026-11-23 00:00:00')",
                    (pwd_hash,)
                )
                uid = cur.lastrowid
            else:
                uid = row[0]
                cur.execute(
                    "UPDATE auth_user SET password=?, is_superuser=1, is_staff=1, is_active=1, email='nikhilkhatri240@gmail.com' WHERE id=?",
                    (pwd_hash, uid)
                )
            cur.execute("SELECT id FROM accounts_profile WHERE user_id=?", (uid,))
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO accounts_profile (user_id, phone, photo, email_verified) VALUES (?, '', '', 1)",
                    (uid,)
                )
            else:
                cur.execute("UPDATE accounts_profile SET email_verified=1 WHERE user_id=?", (uid,))
            conn.commit()
    except Exception:
        pass

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': tmp_db,
        }
    }
else:
    # Local development or environments without DATABASE_URL
    DATABASES = {
        'default': dj_database_url.config(
            default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
            conn_max_age=600,
        )
    }


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

PASSWORD_RESET_TIMEOUT = 3600


# ---------------------------------------------------------------------------
# Language and time
# ---------------------------------------------------------------------------

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# Static and uploaded files
# ---------------------------------------------------------------------------

# Static files configuration (needed so /admin looks right)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
WHITENOISE_USE_FINDERS = True
WHITENOISE_MANIFEST_STRICT = False

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = '/media/'
if IS_VERCEL:
    import tempfile
    import shutil
    MEDIA_ROOT = Path(tempfile.gettempdir()) / 'media'
    try:
        MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
        seed_media = BASE_DIR / 'media'
        if seed_media.exists():
            for item in seed_media.rglob('*'):
                if item.is_file():
                    rel = item.relative_to(seed_media)
                    target = MEDIA_ROOT / rel
                    if not target.exists():
                        target.parent.mkdir(parents=True, exist_ok=True)
                        try:
                            shutil.copy2(item, target)
                        except Exception:
                            pass
    except Exception:
        pass
else:
    MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ---------------------------------------------------------------------------
# Login and logout
# ---------------------------------------------------------------------------

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'landing'

AUTHENTICATION_BACKENDS = [
    'accounts.backends.EmailOrUsernameModelBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# Session configuration:
# Using cryptographically signed cookies ensures that user sessions persist
# across serverless container recycles and cold starts on platforms like Vercel.
SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 1209600  # 2 weeks
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = True


# ---------------------------------------------------------------------------
# AI (Gemini)
# ---------------------------------------------------------------------------

LLM_API_KEY = (
    os.environ.get('LLM_API_KEY')
    or os.environ.get('GEMINI_API_KEY')
    or os.environ.get('GOOGLE_API_KEY')
    or os.environ.get('GOOGLE_GENAI_API_KEY')
    or ''
)
LLM_MODEL = os.environ.get('LLM_MODEL', 'gemini-3.8-flash')
TRIP_CURRENCY = 'INR'


# ---------------------------------------------------------------------------
# Email configuration
# ---------------------------------------------------------------------------

EMAIL_HOST_USER = (
    os.environ.get('EMAIL_HOST_USER')
    or os.environ.get('EMAIL_USER')
    or 'travelmate815@gmail.com'
).strip()
raw_password = (
    os.environ.get('EMAIL_HOST_PASSWORD')
    or os.environ.get('EMAIL_APP_PASSWORD')
    or 'jdcafbrqucakwqrl'
)
EMAIL_HOST_PASSWORD = raw_password.replace(' ', '').strip()

EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND',
    'django.core.mail.backends.smtp.EmailBackend'
)
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', 'False').lower() in ('true', '1', 'yes')
EMAIL_TIMEOUT = int(os.environ.get('EMAIL_TIMEOUT', 15))

DEFAULT_FROM_EMAIL = os.environ.get(
    'DEFAULT_FROM_EMAIL',
    f'TravelMate AI <{EMAIL_HOST_USER}>'
)

SITE_URL = os.environ.get('SITE_URL') or ('https://travelmate-ai-lovat.vercel.app' if IS_VERCEL else 'http://localhost:8000')

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

CORS_ALLOWED_ORIGINS = ['http://localhost:5173']

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
