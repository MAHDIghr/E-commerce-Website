"""Catalogue, recherche et panier invité.

Le navigateur ne fournit que des identifiants et des quantités. Prix, variantes,
offres, publication et disponibilité sont toujours vérifiés côté serveur.
"""
import json
from decimal import Decimal, InvalidOperation

from django.db.models import Q, Prefetch
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from product.models import (
    Category, ProductMedia, ProductOffer, ProductOfferItem, ProductVariant, Review,
)
from product.selectors import product_card_data, published_products


CART_SESSION_KEY = "shop_cart_v1"
MAX_CART_QUANTITY = 10
FREE_SHIPPING_THRESHOLD = Decimal("80.00")


def _search_queryset(queryset, query):
    """Recherche multi-termes : chaque terme doit correspondre à un champ utile."""
    query = " ".join((query or "").split())[:100]
    if not query:
        return queryset
    terms = query.split()[:6]
    for term in terms:
        queryset = queryset.filter(
            Q(name__icontains=term)
            | Q(slug__icontains=term)
            | Q(short_description__icontains=term)
            | Q(description__icontains=term)
            | Q(brand_line__icontains=term)
            | Q(category__name__icontains=term)
            | Q(tagline__icontains=term)
        )
    return queryset


def catalog(request):
    categories = list(Category.objects.filter(is_active=True).order_by("position", "name"))
    query = " ".join(request.GET.get("q", "").split())[:100]
    products = _search_queryset(published_products(), query).select_related("category").prefetch_related(
        Prefetch("variants", queryset=ProductVariant.objects.filter(is_active=True).order_by("position", "pk")),
        Prefetch("media_items", queryset=ProductMedia.objects.order_by("-is_primary", "position", "pk")),
        Prefetch("reviews", queryset=Review.objects.filter(is_approved=True)),
    ).order_by("-published_at", "-created_at", "name")

    color_map = {}
    for product in products:
        for variant in product.variants.all():
            if variant.is_active and variant.color_slug and variant.color_code:
                color_map.setdefault(
                    variant.color_slug,
                    {"hex": variant.color_code, "name": variant.color_name or variant.color_slug},
                )

    catalog_data = {
        "products": product_card_data(products),
        "categories": [{"slug": category.slug, "name": category.name} for category in categories],
        "colors": color_map,
        "query": query,
    }
    return render(request, "catalog.html", {
        "categories": categories,
        "catalog_data": catalog_data,
        "search_query": query,
    })


@require_GET
def search_suggestions(request):
    query = " ".join(request.GET.get("q", "").split())[:100]
    if len(query) < 2:
        return JsonResponse({"query": query, "results": []})

    products = _search_queryset(published_products(), query).select_related("category").prefetch_related(
        Prefetch("variants", queryset=ProductVariant.objects.filter(is_active=True).order_by("position", "pk")),
        Prefetch(
            "media_items",
            queryset=ProductMedia.objects.filter(
                variant__isnull=True, media_type=ProductMedia.IMAGE,
            ).order_by("-is_primary", "position", "pk"),
        ),
    ).order_by("-is_best_seller", "-is_new", "name")[:8]

    results = []
    for product in products:
        variant = product.default_variant
        if not variant:
            continue
        media = next(iter(product.media_items.all()), None)
        image = (media.image.url if media and media.image else media.source_url) if media else ""
        results.append({
            "name": product.name,
            "category": product.category.name,
            "price": f"{variant.price:.2f}",
            "image": image,
            "url": f"/produit/{product.slug}/",
        })
    return JsonResponse({"query": query, "results": results})


def _cart_state(request):
    raw = request.session.get(CART_SESSION_KEY, {})
    if not isinstance(raw, dict):
        return {}
    clean = {}
    for key, quantity in raw.items():
        try:
            variant_id, offer_id = key.split(":", 1)
            variant_id, offer_id, quantity = int(variant_id), int(offer_id), int(quantity)
        except (AttributeError, TypeError, ValueError):
            continue
        if variant_id > 0 and offer_id >= 0 and 1 <= quantity <= MAX_CART_QUANTITY:
            clean[f"{variant_id}:{offer_id}"] = quantity
    return clean


