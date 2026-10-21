"""Administration des données du catalogue."""
from django.contrib import admin

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
    fields = ("variant", "media_type", "source_url", "poster_url", "alt_text", "is_primary", "position")


class ProductReasonInline(admin.TabularInline):
    model = ProductReason
    extra = 0


class ProductContentItemInline(admin.TabularInline):
    model = ProductContentItem
    extra = 0


class ProductCraftDetailInline(admin.TabularInline):
    model = ProductCraftDetail
    extra = 0


class ProductUsageInline(admin.TabularInline):
    model = ProductUsage
    extra = 0


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


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "is_active", "is_new", "is_best_seller", "published_at", "updated_at")
    list_filter = ("is_active", "is_new", "is_best_seller", "category")
    search_fields = ("name", "slug", "short_description", "description")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Identité", {"fields": ("name", "slug", "category", "short_description", "description", "brand_line", "tagline", "material")}),
        ("Dimensions", {"fields": ("width_cm", "height_cm", "depth_cm", "weight_g", "capacity_liters", "usage_section_title")}),
        ("Publication", {"fields": ("is_active", "is_new", "is_best_seller", "published_at")}),
        ("Référencement", {"fields": ("seo_title", "seo_description")}),
        ("Traçabilité", {"fields": ("created_at", "updated_at")}),
    )
    inlines = (
        ProductVariantInline, ProductMediaInline, ProductReasonInline,
        ProductContentItemInline, ProductCraftDetailInline, ProductUsageInline,
        ProductFAQInline, ProductOfferInline,
    )
    ordering = ("name",)


@admin.register(ProductOffer)
class ProductOfferAdmin(admin.ModelAdmin):
    list_display = ("title", "product", "price", "is_featured", "is_active", "position")
    list_filter = ("is_active", "is_featured")
    search_fields = ("title", "product__name")
    ordering = ("product__name", "position")


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
