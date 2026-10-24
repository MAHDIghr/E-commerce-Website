from django.urls import path

from .views import (
    DashboardLoginView, DashboardLogoutView, categories, category_delete, category_edit,
    home, offers, product_delete, product_edit, products,
)

app_name = "dashboard"

urlpatterns = [
    path("connexion/", DashboardLoginView.as_view(), name="login"),
    path("deconnexion/", DashboardLogoutView.as_view(), name="logout"),
    path("", home, name="home"),
    path("produits/", products, name="products"),
    path("produits/ajouter/", product_edit, name="product_add"),
    path("produits/<int:pk>/modifier/", product_edit, name="product_edit"),
    path("produits/<int:pk>/supprimer/", product_delete, name="product_delete"),
    path("categories/", categories, name="categories"),
    path("categories/<int:pk>/modifier/", category_edit, name="category_edit"),
    path("categories/<int:pk>/supprimer/", category_delete, name="category_delete"),
    path("offres/", offers, name="offers"),
]
