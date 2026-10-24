"""Django settings. Secrets come ONLY from environment variables (HARD RULE 4)."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent          # backend/
REPO_ROOT = BASE_DIR.parent                                 # project root (lab_pack/, virtulab_data/, config.json)
sys.path.insert(0, str(REPO_ROOT))                          # so `import lab_pack` works (one copy, not a fork)
load_dotenv(REPO_ROOT / ".env")

TESTING = "test" in sys.argv
if TESTING:                                                  # tests never need your real .env
    os.environ.setdefault("SECRET_KEY", "test-only-secret-key-not-for-real-use-0123456789")
    os.environ.setdefault("HMAC_SECRET", "VIRTULAB-TEST-SECRET-NOT-REAL")

if TESTING:                                                  # fast hashing ONLY while running tests
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

SECRET_KEY = os.environ["SECRET_KEY"]                        # missing key must fail loudly (decision D10)
HMAC_SECRET = os.environ.get("HMAC_SECRET", "")              # checked when a code is redeemed
AI_KEY = os.environ.get("AI_KEY", "")
DEBUG = os.environ.get("DEBUG", "False").lower() in ("1", "true", "yes")
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",") if h.strip()]
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]

INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "rest_framework", "api",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "core.urls"
WSGI_APPLICATION = "core.wsgi.application"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [], "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request", "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages"]},
}]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
AUTH_PASSWORD_VALIDATORS = []                                # PINs are 4-6 digits by design; brute force is rate-limited
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LANGUAGE_CODE = "en"
TIME_ZONE = "Asia/Kolkata"                                   # decision D11
USE_TZ = True
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["api.auth.TokenAuth"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "EXCEPTION_HANDLER": "api.errors.handler",
    "UNAUTHENTICATED_USER": None,
}

if not DEBUG and not TESTING:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
