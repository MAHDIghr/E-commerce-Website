"""Règles commerciales affichées et calculées par le serveur.

Les délais ne sont publiés que lorsqu'ils ont été confirmés en configuration.
Le pourcentage du code de bienvenue est lu dans PromoCode, jamais ici.
"""
import os
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.validators import validate_email


CURRENCY = os.environ.get("STRIPE_CURRENCY", "eur").strip().upper()
if CURRENCY != "EUR":
    raise ImproperlyConfigured("Le catalogue est libellé en euros : STRIPE_CURRENCY doit être eur.")

FREE_SHIPPING_THRESHOLD = Decimal(os.environ.get("CHECKOUT_FREE_SHIPPING_THRESHOLD", "80.00"))
SHIPPING_PRICES = {
    "standard": Decimal(os.environ.get("CHECKOUT_STANDARD_SHIPPING", "4.90")),
    "express": Decimal(os.environ.get("CHECKOUT_EXPRESS_SHIPPING", "9.90")),
}
DELIVERY_DAYS = {
    "standard": os.environ.get("CHECKOUT_STANDARD_DELIVERY_DAYS", "").strip(),
    "express": os.environ.get("CHECKOUT_EXPRESS_DELIVERY_DAYS", "").strip(),
}
COUNTRY_CHOICES = [
    ("FR", "France"), ("BE", "Belgique"), ("LU", "Luxembourg"),
    ("DE", "Allemagne"), ("ES", "Espagne"), ("IT", "Italie"),
    ("NL", "Pays-Bas"), ("PT", "Portugal"), ("CH", "Suisse"), ("GB", "Royaume-Uni"),
]
PAYMENT_UNAVAILABLE = "Paiement temporairement indisponible"
DESTINATION_UNAVAILABLE = "Cette destination n’est pas prise en charge. Consultez les modalités de livraison."


def configured_countries():
    # Liste candidate, non proposée tant que la matrice commerciale n'est pas approuvée.
    codes = getattr(settings, "CHECKOUT_SHIPPING_COUNTRIES", ("FR", "BE", "LU", "DE", "ES", "IT", "NL", "PT"))
    return [(code, label) for code, label in COUNTRY_CHOICES if code in codes]


def shipping_countries():
    return configured_countries() if public_information()["sales_ready"] else []


def shipping_choices(subtotal, *, offer_free=False):
    """Même grille serveur pour formulaire, devis et commande ; express toujours payant."""
    subtotal = Decimal(str(subtotal)) if subtotal is not None else None
    free = offer_free or (subtotal is not None and subtotal >= FREE_SHIPPING_THRESHOLD)
    methods = [("free", "Standard offert", Decimal("0.00"))] if free else [
        ("standard", "Standard", SHIPPING_PRICES["standard"])]
    methods.append(("express", "Express", SHIPPING_PRICES["express"]))
    result = []
    for method, label, amount in methods:
        mode = "standard" if method == "free" else method
        label += " — " + f"{amount:.2f}".replace(".", ",") + " €"
        description = delivery_description(mode)
        if description:
            label += f" — {description}"
        result.append((method, label, amount))
    return result


def delivery_description(mode):
    days = DELIVERY_DAYS.get(mode, "")
    conditions = getattr(settings, "CHECKOUT_DELIVERY_CONDITIONS", {}).get(mode, "")
    if public_information()["sales_ready"] and days and conditions:
        return f"{days} ({conditions})"
    return ""


WELCOME_PROMO_CODE = "BIENVENUE"


def _amount(value):
    return f"{value:.2f}".rstrip("0").rstrip(".")


SALES_UNAVAILABLE = "La prise de commande est momentanément indisponible."
REQUIRED_INFORMATION_PAGES = ("legal", "terms", "privacy", "returns", "delivery", "contact", "about")


def shipping_configuration():
    """Empreinte lisible de la configuration à faire approuver par l’exploitant."""
    return {
        "countries": [code for code, _label in configured_countries()],
        "currency": CURRENCY,
        "free_shipping_threshold": str(FREE_SHIPPING_THRESHOLD),
        "prices": {key: str(value) for key, value in SHIPPING_PRICES.items()},
        "delivery_days": dict(DELIVERY_DAYS),
        "delivery_conditions": dict(getattr(settings, "CHECKOUT_DELIVERY_CONDITIONS", {})),
        "excluded_postal_prefixes": dict(getattr(settings, "CHECKOUT_EXCLUDED_POSTAL_PREFIXES", {})),
        "customs": getattr(settings, "CHECKOUT_CUSTOMS_INFORMATION", ""),
        "free_shipping_scope": "standard_entire_cart_if_any_offer_free",
        "express_above_threshold": "paid",
    }


