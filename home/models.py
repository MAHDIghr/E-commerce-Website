"""Contenus éditoriaux administrables de la page d'accueil."""
from django.core.exceptions import ValidationError
from django.db import models

from product.models import Product


class SignatureSelection(models.Model):
    """Une carte éditoriale avec image dédiée, reliée à un produit publié."""

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="signature_selections",
        verbose_name="Produit associé",
    )
    image = models.ImageField(
        "Image de la carte",
        upload_to="home/signature/%Y/%m/",
        help_text="Image propre à la sélection signature ; ne remplace pas les médias du produit.",
    )
    alt_text = models.CharField("Texte alternatif", max_length=240)
    position = models.PositiveSmallIntegerField("Ordre d'affichage", default=0, db_index=True)
    is_active = models.BooleanField("Afficher sur l'accueil", default=True, db_index=True)

    class Meta:
        ordering = ("position", "pk")
        constraints = [
            models.UniqueConstraint(fields=("product",), name="unique_signature_product"),
        ]
        verbose_name = "carte de la sélection signature"
        verbose_name_plural = "sélection signature"

    def clean(self):
        super().clean()
        if self.image and not self.alt_text.strip():
            raise ValidationError({"alt_text": "Renseignez un texte alternatif pour cette image."})

    def __str__(self):
        return f"{self.position}. {self.product.name}"
