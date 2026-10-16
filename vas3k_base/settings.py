import os
from datetime import timedelta
from pathlib import Path

import sentry_sdk
from django.core.exceptions import ImproperlyConfigured
from sentry_sdk.integrations.django import DjangoIntegration

from utils.strings import random_string

BASE_DIR = Path(__file__).resolve().parent.parent

ONLINE_COUNTRY_ID = "online"
INCLUDE_ONLINE_PARAM = "include_online"

SECRET_KEY = os.getenv("SECRET_KEY") or "wow-so-secret"

DEBUG = (os.getenv("DEBUG") != "false")
if not DEBUG and not os.getenv("SECRET_KEY"):
    raise ImproperlyConfigured("SECRET_KEY must be set when DEBUG is false")

ALLOWED_HOSTS = ["127.0.0.1", "localhost", "0.0.0.0", "basa.club"]
INTERNAL_IPS = ["127.0.0.1", "::1"]
CSRF_TRUSTED_ORIGINS = ["https://basa.club"]
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
    "django.contrib.sitemaps",
    "django.contrib.postgres",
    "django_vite",
    "django_q",
    "authn.apps.AuthnConfig",
    "users.apps.UsersConfig",
    "categories.apps.CategoriesConfig",
    "geo.apps.GeoConfig",
    "items.apps.ItemsConfig",
    "search.apps.SearchConfig",
    "comments.apps.CommentsConfig",
    "counters.apps.CountersConfig",
    "bookmarks.apps.BookmarksConfig",
    "complaints.apps.ComplaintsConfig",
    "notifications.apps.NotificationsConfig",
    "godmode.apps.GodmodeConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "authn.middleware.AuthSessionMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "geo.middleware.GeoMiddleware",
    "vas3k_base.middleware.ExceptionMiddleware",
]

ROOT_URLCONF = "vas3k_base.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(BASE_DIR, "templates"),
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "vas3k_base.context_processors.settings_processor",
                "categories.context_processors.categories",
                "geo.context_processors.geo",
                "notifications.context_processors.listing_subscription",
            ],
            "builtins": [
                "items.templatetags.listing",
                "comments.templatetags.comments",
                "bookmarks.templatetags.bookmarks",
                "complaints.templatetags.complaints",
                "common.templatetags.islands",
                "common.templatetags.text",
                "common.templatetags.paginator",
                "common.templatetags.query_params",
                "django_vite.templatetags.django_vite",
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

REDIS_HOST = os.getenv("REDIS_HOST") or "127.0.0.1"
REDIS_PORT = int(os.getenv("REDIS_PORT") or 6379)

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "vas3k-base",
        "TIMEOUT": 60 * 60 * 24,
    },
    # DB 1: cache.clear() must not flush the django-q queue, which uses DB 0.
    "redis_cache": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/1",
        "TIMEOUT": None,
    },
}

if os.getenv("POSTGRES_USE_POOLING", "").lower() in {"1", "true"}:
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


# Queue (django-q2)

Q_CLUSTER = {
    "name": "vas3k_base",
    "workers": 2,
    "timeout": 60,
    "retry": 90,
    "max_attempts": 3,
    "queue_limit": 200,
    "save_limit": 50,
    "redis": {
        "host": REDIS_HOST,
        "port": REDIS_PORT,
    },
}


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = "ru-RU"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = False

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = os.getenv("STATIC_ROOT") or "/tmp/static"
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "frontend", "static"),
]

# Frontend (Vite)
# dev mode loads JS from `npm run dev` server, otherwise from `npm run build` output in frontend/static/dist

DJANGO_VITE = {
    "default": {
        "dev_mode": (os.getenv("VITE_DEV_MODE") or str(DEBUG)).lower() == "true",
        "dev_server_host": os.getenv("VITE_DEV_SERVER_HOST") or "localhost",
        "dev_server_port": int(os.getenv("VITE_DEV_SERVER_PORT") or 5173),
        "static_url_prefix": "dist",
        "manifest_path": os.path.join(BASE_DIR, "frontend", "static", "dist", ".vite", "manifest.json"),
    }
}


# Email

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "email-smtp.eu-central-1.amazonaws.com")
EMAIL_PORT = os.getenv("EMAIL_PORT", 587)
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "Вастрик Ивенты <events@vas3k.club>")

# Telegram

