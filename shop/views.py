"""Vue du catalogue alimentée par les données métier publiées."""
from django.db.models import Prefetch
from django.shortcuts import render

from product.models import Category, ProductMedia, ProductVariant, Review
from product.selectors import product_card_data, published_products


def catalog(request):
    categories = list(Category.objects.filter(is_active=True).order_by("position", "name"))
    products = published_products().select_related("category").prefetch_related(
        Prefetch("variants", queryset=ProductVariant.objects.filter(is_active=True).order_by("position", "pk")),
        Prefetch("media_items", queryset=ProductMedia.objects.order_by("-is_primary", "position", "pk")),
        Prefetch("reviews", queryset=Review.objects.filter(is_approved=True)),
    ).order_by("-published_at", "-created_at", "name")

    color_map = {}
    for product in products:
        for variant in product.variants.all():
            if variant.is_active and variant.color_slug and variant.color_code:
                color_map.setdefault(variant.color_slug, {"hex": variant.color_code, "name": variant.color_name or variant.color_slug})

    catalog_data = {
        "products": product_card_data(products),
        "categories": [{"slug": category.slug, "name": category.name} for category in categories],
        "colors": color_map,
    }
    return render(request, "catalog.html", {
        "categories": categories,
        "catalog_data": catalog_data,
    })
