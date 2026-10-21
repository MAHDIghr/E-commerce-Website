"""Contextes partagés du catalogue pour les composants de navigation."""

from .models import Category


def active_catalog_categories(request):
    """Expose les catégories actives afin que les liens globaux suivent la base."""
    return {
        "catalog_categories": Category.objects.filter(is_active=True).order_by(
            "position", "name"
        ),
    }
