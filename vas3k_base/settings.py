import os
from pathlib import Path

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

from utils.strings import random_string

# Build paths inside the project like this: BASE_DIR / "subdir".
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY") or "wow-so-secret"

# SECURITY WARNING: don"t run with debug turned on in production!
DEBUG = (os.getenv("DEBUG") != "false")

ALLOWED_HOSTS = ["127.0.0.1", "localhost", "0.0.0.0", "base.vas3k.club"]
INTERNAL_IPS = ["127.0.0.1"]
CSRF_TRUSTED_ORIGINS = ["https://base.vas3k.club"]
RELEASE = random_string(length=8)

ADMINS = [
    ("vas3k", "me@vas3k.ru"),
]


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "authn.apps.AuthnConfig",
    "users.apps.UsersConfig",
    "items.apps.ItemsConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "vas3k_base.middleware.ExceptionMiddleware",
]

ROOT_URLCONF = "vas3k_base.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(BASE_DIR, "templates"),
        ],
        "APP_DIRS": False,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "vas3k_base.context_processors.settings_processor",
            ],
        },
    },
]

WSGI_APPLICATION = "vas3k_base.wsgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB") or "vas3k_base",
        "USER": os.getenv("POSTGRES_USER") or "postgres",
        "PASSWORD": os.getenv("POSTGRES_PASSWORD") or "",
        "HOST": os.getenv("POSTGRES_HOST") or "localhost",
        "PORT": os.getenv("POSTGRES_PORT") or 5432,
    }
}

if bool(os.getenv("POSTGRES_USE_POOLING")):
    DATABASES["default"]["OPTIONS"] = {
        "pool": {
            "min_size": 3,
            "max_size": 10,
            "timeout": 10, # fail in 10 sec under load
            "max_idle": 300, # close idle after 5 min
        }
    }
else:
    DATABASES["default"]["CONN_MAX_AGE"] = 0
    DATABASES["default"]["CONN_HEALTH_CHECKS"] = True


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = "ru-RU"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = False

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = "/static/"
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]


# Email

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "email-smtp.eu-central-1.amazonaws.com")
EMAIL_PORT = os.getenv("EMAIL_PORT", 587)
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "Вастрик Ивенты <events@vas3k.club>")

# Telegram

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_BOT_URL = os.getenv("TELEGRAM_BOT_URL") or "https://t.me/vas3k_club_bot"

# Logging

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler"
        },
    },
    "loggers": {
        "": {  # "catch all" loggers by referencing it with the empty string
            "handlers": ["console"],
            "level": "DEBUG",
        },
    },
}

# App

APP_TITLE = "Вастрик 💽 База"
APP_HOST = os.environ.get("APP_HOST") or "http://127.0.0.1:8000"
DEFAULT_AVATAR = "https://i.vas3k.club/v.png"
SENTRY_DSN = os.getenv("SENTRY_DSN")
LOGIN_URL = "/login/"


# Stripe

STRIPE_API_KEY = os.getenv("STRIPE_API_KEY") or ""
STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY") or ""
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET") or ""
STRIPE_SUCCESS_URL = f"{APP_HOST}/me/"
STRIPE_CANCEL_URL = f"{APP_HOST}/me/"

# Auth

AUTH_USER_MODEL = "users.User"
CLUB_BASE_URL = "https://vas3k.club"
CLUB_OPENID_CONFIG = {
    "name": "club",
    "client_id": "vastrik_baza",
    "client_secret": os.getenv("CLUB_OPENID_CONFIG_SECRET"),
    "api_base_url": CLUB_BASE_URL,
    "server_metadata_url": f"{CLUB_BASE_URL}/.well-known/openid-configuration",
    "client_kwargs": {"scope": "openid contact"},
}
CLUB_SERVICE_TOKEN = os.getenv("CLUB_SERVICE_TOKEN") or ""

# Sentry

if SENTRY_DSN and not DEBUG:
    # activate sentry on production
    sentry_sdk.init(dsn=SENTRY_DSN, integrations=[
        DjangoIntegration(),
    ])
