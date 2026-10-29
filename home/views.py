"""Page d'accueil : les sections commerciales sont issues des modèles."""
from django.db.models import F, Prefetch
from django.shortcuts import render

from product.models import Category, ProductMedia, ProductOffer, ProductVariant, Review
from .models import SignatureSelection
from product.selectors import published_products


def home(request):
    categories = Category.objects.filter(is_active=True).order_by("position", "name")
    signature_selections = SignatureSelection.objects.filter(
        is_active=True,
        image__gt="",
        product__in=published_products(),
    ).select_related("product", "product__category").order_by("position", "pk")
    new_products = published_products().filter(is_new=True).select_related("category").prefetch_related(
        Prefetch("variants", queryset=ProductVariant.objects.filter(is_active=True).order_by("position", "pk")),
        Prefetch(
            "offers",
            queryset=ProductOffer.objects.filter(
                is_active=True,
                items__product_id=F("product_id"),
                items__use_selected_variant=True,
                items__variant__isnull=True,
            ).distinct().order_by("-is_featured", "position", "pk"),
        ),
        Prefetch(
            "media_items",
            queryset=ProductMedia.objects.filter(
                media_type=ProductMedia.IMAGE,
            ).order_by("-is_primary", "position", "pk"),
        ),
    ).order_by("-published_at", "-created_at")[:4]
    featured_reviews = Review.objects.filter(
        is_approved=True,
        is_featured=True,
        product__in=published_products(),
    ).select_related("product").order_by("-created_at")[:3]
    return render(request, "home.html", {
        "categories": categories,
        "signature_selections": signature_selections,
        "new_products": new_products,
        "featured_reviews": featured_reviews,
    })


