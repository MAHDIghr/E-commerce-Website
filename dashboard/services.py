"""Automatisations du catalogue, sans prix attaché aux variantes."""
from decimal import Decimal

from product.models import ProductOffer, ProductOfferItem


def ensure_default_offer(product):
    """Garantit une offre Essentiel de secours pour les créations via Django Admin.

    Le dashboard propose explicitement de une à trois offres avec leurs prix.
    Cette fonction ne remplace jamais un prix déjà saisi et n'en déduit aucun
    depuis une variante, qui ne porte plus de prix.
    """
    offer = product.offers.filter(badge=ProductOffer.BADGE_ESSENTIAL).order_by("pk").first()
    if offer is None:
        offer = ProductOffer.objects.create(
            product=product,
            title="Essentiel",
            badge=ProductOffer.BADGE_ESSENTIAL,
            display_delivery_label=ProductOffer.DELIVERY_PAID,
            price=Decimal("0.00"),
            is_active=False,
        )
    ProductOfferItem.objects.get_or_create(
        offer=offer,
        product=product,
        use_selected_variant=True,
        defaults={"quantity": 1, "position": 0},
    )
    return offer
