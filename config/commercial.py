"""Règles commerciales affichées et calculées par le serveur.

Les délais ne sont publiés que lorsqu'ils ont été confirmés en configuration.
Le pourcentage du code de bienvenue est lu dans PromoCode, jamais ici.
"""
import os
from decimal import Decimal
from django.core.exceptions import ImproperlyConfigured


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
WELCOME_PROMO_CODE = "BIENVENUE"


def _amount(value):
    return f"{value:.2f}".rstrip("0").rstrip(".")


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
    return {"commercial": {
        "currency": CURRENCY,
        "free_shipping_threshold": str(FREE_SHIPPING_THRESHOLD),
        "standard_shipping": str(SHIPPING_PRICES["standard"]),
        "express_shipping": str(SHIPPING_PRICES["express"]),
        "delivery_days": DELIVERY_DAYS,
        "welcome": offer,
    }}
