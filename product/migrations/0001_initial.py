# Generated for the first database-backed product catalog.
from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Category",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, verbose_name="Nom")),
                ("slug", models.SlugField(max_length=140, unique=True, verbose_name="Slug")),
                ("description", models.TextField(blank=True, verbose_name="Description")),
                ("image_url", models.URLField(blank=True, verbose_name="URL de l'image")),
                ("alt_text", models.CharField(blank=True, max_length=180, verbose_name="Texte alternatif")),
                ("is_active", models.BooleanField(db_index=True, default=True, verbose_name="Active")),
                ("position", models.PositiveIntegerField(db_index=True, default=0, verbose_name="Position")),
            ],
            options={
                "verbose_name": "catégorie",
                "verbose_name_plural": "catégories",
                "ordering": ("position", "name"),
            },
        ),
        migrations.CreateModel(
            name="Product",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=180, verbose_name="Nom")),
                ("slug", models.SlugField(max_length=200, unique=True, verbose_name="Slug")),
                ("short_description", models.CharField(blank=True, max_length=240, verbose_name="Accroche courte")),
                ("description", models.TextField(blank=True, verbose_name="Description")),
                ("brand_line", models.CharField(blank=True, max_length=120, verbose_name="Ligne de marque")),
                ("tagline", models.CharField(blank=True, max_length=260, verbose_name="Accroche")),
                ("material", models.CharField(blank=True, max_length=180, verbose_name="Matière")),
                ("width_cm", models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True, verbose_name="Largeur (cm)")),
                ("height_cm", models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True, verbose_name="Hauteur (cm)")),
                ("depth_cm", models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True, verbose_name="Profondeur (cm)")),
                ("weight_g", models.PositiveIntegerField(blank=True, null=True, verbose_name="Poids (g)")),
                ("capacity_liters", models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True, verbose_name="Capacité (L)")),
                ("usage_section_title", models.CharField(default="Un sac, cinq journées", max_length=140, verbose_name="Titre de la section d'usage")),
                ("is_new", models.BooleanField(db_index=True, default=False, verbose_name="Nouveauté")),
                ("is_best_seller", models.BooleanField(db_index=True, default=False, verbose_name="Meilleure vente")),
                ("is_active", models.BooleanField(db_index=True, default=False, verbose_name="Actif")),
                ("published_at", models.DateTimeField(blank=True, db_index=True, null=True, verbose_name="Publié le")),
                ("seo_title", models.CharField(blank=True, max_length=70, verbose_name="Titre SEO")),
                ("seo_description", models.CharField(blank=True, max_length=170, verbose_name="Description SEO")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Créé le")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Mis à jour le")),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="products", to="product.category", verbose_name="Catégorie")),
            ],
            options={
                "verbose_name": "produit",
                "verbose_name_plural": "produits",
                "ordering": ("-published_at", "-created_at"),
            },
        ),
        migrations.CreateModel(
            name="ProductVariant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sku", models.CharField(max_length=80, unique=True, verbose_name="SKU")),
                ("color_name", models.CharField(blank=True, max_length=80, verbose_name="Couleur")),
                ("color_slug", models.SlugField(blank=True, max_length=80, verbose_name="Identifiant de couleur")),
                ("color_code", models.CharField(blank=True, max_length=7, verbose_name="Code couleur")),
                ("price", models.DecimalField(decimal_places=2, max_digits=10, validators=[MinValueValidator(Decimal("0.00"))], verbose_name="Prix de vente (€)")),
                ("compare_at_price", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, validators=[MinValueValidator(Decimal("0.00"))], verbose_name="Prix de référence (€)", help_text="Facultatif. Ne doit être renseigné que si le prix de référence est justifié.")),
                ("stock_quantity", models.PositiveIntegerField(default=0, verbose_name="Stock")),
                ("is_active", models.BooleanField(db_index=True, default=True, verbose_name="Active")),
                ("position", models.PositiveIntegerField(default=0, verbose_name="Position")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="variants", to="product.product", verbose_name="Produit")),
            ],
            options={
                "verbose_name": "variante",
                "verbose_name_plural": "variantes",
                "ordering": ("position", "color_name", "pk"),
                "constraints": [
                    models.UniqueConstraint(condition=~models.Q(("color_slug", "")), fields=("product", "color_slug"), name="unique_product_color_slug"),
                    models.CheckConstraint(condition=models.Q(("stock_quantity__gte", 0)), name="variant_stock_nonnegative"),
                    models.CheckConstraint(condition=models.Q(("price__gte", 0)), name="variant_price_nonnegative"),
                    models.CheckConstraint(condition=models.Q(("compare_at_price__isnull", True)) | models.Q(("compare_at_price__gt", models.F("price"))), name="variant_reference_price_gt_sale"),
                ],
                "indexes": [models.Index(fields=["product", "is_active", "position"], name="variant_product_active_pos_idx")],
            },
        ),
        migrations.CreateModel(
            name="ProductMedia",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("media_type", models.CharField(choices=[("image", "Image"), ("video", "Vidéo")], default="image", max_length=10, verbose_name="Type")),
                ("source_url", models.URLField(max_length=1000, verbose_name="URL du média")),
                ("poster_url", models.URLField(blank=True, max_length=1000, verbose_name="URL de la vignette vidéo")),
                ("alt_text", models.CharField(blank=True, max_length=240, verbose_name="Texte alternatif")),
                ("is_primary", models.BooleanField(default=False, verbose_name="Média principal")),
                ("position", models.PositiveIntegerField(default=0, verbose_name="Position")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="media_items", to="product.product", verbose_name="Produit")),
                ("variant", models.ForeignKey(blank=True, help_text="Laisser vide pour un média commun à toutes les variantes.", null=True, on_delete=django.db.models.deletion.CASCADE, related_name="media_items", to="product.productvariant", verbose_name="Variante")),
            ],
            options={
                "verbose_name": "média produit",
                "verbose_name_plural": "médias produit",
                "ordering": ("-is_primary", "position", "pk"),
                "indexes": [models.Index(fields=["product", "variant", "position"], name="media_product_variant_pos_idx")],
                "constraints": [
                    models.UniqueConstraint(condition=models.Q(("is_primary", True), ("variant__isnull", True)), fields=("product",), name="one_primary_common_media_per_product"),
                    models.UniqueConstraint(condition=models.Q(("is_primary", True), ("variant__isnull", False)), fields=("variant",), name="one_primary_variant_media"),
                ],
            },
        ),
        migrations.CreateModel(
            name="ProductReason",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=160, verbose_name="Titre")),
                ("description", models.TextField(verbose_name="Description")),
                ("position", models.PositiveIntegerField(default=0, verbose_name="Position")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reasons", to="product.product", verbose_name="Produit")),
            ],
            options={"verbose_name": "argument produit", "verbose_name_plural": "arguments produit", "ordering": ("position", "pk")},
        ),
        migrations.CreateModel(
            name="ProductContentItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, verbose_name="Élément")),
                ("fits", models.BooleanField(default=True, verbose_name="Rentre dans le produit")),
                ("position", models.PositiveIntegerField(default=0, verbose_name="Position")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="content_items", to="product.product", verbose_name="Produit")),
            ],
            options={"verbose_name": "élément de capacité", "verbose_name_plural": "éléments de capacité", "ordering": ("position", "pk")},
        ),
        migrations.CreateModel(
            name="ProductCraftDetail",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=160, verbose_name="Titre")),
                ("description", models.TextField(blank=True, verbose_name="Description")),
                ("image_url", models.URLField(blank=True, max_length=1000, verbose_name="URL de l'image")),
                ("alt_text", models.CharField(blank=True, max_length=240, verbose_name="Texte alternatif")),
                ("position", models.PositiveIntegerField(default=0, verbose_name="Position")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="craft_details", to="product.product", verbose_name="Produit")),
            ],
            options={"verbose_name": "détail de fabrication", "verbose_name_plural": "détails de fabrication", "ordering": ("position", "pk")},
        ),
        migrations.CreateModel(
            name="ProductUsage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=120, verbose_name="Titre")),
                ("image_url", models.URLField(max_length=1000, verbose_name="URL de l'image")),
                ("alt_text", models.CharField(blank=True, max_length=240, verbose_name="Texte alternatif")),
                ("position", models.PositiveIntegerField(default=0, verbose_name="Position")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="usages", to="product.product", verbose_name="Produit")),
            ],
            options={"verbose_name": "situation d'usage", "verbose_name_plural": "situations d'usage", "ordering": ("position", "pk")},
        ),
        migrations.CreateModel(
            name="ProductFAQ",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("question", models.CharField(max_length=240, verbose_name="Question")),
                ("answer", models.TextField(verbose_name="Réponse")),
                ("position", models.PositiveIntegerField(default=0, verbose_name="Position")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="faqs", to="product.product", verbose_name="Produit")),
            ],
            options={"verbose_name": "question fréquente", "verbose_name_plural": "questions fréquentes", "ordering": ("position", "pk")},
        ),
        migrations.CreateModel(
            name="Review",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("author_name", models.CharField(max_length=100, verbose_name="Nom affiché")),
                ("author_email", models.EmailField(blank=True, max_length=254, verbose_name="E-mail (privé)")),
                ("rating", models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], verbose_name="Note")),
                ("comment", models.TextField(verbose_name="Commentaire")),
                ("is_approved", models.BooleanField(db_index=True, default=False, verbose_name="Approuvé")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Créé le")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reviews", to="product.product", verbose_name="Produit")),
            ],
            options={
                "verbose_name": "avis",
                "verbose_name_plural": "avis",
                "ordering": ("-created_at",),
                "constraints": [models.CheckConstraint(condition=models.Q(("rating__gte", 1), ("rating__lte", 5)), name="review_rating_1_to_5")],
                "indexes": [models.Index(fields=["product", "is_approved", "-created_at"], name="review_product_approved_date_idx")],
            },
        ),
        migrations.CreateModel(
            name="ProductOffer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=120, verbose_name="Titre")),
                ("badge", models.CharField(blank=True, max_length=100, verbose_name="Badge")),
                ("display_delivery_label", models.CharField(blank=True, help_text="Texte éditorial uniquement ; ne calcule pas les frais de livraison.", max_length=120, verbose_name="Mention de livraison affichée")),
                ("price", models.DecimalField(decimal_places=2, max_digits=10, validators=[MinValueValidator(Decimal("0.00"))], verbose_name="Prix de l'offre (€)")),
                ("is_featured", models.BooleanField(default=False, verbose_name="Offre mise en avant")),
                ("is_active", models.BooleanField(db_index=True, default=True, verbose_name="Active")),
                ("position", models.PositiveIntegerField(default=0, verbose_name="Position")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="offers", to="product.product", verbose_name="Produit principal")),
            ],
            options={
                "verbose_name": "offre",
                "verbose_name_plural": "offres",
                "ordering": ("position", "pk"),
                "constraints": [models.CheckConstraint(condition=models.Q(("price__gte", 0)), name="offer_price_nonnegative")],
            },
        ),
        migrations.CreateModel(
            name="ProductOfferItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("use_selected_variant", models.BooleanField(default=False, help_text="À activer uniquement pour le produit principal de l'offre.", verbose_name="Utiliser la variante choisie sur la fiche")),
                ("quantity", models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1)], verbose_name="Quantité")),
                ("position", models.PositiveIntegerField(default=0, verbose_name="Position")),
                ("offer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="product.productoffer", verbose_name="Offre")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="offer_components", to="product.product", verbose_name="Produit inclus")),
                ("variant", models.ForeignKey(blank=True, help_text="Obligatoire pour un accessoire inclus ; vide uniquement pour le produit principal choisi par le client.", null=True, on_delete=django.db.models.deletion.PROTECT, related_name="offer_components", to="product.productvariant", verbose_name="Variante fixe")),
            ],
            options={
                "verbose_name": "article d'offre",
                "verbose_name_plural": "articles d'offre",
                "ordering": ("position", "pk"),
                "constraints": [models.CheckConstraint(condition=models.Q(("quantity__gte", 1)), name="offer_item_quantity_positive")],
            },
        ),
        migrations.AddIndex(
            model_name="product",
            index=models.Index(fields=["is_active", "is_new", "published_at"], name="product_active_new_pub_idx"),
        ),
        migrations.AddIndex(
            model_name="product",
            index=models.Index(fields=["is_active", "category", "published_at"], name="product_active_cat_pub_idx"),
        ),
    ]
