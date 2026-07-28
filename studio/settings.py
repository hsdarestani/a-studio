import base64
import os
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent


def env(name, default=""):
    return os.environ.get(name, default)


SECRET_KEY = env("SECRET_KEY", "unsafe-development-key")
DEBUG = env("DEBUG", "0") == "1"
ALLOWED_HOSTS = [x.strip() for x in env("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if x.strip()]
CSRF_TRUSTED_ORIGINS = [x.strip() for x in env("CSRF_TRUSTED_ORIGINS", "").split(",") if x.strip()]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.apple",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "studio.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {
        "context_processors": [
            "django.template.context_processors.request",
            "django.contrib.auth.context_processors.auth",
            "django.contrib.messages.context_processors.messages",
            "core.context_processors.platform_context",
        ]
    },
}]
WSGI_APPLICATION = "studio.wsgi.application"
ASGI_APPLICATION = "studio.asgi.application"

_db_url = urlparse(env("DATABASE_URL", f"sqlite:///{BASE_DIR / 'db.sqlite3'}"))
if _db_url.scheme.startswith("postgres"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": _db_url.path.lstrip("/"),
            "USER": _db_url.username,
            "PASSWORD": _db_url.password,
            "HOST": _db_url.hostname,
            "PORT": _db_url.port or 5432,
            "CONN_MAX_AGE": 60,
        }
    }
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "de"
LANGUAGES = [("de", "Deutsch"), ("en", "English")]
LOCALE_PATHS = [BASE_DIR / "locale"]
LANGUAGE_COOKIE_NAME = "astudio_language"
TIME_ZONE = "Europe/Berlin"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "landing"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "optional"
ACCOUNT_UNIQUE_EMAIL = True
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
SOCIALACCOUNT_LOGIN_ON_GET = False

GOOGLE_OAUTH_CLIENT_ID = env("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_OAUTH_CLIENT_SECRET = env("GOOGLE_OAUTH_CLIENT_SECRET")
APPLE_OAUTH_CLIENT_ID = env("APPLE_OAUTH_CLIENT_ID")
APPLE_OAUTH_KEY_ID = env("APPLE_OAUTH_KEY_ID")
APPLE_OAUTH_TEAM_ID = env("APPLE_OAUTH_TEAM_ID")
APPLE_OAUTH_PRIVATE_KEY_B64 = env("APPLE_OAUTH_PRIVATE_KEY_B64")
try:
    APPLE_OAUTH_PRIVATE_KEY = base64.b64decode(APPLE_OAUTH_PRIVATE_KEY_B64).decode() if APPLE_OAUTH_PRIVATE_KEY_B64 else ""
except (ValueError, UnicodeDecodeError):
    APPLE_OAUTH_PRIVATE_KEY = ""

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
        "OAUTH_PKCE_ENABLED": True,
        "VERIFIED_EMAIL": True,
    },
    "apple": {"VERIFIED_EMAIL": True},
}
if GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET:
    SOCIALACCOUNT_PROVIDERS["google"]["APPS"] = [{
        "client_id": GOOGLE_OAUTH_CLIENT_ID,
        "secret": GOOGLE_OAUTH_CLIENT_SECRET,
        "key": "",
    }]
if all([APPLE_OAUTH_CLIENT_ID, APPLE_OAUTH_KEY_ID, APPLE_OAUTH_TEAM_ID, APPLE_OAUTH_PRIVATE_KEY]):
    SOCIALACCOUNT_PROVIDERS["apple"]["APPS"] = [{
        "client_id": APPLE_OAUTH_CLIENT_ID,
        "secret": APPLE_OAUTH_KEY_ID,
        "key": APPLE_OAUTH_TEAM_ID,
        "settings": {"certificate_key": APPLE_OAUTH_PRIVATE_KEY},
    }]

CELERY_BROKER_URL = env("REDIS_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 600
CELERY_TASK_SOFT_TIME_LIMIT = 540

OPENAI_API_KEY = env("OPENAI_API_KEY")
OPENAI_MODEL = env("OPENAI_MODEL", "gpt-5-mini")
APP_PUBLIC_URL = env("APP_PUBLIC_URL", "http://localhost:8000").rstrip("/")
APP_ROOT_DOMAIN = env("APP_ROOT_DOMAIN", "studio.aplus-solution.de")
APP_DATA_ROOT = Path(env("APP_DATA_ROOT", "/data/apps" if not DEBUG else str(BASE_DIR / ".data")))

EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", "smtp.strato.de")
EMAIL_PORT = int(env("EMAIL_PORT", "465"))
EMAIL_USE_SSL = env("EMAIL_USE_SSL", "1") == "1"
EMAIL_USE_TLS = env("EMAIL_USE_TLS", "0") == "1"
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "app@aplus-solution.de")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
EMAIL_TIMEOUT = int(env("EMAIL_TIMEOUT", "20"))
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "A+ Studio <app@aplus-solution.de>")
SERVER_EMAIL = env("SERVER_EMAIL", DEFAULT_FROM_EMAIL)
BILLING_CONTACT_EMAIL = env("BILLING_CONTACT_EMAIL", "app@aplus-solution.de")

GITHUB_TOKEN = env("GITHUB_TOKEN")
GITHUB_OWNER = env("GITHUB_OWNER", "hsdarestani")
GITHUB_REPOSITORY_PREFIX = env("GITHUB_REPOSITORY_PREFIX", "astudio-app-")
