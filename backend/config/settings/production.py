"""Environment-driven production security policy."""

from .base import *  # noqa: F403


def require_env(name):
    value = os.getenv(name, "").strip()  # noqa: F405
    if not value:
        raise RuntimeError(f"{name} production ortamında zorunludur.")
    return value


SECRET_KEY = require_env("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = [
    item.strip()
    for item in require_env("DJANGO_ALLOWED_HOSTS").split(",")
    if item.strip()
]
CSRF_TRUSTED_ORIGINS = [
    item.strip()
    for item in require_env("CSRF_TRUSTED_ORIGINS").split(",")
    if item.strip()
]
PUBLIC_ORIGIN = require_env("PUBLIC_ORIGIN")
for database_key, environment_name in (
    ("NAME", "POSTGRES_DB"),
    ("USER", "POSTGRES_USER"),
    ("PASSWORD", "POSTGRES_PASSWORD"),
    ("HOST", "POSTGRES_HOST"),
    ("PORT", "POSTGRES_PORT"),
):
    DATABASES["default"][database_key] = require_env(environment_name)  # noqa: F405

for path_setting in (
    "MODEL_ARTIFACT_PATH",
    "MODEL_METADATA_PATH",
    "FAILURE_TYPE_MODEL_ARTIFACT_PATH",
    "FAILURE_TYPE_MODEL_METADATA_PATH",
    "INPUT_DOMAIN_CONTRACT_PATH",
    "REPLAY_PREPARED_DATASET_PATH",
    "REPLAY_PREPARED_METADATA_PATH",
):
    if not os.getenv(path_setting, "").strip():  # noqa: F405
        raise RuntimeError(f"{path_setting} production ortamında zorunludur.")

DEBUG = False
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)  # noqa: F405
SESSION_COOKIE_SECURE = env_bool("DJANGO_SESSION_COOKIE_SECURE", True)  # noqa: F405
CSRF_COOKIE_SECURE = env_bool("DJANGO_CSRF_COOKIE_SECURE", True)  # noqa: F405
SECURE_HSTS_SECONDS = env_int(  # noqa: F405
    "DJANGO_SECURE_HSTS_SECONDS", 31536000, minimum=0, maximum=63072000
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(  # noqa: F405
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", True
)
SECURE_HSTS_PRELOAD = env_bool("DJANGO_SECURE_HSTS_PRELOAD", False)  # noqa: F405
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

if env_bool("DJANGO_TRUST_PROXY_SSL_HEADER", False):  # noqa: F405
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

database_sslmode = os.getenv("POSTGRES_SSLMODE", "require")  # noqa: F405
DATABASES["default"].setdefault("OPTIONS", {})["sslmode"] = database_sslmode  # noqa: F405

JWT_REFRESH_COOKIE_SECURE = env_bool("JWT_REFRESH_COOKIE_SECURE", True)  # noqa: F405
ENABLE_API_DOCS = env_bool("ENABLE_API_DOCS", False)  # noqa: F405
