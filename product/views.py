"""Vues produit : données métier issues de la base, sans catalogue fictif."""
from decimal import Decimal

from django.db.models import Avg, Count, Prefetch
from django.http import Http404
from django.shortcuts import render
from django.utils import timezone

from .models import Product, ProductMedia, ProductOffer, ProductVariant


def published_products():
    """Queryset partagé : seuls les produits actifs et déjà publiables sont visibles."""
    now = timezone.now()
    return Product.objects.filter(is_active=True).filter(
        published_at__isnull=True
    ) | Product.objects.filter(is_active=True, published_at__lte=now)


def product_card_data(queryset):
    """Convertit des produits publiables en données JSON sûres pour le catalogue JS."""
    products = []
    for product in queryset:
        variant = product.default_variant
        if not variant:
            continue
        media = product.media_items.filter(variant__isnull=True, media_type=ProductMedia.IMAGE).first()
        if not media:
            media = product.media_items.filter(media_type=ProductMedia.IMAGE).first()
        approved = product.reviews.filter(is_approved=True)
        aggregate = approved.aggregate(rating=Avg("rating"), reviews=Count("id"))
        colors = [
            {"slug": item.color_slug, "name": item.color_name, "hex": item.color_code}
            for item in product.variants.all()
            if item.is_active and item.color_slug
        ]
        old_price = variant.compare_at_price
        products.append({
            "id": product.slug,
            "name": product.name,
            "cat": product.category.slug,
            "price": float(variant.price),
            "old": float(old_price) if old_price and old_price > variant.price else None,
            "colors": [color["slug"] for color in colors],
            "color_details": colors,
            "rating": float(aggregate["rating"] or 0),
            "reviews": int(aggregate["reviews"] or 0),
            "stock": int(variant.stock_quantity),
            "isNew": bool(product.is_new),
            "pop": 0,
            "best": bool(product.is_best_seller),
            "img": media.source_url if media else "",
        })
    return products


def _eur(value):
    return f"{value:.2f}".replace(".", ",") + " €"


def _detail_queryset():
    return published_products().select_related("category").prefetch_related(
        Prefetch("variants", queryset=ProductVariant.objects.filter(is_active=True).order_by("position", "pk")),
        Prefetch("media_items", queryset=ProductMedia.objects.order_by("position", "pk")),
        "reasons", "content_items", "craft_details", "usages", "faqs",
        Prefetch("offers", queryset=ProductOffer.objects.filter(is_active=True).prefetch_related("items__product", "items__variant")),
        Prefetch("reviews", queryset=Product.reviews.rel.related_model.objects.filter(is_approved=True).order_by("-created_at")),
    )


