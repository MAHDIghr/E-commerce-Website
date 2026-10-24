from django.urls import path

from . import views

app_name = "shop"

urlpatterns = [
    path("recherche/", views.search_suggestions, name="search_suggestions"),
    path("offres/<slug:slug>/", views.offer_options, name="offer_options"),
    path("panier/", views.cart_api, name="cart_api"),
    path("panier/modifier/", views.cart_mutation, name="cart_mutation"),
    path("", views.catalog, name="catalog"),
]
