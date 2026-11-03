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
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from product.models import Category, ProductMedia, ProductOffer, ProductVariant, Review
from .models import NewsletterSubscription, SignatureSelection
from product.selectors import published_products
from checkout.models import PromoCode


@require_GET
def home(request):
    now = timezone.now()
    flash_promo = PromoCode.objects.filter(
        is_flash_campaign=True, is_active=True, starts_at__lte=now, ends_at__gt=now,
        discount_type=PromoCode.PERCENT, value__gt=0, value__lte=100,
    ).order_by("ends_at", "pk").first()
    flash_campaign = None
    if flash_promo:
        percent = f"{flash_promo.value:.2f}".rstrip("0").rstrip(".")
        flash_campaign = {
            "id": flash_promo.pk,
            "code": flash_promo.code,
            "ends_at": flash_promo.ends_at,
            "ends_at_iso": flash_promo.ends_at.isoformat(),
            "percent": percent,
            "minimum": flash_promo.minimum_subtotal,
            "maximum": flash_promo.maximum_discount,
            "once_per_email": flash_promo.once_per_email,
        }
    categories = list(Category.objects.filter(is_active=True).order_by("position", "name"))
    handbags_category = next((category for category in categories if
        category.slug in {"handbags", "sacs-a-main", "sacs-main"} or
        "sacs à main" in category.name.casefold()), None)
    signature_selections = SignatureSelection.objects.filter(
        is_active=True,
        image__gt="",
        product__in=published_products(),
    ).select_related("product", "product__category").prefetch_related(
        Prefetch("product__offers", queryset=ProductOffer.objects.filter(is_active=True).prefetch_related("items")),
        Prefetch("product__variants", queryset=ProductVariant.objects.filter(is_active=True).order_by("position", "pk")),
        Prefetch("product__media_items", queryset=ProductMedia.objects.filter(media_type=ProductMedia.IMAGE).order_by("-is_primary", "position", "pk")),
    ).order_by("position", "pk")
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
        "handbags_category": handbags_category,
        "signature_selections": signature_selections,
        "new_products": new_products,
        "featured_reviews": featured_reviews,
        "flash_campaign": flash_campaign,
        "newsletter_notice": request.session.pop("newsletter_notice", ""),
        "newsletter_error": request.session.pop("newsletter_error", ""),
    })


@require_GET
def flash_campaign_status(request, promo_id):
    """Permet de retirer rapidement un bandeau si l'admin désactive son code."""
    now = timezone.now()
    active = PromoCode.objects.filter(
        pk=promo_id, is_flash_campaign=True, is_active=True,
        starts_at__lte=now, ends_at__gt=now,
        discount_type=PromoCode.PERCENT, value__gt=0, value__lte=100,
    ).exists()
    response = JsonResponse({"active": active})
    response["Cache-Control"] = "no-store"
    return response


@require_GET
def sitemap_xml(request):
    """Expose uniquement les URL publiques canoniques et les produits publiés."""
    from xml.sax.saxutils import escape
    from django.http import HttpResponse
    from django.urls import reverse

    paths = [
        reverse("home:home"),
        reverse("shop:catalog"),
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


@require_GET
def robots_txt(request):
    """Robots.txt public ; ces règles ne remplacent jamais le contrôle d'accès."""
    from django.http import HttpResponse

    sitemap = request.build_absolute_uri("/sitemap.xml")
    body = (
        "User-agent: *\n"
        "Disallow: /admin/\n"
        "Disallow: /gestion/\n"
        "Disallow: /boutique/panier/\n"
        "Disallow: /boutique/recherche/\n"
        f"Sitemap: {sitemap}\n"
    )
    return HttpResponse(body, content_type="text/plain; charset=utf-8")


logger = logging.getLogger(__name__)


def _increment_rate_limit(key, timeout):
    """Compteur atomique de limitation des tentatives publiques."""
    cache.add(key, 0, timeout=timeout)
    try:
        return cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=timeout)
        return 1


