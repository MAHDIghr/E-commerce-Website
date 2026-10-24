"""Administration des données du catalogue."""
from django.contrib import admin
from django import forms
from django.utils import timezone
from django.utils.html import format_html, format_html_join

from .models import (
    Category, Product, ProductContentItem, ProductCraftDetail, ProductFAQ,
    ProductMedia, ProductOffer, ProductOfferItem, ProductReason, ProductUsage,
    ProductVariant, Review,
)


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ("sku", "color_name", "color_slug", "color_code", "price", "compare_at_price", "stock_quantity", "is_active", "position")


class ProductMediaInline(admin.TabularInline):
    model = ProductMedia
    extra = 0
    fields = ("variant", "media_type", "image", "source_url", "poster_url", "alt_text", "is_primary", "position")


class ProductReasonInline(admin.TabularInline):
    model = ProductReason
    extra = 0


class ProductContentItemInline(admin.TabularInline):
    model = ProductContentItem
    extra = 0


class ProductCraftDetailInline(admin.TabularInline):
    model = ProductCraftDetail
    extra = 0
    fields = ("title", "description", "image", "image_url", "alt_text", "position")


class ProductUsageInline(admin.TabularInline):
    model = ProductUsage
    extra = 0
    fields = ("title", "image", "image_url", "alt_text", "position")


class ProductFAQInline(admin.TabularInline):
    model = ProductFAQ
    extra = 0


class ProductOfferInline(admin.TabularInline):
    model = ProductOffer
    extra = 0
    fields = ("badge", "display_delivery_label", "price", "is_featured", "is_active")
    show_change_link = True
    ordering = ("position", "pk")


class ProductOfferItemInline(admin.TabularInline):
    model = ProductOfferItem
    extra = 1
    fields = ("product", "variant", "use_selected_variant", "quantity", "position")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "position")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("position", "name")
    fields = ("name", "slug", "description", "image", "image_url", "alt_text", "is_active", "position")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "is_active", "is_new", "is_best_seller", "published_at", "catalog_status", "updated_at")
    list_filter = ("is_active", "is_new", "is_best_seller", "category")
    search_fields = ("name", "slug", "short_description", "description")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at", "catalog_publication_diagnostics")
    fieldsets = (
        ("Identité", {"fields": ("name", "slug", "category", "short_description", "description", "brand_line", "tagline", "material")}),
        ("Dimensions", {"fields": ("width_cm", "height_cm", "depth_cm", "weight_g", "capacity_liters", "usage_section_title")}),
        ("Publication", {"fields": ("is_active", "is_new", "is_best_seller", "published_at", "catalog_publication_diagnostics")}),
        ("Référencement", {"fields": ("seo_title", "seo_description")}),
        ("Traçabilité", {"fields": ("created_at", "updated_at")}),
    )
    inlines = (
        ProductVariantInline, ProductMediaInline, ProductReasonInline,
        ProductContentItemInline, ProductCraftDetailInline, ProductUsageInline,
        ProductFAQInline, ProductOfferInline,
    )
    ordering = ("name",)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        # Crée l'offre par défaut après les variantes et les offres saisies dans les inlines.
        from dashboard.services import ensure_default_offer
        ensure_default_offer(form.instance)

    def get_queryset(self, request):
        """Précharge les relations utilisées par le diagnostic de publication."""
        return super().get_queryset(request).select_related("category").prefetch_related(
            "variants", "media_items"
        )

    @staticmethod
    def _publication_issues(obj):
        """Retourne les conditions qui empêchent un produit d'apparaître publiquement."""
        if obj is None or not obj.pk:
            return ["Enregistrez le produit pour vérifier sa publication."]

        issues = []
        now = timezone.now()
        if not obj.is_active:
            issues.append("Produit désactivé : cochez « Actif ».")
        if not obj.category.is_active:
            issues.append("Catégorie inactive : activez la catégorie associée.")
        if obj.published_at and obj.published_at > now:
            issues.append("Date de publication future : le produit n'est pas encore visible.")

        variants = list(obj.variants.all())
        if not any(variant.is_active for variant in variants):
            issues.append("Aucune variante active : ajoutez ou activez une variante avec prix et stock.")

        common_images = [
            media for media in obj.media_items.all()
            if media.variant_id is None
            and media.media_type == ProductMedia.IMAGE
            and (bool(media.image) or bool(media.source_url))
        ]
        if not common_images:
            issues.append(
                "Aucune image commune valide : ajoutez un média de type Image et laissez « Variante » vide."
            )

        has_valid_offer = ProductOffer.objects.filter(
            product=obj,
            is_active=True,
            items__product=obj,
            items__use_selected_variant=True,
            items__variant__isnull=True,
        ).exists()
        if not has_valid_offer:
            issues.append("Aucune offre active valide : créez une offre et reliez-y le produit principal.")

        return issues

    @admin.display(description="État catalogue", ordering="is_active")
    def catalog_status(self, obj):
        """Indicateur de préparation visible dans la liste d'administration."""
        return "Prêt" if not self._publication_issues(obj) else "À compléter"

    @admin.display(description="Diagnostic de publication")
    def catalog_publication_diagnostics(self, obj):
        """Explique en clair les conditions de visibilité publique manquantes."""
        issues = self._publication_issues(obj)
        if not issues:
            status = format_html("<strong>{}</strong>", "Prêt pour le catalogue")
        else:
            status = format_html(
                "<strong>{}</strong><ul>{}</ul>",
                "Non visible dans le catalogue",
                format_html_join("", "<li>{}</li>", ((issue,) for issue in issues)),
            )

        if not obj.pk:
            return status
        if not obj.is_new:
            home_note = "Accueil : cochez « Nouveauté » si ce produit doit apparaître dans la sélection des nouveautés."
        else:
            home_note = "Accueil : seules les 4 nouveautés les plus récentes sont affichées ; ce produit peut ne pas être dans cette sélection."
        return format_html("{}<p>{}</p>", status, home_note)


