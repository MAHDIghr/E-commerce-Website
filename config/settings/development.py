"""
Django development settings.
"""

import os

from dotenv import load_dotenv

from .base import *


load_dotenv(BASE_DIR / ".env")


SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

DEBUG = True

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        "DJANGO_ALLOWED_HOSTS",
        "127.0.0.1,localhost",
    ).split(",")
    if host.strip()
]


EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"