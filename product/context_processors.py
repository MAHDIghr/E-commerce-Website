"""Contextes partagés du catalogue pour les composants de navigation."""

from .models import Category


def active_catalog_categories(request):
    """Expose les catégories actives et les destinations des entrées de navigation."""
    categories = list(Category.objects.filter(is_active=True).order_by("position", "name"))

    def find_category(slugs, name_terms):
        for category in categories:
            slug = category.slug.casefold()
            name = category.name.casefold()
            if slug in slugs or any(term in name for term in name_terms):
                return category
        return None

    return {
        "catalog_categories": categories,
        "catalog_accessories_category": find_category(
            {"accessoires", "accessory", "accessories"}, ("accessoire", "accessory")
        ),
        "catalog_collection_category": find_category(
            {"collection", "collections"}, ("collection",)
        ),
    }
