from django.urls import path
from django.views.generic import RedirectView

from . import views


app_name = "home"


urlpatterns = [
    path("", views.home, name="home"),
    path("campagne/<int:promo_id>/statut/", views.flash_campaign_status, name="flash_campaign_status"),
    path("livraison/", RedirectView.as_view(pattern_name="pages:delivery", permanent=True), name="delivery"),
    path("retours/", RedirectView.as_view(pattern_name="pages:returns", permanent=True), name="returns"),
    path("faq/", RedirectView.as_view(pattern_name="pages:faq", permanent=True), name="faq"),
    path("contact/", RedirectView.as_view(pattern_name="pages:contact", permanent=True), name="contact"),
    path("mentions-legales/", RedirectView.as_view(pattern_name="pages:legal", permanent=True), name="legal"),
    path("confidentialite/", RedirectView.as_view(pattern_name="pages:privacy", permanent=True), name="privacy"),
    path("conditions-generales-de-vente/", RedirectView.as_view(pattern_name="pages:terms", permanent=True), name="terms"),
    path("newsletter/inscription/", views.newsletter_subscribe, name="newsletter_subscribe"),
    path("newsletter/confirmer/<str:token>/", views.newsletter_confirm, name="newsletter_confirm"),
    path("newsletter/desinscription/<uuid:token>/", views.newsletter_unsubscribe, name="newsletter_unsubscribe"),
]
