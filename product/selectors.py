"""Sélecteurs partagés pour le catalogue public.

Les vues ne doivent exposer que des produits publiables et des données
nécessaires à la présentation. Les montants ici sont informatifs côté client ;
le panier et les commandes devront recalculer les prix côté serveur.
"""
from django.db.models import F, Q
from django.utils import timezone

from .models import Product, ProductMedia


def published_products():
    """Produits actifs, catégorie active, date atteinte, image produit et variante active."""
    now = timezone.now()
    return Product.objects.filter(
        Q(
            is_active=True,
            category__is_active=True,
            media_items__media_type=ProductMedia.IMAGE,
            variants__is_active=True,
            offers__is_active=True,
            offers__items__use_selected_variant=True,
            offers__items__product_id=F("pk"),
            offers__items__variant__isnull=True,
        )
        & (Q(published_at__isnull=True) | Q(published_at__lte=now))
        & (Q(media_items__image__gt="") | Q(media_items__source_url__gt=""))
    ).distinct()


def product_card_data(queryset):
    """Sérialise les champs publics nécessaires aux cartes du catalogue."""
    products = []
    for product in queryset:
        variant = product.display_variant
        if not variant:
            continue

        media_items = list(product.media_items.all())
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
            for item in product.public_variants
            if item.color_slug and item.color_code
        ]
        active_offers = product._active_offers()
        valid_offers = [
            candidate for candidate in active_offers
            if sum(
                1 for item in candidate.items.all()
                if item.use_selected_variant
                and item.product_id == product.pk
                and item.variant_id is None
                and item.quantity > 0
            ) == 1
        ]
        essential_offer = next((candidate for candidate in valid_offers if candidate.badge == "essential"), None)
        offer = essential_offer or next(
            (candidate for candidate in valid_offers if candidate.is_featured),
            valid_offers[0] if valid_offers else None,
        )
        if offer is None:
            continue
        products.append({
            "id": product.slug,
            "variantId": variant.pk,
            "variantName": variant.color_name,
            "name": product.display_name_for(variant),
            "cat": product.category.slug,
            "category_label": product.category.name or product.category.slug.replace("-", " ").capitalize(),
            "price": float(offer.price),
            # Prix de référence : affichage uniquement s'il est renseigné et vérifié.
            "old": (
                float(essential_offer.reference_price)
                if essential_offer and essential_offer.reference_price is not None and essential_offer.reference_price > offer.price
                else None
            ),
            "offerId": offer.pk,
            "offerTitle": offer.title,
            "colors": [color["slug"] for color in colors],
            "color_details": colors,
            "rating": round(float(rating), 1),
            "reviews": review_count,
            "stock": int(variant.stock_quantity),
            "isNew": bool(product.is_new),
            "pop": 0,
            "img": variant.image_src or ((media.image.url if media and media.image else media.source_url) if media else ""),
        })
    return products


def catalog_queryset(queryset):
    """Champs de tri/filtre correspondant à l'offre et à la variante des cartes."""
    from django.db.models import OuterRef, Subquery, Case, When, Value, IntegerField, Count, Avg
    from .models import ProductOffer, ProductVariant
    offers = ProductOffer.objects.filter(product_id=OuterRef("pk"), is_active=True).annotate(
        main_count=Count("items", filter=Q(items__use_selected_variant=True)),
        priority=Case(When(badge="essential", then=Value(0)), When(is_featured=True, then=Value(1)), default=Value(2), output_field=IntegerField()),
    ).filter(main_count=1, items__use_selected_variant=True, items__product_id=F("product_id"),
             items__variant__isnull=True, items__quantity__gt=0).order_by("priority", "position", "pk")
    variants = ProductVariant.objects.filter(product_id=OuterRef("pk"), is_active=True).annotate(
        illustrated=Case(When(Q(image__gt="") | Q(image_url__gt=""), then=Value(0)), default=Value(1), output_field=IntegerField()),
        sold_out=Case(When(stock_quantity__gt=0, then=Value(0)), default=Value(1), output_field=IntegerField()),
    ).order_by("illustrated", "sold_out", "position", "pk")
    return queryset.annotate(
        card_price=Subquery(offers.values("price")[:1]),
        card_reference=Subquery(offers.values("reference_price")[:1]),
        card_badge=Subquery(offers.values("badge")[:1]),
        card_variant=Subquery(variants.values("pk")[:1]),
        card_stock=Subquery(variants.values("stock_quantity")[:1]),
        card_rating=Avg("reviews__rating", filter=Q(reviews__is_approved=True)),
    ).filter(card_price__isnull=False)


def catalog_color_variants():
    """Même ensemble public de couleurs que Product.public_variants, sans charger le catalogue."""
    from django.db.models import OuterRef, Subquery, Exists, Case, When, Value, IntegerField
    from .models import ProductVariant
    siblings = ProductVariant.objects.filter(product_id=OuterRef("product_id"), is_active=True)
    first = siblings.annotate(sold_out=Case(When(stock_quantity__gt=0, then=Value(0)), default=Value(1), output_field=IntegerField())).order_by("sold_out", "position", "pk")
    return ProductVariant.objects.filter(is_active=True, product__in=published_products()).annotate(
        has_illustrated=Exists(siblings.filter(Q(image__gt="") | Q(image_url__gt=""))),
        fallback_pk=Subquery(first.values("pk")[:1]),
    ).filter(Q(image__gt="") | Q(image_url__gt="") | Q(has_illustrated=False, pk=F("fallback_pk")))
