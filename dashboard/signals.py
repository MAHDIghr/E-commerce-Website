"""Automatisations sûres du catalogue lors de la création d'un produit."""
from decimal import Decimal

from django.db.models.signals import post_save
from django.dispatch import receiver

from product.models import Product, ProductOffer, ProductOfferItem, ProductVariant


@receiver(post_save, sender=Product)
def create_default_offer_for_product(sender, instance, created, **kwargs):
    """Prépare une offre Essentiel et son composant principal, sans publier prématurément."""
    if not created:
        return

    offer, offer_created = ProductOffer.objects.get_or_create(
        product=instance,
        badge=ProductOffer.BADGE_ESSENTIAL,
        defaults={
            "title": "Essentiel",
            "display_delivery_label": ProductOffer.DELIVERY_PAID,
            "price": Decimal("0.00"),
            "is_active": False,
            "position": ProductOffer.BADGE_ORDER[ProductOffer.BADGE_ESSENTIAL],
        },
    )
    if offer_created:
        ProductOfferItem.objects.get_or_create(
            offer=offer,
            product=instance,
            use_selected_variant=True,
            defaults={"quantity": 1, "position": 0},
        )


@receiver(post_save, sender=ProductVariant)
def complete_default_offer_price(sender, instance, created, **kwargs):
    """Initialise l'offre automatique dès qu'une variante active fournit un prix réel."""
    if not instance.is_active:
        return

    offer = ProductOffer.objects.filter(
        product=instance.product,
        badge=ProductOffer.BADGE_ESSENTIAL,
        is_active=False,
        price=Decimal("0.00"),
    ).first()
    if offer is None:
        return

    offer.price = instance.price
    offer.is_active = True
    offer.save(update_fields=("price", "is_active", "title", "position"))
