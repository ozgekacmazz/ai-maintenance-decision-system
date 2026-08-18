from .base import *  # noqa: F403

CORS_ALLOWED_ORIGINS = env_list(  # noqa: F405
    "CORS_ALLOWED_ORIGINS", "http://localhost:5173"
)