def _line_details(variant_id, offer_id, quantity):
    variant = ProductVariant.objects.select_related("product", "product__category").filter(
        pk=variant_id, is_active=True,
    ).first()
    if not variant or not published_products().filter(pk=variant.product_id).exists():
        return None

    offer = None
    offer_items = []
    if offer_id:
        offer = ProductOffer.objects.filter(
            pk=offer_id, product_id=variant.product_id, is_active=True,
        ).first()
        if not offer:
            return None
        offer_items = list(offer.items.select_related(
            "product", "product__category", "variant", "variant__product", "variant__product__category",
        ))
        if not offer_items or not any(
            item.use_selected_variant and item.product_id == variant.product_id and item.variant_id is None
            for item in offer_items
        ):
            return None
        for item in offer_items:
            if item.use_selected_variant:
                component = variant
            else:
                component = item.variant
                if (
                    not component or not component.is_active
                    or component.product_id != item.product_id
                    or not published_products().filter(pk=item.product_id).exists()
                ):
                    return None
            if component.stock_quantity < quantity * item.quantity:
                # Keep the line visible so the client can reduce or remove it.
                pass

    if offer:
        simple_variant_offer = len(offer_items) == 1 and offer_items[0].use_selected_variant
        if simple_variant_offer:
            unit_price = variant.price * offer_items[0].quantity
        else:
            unit_price = offer.price
        title = f"{variant.product.name} — {offer.title}"
        if variant.color_name:
            title += f" ({variant.color_name})"
        max_available = min(
            (variant.stock_quantity // item.quantity if item.use_selected_variant
             else item.variant.stock_quantity // item.quantity)
            for item in offer_items
        )
    else:
        unit_price = variant.price
        title = f"{variant.product.name} — {variant.color_name}" if variant.color_name else variant.product.name
        max_available = variant.stock_quantity

    media = ProductMedia.objects.filter(
        product_id=variant.product_id, variant__isnull=True, media_type=ProductMedia.IMAGE,
    ).order_by("-is_primary", "position", "pk").first()
    image = (media.image.url if media and media.image else media.source_url) if media else ""
    available = max_available >= quantity and max_available > 0
    return {
        "key": f"{variant.pk}:{offer.pk if offer else 0}",
        "product_id": variant.product_id,
        "product_slug": variant.product.slug,
        "variant_id": variant.pk,
        "offer_id": offer.pk if offer else None,
        "name": title,
        "variant_name": variant.color_name,
        "image": image,
        "quantity": quantity,
        "unit_price": f"{unit_price:.2f}",
        "line_total": f"{unit_price * quantity:.2f}",
        "available_quantity": min(max_available, MAX_CART_QUANTITY),
        "available": available,
    }


def _cart_payload(request):
    state = _cart_state(request)
    items = []
    stale_keys = []
    for key, quantity in state.items():
        variant_id, offer_id = map(int, key.split(":"))
        details = _line_details(variant_id, offer_id, quantity)
        if details is None:
            stale_keys.append(key)
            continue
        items.append(details)

    if stale_keys:
        for key in stale_keys:
            state.pop(key, None)
        request.session[CART_SESSION_KEY] = state
        request.session.modified = True

    subtotal = sum((Decimal(item["line_total"]) for item in items), Decimal("0.00"))
    count = sum(item["quantity"] for item in items)
    return {
        "items": items,
        "count": count,
        "subtotal": f"{subtotal:.2f}",
        "free_shipping_threshold": f"{FREE_SHIPPING_THRESHOLD:.2f}",
        "amount_to_free_shipping": f"{max(FREE_SHIPPING_THRESHOLD - subtotal, Decimal('0.00')):.2f}",
        "free_shipping_reached": subtotal >= FREE_SHIPPING_THRESHOLD,
    }


@ensure_csrf_cookie
@require_GET
def cart_api(request):
    return JsonResponse(_cart_payload(request))


@require_POST
def cart_mutation(request):
    try:
        data = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Requête invalide."}, status=400)
    if not isinstance(data, dict):
        return JsonResponse({"error": "Requête invalide."}, status=400)

    action = data.get("action")
    state = _cart_state(request)
    try:
        variant_id = int(data.get("variant_id", 0))
        offer_id = int(data.get("offer_id") or 0)
    except (TypeError, ValueError):
        return JsonResponse({"error": "Variante ou offre invalide."}, status=400)
    key = f"{variant_id}:{offer_id}"

    if action == "clear":
        request.session[CART_SESSION_KEY] = {}
    elif action == "add":
        try:
            quantity = int(data.get("quantity", 1))
        except (TypeError, ValueError):
            return JsonResponse({"error": "Quantité invalide."}, status=400)
        if variant_id <= 0 or offer_id < 0 or quantity < 1 or quantity > MAX_CART_QUANTITY:
            return JsonResponse({"error": "Variante, offre ou quantité invalide."}, status=400)
        current = state.get(key, 0)
        details = _line_details(variant_id, offer_id, current + quantity)
        if details is None:
            return JsonResponse({"error": "Ce produit ou cette offre n'est plus disponible."}, status=400)
        if not details["available"]:
            return JsonResponse({"error": "Le stock disponible ne permet pas cette quantité."}, status=409)
        state[key] = current + quantity
        request.session[CART_SESSION_KEY] = state
    elif action in {"update", "remove"}:
        if key not in state:
            return JsonResponse({"error": "Article introuvable dans le panier."}, status=404)
        if action == "remove":
            state.pop(key, None)
        else:
            try:
                quantity = int(data.get("quantity", 0))
            except (TypeError, ValueError):
                return JsonResponse({"error": "Quantité invalide."}, status=400)
            if quantity < 1 or quantity > MAX_CART_QUANTITY:
                return JsonResponse({"error": "La quantité doit être comprise entre 1 et 10."}, status=400)
            details = _line_details(variant_id, offer_id, quantity)
            if details is None:
                return JsonResponse({"error": "Ce produit ou cette offre n'est plus disponible."}, status=400)
            if not details["available"]:
                return JsonResponse({"error": "Le stock disponible ne permet pas cette quantité."}, status=409)
            state[key] = quantity
        request.session[CART_SESSION_KEY] = state
    else:
        return JsonResponse({"error": "Action de panier inconnue."}, status=400)

    request.session.modified = True
    return JsonResponse(_cart_payload(request))