TELEGRAM_PUBLIC_CHAT_URL = os.getenv("TELEGRAM_PUBLIC_CHAT_URL") or "https://t.me/vas3k_base"
TELEGRAM_ADMIN_CHAT_ID = os.getenv("TELEGRAM_ADMIN_CHAT_ID") or None
TELEGRAM_BASE_CHAT_ID = os.getenv("TELEGRAM_BASE_CHAT_ID") or None
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or "000000000:MOCK_TOKEN_REPLACE_ME"
TELEGRAM_BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME") or "vas3k_base_bot"
TELEGRAM_BOT_URL = os.getenv("TELEGRAM_BOT_URL") or f"https://t.me/{TELEGRAM_BOT_USERNAME}"
TELEGRAM_BOT_WEBHOOK_HOST = os.getenv("TELEGRAM_BOT_WEBHOOK_HOST") or "0.0.0.0"
TELEGRAM_BOT_WEBHOOK_PORT = int(os.getenv("TELEGRAM_BOT_WEBHOOK_PORT") or 8814)
TELEGRAM_BOT_WEBHOOK_URL = os.getenv("TELEGRAM_BOT_WEBHOOK_URL") or ""

# Logging

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "": {  # "catch all" loggers by referencing it with the empty string
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
        },
    },
}

# App

APP_TITLE = "Вастрик База"
APP_HOST = os.environ.get("APP_HOST") or "http://127.0.0.1:8000"
if not TELEGRAM_BOT_WEBHOOK_URL:
    TELEGRAM_BOT_WEBHOOK_URL = f"{APP_HOST}/telegram/webhook/"
DEFAULT_AVATAR = "https://i.vas3k.club/v.png"
DEFAULT_PAGE_SIZE = 70
PROFILE_POSTS_PAGE_SIZE = 30
PROFILE_COMMENTS_PAGE_SIZE = 100

# Limits

RATE_LIMIT_PERIOD = timedelta(hours=24)
COMMENT_RATE_LIMIT = 100
COMMENT_EDIT_PERIOD = timedelta(days=20)
COMMENT_DELETE_PERIOD = timedelta(days=20)
ITEM_RATE_LIMIT = 50
ITEM_VOTE_RATE_LIMIT = 100
COMMENT_VOTE_RATE_LIMIT = 100
VOTE_RETRACT_PERIOD = timedelta(days=20)

ITEM_MODERATION_REASONS = [
    {
        "title": "Дубликат.",
        "description": "Такой пост уже существует.",
    },
    {
        "title": "Плохой заголовок.",
        "description": "Заголовок не дает понять о чем пост либо слишком рекламный.",
    },
    {
        "title": "Недостаточно описания.",
        "description": "Добавьте описание и подробности, чтобы остальным было легче",
    },
    {
        "title": "Недостаточно контактов.",
        "description": "Добавьте контакты для связи или адрес.",
    },
    {
        "title": "Неправильная категория.",
        "description": "Категория или город выбраны неправильно для этой записи.",
    },
    {
        "title": "Недооформлено.",
        "description": "Проверьте заголовок, добавьте описание, контакты, адреса и всё остальное необходимое",
    },
]
MEDIA_UPLOAD_URL = "https://i.vas3k.club/upload/multipart/"
MEDIA_UPLOAD_CODE = os.getenv("MEDIA_UPLOAD_CODE") or ""
SENTRY_DSN = os.getenv("SENTRY_DSN")
LOGIN_URL = "/login/"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 365 * 2
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SAMESITE = "Lax"


# AI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or ""

# Stripe

STRIPE_API_KEY = os.getenv("STRIPE_API_KEY") or ""
STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY") or ""
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET") or ""
STRIPE_SUCCESS_URL = f"{APP_HOST}/user/me/"
STRIPE_CANCEL_URL = f"{APP_HOST}/user/me/"

# Auth

AUTH_USER_MODEL = "users.User"
BOT_USER_SLUG = "bot"
MODERATOR_USER_SLUG = "moderator"
DELETED_USER_SLUG = "deleted"
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
AUTH_CODE_LENGTH = 16
AUTH_CODE_EXPIRATION_TIMEDELTA = timedelta(minutes=10)
AUTH_MAX_CODE_TIMEDELTA = timedelta(hours=3)
AUTH_MAX_CODE_COUNT = 5
AUTH_MAX_CODE_COUNT_PER_IP = 5
AUTH_MAX_CODE_COUNT_TOTAL = 100

# Debug toolbar

if DEBUG:
    INSTALLED_APPS = ["debug_toolbar", *INSTALLED_APPS]
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")

# Sentry

if SENTRY_DSN and not DEBUG:
    # activate sentry on production
    sentry_sdk.init(dsn=SENTRY_DSN, integrations=[
        DjangoIntegration(),
    ])
