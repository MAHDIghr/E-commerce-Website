"""Page d'accueil et parcours publics d'information/newsletter."""
import hashlib
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import F, Prefetch
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from product.models import Category, ProductMedia, ProductOffer, ProductVariant, Review
from .models import NewsletterSubscription, SignatureSelection
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
        "newsletter_notice": request.session.pop("newsletter_notice", ""),
        "newsletter_error": request.session.pop("newsletter_error", ""),
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


logger = logging.getLogger(__name__)


@require_POST
def newsletter_subscribe(request):
    """Enregistre le consentement puis demande une confirmation par e-mail."""
    remote_addr = request.META.get("REMOTE_ADDR", "unknown")
    rate_key = "newsletter-submit:" + hashlib.sha256(remote_addr.encode("utf-8")).hexdigest()
    attempts = cache.get(rate_key, 0) + 1
    cache.set(rate_key, attempts, timeout=900)
    if attempts > 5:
        request.session["newsletter_error"] = "Trop de tentatives. Réessayez dans quelques minutes."
        return redirect("home:home")

    # Champ piège pour limiter les inscriptions automatisées sans révéler le contrôle.
    if request.POST.get("website", "").strip():
        request.session["newsletter_notice"] = "Si une confirmation est nécessaire, un e-mail sera envoyé."
        return redirect("home:home")

    email = request.POST.get("email", "").strip().lower()
    if len(email) > 254:
        request.session["newsletter_error"] = "Saisissez une adresse e-mail valide."
        return redirect("home:home")
    try:
        validate_email(email)
    except ValidationError:
        request.session["newsletter_error"] = "Saisissez une adresse e-mail valide."
        return redirect("home:home")

    if request.POST.get("consent") != "yes":
        request.session["newsletter_error"] = "Votre consentement est nécessaire pour recevoir la newsletter."
        return redirect("home:home")

    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = timezone.now()
    confirmation_url = request.build_absolute_uri(
        reverse("home:newsletter_confirm", kwargs={"token": token})
    )
    send_confirmation = False

    with transaction.atomic():
        subscription = NewsletterSubscription.objects.select_for_update().filter(email=email).first()
        if subscription is None:
            subscription = NewsletterSubscription.objects.create(
                email=email,
                is_confirmed=False,
                is_active=False,
                consent_at=now,
                consent_version="newsletter-v1",
                confirmation_token_hash=token_hash,
                confirmation_expires_at=now + timedelta(hours=24),
            )
            send_confirmation = True
        elif not (subscription.is_confirmed and subscription.is_active):
            subscription.is_active = False
            subscription.consent_at = now
            subscription.consent_version = "newsletter-v1"
            subscription.confirmation_token_hash = token_hash
            subscription.confirmation_expires_at = now + timedelta(hours=24)
            subscription.unsubscribed_at = None
            subscription.save(update_fields=[
                "is_active", "consent_at", "consent_version",
                "confirmation_token_hash", "confirmation_expires_at",
                "unsubscribed_at", "updated_at",
            ])
            send_confirmation = True

    if send_confirmation:
        try:
            send_mail(
                subject="Confirmez votre inscription — My Line Collection",
                message=(
                    "Bonjour,\\n\\nVous avez demandé à recevoir les actualités de My Line Collection. "
                    "Pour confirmer votre inscription, ouvrez ce lien dans les 24 heures :\\n"
                    f"{confirmation_url}\\n\\n"
                    "Si vous n’êtes pas à l’origine de cette demande, ignorez cet e-mail. "
                    "Aucune inscription marketing ne sera activée sans confirmation.\\n\\n"
                    "My Line Collection"
                ),
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                recipient_list=[email],
                fail_silently=False,
            )
        except Exception as exc:
            logger.warning("Newsletter confirmation delivery failed (%s)", type(exc).__name__)

    request.session["newsletter_notice"] = (
        "Si cette adresse nécessite une confirmation, un e-mail vous sera envoyé. "
        "Vérifiez votre boîte de réception et vos courriers indésirables."
    )
    return redirect("home:home")


@require_GET
def newsletter_confirm(request, token):
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = timezone.now()
    with transaction.atomic():
        subscription = NewsletterSubscription.objects.select_for_update().filter(
            confirmation_token_hash=token_hash,
            confirmation_expires_at__gt=now,
            is_confirmed=False,
        ).first()
        if subscription:
            subscription.is_confirmed = True
            subscription.is_active = True
            subscription.confirmed_at = now
            subscription.confirmation_token_hash = ""
            subscription.confirmation_expires_at = None
            subscription.save(update_fields=[
                "is_confirmed", "is_active", "confirmed_at",
                "confirmation_token_hash", "confirmation_expires_at", "updated_at",
            ])
    if not subscription:
        return render(request, "newsletter_status.html", {
            "title": "Lien de confirmation invalide",
            "message": "Ce lien est invalide, a déjà été utilisé ou a expiré. Vous pouvez demander une nouvelle confirmation depuis la page d’accueil.",
            "success": False,
        }, status=400)
    response = render(request, "newsletter_status.html", {
        "title": "Inscription confirmée",
        "message": "Votre adresse est confirmée. Vous recevrez les communications de la newsletter conformément à votre consentement.",
        "success": True,
    })
    response["Cache-Control"] = "no-store"
    response["Referrer-Policy"] = "no-referrer"
    return response


@require_http_methods(["GET", "POST"])
def newsletter_unsubscribe(request, token):
    subscription = NewsletterSubscription.objects.filter(unsubscribe_token=token).first()
    if not subscription:
        return render(request, "newsletter_status.html", {
            "title": "Lien de désinscription invalide",
            "message": "Ce lien de désinscription n’est pas valide.",
            "success": False,
        }, status=404)

    if request.method == "GET":
        return render(request, "newsletter_status.html", {
            "title": "Se désinscrire de la newsletter",
            "message": "Confirmez la désinscription pour ne plus recevoir les communications de la newsletter.",
            "confirm_unsubscribe": True,
            "unsubscribe_token": token,
            "success": True,
        })

    with transaction.atomic():
        subscription = NewsletterSubscription.objects.select_for_update().get(pk=subscription.pk)
        subscription.is_active = False
        subscription.unsubscribed_at = timezone.now()
        subscription.confirmation_token_hash = ""
        subscription.confirmation_expires_at = None
        subscription.save(update_fields=[
            "is_active", "unsubscribed_at", "confirmation_token_hash",
            "confirmation_expires_at", "updated_at",
        ])
    response = render(request, "newsletter_status.html", {
        "title": "Désinscription enregistrée",
        "message": "Votre adresse ne recevra plus les communications de la newsletter.",
        "success": True,
    })
    response["Cache-Control"] = "no-store"
    response["Referrer-Policy"] = "no-referrer"
    return response
