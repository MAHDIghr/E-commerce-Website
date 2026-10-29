from .customer_auth import CustomerLoginView, CustomerLogoutView, customer_signup
from django.urls import path
from . import views

app_name = "checkout"
urlpatterns = [
    path("compte/connexion/", CustomerLoginView.as_view(), name="customer_login"),
    path("compte/deconnexion/", CustomerLogoutView.as_view(), name="customer_logout"),
    path("compte/inscription/", customer_signup, name="customer_signup"),
    path("", views.checkout, name="checkout"),
    path("mes-commandes/", views.customer_orders, name="customer_orders"),
    path("mes-commandes/<uuid:public_id>/", views.customer_order_detail, name="customer_order_detail"),
    path("mes-commandes/<uuid:public_id>/retour/", views.customer_return_request, name="customer_return_request"),
    path("retour/<uuid:public_id>/", views.order_result, name="result"),
    path("suivi/<uuid:public_id>/", views.order_tracking, name="tracking"),
    path("suivi/<uuid:public_id>/retour/", views.order_return_request, name="return_request"),
    path("stripe/webhook/", views.stripe_webhook, name="stripe_webhook"),
]