def detail(request, slug):
    """Rend une fiche à partir des données publiées ; les brouillons renvoient 404."""
    try:
        product = _detail_queryset().get(slug=slug)
    except Product.DoesNotExist as exc:
        raise Http404("Produit introuvable.") from exc

    variants = list(product.variants.all())
    if not variants:
        raise Http404("Produit indisponible.")
    default_variant = variants[0]

    media_items = [
        item for item in product.media_items.all()
        if item.variant_id is None or item.variant_id == default_variant.pk
    ]
    media = [{
        "type": item.media_type,
        "src": item.source_url,
        "poster": item.poster_url or item.source_url,
        "thumb": item.poster_url or item.source_url,
        "alt": item.alt_text,
    } for item in media_items]

    offers = []
    for offer_obj in product.offers.all():
        lines = []
        reference_total = Decimal("0.00")
        for item in offer_obj.items.all():
            lines.append(f"{item.product.name} × {item.quantity}" if item.quantity > 1 else item.product.name)
            component_variant = default_variant if item.use_selected_variant else item.variant
            if component_variant:
                reference_price = component_variant.compare_at_price or component_variant.price
                reference_total += reference_price * item.quantity
        # Une offre sans lignes configurées ne doit pas être affichée comme une offre achetable.
        if not lines:
            continue
        old_price = reference_total if reference_total > offer_obj.price else None
        off = round((1 - offer_obj.price / old_price) * 100) if old_price else 0
        offers.append({
            "id": str(offer_obj.pk),
            "title": offer_obj.title,
            "items": " + ".join(lines),
            "price": float(offer_obj.price),
            "old": float(old_price) if old_price else None,
            "price_label": _eur(offer_obj.price),
            "old_label": _eur(old_price) if old_price else "",
            "save_label": _eur(old_price - offer_obj.price) if old_price else "",
            "off": off,
            "ship": offer_obj.display_delivery_label,
            "badge": offer_obj.badge,
            "featured": offer_obj.is_featured,
        })

    if not offers:
        # L'offre implicite n'est pas une donnée commerciale : on affiche le prix de la variante.
        offers = [{
            "id": "default", "title": "À l'unité", "items": product.name,
            "price": float(default_variant.price),
            "old": float(default_variant.compare_at_price) if default_variant.compare_at_price else None,
            "price_label": _eur(default_variant.price),
            "old_label": _eur(default_variant.compare_at_price) if default_variant.compare_at_price else "",
            "save_label": _eur(default_variant.compare_at_price - default_variant.price) if default_variant.compare_at_price else "",
            "off": round((1 - default_variant.price / default_variant.compare_at_price) * 100) if default_variant.compare_at_price and default_variant.compare_at_price > default_variant.price else 0,
            "ship": "", "badge": "", "featured": True,
        }]
    selected = next((item for item in offers if item["featured"]), offers[0])
    reviews = list(product.reviews.all())
    reviews_count = len(reviews)
    rating = round(sum(review.rating for review in reviews) / reviews_count, 1) if reviews_count else 0
    distribution = []
    for stars in range(5, 0, -1):
        count = sum(review.rating == stars for review in reviews)
        distribution.append({"n": stars, "pct": round(count * 100 / reviews_count) if reviews_count else 0})

    dims = {
        "w": product.width_cm or 0,
        "h": product.height_cm or 0,
        "d": product.depth_cm or 0,
        "weight": f"{product.weight_g / 1000:.1f}".replace(".", ",") + " kg" if product.weight_g is not None else "—",
        "volume": f"{product.capacity_liters}".replace(".", ",") + " L" if product.capacity_liters is not None else "—",
    }
    context_product = {
        "slug": product.slug,
        "name": product.name,
        "brand_line": product.brand_line,
        "tagline": product.tagline or product.short_description,
        "seo_title": product.seo_title,
        "rating": rating,
        "reviews_count": reviews_count,
        "media": media,
        "colors": [{
            "id": str(variant.pk),
            "label": variant.color_name or "Standard",
            "hex": variant.color_code or "#b07a4a",
        } for variant in variants],
        "offers": offers,
        "selected": selected,
        "max_off": max((item["off"] for item in offers), default=0),
        "upgrade": "",
        "benefits": [{"t": item.title, "d": item.description} for item in product.reasons.all()],
        "fits": [(item.name, item.fits) for item in product.content_items.all()],
        "dims": dims,
        "craft": [{"t": item.title, "d": item.description, "img": item.image_url, "alt": item.alt_text} for item in product.craft_details.all()],
        "lifestyle": [(item.title, item.image_url) for item in product.usages.all()],
        "dist": distribution,
        "reviews": [{"who": item.author_name, "stars": item.rating, "t": item.comment} for item in reviews],
        "faq": [(item.question, item.answer) for item in product.faqs.all()],
        # Produits associés exclus du périmètre actuel ; aucun contenu fictif n'est injecté.
        "related": [],
        "dims_raw": dims,
    }
    context_product["tagline"] = context_product["tagline"] or ""
    context_product["seo_title"] = context_product["seo_title"] or product.name
    context_product["seo_description"] = product.seo_description or product.short_description or product.name
    return render(request, "product.html", {"product": context_product})
