"""Sélecteurs partagés pour le catalogue public.

Les vues ne doivent exposer que des produits publiables et des données
nécessaires à la présentation. Les montants ici sont informatifs côté client ;
le panier et les commandes devront recalculer les prix côté serveur.
"""
from django.db.models import Q
from django.utils import timezone

from .models import Product, ProductMedia


def published_products():
    """Produits actifs, catégorie active, date atteinte, image commune et variante active."""
    now = timezone.now()
    return Product.objects.filter(
        is_active=True,
        category__is_active=True,
        media_items__variant__isnull=True,
        media_items__media_type=ProductMedia.IMAGE,
        variants__is_active=True,
    ).filter(
        Q(published_at__isnull=True) | Q(published_at__lte=now)
    ).distinct()


def product_card_data(queryset):
    """Sérialise les champs publics nécessaires aux cartes du catalogue."""
    products = []
    for product in queryset:
        variant = product.default_variant
        if not variant:
            continue

        media_items = list(product.media_items.all())
        media = next(
            (item for item in media_items if item.variant_id is None and item.media_type == ProductMedia.IMAGE),
            None,
        )
        if media is None:
            media = next((item for item in media_items if item.media_type == ProductMedia.IMAGE), None)

        approved_reviews = [
            review for review in product.reviews.all() if review.is_approved
        ]
        review_count = len(approved_reviews)
        rating = (
            sum(review.rating for review in approved_reviews) / review_count
            if review_count else 0
        )
        colors = [
            {"slug": item.color_slug, "name": item.color_name, "hex": item.color_code}
            for item in product.variants.all()
            if item.is_active and item.color_slug and item.color_code
        ]
        old_price = variant.compare_at_price
        products.append({
            "id": product.slug,
            "variantId": variant.pk,
            "variantName": variant.color_name,
            "name": product.name,
            "cat": product.category.slug,
            "price": float(variant.price),
            "old": float(old_price) if old_price and old_price > variant.price else None,
            "colors": [color["slug"] for color in colors],
            "color_details": colors,
            "rating": round(float(rating), 1),
            "reviews": review_count,
            "stock": int(variant.stock_quantity),
            "isNew": bool(product.is_new),
            "pop": 0,
            "best": bool(product.is_best_seller),
            "img": (media.image.url if media and media.image else media.source_url) if media else "",
        })
    return products
