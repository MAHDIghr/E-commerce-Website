from django.urls import path

from . import views


app_name = "home"


urlpatterns = [
    path("", views.home, name="home"),
    path("livraison/", views.information_page, {"page": "delivery"}, name="delivery"),
    path("retours/", views.information_page, {"page": "returns"}, name="returns"),
    path("faq/", views.information_page, {"page": "faq"}, name="faq"),
    path("contact/", views.information_page, {"page": "contact"}, name="contact"),
    path("mentions-legales/", views.information_page, {"page": "legal"}, name="legal"),
    path("confidentialite/", views.information_page, {"page": "privacy"}, name="privacy"),
    path("conditions-generales-de-vente/", views.information_page, {"page": "terms"}, name="terms"),
    path("newsletter/inscription/", views.newsletter_subscribe, name="newsletter_subscribe"),
    path("newsletter/confirmer/<str:token>/", views.newsletter_confirm, name="newsletter_confirm"),
    path("newsletter/desinscription/<uuid:token>/", views.newsletter_unsubscribe, name="newsletter_unsubscribe"),
]