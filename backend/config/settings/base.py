import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BASE_DIR.parent


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [
        item.strip() for item in os.getenv(name, default).split(",") if item.strip()
    ]


def env_int(name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"{name} tam sayı olmalıdır.") from exc
    if str(value) != raw.strip() or not minimum <= value <= maximum:
        raise RuntimeError(f"{name} {minimum} ile {maximum} arasında olmalıdır.")
    return value


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("DJANGO_SECRET_KEY ortam degiskeni tanimlanmalidir.")

DEBUG = env_bool("DJANGO_DEBUG")
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

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
    "apps.core",
    "apps.kullanicilar",
    "apps.bakim",
    "apps.tahminler",
]

MODEL_ARTIFACT_PATH = Path(
    os.getenv(
        "MODEL_ARTIFACT_PATH",
        REPO_ROOT / "ml" / "artifacts" / "binary-failure-1.0.0.joblib",
    )
)
MODEL_METADATA_PATH = Path(
    os.getenv(
        "MODEL_METADATA_PATH",
        REPO_ROOT / "data" / "metadata" / "binary_failure_model.json",
    )
)
FAILURE_TYPE_MODEL_ARTIFACT_PATH = Path(
    os.getenv(
        "FAILURE_TYPE_MODEL_ARTIFACT_PATH",
        REPO_ROOT / "ml" / "artifacts" / "failure-type-1.0.0.joblib",
    )
)
FAILURE_TYPE_MODEL_METADATA_PATH = Path(
    os.getenv(
        "FAILURE_TYPE_MODEL_METADATA_PATH",
        REPO_ROOT / "data" / "metadata" / "failure_type_model.json",
    )
)
SHAP_TOP_N = env_int("SHAP_TOP_N", 3, minimum=1, maximum=5)
REPLAY_PREPARED_DATASET_PATH = Path(
    os.getenv("REPLAY_PREPARED_DATASET_PATH", "/data/processed/ai4i2020_prepared.csv")
)
REPLAY_PREPARED_METADATA_PATH = Path(
    os.getenv(
        "REPLAY_PREPARED_METADATA_PATH", "/data/metadata/failure_label_analysis.json"
    )
)

MIDDLEWARE = [
    "apps.core.middleware.TraceIdMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB"),
        "USER": os.getenv("POSTGRES_USER"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
        "HOST": os.getenv("POSTGRES_HOST", "db"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "tr"
TIME_ZONE = "Europe/Istanbul"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "kullanicilar.Kullanici"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_THROTTLE_RATES": {"login": os.getenv("LOGIN_THROTTLE_RATE", "10/min")},
    "EXCEPTION_HANDLER": "apps.core.exception_handler.standart_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=int(os.getenv("JWT_ACCESS_MINUTES", "5"))
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.getenv("JWT_REFRESH_DAYS", "1"))),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,
}

JWT_REFRESH_COOKIE_NAME = os.getenv("JWT_REFRESH_COOKIE_NAME", "refresh_token")
JWT_REFRESH_COOKIE_SECURE = env_bool("JWT_REFRESH_COOKIE_SECURE")
JWT_REFRESH_COOKIE_SAMESITE = os.getenv("JWT_REFRESH_COOKIE_SAMESITE", "Lax")
JWT_REFRESH_COOKIE_PATH = "/api/auth/"
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", "http://localhost:5173")
CSRF_COOKIE_HTTPONLY = False

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "guvenli_json": {"()": "apps.core.logging.GuvenliJsonFormatter"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "guvenli_json"},
    },
    "loggers": {
        "api.request": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "api.exception": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.server": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
