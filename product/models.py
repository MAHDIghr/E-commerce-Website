"""Modèles métier du catalogue My Line Collection.

Les prix et les stocks sont portés par les variantes, jamais par Product.
Les contenus éditoriaux restent rattachés au produit afin d'être administrables.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone
from urllib.parse import urlparse
from django.utils.text import slugify


def _require_https(value, field_name):
    if value and urlparse(value).scheme != "https":
        raise ValidationError({field_name: "Utilisez une URL HTTPS pour les médias publics."})


class Category(models.Model):
    name = models.CharField("Nom", max_length=120)
    slug = models.SlugField("Slug", max_length=140, unique=True)
    description = models.TextField("Description", blank=True)
    image_url = models.URLField("URL de l'image", blank=True)
    alt_text = models.CharField("Texte alternatif", max_length=180, blank=True)
    is_active = models.BooleanField("Active", default=True, db_index=True)
    position = models.PositiveIntegerField("Position", default=0, db_index=True)

    class Meta:
        ordering = ("position", "name")
        verbose_name = "catégorie"
        verbose_name_plural = "catégories"

    def clean(self):
        super().clean()
        _require_https(self.image_url, "image_url")

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products",
        verbose_name="Catégorie",
    )
    name = models.CharField("Nom", max_length=180)
    slug = models.SlugField("Slug", max_length=200, unique=True)
    short_description = models.CharField("Accroche courte", max_length=240, blank=True)
    description = models.TextField("Description", blank=True)
    brand_line = models.CharField("Ligne de marque", max_length=120, blank=True)
    tagline = models.CharField("Accroche", max_length=260, blank=True)
    material = models.CharField("Matière", max_length=180, blank=True)

    # Les dimensions sont facultatives : les accessoires n'ont pas tous ces attributs.
    width_cm = models.DecimalField("Largeur (cm)", max_digits=7, decimal_places=2, null=True, blank=True)
    height_cm = models.DecimalField("Hauteur (cm)", max_digits=7, decimal_places=2, null=True, blank=True)
    depth_cm = models.DecimalField("Profondeur (cm)", max_digits=7, decimal_places=2, null=True, blank=True)
    weight_g = models.PositiveIntegerField("Poids (g)", null=True, blank=True)
    capacity_liters = models.DecimalField("Capacité (L)", max_digits=7, decimal_places=2, null=True, blank=True)
    usage_section_title = models.CharField("Titre de la section d'usage", max_length=140, default="Un sac, cinq journées")

    is_new = models.BooleanField("Nouveauté", default=False, db_index=True)
    is_best_seller = models.BooleanField("Meilleure vente", default=False, db_index=True)
    is_active = models.BooleanField("Actif", default=False, db_index=True)
    published_at = models.DateTimeField("Publié le", null=True, blank=True, db_index=True)

    seo_title = models.CharField("Titre SEO", max_length=70, blank=True)
    seo_description = models.CharField("Description SEO", max_length=170, blank=True)
    created_at = models.DateTimeField("Créé le", auto_now_add=True)
    updated_at = models.DateTimeField("Mis à jour le", auto_now=True)

    class Meta:
        ordering = ("-published_at", "-created_at")
        indexes = [
            models.Index(fields=("is_active", "is_new", "published_at"), name="product_active_new_pub_idx"),
            models.Index(fields=("is_active", "category", "published_at"), name="product_active_cat_pub_idx"),
        ]
        verbose_name = "produit"
        verbose_name_plural = "produits"

    def __str__(self):
        return self.name

    @property
    def is_published(self):
        return self.is_active and (self.published_at is None or self.published_at <= timezone.now())

    @property
    def default_variant(self):
        variants = getattr(self, "_prefetched_objects_cache", {}).get("variants")
        if variants is not None:
            active = [variant for variant in variants if variant.is_active]
            return active[0] if active else None
        return self.variants.filter(is_active=True).order_by("position", "pk").first()

    @property
    def display_price(self):
        variant = self.default_variant
        return variant.price if variant else None

    @property
    def approved_reviews(self):
        return self.reviews.filter(is_approved=True)


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants", verbose_name="Produit")
    sku = models.CharField("SKU", max_length=80, unique=True)
    color_name = models.CharField("Couleur", max_length=80, blank=True)
    color_slug = models.SlugField("Identifiant de couleur", max_length=80, blank=True)
    color_code = models.CharField("Code couleur", max_length=7, blank=True)
    price = models.DecimalField("Prix de vente (€)", max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    compare_at_price = models.DecimalField(
        "Prix de référence (€)", max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Facultatif. Ne doit être renseigné que si le prix de référence est justifié.",
    )
    stock_quantity = models.PositiveIntegerField("Stock", default=0)
    is_active = models.BooleanField("Active", default=True, db_index=True)
    position = models.PositiveIntegerField("Position", default=0)

    class Meta:
        ordering = ("position", "color_name", "pk")
        constraints = [
            models.CheckConstraint(condition=Q(stock_quantity__gte=0), name="variant_stock_nonnegative"),
            models.CheckConstraint(condition=Q(price__gte=0), name="variant_price_nonnegative"),
        ]
        indexes = [models.Index(fields=("product", "is_active", "position"), name="variant_product_active_pos_idx")]
        verbose_name = "variante"
        verbose_name_plural = "variantes"

    def clean(self):
        super().clean()
        if self.compare_at_price is not None and self.compare_at_price <= self.price:
            raise ValidationError({"compare_at_price": "Le prix de référence doit être supérieur au prix de vente."})
        if self.color_code and not (len(self.color_code) == 7 and self.color_code.startswith("#")):
            raise ValidationError({"color_code": "Utilisez un code hexadécimal au format #RRGGBB."})

    def __str__(self):
        return f"{self.product.name} — {self.color_name or 'Variante standard'} ({self.sku})"

    @property
    def is_in_stock(self):
        return self.is_active and self.stock_quantity > 0


class ProductMedia(models.Model):
    IMAGE = "image"
    VIDEO = "video"
    MEDIA_TYPES = [(IMAGE, "Image"), (VIDEO, "Vidéo")]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="media_items", verbose_name="Produit")
    variant = models.ForeignKey(
        ProductVariant, on_delete=models.CASCADE, related_name="media_items",
        null=True, blank=True, verbose_name="Variante",
        help_text="Laisser vide pour un média commun à toutes les variantes.",
    )
    media_type = models.CharField("Type", max_length=10, choices=MEDIA_TYPES, default=IMAGE)
    source_url = models.URLField("URL du média", max_length=1000)
    poster_url = models.URLField("URL de la vignette vidéo", max_length=1000, blank=True)
    alt_text = models.CharField("Texte alternatif", max_length=240, blank=True)
    is_primary = models.BooleanField("Média principal", default=False)
    position = models.PositiveIntegerField("Position", default=0)

    class Meta:
        ordering = ("position", "pk")
        indexes = [models.Index(fields=("product", "variant", "position"), name="media_product_variant_pos_idx")]
        verbose_name = "média produit"
        verbose_name_plural = "médias produit"

    def clean(self):
        super().clean()
        _require_https(self.source_url, "source_url")
        _require_https(self.poster_url, "poster_url")
        if self.variant_id and self.product_id and self.variant.product_id != self.product_id:
            raise ValidationError({"variant": "La variante doit appartenir au produit sélectionné."})
        if self.media_type == self.IMAGE and not self.alt_text.strip():
            raise ValidationError({"alt_text": "Un texte alternatif est requis pour une image."})
        if self.media_type == self.VIDEO and not self.poster_url:
            raise ValidationError({"poster_url": "Une vidéo doit avoir une vignette."})

    def __str__(self):
        return f"{self.product.name} — {self.get_media_type_display()}"


class ProductReason(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reasons", verbose_name="Produit")
    title = models.CharField("Titre", max_length=160)
    description = models.TextField("Description")
    position = models.PositiveIntegerField("Position", default=0)

    class Meta:
        ordering = ("position", "pk")
        verbose_name = "argument produit"
        verbose_name_plural = "arguments produit"

    def __str__(self):
        return self.title


class ProductContentItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="content_items", verbose_name="Produit")
    name = models.CharField("Élément", max_length=120)
    fits = models.BooleanField("Rentre dans le produit", default=True)
    position = models.PositiveIntegerField("Position", default=0)

    class Meta:
        ordering = ("position", "pk")
        verbose_name = "élément de capacité"
        verbose_name_plural = "éléments de capacité"

    def __str__(self):
        return self.name


class ProductCraftDetail(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="craft_details", verbose_name="Produit")
    title = models.CharField("Titre", max_length=160)
    description = models.TextField("Description", blank=True)
    image_url = models.URLField("URL de l'image", max_length=1000, blank=True)
    alt_text = models.CharField("Texte alternatif", max_length=240, blank=True)
    position = models.PositiveIntegerField("Position", default=0)

    class Meta:
        ordering = ("position", "pk")
        verbose_name = "détail de fabrication"
        verbose_name_plural = "détails de fabrication"

    def clean(self):
        super().clean()
        _require_https(self.image_url, "image_url")

    def __str__(self):
        return self.title


class ProductUsage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="usages", verbose_name="Produit")
    title = models.CharField("Titre", max_length=120)
    image_url = models.URLField("URL de l'image", max_length=1000)
    alt_text = models.CharField("Texte alternatif", max_length=240, blank=True)
    position = models.PositiveIntegerField("Position", default=0)

    class Meta:
        ordering = ("position", "pk")
        verbose_name = "situation d'usage"
        verbose_name_plural = "situations d'usage"

    def clean(self):
        super().clean()
        _require_https(self.image_url, "image_url")

    def __str__(self):
        return self.title


class ProductFAQ(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="faqs", verbose_name="Produit")
    question = models.CharField("Question", max_length=240)
    answer = models.TextField("Réponse")
    position = models.PositiveIntegerField("Position", default=0)

    class Meta:
        ordering = ("position", "pk")
        verbose_name = "question fréquente"
        verbose_name_plural = "questions fréquentes"

    def __str__(self):
        return self.question


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews", verbose_name="Produit")
    author_name = models.CharField("Nom affiché", max_length=100)
    author_email = models.EmailField("E-mail (privé)", blank=True)
    rating = models.PositiveSmallIntegerField("Note", validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField("Commentaire")
    is_approved = models.BooleanField("Approuvé", default=False, db_index=True)
    created_at = models.DateTimeField("Créé le", auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("product", "is_approved", "-created_at"), name="review_product_approved_date_idx")]
        constraints = [models.CheckConstraint(condition=Q(rating__gte=1) & Q(rating__lte=5), name="review_rating_1_to_5")]
        verbose_name = "avis"
        verbose_name_plural = "avis"

    def __str__(self):
        return f"Avis de {self.author_name} — {self.product.name}"


class ProductOffer(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="offers", verbose_name="Produit principal")
    title = models.CharField("Titre", max_length=120)
    badge = models.CharField("Badge", max_length=100, blank=True)
    display_delivery_label = models.CharField(
        "Mention de livraison affichée", max_length=120, blank=True,
        help_text="Texte éditorial uniquement ; ne calcule pas les frais de livraison.",
    )
    price = models.DecimalField("Prix de l'offre (€)", max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    is_featured = models.BooleanField("Offre mise en avant", default=False)
    is_active = models.BooleanField("Active", default=True, db_index=True)
    position = models.PositiveIntegerField("Position", default=0)

    class Meta:
        ordering = ("position", "pk")
        constraints = [models.CheckConstraint(condition=Q(price__gte=0), name="offer_price_nonnegative")]
        verbose_name = "offre"
        verbose_name_plural = "offres"

    def __str__(self):
        return f"{self.product.name} — {self.title}"


class ProductOfferItem(models.Model):
    offer = models.ForeignKey(ProductOffer, on_delete=models.CASCADE, related_name="items", verbose_name="Offre")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="offer_components", verbose_name="Produit inclus")
    variant = models.ForeignKey(
        ProductVariant, on_delete=models.PROTECT, related_name="offer_components",
        null=True, blank=True, verbose_name="Variante fixe",
        help_text="Obligatoire pour un accessoire inclus ; vide uniquement pour le produit principal choisi par le client.",
    )
    use_selected_variant = models.BooleanField(
        "Utiliser la variante choisie sur la fiche", default=False,
        help_text="À activer uniquement pour le produit principal de l'offre.",
    )
    quantity = models.PositiveSmallIntegerField("Quantité", default=1, validators=[MinValueValidator(1)])
    position = models.PositiveIntegerField("Position", default=0)

    class Meta:
        ordering = ("position", "pk")
        constraints = [models.CheckConstraint(condition=Q(quantity__gte=1), name="offer_item_quantity_positive")]
        verbose_name = "article d'offre"
        verbose_name_plural = "articles d'offre"

    def clean(self):
        super().clean()
        errors = {}
        if self.use_selected_variant:
            if self.variant_id:
                errors["variant"] = "La variante doit rester vide lorsque la variante est choisie sur la fiche."
            if self.offer_id and self.product_id and self.product_id != self.offer.product_id:
                errors["product"] = "Seul le produit principal de l'offre peut utiliser la variante choisie sur la fiche."
        else:
            if not self.variant_id:
                errors["variant"] = "Sélectionnez une variante fixe pour cet article."
            elif self.product_id and self.variant.product_id != self.product_id:
                errors["variant"] = "La variante fixe doit appartenir au produit inclus."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.offer.title} — {self.product.name} × {self.quantity}"
