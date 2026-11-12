"""Base settings shared by every AquaSafe environment."""

from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CORS_ALLOWED_ORIGINS=(list, ["http://localhost:3000", "http://127.0.0.1:3000"]),
    MQTT_PORT=(int, 1883),
    MQTT_TLS=(bool, False),
    REDIS_URL=(str, "redis://localhost:6379/0"),
    CELERY_TASK_ALWAYS_EAGER=(bool, False),
)

if (BASE_DIR / ".env").exists():
    environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="insecure-development-key-change-me")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "django_filters",
    "channels",
    "apps.common",
    "apps.accounts",
    "apps.audit",
    "apps.farms",
    "apps.devices",
    "apps.telemetry",
    "apps.commands",
    "apps.alerts",
    "apps.simulations",
    "apps.marketplace",
    "apps.messaging",
    "apps.support",
    "apps.installations",
    "apps.subscriptions",
    "apps.notifications",
    "apps.sync",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.common.middleware.RequestIdMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": env.db("DATABASE_URL", default="postgres:///aquasafe"),
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 6},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_RENDERER_CLASSES": (
        "apps.common.renderers.CamelCaseJSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ),
    "DEFAULT_PARSER_CLASSES": (
        "apps.common.parsers.CamelCaseJSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ),
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "EXCEPTION_HANDLER": "apps.common.exceptions.api_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": ("rest_framework.throttling.ScopedRateThrottle",),
    "DEFAULT_THROTTLE_RATES": {
        "auth": "20/min",
        "register": "10/min",
        "password": "5/min",
        "telemetry": "600/min",
        "provision": "10/min",
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "TOKEN_OBTAIN_SERIALIZER": "apps.accounts.serializers.AquaSafeTokenObtainPairSerializer",
    "TOKEN_REFRESH_SERIALIZER": "apps.accounts.serializers.AquaSafeTokenRefreshSerializer",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "AquaSafe API",
    "DESCRIPTION": "Aquaculture management, telemetry and device communication API.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": r"/api/v1",
}

CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS", default=["http://localhost:3000", "http://127.0.0.1:3000"]
)
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS", default=["http://localhost:3000", "http://127.0.0.1:3000"]
)

REDIS_URL = env.str("REDIS_URL", default="redis://localhost:6379/0")

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [REDIS_URL]},
    }
}

CELERY_BROKER_URL = env.str("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = env.str("CELERY_RESULT_BACKEND", default=REDIS_URL)
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = "UTC"
CELERY_BEAT_SCHEDULE = {
    "expire-device-commands": {
        "task": "apps.commands.tasks.expire_device_commands",
        "schedule": 60.0,
    },
    "mark-stale-devices": {
        "task": "apps.devices.tasks.mark_stale_devices",
        "schedule": 60.0,
    },
    "dispatch-pending-notifications": {
        "task": "apps.notifications.tasks.dispatch_pending_notifications",
        "schedule": 60.0,
    },
}

MQTT_HOST = env.str("MQTT_HOST", default="localhost")
MQTT_PORT = env.int("MQTT_PORT", default=1883)
MQTT_TLS = env.bool("MQTT_TLS", default=False)
MQTT_CA_CERTS = env.str("MQTT_CA_CERTS", default="")
MQTT_USERNAME = env.str("MQTT_USERNAME", default="aquasafe-backend")
MQTT_PASSWORD = env.str("MQTT_PASSWORD", default="")
MQTT_TOPIC_PREFIX = env.str("MQTT_TOPIC_PREFIX", default="aquasafe/v1")
MQTT_QOS = env.int("MQTT_QOS", default=1)
MQTT_KEEPALIVE = env.int("MQTT_KEEPALIVE", default=60)
SIMULATION_LEGACY_BRIDGE_ENABLED = env.bool("SIMULATION_LEGACY_BRIDGE_ENABLED", default=False)
SIMULATION_LEGACY_BRIDGE_POND_ID = env.str("SIMULATION_LEGACY_BRIDGE_POND_ID", default="")
SIMULATION_LEGACY_MQTT_HOST = env.str("SIMULATION_LEGACY_MQTT_HOST", default="broker.hivemq.com")
SIMULATION_LEGACY_MQTT_PORT = env.int("SIMULATION_LEGACY_MQTT_PORT", default=1883)
SIMULATION_LEGACY_TOPIC = env.str(
    "SIMULATION_LEGACY_TOPIC", default="techsharks-fishpond-7731/readings"
)
DEVICE_SECRET_ENCRYPTION_KEY = env.str("DEVICE_SECRET_ENCRYPTION_KEY", default="")
DEVICE_STALE_AFTER_SECONDS = env.int("DEVICE_STALE_AFTER_SECONDS", default=180)
NOTIFICATION_EMAIL_ENABLED = env.bool("NOTIFICATION_EMAIL_ENABLED", default=False)
NOTIFICATION_BATCH_SIZE = env.int("NOTIFICATION_BATCH_SIZE", default=100)
DEFAULT_FROM_EMAIL = env.str("DEFAULT_FROM_EMAIL", default="AquaSafe <alerts@localhost>")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {"()": "apps.common.logging.JsonFormatter"},
        "simple": {"format": "%(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
        },
    },
    "root": {"handlers": ["console"], "level": env.str("LOG_LEVEL", default="INFO")},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
