from django.urls import path

from .views import information_page


app_name = "pages"

urlpatterns = [
    path("mentions-legales/", information_page, {"page": "legal"}, name="legal"),
    path("conditions-generales-de-vente/", information_page, {"page": "terms"}, name="terms"),
    path("confidentialite/", information_page, {"page": "privacy"}, name="privacy"),
    path("retours-et-retractation/", information_page, {"page": "returns"}, name="returns"),
    path("livraison/", information_page, {"page": "delivery"}, name="delivery"),
    path("contact/", information_page, {"page": "contact"}, name="contact"),
    path("faq/", information_page, {"page": "faq"}, name="faq"),
    path("a-propos/", information_page, {"page": "about"}, name="about"),
]
