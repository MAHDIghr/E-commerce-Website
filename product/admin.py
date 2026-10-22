"""Administration des données du catalogue."""
from django.contrib import admin
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
    fields = ("title", "badge", "display_delivery_label", "price", "is_featured", "is_active", "position")


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
    fields = ("product", "title", "badge", "display_delivery_label", "price", "is_featured", "is_active")


@admin.register(ProductOfferItem)
class ProductOfferItemAdmin(admin.ModelAdmin):
    list_display = ("offer", "product", "variant", "use_selected_variant", "quantity", "position")
    list_filter = ("use_selected_variant",)
    search_fields = ("offer__title", "product__name", "variant__sku")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "author_name", "rating", "is_approved", "created_at")
    list_filter = ("is_approved", "rating", "created_at")
    search_fields = ("product__name", "author_name", "comment")
    readonly_fields = ("created_at",)
    actions = ("approve_reviews",)

    @admin.action(description="Approuver les avis sélectionnés")
    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)
