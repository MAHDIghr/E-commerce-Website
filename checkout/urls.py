from django.urls import path
from . import views

app_name = "checkout"
urlpatterns = [
    path("", views.checkout, name="checkout"),
    path("retour/<uuid:public_id>/", views.order_result, name="result"),
    path("suivi/", views.order_tracking_lookup, name="tracking_lookup"),
    path("suivi/<uuid:public_id>/", views.order_tracking, name="tracking"),
    path("suivi/<uuid:public_id>/retour/", views.order_return_request, name="return_request"),
    path("stripe/webhook/", views.stripe_webhook, name="stripe_webhook"),
]
