"""
Django production settings.
"""

import os

from .base import *


def get_required_env(name: str) -> str:
    """Return a required environment variable."""
    value = os.environ.get(name)

    if not value:
        raise RuntimeError(
            f"Required environment variable is missing: {name}"
        )

    return value


def get_env_bool(name: str, default: bool = False) -> bool:
    """Return an environment variable converted to bool."""
    value = os.environ.get(name)

    if value is None:
        return default

    return value.lower() in {"1", "true", "yes", "on"}


SECRET_KEY = get_required_env("DJANGO_SECRET_KEY")

DEBUG = False

ALLOWED_HOSTS = [
    host.strip()
    for host in get_required_env("DJANGO_ALLOWED_HOSTS").split(",")
    if host.strip()
]


# -----------------------------------------------------------------------------
# CSRF
# -----------------------------------------------------------------------------

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in get_required_env(
        "DJANGO_CSRF_TRUSTED_ORIGINS"
    ).split(",")
    if origin.strip()
]


# -----------------------------------------------------------------------------
# HTTPS
# -----------------------------------------------------------------------------

SECURE_SSL_REDIRECT = True

SECURE_HSTS_SECONDS = 31536000

SECURE_HSTS_INCLUDE_SUBDOMAINS = False

SECURE_HSTS_PRELOAD = False


# -----------------------------------------------------------------------------
# Secure cookies
# -----------------------------------------------------------------------------

SESSION_COOKIE_SECURE = True

CSRF_COOKIE_SECURE = True


# -----------------------------------------------------------------------------
# Email
# -----------------------------------------------------------------------------

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

EMAIL_HOST = get_required_env("EMAIL_HOST")

EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))

EMAIL_USE_TLS = get_env_bool("EMAIL_USE_TLS", True)

EMAIL_USE_SSL = get_env_bool("EMAIL_USE_SSL", False)

EMAIL_HOST_USER = get_required_env("EMAIL_HOST_USER")

EMAIL_HOST_PASSWORD = get_required_env("EMAIL_HOST_PASSWORD")

DEFAULT_FROM_EMAIL = get_required_env("DEFAULT_FROM_EMAIL")

SERVER_EMAIL = get_required_env("SERVER_EMAIL")


# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "django": {
            "format": "{levelname} {asctime} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "django",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

# =============================================================================
# DEPLOYMENT REMINDER - cPanel
# =============================================================================
#
# Lors du déploiement en production sur cPanel/Linux :
#
# 1. Configurer dans l'environnement de l'application Python :
#
#    DJANGO_SETTINGS_MODULE=config.settings.production
#
# 2. Configurer les variables d'environnement de production :
#
#    DJANGO_SECRET_KEY
#    DJANGO_ALLOWED_HOSTS
#    DJANGO_CSRF_TRUSTED_ORIGINS
#    EMAIL_HOST
#    EMAIL_PORT
#    EMAIL_USE_TLS
#    EMAIL_USE_SSL
#    EMAIL_HOST_USER
#    EMAIL_HOST_PASSWORD
#    DEFAULT_FROM_EMAIL
#    SERVER_EMAIL
#
# 3. NE PAS mettre ces secrets directement dans ce fichier.
#
# 4. Configurer l'application Django avec le serveur WSGI/Passenger
#    de cPanel.
#
# 5. Exécuter les commandes Django avec les settings de production :
#
#    python manage.py migrate --settings=config.settings.production
#
#    python manage.py collectstatic --noinput \
#        --settings=config.settings.production
#
#    python manage.py check --deploy \
#        --settings=config.settings.production
#
# 6. Vérifier que HTTPS est correctement configuré avant de conserver :
#
#    SECURE_SSL_REDIRECT = True
#
#    SESSION_COOKIE_SECURE = True
#
#    CSRF_COOKIE_SECURE = True
#
# 7. Vérifier la configuration du reverse proxy / serveur web de cPanel
#    avant d'ajouter SECURE_PROXY_SSL_HEADER.
#
# 8. Vérifier les permissions de db.sqlite3, staticfiles/ et media/
#    si SQLite reste utilisé en production.
#
# 9. Mettre en place une stratégie de sauvegarde de la base de données
#    et des fichiers media avant la mise en production.
#
# IMPORTANT :
# La configuration de production doit être testée avec :
#
#    python manage.py check --deploy \
#        --settings=config.settings.production
#
# Ne jamais utiliser DEBUG=True en production.
# =============================================================================