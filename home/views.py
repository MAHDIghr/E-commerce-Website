"""Page d'accueil : les sections commerciales sont issues des modèles."""
from django.db.models import Prefetch
from django.shortcuts import render

from product.models import Category, ProductMedia, ProductVariant
from product.views import published_products


def home(request):
    categories = Category.objects.filter(is_active=True).order_by("position", "name")
    new_products = published_products().filter(is_new=True).select_related("category").prefetch_related(
        Prefetch("variants", queryset=ProductVariant.objects.filter(is_active=True).order_by("position", "pk")),
        Prefetch("media_items", queryset=ProductMedia.objects.filter(variant__isnull=True).order_by("-is_primary", "position", "pk")),
    ).order_by("-published_at", "-created_at")[:4]
    return render(request, "home.html", {
        "categories": categories,
        "new_products": new_products,
    })
