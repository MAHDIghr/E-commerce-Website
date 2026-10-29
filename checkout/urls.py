from django.urls import path
from . import views

app_name = "checkout"
urlpatterns = [
    path("", views.checkout, name="checkout"),
    path("mes-commandes/", views.customer_orders, name="customer_orders"),
    path("mes-commandes/<uuid:public_id>/", views.customer_order_detail, name="customer_order_detail"),
    path("mes-commandes/<uuid:public_id>/retour/", views.customer_return_request, name="customer_return_request"),
    path("retour/<uuid:public_id>/", views.order_result, name="result"),
    path("suivi/<uuid:public_id>/", views.order_tracking, name="tracking"),
    path("suivi/<uuid:public_id>/retour/", views.order_return_request, name="return_request"),
    path("stripe/webhook/", views.stripe_webhook, name="stripe_webhook"),
]
