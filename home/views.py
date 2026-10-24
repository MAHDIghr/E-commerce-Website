"""Page d'accueil : les sections commerciales sont issues des modèles."""
from django.db.models import Prefetch
from django.shortcuts import render

from product.models import Category, ProductMedia, ProductOffer, ProductVariant, Review
from .models import SignatureSelection
from product.selectors import published_products


def home(request):
    categories = Category.objects.filter(is_active=True).order_by("position", "name")
    signature_selections = SignatureSelection.objects.filter(
        is_active=True,
        image__gt="",
        product__in=published_products(),
    ).select_related("product", "product__category").order_by("position", "pk")
    new_products = published_products().filter(is_new=True).select_related("category").prefetch_related(
        Prefetch("variants", queryset=ProductVariant.objects.filter(is_active=True).order_by("position", "pk")),
        Prefetch("offers", queryset=ProductOffer.objects.filter(is_active=True).order_by("-is_featured", "position", "pk")),
        Prefetch(
            "media_items",
            queryset=ProductMedia.objects.filter(
                media_type=ProductMedia.IMAGE,
            ).order_by("-is_primary", "position", "pk"),
        ),
    ).order_by("-published_at", "-created_at")[:4]
    featured_reviews = Review.objects.filter(
        is_approved=True,
        is_featured=True,
        product__in=published_products(),
    ).select_related("product").order_by("-created_at")[:3]
    return render(request, "home.html", {
        "categories": categories,
        "signature_selections": signature_selections,
        "new_products": new_products,
        "featured_reviews": featured_reviews,
    })
