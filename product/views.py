"""Vues produit : données métier issues de la base, sans catalogue fictif."""
import json
from decimal import Decimal

from django.db.models import Prefetch
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET

from .models import Product, ProductMedia, ProductOffer, ProductVariant, Review
from .selectors import published_products


def _eur(value):
    return f"{value:.2f}".replace(".", ",") + " €"


def _detail_queryset():
    return published_products().select_related("category").prefetch_related(
        Prefetch("variants", queryset=ProductVariant.objects.filter(is_active=True).order_by("position", "pk")),
        Prefetch("media_items", queryset=ProductMedia.objects.order_by("-is_primary", "position", "pk")),
        "reasons", "content_items", "craft_details", "usages", "faqs",
        Prefetch(
            "offers",
            queryset=ProductOffer.objects.filter(is_active=True).prefetch_related(
                "items__variant",
                Prefetch(
                    "items__product__media_items",
                    queryset=ProductMedia.objects.order_by("-is_primary", "position", "pk"),
                ),
                Prefetch(
                    "items__product__offers",
                    queryset=ProductOffer.objects.filter(is_active=True).prefetch_related("items"),
                ),
            ),
        ),
        Prefetch("reviews", queryset=Review.objects.filter(is_approved=True).order_by("-created_at")),
    )


@require_GET
@ensure_csrf_cookie
def detail(request, slug):
    """Affiche une fiche publiée et ses avis créés/modérés depuis Django Admin."""
    try:
        product = _detail_queryset().get(slug=slug)
    except Product.DoesNotExist as exc:
        raise Http404("Produit introuvable.") from exc

    variants = list(product.variants.all())
    if not variants:
        raise Http404("Produit indisponible.")
    # Le sélecteur démarre sur une variante vendable si l'une existe.
    variants.sort(key=lambda variant: (variant.stock_quantity <= 0, variant.position, variant.pk))
    default_variant = variants[0]

    media_items = list(product.media_items.all())
    media = [{
        "type": item.media_type,
        "src": item.image.url if item.image else item.source_url,
        "poster": item.poster_url or (item.image.url if item.image else item.source_url),
        "thumb": item.poster_url or (item.image.url if item.image else item.source_url),
        "alt": item.alt_text,
    } for item in media_items]

    offers = []
    for offer_obj in product.offers.all():
        lines = []
        accessories = []
        offer_items = list(offer_obj.items.all())
        main_items = [item for item in offer_items if item.use_selected_variant]
        invalid_offer = len(main_items) != 1
        for item in offer_items:
            if item.use_selected_variant:
                if (
                    item.product_id != product.pk
                    or item.variant_id is not None
                    or item.quantity < 1
                ):
                    invalid_offer = True
                    break
                lines.append(f"{item.product.name} × {item.quantity}" if item.quantity > 1 else item.product.name)
            else:
                if (
                    item.product_id == product.pk
                    or not item.variant_id
                    or item.variant.product_id != item.product_id
                    or not item.variant.is_active
                    or item.quantity < 1
                    or not item.product.is_published
                    or not item.product.category.is_active
                ):
                    invalid_offer = True
                    break
                media_item = next(
                    (
                        candidate for candidate in item.product.media_items.all()
                        if candidate.media_type == ProductMedia.IMAGE
                    ),
                    None,
                )
                accessory_image = (
                    media_item.image.url if media_item and media_item.image else media_item.source_url
                ) if media_item else ""
                accessory_offers = [
                    candidate for candidate in item.product.offers.all()
                    if candidate.is_active and any(
                        component.product_id == item.product_id
                        and component.use_selected_variant
                        and component.variant_id is None
                        and component.quantity > 0
                        for component in candidate.items.all()
                    )
                ]
                essential = next(
                    (candidate for candidate in accessory_offers if candidate.badge == ProductOffer.BADGE_ESSENTIAL),
                    None,
                )
                standalone_offer = essential or next(
                    (candidate for candidate in accessory_offers if candidate.is_featured),
                    accessory_offers[0] if accessory_offers else None,
                )
                accessories.append({
                    "item_id": item.pk,
                    "product_id": item.product_id,
                    "slug": item.product.slug,
                    "name": item.product.name,
                    "variant_name": item.variant.color_name or "",
                    "image": accessory_image,
                    "quantity": item.quantity,
                    "original_price": float(standalone_offer.reference_price if standalone_offer.reference_price is not None and standalone_offer.reference_price > standalone_offer.price else standalone_offer.price) if standalone_offer else None,
                    "available": item.variant.stock_quantity >= item.quantity,
                    "available_quantity": item.variant.stock_quantity // item.quantity,
                })
        # Une offre publique doit avoir exactement un composant principal valide.
        if (
            not lines
            or invalid_offer
            or main_items[0].product_id != product.pk
            or main_items[0].variant_id is not None
            or main_items[0].quantity < 1
        ):
            continue
        # Aucun prix n'est stocké sur les variantes : une offre porte son propre prix.
        old_price = offer_obj.reference_price
        if old_price is not None and old_price <= offer_obj.price:
            old_price = None
        off = (
            round((old_price - offer_obj.price) * 100 / old_price)
            if old_price is not None and old_price > 0
            else 0
        )
        offers.append({
            "id": str(offer_obj.pk),
            "title": offer_obj.title,
            "items": " + ".join(lines) + (" · Accessoires inclus — sélection obligatoire" if accessories else ""),
            "accessories": accessories,
            "price": float(offer_obj.price),
            "old": float(old_price) if old_price else None,
            "reference_total": float(old_price) if old_price is not None else None,
            "price_label": _eur(offer_obj.price),
            "old_label": _eur(old_price) if old_price else "",
            "save_label": _eur(old_price - offer_obj.price) if old_price else "",
            "off": off,
            "ship": offer_obj.get_display_delivery_label_display(),
            "badge": offer_obj.get_badge_display(),
            "featured": offer_obj.is_featured,
            "includes_selected_variant": any(item.use_selected_variant for item in offer_items),
            "uses_variant_price": False,
            "main_quantity": sum(item.quantity for item in offer_items if item.use_selected_variant),
            "has_accessories": bool(accessories),
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
    context_product["category"] = product.category.name
    structured_data = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": context_product["name"],
        "description": context_product["seo_description"],
        "brand": {"@type": "Brand", "name": "My Line Collection"},
        "category": context_product["category"],
        "url": request.build_absolute_uri(reverse("product:detail", kwargs={"slug": product.slug})),
        "image": [
            request.build_absolute_uri(item["src"])
            for item in media if item["type"] == ProductMedia.IMAGE and item.get("src")
        ],
        "offers": {
            "@type": "AggregateOffer",
            "priceCurrency": "EUR",
            "lowPrice": min(item["price"] for item in offers),
            "highPrice": max(item["price"] for item in offers),
            "offerCount": len(offers),
            "availability": "https://schema.org/InStock" if any(item["stock"] > 0 for item in context_product["colors"]) else "https://schema.org/OutOfStock",
            "url": request.build_absolute_uri(reverse("product:detail", kwargs={"slug": product.slug})),
        },
    }
    if reviews_count:
        structured_data["aggregateRating"] = {
            "@type": "AggregateRating",
            "ratingValue": rating,
            "reviewCount": reviews_count,
            "bestRating": 5,
            "worstRating": 1,
        }
    context_product["structured_data_json"] = json.dumps(
        structured_data, ensure_ascii=False, separators=(",", ":")
    ).replace("<", "\\u003C").replace(">", "\\u003E").replace("&", "\\u0026")
    return render(request, "product.html", {"product": context_product})
