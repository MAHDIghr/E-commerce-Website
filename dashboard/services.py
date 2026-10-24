"""Automatisations explicites du catalogue, exécutées après l'enregistrement des variantes."""
from decimal import Decimal

from product.models import ProductOffer, ProductOfferItem


def ensure_default_offer(product):
    """Assure une offre Essentiel cohérente sans écraser une offre déjà configurée.

    Si aucune variante active n'existe, l'offre est créée inactive à 0 €.
    Dès qu'une variante active est disponible, ce prix provisoire est initialisé
    une seule fois. Le prix d'une offre déjà configurée n'est jamais écrasé.
    """
    variant = product.variants.filter(is_active=True).order_by("position", "pk").first()
    offer = product.offers.filter(badge=ProductOffer.BADGE_ESSENTIAL).order_by("pk").first()

    if offer is None:
        offer = ProductOffer.objects.create(
            product=product,
            title="Essentiel",
            badge=ProductOffer.BADGE_ESSENTIAL,
            display_delivery_label=ProductOffer.DELIVERY_PAID,
            price=variant.price if variant else Decimal("0.00"),
            is_active=variant is not None,
        )
    elif not offer.is_active and offer.price == Decimal("0.00") and variant is not None:
        offer.price = variant.price
        offer.is_active = True
        offer.save(update_fields=("price", "is_active", "title", "position"))

    ProductOfferItem.objects.get_or_create(
        offer=offer,
        product=product,
        use_selected_variant=True,
        defaults={"quantity": 1, "position": 0},
    )
    return offer
