"""Pages d’information : seuls les contenus approuvés sont rendus publics."""
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.http import require_GET
from config.commercial import public_information


PAGE_TITLES = {
    "legal": "Mentions légales",
    "terms": "Conditions générales de vente",
    "privacy": "Politique de confidentialité",
    "returns": "Retours et rétractation",
    "delivery": "Livraison",
    "contact": "Contact",
    "faq": "Questions fréquentes",
    "about": "À propos",
}


@require_GET
def information_page(request, page):
    title = PAGE_TITLES.get(page)
    if title is None:
        raise Http404
    information = public_information()
    sections = information["pages"].get(page, [])
    return render(request, "pages/information_page.html", {
        "page": {"title": title, "sections": sections},
        "information_available": bool(sections),
    })
