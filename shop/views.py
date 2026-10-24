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
        Prefetch("offers", queryset=ProductOffer.objects.filter(is_active=True).prefetch_related("items")),
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
                media_type=ProductMedia.IMAGE,
            ).order_by("-is_primary", "position", "pk"),
        ),
        Prefetch("offers", queryset=ProductOffer.objects.filter(is_active=True).prefetch_related("items")),
    ).order_by("-is_best_seller", "-is_new", "name")[:8]

    results = []
    for product in products:
        variant = product.default_variant
        if not variant:
            continue
        media = next((item for item in product.media_items.all() if item.media_type == ProductMedia.IMAGE), None)
        image = (media.image.url if media and media.image else media.source_url) if media else ""
        offers = [
            candidate for candidate in product._active_offers()
            if sum(
                1 for item in candidate.items.all()
                if item.use_selected_variant
                and item.product_id == product.pk
                and item.variant_id is None
                and item.quantity > 0
            ) == 1
        ]
        offer = next((candidate for candidate in offers if candidate.is_featured), offers[0] if offers else None)
        if offer is None:
            continue
        results.append({
            "name": product.name,
            "category": product.category.name,
            "price": f"{offer.price:.2f}",
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


def _parse_selected_item_ids(value):
    """Valide la liste d'articles accessoires choisis pour une offre."""
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > 20:
        raise ValueError("Sélection d'accessoires invalide.")
    parsed = []
    for raw in value:
        item_id = _strict_int(raw)
        if item_id in parsed:
            raise ValueError("Un accessoire ne peut pas être sélectionné plusieurs fois.")
        parsed.append(item_id)
    return sorted(parsed)


def _cart_key(variant_id, offer_id, selected_item_ids=None):
    selected = sorted(selected_item_ids or [])
    base = f"{variant_id}:{offer_id}"
    return f"{base}:{','.join(str(item_id) for item_id in selected)}" if selected else base


def _cart_key_parts(key):
    """Lit les anciennes clés variant:offre et les clés avec accessoires optionnels."""
    if not isinstance(key, str):
        raise ValueError("Clé de panier invalide.")
    parts = key.split(":")
    if len(parts) not in (2, 3):
        raise ValueError("Clé de panier invalide.")
    variant_id = _strict_int(parts[0])
    offer_id = _strict_int(parts[1], allow_zero=True)
    selected_ids = []
    if len(parts) == 3 and parts[2]:
        raw_ids = parts[2].split(",")
        if len(raw_ids) > 20:
            raise ValueError("Clé de panier invalide.")
        for raw in raw_ids:
            item_id = _strict_int(raw)
            if item_id in selected_ids:
                raise ValueError("Clé de panier invalide.")
            selected_ids.append(item_id)
        selected_ids.sort()
    return variant_id, offer_id, selected_ids


def _cart_state(request):
    """Normalise la session et borne le nombre de lignes contrôlées par le client."""
    raw = request.session.get(CART_SESSION_KEY, {})
    if not isinstance(raw, dict):
        return {}

    clean = {}
    for key, quantity in raw.items():
        if len(clean) >= MAX_CART_LINES:
            break
        try:
            variant_id, offer_id, selected_ids = _cart_key_parts(key)
            quantity = _strict_int(quantity)
        except (TypeError, ValueError):
            continue
        if quantity <= MAX_CART_QUANTITY:
            clean[_cart_key(variant_id, offer_id, selected_ids)] = quantity
    return clean


def _product_reference_price(product):
    """Prix public de référence d'un accessoire : offre Essentiel, sinon première offre valide."""
    offers = ProductOffer.objects.filter(
        product_id=product.pk,
        is_active=True,
        items__product_id=product.pk,
        items__use_selected_variant=True,
        items__variant__isnull=True,
    ).distinct()
    essential = offers.filter(badge=ProductOffer.BADGE_ESSENTIAL).order_by("position", "pk").first()
    offer = essential or offers.order_by("-is_featured", "position", "pk").first()
    return (offer.reference_price if offer.reference_price is not None and offer.reference_price > offer.price else offer.price) if offer else None


def _accessory_option(item):
    """Construit une option d'accessoire sans jamais lui attribuer un prix client."""
    component = item.variant
    if (
        item.use_selected_variant
        or item.quantity < 1
        or component is None
        or not component.is_active
        or component.product_id != item.product_id
        or not item.product.is_published
        or not item.product.category.is_active
    ):
        return None
    media = ProductMedia.objects.filter(
        product_id=item.product_id, media_type=ProductMedia.IMAGE,
    ).order_by("-is_primary", "position", "pk").first()
    image = (media.image.url if media and media.image else media.source_url) if media else ""
    reference_price = _product_reference_price(item.product)
    available_quantity = component.stock_quantity // max(1, item.quantity)
    return {
        "item_id": item.pk,
        "product_id": item.product_id,
        "slug": item.product.slug,
        "name": item.product.name,
        "variant_name": component.color_name or "",
        "image": image,
        "quantity": item.quantity,
        "original_price": f"{reference_price:.2f}" if reference_price is not None else "",
        "unit_price": "0.00",
        "is_gift": True,
        "available": available_quantity > 0,
        "available_quantity": available_quantity,
    }


def _line_details(variant_id, offer_id, quantity, selected_item_ids=None):
    """Recalcule l'offre et les accessoires sélectionnés depuis la base de données."""
    selected_item_ids = sorted(selected_item_ids or [])
    if quantity < 1 or quantity > MAX_CART_QUANTITY or not offer_id:
        return None

    variant = ProductVariant.objects.select_related("product", "product__category").filter(
        pk=variant_id, is_active=True,
    ).first()
    if not variant or not published_products().filter(pk=variant.product_id).exists():
        return None

    offer = ProductOffer.objects.filter(
        pk=offer_id, product_id=variant.product_id, is_active=True,
    ).first()
    if not offer:
        return None

    offer_items = list(offer.items.select_related(
        "product", "product__category", "variant", "variant__product",
    ).order_by("position", "pk"))
    main_items = [item for item in offer_items if item.use_selected_variant]
    if (
        len(main_items) != 1
        or main_items[0].product_id != variant.product_id
        or main_items[0].variant_id is not None
        or main_items[0].quantity < 1
    ):
        return None

    fixed_items = {item.pk: item for item in offer_items if not item.use_selected_variant}
    if any(item_id not in fixed_items for item_id in selected_item_ids):
        return None

    # Regrouper les composants par variante : plusieurs composants peuvent consommer
    # le stock du même SKU et ne doivent pas être comptés comme des stocks indépendants.
    requirements_per_unit = {variant.pk: main_items[0].quantity}
    stock_levels = {variant.pk: variant.stock_quantity}
    components = []
    for item_id in selected_item_ids:
        item = fixed_items[item_id]
        accessory = _accessory_option(item)
        if accessory is None:
            return None
        requirements_per_unit[item.variant_id] = requirements_per_unit.get(item.variant_id, 0) + item.quantity
        stock_levels[item.variant_id] = item.variant.stock_quantity
        components.append(accessory)

    max_available_values = [
        stock_levels[variant_id] // per_unit
        for variant_id, per_unit in requirements_per_unit.items()
        if per_unit > 0
    ]
    max_available = min(max_available_values, default=0)
    stock_requirements = {
        str(variant_id): per_unit * quantity
        for variant_id, per_unit in requirements_per_unit.items()
    }
    media = ProductMedia.objects.filter(
        product_id=variant.product_id, media_type=ProductMedia.IMAGE,
    ).order_by("-is_primary", "position", "pk").first()
    image = (media.image.url if media and media.image else media.source_url) if media else ""
    title = f"{variant.product.name} — {offer.title}"
    if variant.color_name:
        title += f" ({variant.color_name})"
    available = max_available >= quantity and max_available > 0
    return {
        "key": _cart_key(variant.pk, offer.pk, selected_item_ids),
        "product_id": variant.product_id,
        "product_slug": variant.product.slug,
        "variant_id": variant.pk,
        "offer_id": offer.pk,
        "name": title,
        "variant_name": variant.color_name,
        "image": image,
        "components": components,
        "selected_item_ids": selected_item_ids,
        "quantity": quantity,
        "unit_price": f"{offer.price:.2f}",
        "line_total": f"{offer.price * quantity:.2f}",
        "available_quantity": min(max_available, MAX_CART_QUANTITY),
        "available": available,
        # Métadonnées internes pour agréger le stock entre toutes les lignes du panier.
        "stock_requirements_per_unit": requirements_per_unit,
        "stock_levels": stock_levels,
        "stock_requirements": stock_requirements,
    }


def _cart_stock_conflicts(state):
    """Retourne les variantes dont le panier cumule plus d'unités que le stock réel."""
    usage = {}
    stock_levels = {}
    for key, quantity in state.items():
        try:
            variant_id, offer_id, selected_ids = _cart_key_parts(key)
        except (TypeError, ValueError):
            continue
        details = _line_details(variant_id, offer_id, quantity, selected_ids)
        if details is None:
            continue
        for variant_key, required in details["stock_requirements"].items():
            variant_pk = int(variant_key)
            usage[variant_pk] = usage.get(variant_pk, 0) + required
            stock_levels[variant_pk] = details["stock_levels"][variant_pk]
    return {
        variant_id for variant_id, used in usage.items()
        if used > stock_levels.get(variant_id, 0)
    }


@require_GET
@ensure_csrf_cookie
def offer_options(request, slug):
    """Expose les offres valides et leurs accessoires optionnels pour une variante."""
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
        offer_items = list(offer.items.all())
        main_item = next((item for item in offer_items if item.use_selected_variant), None)
        if main_item is None or main_item.product_id != product.pk:
            continue
        accessories = [
            option for item in offer_items if not item.use_selected_variant
            for option in [_accessory_option(item)] if option is not None
        ]
        offers.append({
            "id": offer.pk,
            "title": offer.title,
            "badge": offer.get_badge_display(),
            "delivery_label": offer.get_display_delivery_label_display(),
            "featured": offer.is_featured,
            "price": f"{offer.price:.2f}",
            "reference_total": f"{offer.reference_price:.2f}" if offer.reference_price else f"{offer.price:.2f}",
            "saving": "0.00",
            "components": [{
                "name": product.name,
                "quantity": main_item.quantity,
                "variant_name": variant.color_name or "",
            }],
            "accessories": accessories,
            "component_count": main_item.quantity,
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
    details_by_key = {}
    stale_keys = []
    for key, quantity in state.items():
        try:
            variant_id, offer_id, selected_ids = _cart_key_parts(key)
        except (TypeError, ValueError):
            stale_keys.append(key)
            continue
        details = _line_details(variant_id, offer_id, quantity, selected_ids)
        if details is None:
            stale_keys.append(key)
            continue
        details_by_key[key] = details

    if stale_keys:
        for key in stale_keys:
            state.pop(key, None)
        request.session[CART_SESSION_KEY] = state
        request.session.modified = True
        details_by_key = {key: details for key, details in details_by_key.items() if key in state}

    # Le stock est mutualisé entre toutes les lignes du panier, accessoires sélectionnés inclus.
    total_usage = {}
    stock_levels = {}
    for details in details_by_key.values():
        for variant_key, required in details["stock_requirements"].items():
            variant_id = int(variant_key)
            total_usage[variant_id] = total_usage.get(variant_id, 0) + required
            stock_levels[variant_id] = details["stock_levels"][variant_id]

    items = []
    for details in details_by_key.values():
        quantity = details["quantity"]
        effective_capacity = MAX_CART_QUANTITY
        for variant_id, units_per_offer in details["stock_requirements_per_unit"].items():
            other_lines_usage = total_usage.get(variant_id, 0) - units_per_offer * quantity
            remaining_for_line = stock_levels.get(variant_id, 0) - other_lines_usage
            effective_capacity = min(
                effective_capacity,
                max(0, remaining_for_line // units_per_offer),
            )
        details["available_quantity"] = effective_capacity
        details["available"] = quantity <= effective_capacity
        details.pop("stock_requirements_per_unit", None)
        details.pop("stock_levels", None)
        details.pop("stock_requirements", None)
        items.append(details)

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
        selected_item_ids = _parse_selected_item_ids(data.get("selected_item_ids", []))
    except (TypeError, ValueError):
        return JsonResponse({"error": "Variante, offre ou sélection d'accessoires invalide."}, status=400)
    key = _cart_key(variant_id, offer_id, selected_item_ids)

    if action == "add":
        if offer_id == 0:
            return JsonResponse({"error": "Sélectionnez une offre avant d'ajouter ce produit au panier."}, status=400)
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

        details = _line_details(variant_id, offer_id, combined_quantity, selected_item_ids)
        if details is None:
            return JsonResponse({"error": "Ce produit ou cette offre n'est plus disponible."}, status=400)
        proposed_state = dict(state)
        proposed_state[key] = combined_quantity
        conflicts = _cart_stock_conflicts(proposed_state)
        affected_variants = {int(variant_id) for variant_id in details["stock_requirements"]}
        if conflicts & affected_variants:
            return JsonResponse({
                "error": "Le stock disponible ne permet pas cette quantité pour l'ensemble du panier. Réduisez une autre ligne ou cette quantité."
            }, status=409)
        state = proposed_state

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
            details = _line_details(variant_id, offer_id, quantity, selected_item_ids)
            if details is None:
                return JsonResponse({"error": "Ce produit ou cette offre n'est plus disponible."}, status=400)
            if quantity >= state[key]:
                proposed_state = dict(state)
                proposed_state[key] = quantity
                conflicts = _cart_stock_conflicts(proposed_state)
                affected_variants = {int(variant_id) for variant_id in details["stock_requirements"]}
                if conflicts & affected_variants:
                    return JsonResponse({
                        "error": "Le stock disponible ne permet pas cette quantité pour l'ensemble du panier. Réduisez une autre ligne ou cette quantité."
                    }, status=409)
                state = proposed_state
            else:
                # Toujours autoriser une diminution pour corriger un panier devenu indisponible.
                state[key] = quantity
    else:
        return JsonResponse({"error": "Action de panier inconnue."}, status=400)

    request.session[CART_SESSION_KEY] = state
    request.session.modified = True
    return JsonResponse(_cart_payload(request))
