"""Catalogue, recherche et panier invité.

Le navigateur ne fournit que des identifiants et des quantités. Prix, variantes,
offres, publication et disponibilité sont toujours vérifiés côté serveur.
"""
import json
from decimal import Decimal

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
MAX_CART_LINES = 30
MAX_CART_REQUEST_BYTES = 8192
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


def _strict_int(value, *, allow_zero=False):
    """Parse un entier JSON sans accepter booléens, flottants ou coercitions ambiguës."""
    if isinstance(value, bool):
        raise ValueError("Entier invalide.")
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str) and value.isascii() and value.isdecimal():
        parsed = int(value)
    else:
        raise ValueError("Entier invalide.")
    if parsed < 0 or (parsed == 0 and not allow_zero):
        raise ValueError("Entier invalide.")
    return parsed


def _cart_state(request):
    """Normalise la session et borne le nombre de lignes contrôlées par le client."""
    raw = request.session.get(CART_SESSION_KEY, {})
    if not isinstance(raw, dict):
        return {}

    clean = {}
    for key, quantity in raw.items():
        if len(clean) >= MAX_CART_LINES:
            break
        if not isinstance(key, str) or key.count(":") != 1:
            continue
        variant_raw, offer_raw = key.split(":", 1)
        try:
            variant_id = _strict_int(variant_raw)
            offer_id = _strict_int(offer_raw, allow_zero=True)
            quantity = _strict_int(quantity)
        except (TypeError, ValueError):
            continue
        if quantity <= MAX_CART_QUANTITY:
            clean[f"{variant_id}:{offer_id}"] = quantity
    return clean

def _line_details(variant_id, offer_id, quantity):
    """Retourne une ligne recalculée depuis le catalogue, ou None si elle n'est plus valide."""
    if quantity < 1 or quantity > MAX_CART_QUANTITY:
        return None

    variant = ProductVariant.objects.select_related("product", "product__category").filter(
        pk=variant_id, is_active=True,
    ).first()
    if not variant or not published_products().filter(pk=variant.product_id).exists():
        return None

    offer = None
    offer_items = []
    components = []
    if offer_id:
        offer = ProductOffer.objects.filter(
            pk=offer_id, product_id=variant.product_id, is_active=True,
        ).first()
        if not offer:
            return None

        offer_items = list(offer.items.select_related(
            "product", "product__category", "variant", "variant__product",
            "variant__product__category",
        ).order_by("position", "pk"))
        selected_items = [item for item in offer_items if item.use_selected_variant]
        if (
            not offer_items
            or len(selected_items) != 1
            or selected_items[0].product_id != variant.product_id
            or selected_items[0].variant_id is not None
        ):
            return None

        max_available_values = []
        for item in offer_items:
            if item.quantity < 1:
                return None
            if item.use_selected_variant:
                if item.product_id != variant.product_id or item.variant_id is not None:
                    return None
                component = variant
            else:
                component = item.variant
                if (
                    component is None
                    or not component.is_active
                    or component.product_id != item.product_id
                    or not published_products().filter(pk=item.product_id).exists()
                ):
                    return None
            max_available_values.append(component.stock_quantity // item.quantity)
            components.append({
                "name": item.product.name,
                "quantity": item.quantity,
                "variant_name": component.color_name or "",
            })

        max_available = min(max_available_values, default=0)
        unit_price = offer.price
        title = f"{variant.product.name} — {offer.title}"
        if variant.color_name:
            title += f" ({variant.color_name})"
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
        "components": components,
        "quantity": quantity,
        "unit_price": f"{unit_price:.2f}",
        "line_total": f"{unit_price * quantity:.2f}",
        "available_quantity": min(max_available, MAX_CART_QUANTITY),
        "available": available,
    }