INFO_PAGES = {
    "delivery": {
        "title": "Livraison",
        "description": "Informations sur le traitement et le suivi des commandes My Line Collection.",
        "intro": "Les informations définitives sur les zones desservies, les transporteurs, les frais et les délais doivent être confirmées avant l’ouverture des ventes.",
        "sections": [
            {"title": "Suivre une commande", "paragraphs": ["Après avoir reçu votre référence de commande, utilisez la page de suivi pour consulter l’état disponible et les événements de livraison."]},
            {"title": "Informations à confirmer", "paragraphs": ["Les zones de livraison, les tarifs, les délais estimés, les transporteurs et la procédure en cas de colis retardé doivent être précisés dans la politique de livraison finale."]},
        ],
    },
    "returns": {
        "title": "Retours et remboursements",
        "description": "Informations sur les demandes de retour et leur suivi.",
        "intro": "Une demande envoyée depuis le suivi de commande est enregistrée pour examen. Son envoi ne vaut pas acceptation du retour ni confirmation de remboursement.",
        "sections": [
            {"title": "Faire une demande", "paragraphs": ["Ouvrez le suivi avec la référence de commande, sélectionnez les articles concernés et décrivez le motif de votre demande."]},
            {"title": "Traitement", "paragraphs": ["Les conditions d’éligibilité, les délais, les frais de retour et les modalités de remboursement doivent être précisés dans la politique de retour finale."]},
        ],
    },
    "faq": {
        "title": "Questions fréquentes",
        "description": "Réponses aux questions fréquentes concernant les commandes My Line Collection.",
        "intro": "Cette page rassemble les premiers repères utiles pour consulter une commande et demander de l’aide.",
        "sections": [
            {"title": "Comment suivre ma commande ?", "paragraphs": ["Utilisez le lien « Suivre ma commande » et saisissez la référence complète reçue dans l’e-mail de confirmation. Aucun compte client n’est nécessaire."]},
            {"title": "Je ne retrouve pas ma référence", "paragraphs": ["Recherchez l’e-mail de confirmation de commande. Si vous ne le retrouvez pas, utilisez les coordonnées de contact publiées par la boutique lorsqu’elles seront configurées."]},
            {"title": "Puis-je demander un retour ?", "paragraphs": ["Lorsque la commande est payée, le suivi permet de soumettre une demande. L’équipe doit ensuite l’examiner selon les conditions applicables."]},
        ],
    },
    "contact": {
        "title": "Contact",
        "description": "Contacter My Line Collection au sujet d’une commande ou d’un produit.",
        "intro": "Pour toute question relative à une commande, préparez votre référence afin de faciliter son identification.",
        "sections": [
            {"title": "À propos d’une commande", "paragraphs": ["La page de suivi permet de consulter les informations logistiques disponibles et de soumettre une demande liée à une commande payée."]},
            {"title": "Coordonnées", "paragraphs": ["Les coordonnées officielles du service client doivent être renseignées par l’exploitant avant l’ouverture des ventes."]},
        ],
    },
    "legal": {
        "title": "Mentions légales",
        "description": "Informations d’identification de l’éditeur du site My Line Collection.",
        "draft_notice": True,
        "intro": "Cette page est une trame de travail et ne constitue pas encore des mentions légales complètes.",
        "sections": [
            {"title": "Éditeur du site", "paragraphs": ["À compléter : nom légal ou dénomination sociale, forme juridique, adresse du siège, numéro d’immatriculation applicable et coordonnées de contact."]},
            {"title": "Responsable de publication", "paragraphs": ["À compléter : identité du responsable de publication."]},
            {"title": "Hébergement", "paragraphs": ["À compléter : raison sociale, adresse et coordonnées de l’hébergeur du site."]},
        ],
    },
    "privacy": {
        "title": "Politique de confidentialité",
        "description": "Informations sur les données personnelles traitées par My Line Collection.",
        "draft_notice": True,
        "intro": "Cette page est une trame de travail. Elle doit être complétée à partir des traitements réellement utilisés sur le site avant toute collecte de données clients.",
        "sections": [
            {"title": "Données et finalités", "paragraphs": ["À documenter : données collectées lors d’une commande, finalités, bases juridiques, destinataires et durées de conservation."]},
            {"title": "Prestataires", "paragraphs": ["À documenter : prestataires de paiement, d’hébergement, d’e-mail, d’analytique et éventuels transferts hors de l’Espace économique européen."]},
            {"title": "Droits et contact", "paragraphs": ["À compléter : modalités d’exercice des droits des personnes, coordonnées du responsable du traitement et procédure de réclamation."]},
            {"title": "Cookies et traceurs", "paragraphs": ["À documenter après inventaire des scripts et traceurs réellement activés sur le site."]},
        ],
    },
    "terms": {
        "title": "Conditions générales de vente",
        "description": "Conditions contractuelles applicables aux achats sur My Line Collection.",
        "draft_notice": True,
        "intro": "Cette page est une trame de travail et ne constitue pas des conditions générales de vente prêtes à être appliquées.",
        "sections": [
            {"title": "Vendeur et produits", "paragraphs": ["À compléter : identité du vendeur, caractéristiques essentielles des produits et règles de disponibilité."]},
            {"title": "Prix et paiement", "paragraphs": ["À compléter : prix TTC, moyens de paiement, facturation, éventuels frais et règles de promotion."]},
            {"title": "Livraison, rétractation et garanties", "paragraphs": ["À compléter et faire vérifier : zones et délais de livraison, droit de rétractation et exceptions, garanties légales, retours et remboursements."]},
            {"title": "Litiges", "paragraphs": ["À compléter : droit applicable, procédure de réclamation et dispositif de médiation de la consommation applicable."]},
        ],
    },
}


def information_page(request, page):
    from django.http import Http404

    content = INFO_PAGES.get(page)
    if content is None:
        raise Http404
    return render(request, "info_page.html", {"page": content})


def sitemap_xml(request):
    """Expose uniquement les URL publiques canoniques et les produits publiés."""
    from xml.sax.saxutils import escape
    from django.http import HttpResponse
    from django.urls import reverse

    paths = [
        reverse("home:home"),
        reverse("shop:catalog"),
        reverse("home:delivery"),
        reverse("home:returns"),
        reverse("home:faq"),
        reverse("home:contact"),
    ]
    paths.extend(
        reverse("product:detail", kwargs={"slug": product.slug})
        for product in published_products().only("slug").order_by("slug")
    )
    urls = "".join(
        f"<url><loc>{escape(request.build_absolute_uri(path))}</loc></url>"
        for path in paths
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{urls}</urlset>"
    )
    return HttpResponse(xml, content_type="application/xml; charset=utf-8")


def robots_txt(request):
    """Robots.txt public ; ces règles ne remplacent jamais le contrôle d'accès."""
    from django.http import HttpResponse

    sitemap = request.build_absolute_uri("/sitemap.xml")
    body = (
        "User-agent: *\\n"
        "Disallow: /admin/\\n"
        "Disallow: /gestion/\\n"
        "Disallow: /boutique/mon-panier/\\n"
        "Disallow: /boutique/panier/\\n"
        "Disallow: /boutique/recherche/\\n"
        f"Sitemap: {sitemap}\\n"
    )
    return HttpResponse(body, content_type="text/plain; charset=utf-8")