@require_POST
def newsletter_subscribe(request):
    """Enregistre le consentement puis demande une confirmation par e-mail."""
    remote_addr = request.META.get("REMOTE_ADDR", "unknown")
    rate_key = "newsletter-submit:" + hashlib.sha256(remote_addr.encode("utf-8")).hexdigest()
    attempts = _increment_rate_limit(rate_key, 900)
    if attempts > 5:
        request.session["newsletter_error"] = "Trop de tentatives. Réessayez dans quelques minutes."
        return redirect(f"{reverse('home:home')}#newsletter")

    # Champ piège pour limiter les inscriptions automatisées sans révéler le contrôle.
    if request.POST.get("website", "").strip():
        request.session["newsletter_notice"] = "Si une confirmation est nécessaire, un e-mail sera envoyé."
        return redirect(f"{reverse('home:home')}#newsletter")

    email = request.POST.get("email", "").strip().lower()
    if len(email) > 254:
        request.session["newsletter_error"] = "Saisissez une adresse e-mail valide."
        return redirect(f"{reverse('home:home')}#newsletter")
    try:
        validate_email(email)
    except ValidationError:
        request.session["newsletter_error"] = "Saisissez une adresse e-mail valide."
        return redirect(f"{reverse('home:home')}#newsletter")

    if request.POST.get("consent") != "yes":
        request.session["newsletter_error"] = "Votre consentement est nécessaire pour recevoir la newsletter."
        return redirect(f"{reverse('home:home')}#newsletter")

    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = timezone.now()
    confirmation_url = request.build_absolute_uri(
        reverse("home:newsletter_confirm", kwargs={"token": token})
    )
    send_confirmation = False

    with transaction.atomic():
        subscription, created = NewsletterSubscription.objects.select_for_update().get_or_create(
            email=email,
            defaults={
                "is_confirmed": False,
                "is_active": False,
                "consent_at": now,
                "consent_version": "newsletter-v1",
                "confirmation_token_hash": token_hash,
                "confirmation_expires_at": now + timedelta(hours=24),
            },
        )
        if created:
            send_confirmation = True
        elif not (subscription.is_confirmed and subscription.is_active):
            # Toute réinscription doit repasser par le double opt-in, y compris
            # une adresse confirmée auparavant puis désinscrite.
            subscription.is_confirmed = False
            subscription.is_active = False
            subscription.confirmed_at = None
            subscription.consent_at = now
            subscription.consent_version = "newsletter-v1"
            subscription.confirmation_token_hash = token_hash
            subscription.confirmation_expires_at = now + timedelta(hours=24)
            subscription.unsubscribed_at = None
            subscription.save(update_fields=[
                "is_confirmed", "is_active", "confirmed_at",
                "consent_at", "consent_version", "confirmation_token_hash",
                "confirmation_expires_at", "unsubscribed_at", "updated_at",
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
    return redirect(f"{reverse('home:home')}#newsletter")


@require_http_methods(["GET", "POST"])
def newsletter_confirm(request, token):
    """GET affiche une confirmation explicite ; seul le POST active l'inscription."""
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = timezone.now()

    if request.method == "GET":
        valid_token = NewsletterSubscription.objects.filter(
            confirmation_token_hash=token_hash,
            confirmation_expires_at__gt=now,
            is_confirmed=False,
        ).exists()
        if not valid_token:
            response = render(request, "newsletter_status.html", {
                "title": "Lien de confirmation invalide",
                "message": "Ce lien est invalide, a déjà été utilisé ou a expiré. Vous pouvez demander une nouvelle confirmation depuis la page d’accueil.",
                "success": False,
            }, status=400)
        else:
            response = render(request, "newsletter_status.html", {
                "title": "Confirmer votre inscription",
                "message": "Pour activer votre inscription, confirmez votre choix ci-dessous. Aucune inscription ne sera activée par la simple ouverture du lien.",
                "confirm_subscription": True,
                "confirmation_token": token,
                "success": True,
            })
        response["Cache-Control"] = "no-store"
        response["Referrer-Policy"] = "no-referrer"
        return response

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
        response = render(request, "newsletter_status.html", {
            "title": "Lien de confirmation invalide",
            "message": "Ce lien est invalide, a déjà été utilisé ou a expiré. Vous pouvez demander une nouvelle confirmation depuis la page d’accueil.",
            "success": False,
        }, status=400)
        response["Cache-Control"] = "no-store"
        response["Referrer-Policy"] = "no-referrer"
        return response

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
        response = render(request, "newsletter_status.html", {
            "title": "Lien de désinscription invalide",
            "message": "Ce lien de désinscription n’est pas valide.",
            "success": False,
        }, status=404)
        response["Cache-Control"] = "no-store"
        response["Referrer-Policy"] = "no-referrer"
        return response

    if request.method == "GET":
        response = render(request, "newsletter_status.html", {
            "title": "Se désinscrire de la newsletter",
            "message": "Confirmez la désinscription pour ne plus recevoir les communications de la newsletter.",
            "confirm_unsubscribe": True,
            "unsubscribe_token": token,
            "success": True,
        })
        response["Cache-Control"] = "no-store"
        response["Referrer-Policy"] = "no-referrer"
        return response

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
