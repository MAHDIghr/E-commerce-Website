"""Vues produit : données métier issues de la base, sans catalogue fictif."""
from decimal import Decimal

from django.db.models import Prefetch
from django.http import Http404
from django.shortcuts import render

from .models import Product, ProductMedia, ProductOffer, ProductVariant, Review
from .selectors import published_products


def _eur(value):
    return f"{value:.2f}".replace(".", ",") + " €"


def _detail_queryset():
    return published_products().select_related("category").prefetch_related(
        Prefetch("variants", queryset=ProductVariant.objects.filter(is_active=True).order_by("position", "pk")),
        Prefetch("media_items", queryset=ProductMedia.objects.order_by("-is_primary", "position", "pk")),
        "reasons", "content_items", "craft_details", "usages", "faqs",
        Prefetch("offers", queryset=ProductOffer.objects.filter(is_active=True).prefetch_related("items__product", "items__variant")),
        Prefetch("reviews", queryset=Review.objects.filter(is_approved=True).order_by("-created_at")),
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

    media_items = list(product.media_items.all())
    media = [{
        "type": item.media_type,
        "src": item.image.url if item.image else item.source_url,
        "poster": item.poster_url or (item.image.url if item.image else item.source_url),
        "thumb": item.poster_url or (item.image.url if item.image else item.source_url),
        "alt": item.alt_text,
        "variant_id": str(item.variant_id) if item.variant_id else "",
    } for item in media_items]

    offers = []
    for offer_obj in product.offers.all():
        lines = []
        reference_total = Decimal("0.00")
        offer_items = list(offer_obj.items.all())
        invalid_offer = not any(item.use_selected_variant for item in offer_items)
        for item in offer_items:
            if item.use_selected_variant:
                if (
                    item.product_id != product.pk
                    or item.variant_id is not None
                    or default_variant.stock_quantity < item.quantity
                ):
                    invalid_offer = True
                    break
                component_variant = default_variant
            else:
                if (
                    item.product_id == product.pk
                    or not item.variant_id
                    or item.variant.product_id != item.product_id
                    or not item.variant.is_active
                    or item.variant.stock_quantity < item.quantity
                    or not item.product.is_published
                    or not item.product.category.is_active
                ):
                    invalid_offer = True
                    break
                component_variant = item.variant
            lines.append(f"{item.product.name} × {item.quantity}" if item.quantity > 1 else item.product.name)
            # Le prix de référence du lot est la somme des prix de vente actuels,
            # pas la somme de prix barrés potentiellement déjà remisés.
            reference_total += component_variant.price * item.quantity
        # Les offres incomplètes ou incohérentes ne sont jamais exposées au client.
        if not lines or invalid_offer:
            continue
        old_price = reference_total if reference_total > offer_obj.price else None
        off = round((1 - offer_obj.price / old_price) * 100) if old_price else 0
        offers.append({
            "id": str(offer_obj.pk),
            "title": offer_obj.title,
            "items": " + ".join(lines),
            "price": float(offer_obj.price),
            "old": float(old_price) if old_price else None,
            "reference_total": float(reference_total),
            "price_label": _eur(offer_obj.price),
            "old_label": _eur(old_price) if old_price else "",
            "save_label": _eur(old_price - offer_obj.price) if old_price else "",
            "off": off,
            "ship": offer_obj.get_display_delivery_label_display(),
            "badge": offer_obj.badge,
            "featured": offer_obj.is_featured,
            "includes_selected_variant": any(item.use_selected_variant for item in offer_items),
            "main_quantity": sum(item.quantity for item in offer_items if item.use_selected_variant),
        })

    if not offers:
        raise Http404("Offre indisponible.")

    selected = next((item for item in offers if item["featured"]), offers[0])
    for offer_data in offers:
        offer_data["featured"] = offer_data is selected
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
        "default_variant_price": str(default_variant.price),
        "usage_section_title": product.usage_section_title,
        "tagline": product.tagline or product.short_description,
        "seo_title": product.seo_title,
        "rating": rating,
        "rating_stars": "★" * int(round(rating)) + "☆" * (5 - int(round(rating))),
        "reviews_count": reviews_count,
        "media": media,
        "colors": [{
            "id": str(variant.pk),
            "label": variant.color_name or "Standard",
            "hex": variant.color_code or "#b07a4a",
            "price": str(variant.price),
            "price_label": _eur(variant.price),
            "old_label": _eur(variant.compare_at_price) if variant.compare_at_price and variant.compare_at_price > variant.price else "",
            "off": round((1 - variant.price / variant.compare_at_price) * 100) if variant.compare_at_price and variant.compare_at_price > variant.price else 0,
            "stock": variant.stock_quantity,
        } for variant in variants],
        "offers": offers,
        "selected": selected,
        "max_off": max((item["off"] for item in offers), default=0),
        "upgrade": "",
        "benefits": [{"t": item.title, "d": item.description} for item in product.reasons.all()],
        "fits": [(item.name, item.fits) for item in product.content_items.all()],
        "dims": dims,
        "craft": [{"t": item.title, "d": item.description, "img": item.image.url if item.image else item.image_url, "alt": item.alt_text} for item in product.craft_details.all()],
        "lifestyle": [{"title": item.title, "img": item.image.url if item.image else item.image_url, "alt": item.alt_text} for item in product.usages.all()],
        "dist": distribution,
        "reviews": [{"who": item.author_name, "stars": item.rating, "stars_display": "★" * item.rating + "☆" * (5 - item.rating), "t": item.comment} for item in reviews],
        "faq": [(item.question, item.answer) for item in product.faqs.all()],
        # Produits associés exclus du périmètre actuel ; aucun contenu fictif n'est injecté.
        "related": [],
        "dims_raw": dims,
    }
    context_product["tagline"] = context_product["tagline"] or ""
    context_product["seo_title"] = context_product["seo_title"] or product.name
    context_product["seo_description"] = product.seo_description or product.short_description or product.name
    return render(request, "product.html", {"product": context_product})
