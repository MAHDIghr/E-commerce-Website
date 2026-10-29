from django.urls import path

from .views import (
    DashboardLoginView, DashboardLogoutView, categories, category_delete, category_edit,
    home, offers, product_delete, product_edit, products,
)
from .order_views import (
    orders, order_detail, order_update_fulfillment, order_create_shipment,
    shipment_update_status, return_update_status, order_create_refund,
    order_create_incident, order_update_incident, order_retry_notification,
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
    path("commandes/", orders, name="orders"),
    path("commandes/<int:pk>/", order_detail, name="order_detail"),
    path("commandes/<int:pk>/suivi/", order_update_fulfillment, name="order_update_fulfillment"),
    path("commandes/<int:pk>/expeditions/ajouter/", order_create_shipment, name="order_create_shipment"),
    path("commandes/<int:pk>/expeditions/<int:shipment_pk>/etat/", shipment_update_status, name="shipment_update_status"),
    path("commandes/<int:pk>/retours/<int:return_pk>/etat/", return_update_status, name="return_update_status"),
    path("commandes/<int:pk>/remboursements/ajouter/", order_create_refund, name="order_create_refund"),
    path("commandes/<int:pk>/incidents/ajouter/", order_create_incident, name="order_create_incident"),
    path("commandes/<int:pk>/incidents/<int:incident_pk>/etat/", order_update_incident, name="order_update_incident"),
    path("commandes/<int:pk>/notifications/<int:notification_pk>/relancer/", order_retry_notification, name="order_retry_notification"),
]