def _confirmed_text(value):
    return (isinstance(value, str) and bool(value.strip())
            and "à compléter" not in value.casefold()
            and "a completer" not in value.casefold())


def public_information():
    """Publication fermée par défaut ; l’approbation reste une décision humaine.

    Les textes sont des paragraphes bruts échappés par Django, jamais du HTML.
    Aucun contenu partiel/non approuvé n’est exposé dans le JSON public.
    """
    data = getattr(settings, "COMMERCIAL_INFORMATION", {})
    closed = {"sales_ready": False, "contact_email": "", "pages": {}}
    if not isinstance(data, dict) or data.get("approved") is not True:
        return closed
    if not _confirmed_text(data.get("approval_reference")):
        return closed
    email = data.get("contact_email", "")
    if not isinstance(email, str):
        return closed
    try:
        validate_email(email)
    except (ValidationError, TypeError):
        return closed
    if data.get("shipping") != shipping_configuration():
        return closed
    pages = data.get("pages", {})
    if not isinstance(pages, dict):
        return closed
    cleaned = {}
    for name, sections in pages.items():
        if not isinstance(sections, (list, tuple)) or not sections:
            return closed
        for section in sections:
            if not isinstance(section, (list, tuple)) or len(section) != 2:
                return closed
            heading, paragraphs = section
            if (not _confirmed_text(heading) or not isinstance(paragraphs, (list, tuple))
                    or not paragraphs or not all(_confirmed_text(p) for p in paragraphs)):
                return closed
        cleaned[name] = sections
    if any(name not in cleaned for name in REQUIRED_INFORMATION_PAGES):
        return closed
    return {"sales_ready": True, "contact_email": email, "pages": cleaned}


def shipping_message(*, offer_free=False):
    if not public_information()["sales_ready"]:
        return SALES_UNAVAILABLE
    if offer_free:
        return "Cette offre inclut la livraison standard gratuite pour tout le panier. Express payant."
    return (f"Livraison standard offerte dès {_amount(FREE_SHIPPING_THRESHOLD)} € de sous-total après remise "
            "ou avec une offre incluant la livraison gratuite. Express payant.")


def commercial_context(request):
    """Une promotion n'est annoncée que si son code serveur est réellement utilisable."""
    from django.utils import timezone
    from checkout.models import PromoCode

    now = timezone.now()
    promo = PromoCode.objects.filter(
        code=WELCOME_PROMO_CODE, discount_type=PromoCode.PERCENT,
        is_active=True, value__gt=0, value__lte=100,
    ).first()
    if promo and ((promo.starts_at and promo.starts_at > now) or
                  (promo.ends_at and promo.ends_at <= now)):
        promo = None
    offer = None
    if promo:
        percent = _amount(promo.value)
        minimum = _amount(promo.minimum_subtotal)
        cap = _amount(promo.maximum_discount) if promo.maximum_discount is not None else ""
        offer = {
            "code": promo.code, "percent": percent,
            "minimum": minimum, "maximum": cap, "once_per_email": promo.once_per_email,
            "message": f"−{percent} % avec le code {promo.code} dès {minimum} € d'achat"
                       + (f", remise plafonnée à {cap} €" if cap else "")
                       + (", une fois par adresse e-mail." if promo.once_per_email else "."),
        }
    information = public_information()
    return {"commercial": {
        "sales_ready": information["sales_ready"],
        "sales_unavailable": SALES_UNAVAILABLE,
        "shipping_message": shipping_message(),
        "contact_email": information["contact_email"],
        "currency": CURRENCY,
        "free_shipping_threshold": str(FREE_SHIPPING_THRESHOLD),
        "standard_shipping": str(SHIPPING_PRICES["standard"]),
        "express_shipping": str(SHIPPING_PRICES["express"]),
        "delivery_days": {mode: delivery_description(mode) for mode in DELIVERY_DAYS},
        "welcome": offer,
    }}