@require_GET
def offer_options(request, slug):
    """Expose uniquement les offres réellement ajoutables pour une variante précise."""
    product = published_products().filter(slug=slug).first()
    if product is None:
        return JsonResponse({"error": "Produit introuvable ou indisponible."}, status=404)

    try:
        variant_id = _strict_int(request.GET.get("variant_id"))
    except (TypeError, ValueError):
        return JsonResponse({"error": "Variante invalide."}, status=400)

    variant = ProductVariant.objects.filter(
        pk=variant_id, product_id=product.pk, is_active=True,
    ).select_related("product").first()
    if variant is None:
        return JsonResponse({"error": "Cette variante n'est pas disponible pour ce produit."}, status=404)

    offers = []
    queryset = ProductOffer.objects.filter(
        product_id=product.pk, is_active=True,
    ).prefetch_related(
        Prefetch(
            "items",
            queryset=ProductOfferItem.objects.select_related(
                "product", "product__category", "variant", "variant__product",
            ).order_by("position", "pk"),
        ),
    ).order_by("position", "pk")

    for offer in queryset:
        details = _line_details(variant.pk, offer.pk, 1)
        if not details or not details["available"]:
            continue

        components = []
        offer_items = list(offer.items.all())
        reference_total = Decimal("0.00")
        for item in offer_items:
            component = variant if item.use_selected_variant else item.variant
            if component is None:
                components = []
                break
            components.append({
                "name": item.product.name,
                "quantity": item.quantity,
            })
            reference_total += component.price * item.quantity
        if not components:
            continue

        unit_price = Decimal(details["unit_price"])
        saving = reference_total - unit_price if reference_total > unit_price else Decimal("0.00")
        offers.append({
            "id": offer.pk,
            "title": offer.title,
            "badge": offer.get_badge_display(),
            "featured": offer.is_featured,
            "price": f"{unit_price:.2f}",
            "reference_total": f"{reference_total:.2f}",
            "saving": f"{saving:.2f}",
            "components": components,
            "component_count": sum(component["quantity"] for component in components),
            "uses_variant_price": False,
        })

    return JsonResponse({
        "product": {"slug": product.slug, "name": product.name},
        "variant": {"id": variant.pk, "name": variant.color_name},
        "offers": offers,
    })


def _cart_payload(request):
    raw_state = request.session.get(CART_SESSION_KEY, {})
    state = _cart_state(request)
    if raw_state != state:
        request.session[CART_SESSION_KEY] = state
        request.session.modified = True
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
    """Modifie le panier invité après validation stricte de l'action et du catalogue."""
    if len(request.body) > MAX_CART_REQUEST_BYTES:
        return JsonResponse({"error": "Requête trop volumineuse."}, status=413)
    try:
        data = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Requête invalide."}, status=400)
    if not isinstance(data, dict):
        return JsonResponse({"error": "Requête invalide."}, status=400)

    action = data.get("action")
    if not isinstance(action, str):
        return JsonResponse({"error": "Action de panier invalide."}, status=400)

    state = _cart_state(request)
    if action == "clear":
        request.session[CART_SESSION_KEY] = {}
        request.session.modified = True
        return JsonResponse(_cart_payload(request))

    try:
        variant_id = _strict_int(data.get("variant_id"))
        offer_id = _strict_int(data.get("offer_id", 0), allow_zero=True)
    except (TypeError, ValueError):
        return JsonResponse({"error": "Variante ou offre invalide."}, status=400)
    key = f"{variant_id}:{offer_id}"

    if action == "add":
        try:
            quantity = _strict_int(data.get("quantity", 1))
        except (TypeError, ValueError):
            return JsonResponse({"error": "Quantité invalide."}, status=400)
        if quantity > MAX_CART_QUANTITY:
            return JsonResponse({"error": "La quantité maximale est de 10 par ligne."}, status=400)
        current = state.get(key, 0)
        combined_quantity = current + quantity
        if combined_quantity > MAX_CART_QUANTITY:
            return JsonResponse({"error": "La quantité maximale est de 10 par ligne."}, status=400)
        if key not in state and len(state) >= MAX_CART_LINES:
            return JsonResponse({"error": "Le panier contient déjà le nombre maximal de références."}, status=409)

        details = _line_details(variant_id, offer_id, combined_quantity)
        if details is None:
            return JsonResponse({"error": "Ce produit ou cette offre n'est plus disponible."}, status=400)
        if not details["available"]:
            return JsonResponse({"error": "Le stock disponible ne permet pas cette quantité."}, status=409)
        state[key] = combined_quantity

    elif action in {"update", "remove"}:
        if key not in state:
            return JsonResponse({"error": "Article introuvable dans le panier."}, status=404)
        if action == "remove":
            state.pop(key, None)
        else:
            try:
                quantity = _strict_int(data.get("quantity"))
            except (TypeError, ValueError):
                return JsonResponse({"error": "Quantité invalide."}, status=400)
            if quantity > MAX_CART_QUANTITY:
                return JsonResponse({"error": "La quantité maximale est de 10 par ligne."}, status=400)
            details = _line_details(variant_id, offer_id, quantity)
            if details is None:
                return JsonResponse({"error": "Ce produit ou cette offre n'est plus disponible."}, status=400)
            if not details["available"] and quantity >= state[key]:
                return JsonResponse({"error": "Le stock disponible ne permet pas cette quantité."}, status=409)
            # Autoriser une baisse progressive même si le stock a baissé depuis l'ajout initial.
            state[key] = quantity
    else:
        return JsonResponse({"error": "Action de panier inconnue."}, status=400)

    request.session[CART_SESSION_KEY] = state
    request.session.modified = True
    return JsonResponse(_cart_payload(request))
