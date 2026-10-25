from django.urls import path
from . import views

app_name = "checkout"
urlpatterns = [
    path("", views.checkout, name="checkout"),
    path("retour/<uuid:public_id>/", views.order_result, name="result"),
    path("stripe/webhook/", views.stripe_webhook, name="stripe_webhook"),
]
