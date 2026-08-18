import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-not-for-production")
os.environ.setdefault("POSTGRES_DB", "test_sensor")
os.environ.setdefault("POSTGRES_USER", "test_sensor")
os.environ.setdefault("POSTGRES_PASSWORD", "test_sensor")

from .base import *  # noqa: E402,F403

DEBUG = False