@admin.register(ProductOffer)
class ProductOfferAdmin(admin.ModelAdmin):
    list_display = ("product", "badge", "display_delivery_label", "price", "is_featured", "is_active", "position")
    list_filter = ("badge", "display_delivery_label", "is_active", "is_featured")
    search_fields = ("title", "product__name")
    ordering = ("product__name", "position")
    fields = ("product", "badge", "display_delivery_label", "price", "is_featured", "is_active")
    inlines = (ProductOfferItemInline,)


@admin.register(ProductOfferItem)
class ProductOfferItemAdmin(admin.ModelAdmin):
    list_display = ("offer", "product", "variant", "use_selected_variant", "quantity", "position")
    list_filter = ("use_selected_variant",)
    search_fields = ("offer__title", "product__name", "variant__sku")


class ReviewAdminForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = "__all__"
        widgets = {
            "author_name": forms.TextInput(attrs={"class": "review-admin-input", "placeholder": "Ex. : Camille"}),
            "author_email": forms.EmailInput(attrs={"class": "review-admin-input", "autocomplete": "off"}),
            "comment": forms.Textarea(attrs={"class": "review-admin-input review-admin-comment", "rows": 6, "placeholder": "Rédigez un retour précis, naturel et utile aux clientes."}),
        }


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    form = ReviewAdminForm
    list_display = ("product", "author_name", "rating_display", "is_approved", "is_featured", "created_at")
    list_filter = ("is_approved", "is_featured", "rating", "created_at")
    search_fields = ("product__name", "author_name", "comment")
    list_select_related = ("product",)
    readonly_fields = ("created_at", "review_preview")
    actions = ("approve_reviews",)
    fieldsets = (
        ("Avis et produit", {"description": "Créez un avis de test ici. Les avis ne peuvent pas être envoyés depuis le site public à ce stade.", "fields": ("product", "author_name", "author_email", "rating", "comment")}),
        ("Publication", {"description": "Un avis doit être approuvé pour apparaître sur la fiche produit. Cochez aussi « Mis en avant » pour l'afficher sur l'accueil.", "fields": ("is_approved", "is_featured", "review_preview")}),
        ("Traçabilité", {"fields": ("created_at",)}),
    )

    class Media:
        css = {"all": ("admin/css/review_admin.css",)}

    @admin.display(description="Aperçu de la note", ordering="rating")
    def rating_display(self, obj):
        return format_html('<span class="review-rating-preview" aria-label="{} sur 5">{}<span class="review-rating-muted">{}</span></span>', obj.rating, "★" * obj.rating, "☆" * (5 - obj.rating))

    @admin.display(description="Aperçu de l'avis")
    def review_preview(self, obj):
        if not obj or not obj.pk:
            return "L'aperçu apparaîtra après l'enregistrement."
        return format_html('<div class="review-admin-preview"><div class="review-admin-preview__stars">{}</div><strong>{}</strong><p>{}</p><small>{}</small></div>', "★" * obj.rating + "☆" * (5 - obj.rating), obj.author_name, obj.comment, obj.product.name)

    def save_model(self, request, obj, form, change):
        if not obj.is_approved:
            obj.is_featured = False
        super().save_model(request, obj, form, change)

    @admin.action(description="Approuver les avis sélectionnés")
    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True, is_featured=False)
