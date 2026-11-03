"""Parcours de commande et endpoint webhook Stripe."""
import hashlib
import logging
import os
import uuid
from decimal import Decimal
import stripe
from django.contrib import messages
from config.commercial import FREE_SHIPPING_THRESHOLD, SHIPPING_PRICES, public_information, SALES_UNAVAILABLE
from django.db import transaction
from django.core.cache import cache
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseNotFound, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from shop.views import CART_SESSION_KEY, _cart_state
from .forms import CheckoutForm, ShippingQuoteForm, COUNTRIES
from .models import Order, PaymentAttempt, OrderNotification
from .services import CheckoutProblem, RetryableWebhookError, apply_promo_code, create_order_and_reserve, create_stripe_session, process_stripe_event, release_reserved_stock, shipping_price, stripe_configured, validated_cart
from .lifecycle import LifecycleProblem, create_return_request, queue_notification, deliver_notification

logger = logging.getLogger(__name__)


def _increment_rate_limit(key, timeout):
    """Compteur de limitation atomique avec récupération si la clé expire en course."""
    cache.add(key, 0, timeout=timeout)
    try:
        return cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=timeout)
        return 1


@ensure_csrf_cookie
@require_http_methods(["GET", "POST"])
def checkout(request):
    async_update = request.method == "POST" and request.headers.get("X-Checkout-Update") == "1"
    preserve_fields = request.POST.get("checkout_fields_present") == "1"
    editing = async_update or (preserve_fields and request.POST.get("promo_action") in {"apply", "remove"})
    promo_notice, promo_error = "", ""
    if not _cart_state(request) and not async_update:
        messages.info(request, "Votre panier est vide. Choisissez un article pour commencer votre commande.")
        return redirect("shop:catalog")
    cart_items, subtotal, cart_error = [], None, ""
    try:
        lines, _, subtotal = validated_cart(request)
        cart_items = [{**details, "quantity": quantity} for details, quantity in lines]
    except CheckoutProblem as exc:
        cart_error = str(exc)

    if request.method == "POST" and request.POST.get("promo_action") in {"apply", "remove"}:
        action = request.POST.get("promo_action")
        request.session.pop("checkout_promo_notice", None)
        request.session.pop("checkout_promo_error", None)
        if action == "remove":
            request.session.pop("checkout_promo_code", None)
            request.session.pop("checkout_attempt_key", None)
            promo_notice = "Code promo retiré."
        elif cart_error:
            promo_error = cart_error
        else:
            try:
                promo, _discount = apply_promo_code(request.POST.get("promo_code", ""), subtotal)
                if promo is None:
                    raise CheckoutProblem("Saisissez un code promo.")
                request.session["checkout_promo_code"] = promo.code
                request.session.pop("checkout_attempt_key", None)
                promo_notice = f"Code {promo.code} appliqué. La remise sera recalculée avant le paiement."
            except CheckoutProblem as exc:
                promo_error = str(exc)
        if not editing:
            request.session["checkout_promo_notice"] = promo_notice
            request.session["checkout_promo_error"] = promo_error
            return redirect("checkout:checkout")

    if not async_update and not editing:
        promo_notice = request.session.pop("checkout_promo_notice", "")
        promo_error = request.session.pop("checkout_promo_error", "")
    promo, promo_discount = None, Decimal("0.00")
    if subtotal is not None and request.session.get("checkout_promo_code"):
        try:
            promo, promo_discount = apply_promo_code(request.session["checkout_promo_code"], subtotal)
        except CheckoutProblem as exc:
            promo_error = str(exc)
            promo_notice = ""
            if not async_update:
                request.session.pop("checkout_promo_code", None)
                request.session.pop("checkout_attempt_key", None)
    discounted_subtotal = max(Decimal("0.00"), subtotal - promo_discount) if subtotal is not None else None
    if editing:
        # Valeurs limitées aux champs du formulaire, uniquement pour cette réponse.
        # Aucun brouillon de coordonnées dans la session, les URL ou les journaux.
        initial = {}
        if preserve_fields:
            for name, field in CheckoutForm.base_fields.items():
                if name in {"billing_same_as_shipping", "accept_terms"}:
                    initial[name] = request.POST.get(name) in {"on", "true", "1", "yes"}
                else:
                    initial[name] = request.POST.get(name, "")
        if async_update:
            initial["shipping_method"] = request.POST.get("shipping_method", "")
        form = CheckoutForm(initial=initial, subtotal=discounted_subtotal)
    else:
        form = CheckoutForm(request.POST or None, subtotal=discounted_subtotal)
    initial_method = "free" if discounted_subtotal is not None and discounted_subtotal >= FREE_SHIPPING_THRESHOLD else "standard"
    selected_method = form["shipping_method"].value()
    if selected_method not in dict(form.fields["shipping_method"].choices):
        selected_method = initial_method
    estimated_shipping = shipping_price(selected_method, discounted_subtotal) if discounted_subtotal is not None else None
    estimated_total = discounted_subtotal + estimated_shipping if discounted_subtotal is not None else None
    if request.method == "POST" and not editing:
        if not form.is_valid():
            pass
        elif not public_information()["sales_ready"]:
            form.add_error(None, SALES_UNAVAILABLE)
        elif cart_error:
            form.add_error(None, cart_error)
        elif not stripe_configured():
            form.add_error(None, "Le paiement Stripe n’est pas configuré. Aucun paiement ne sera simulé et aucune commande ne sera marquée comme payée.")
        else:
            raw_key = request.session.get("checkout_attempt_key")
            try:
                checkout_key = uuid.UUID(raw_key) if raw_key else uuid.uuid4()
            except (ValueError, TypeError):
                checkout_key = uuid.uuid4()
            request.session["checkout_attempt_key"] = str(checkout_key)
            order = None
            try:
                order, reused = create_order_and_reserve(request, form, checkout_key)
                if reused and order.stripe_session_id:
                    stripe.api_key = os.environ["STRIPE_SECRET_KEY"].strip()
                    session = stripe.checkout.Session.retrieve(order.stripe_session_id)
                    if session.status == "open" and session.url:
                        request.session.pop(CART_SESSION_KEY, None)
                        return redirect(session.url)
                    if session.status == "complete":
                        return redirect(f"{reverse('checkout:result', kwargs={'public_id': order.public_id})}?session_id={session.id}")
                    if session.status == "expired":
                        with transaction.atomic():
                            locked = Order.objects.select_for_update().get(pk=order.pk)
                            release_reserved_stock(locked)
                            locked.status = Order.EXPIRED
                            locked.commercial_status = Order.COMMERCIAL_CANCELLED
                            locked.save(update_fields=["stock_reserved", "status", "commercial_status", "updated_at"])
                        if not request.session.get(CART_SESSION_KEY):
                            request.session[CART_SESSION_KEY] = order.cart_snapshot or {}
                        request.session.pop("checkout_attempt_key", None)
                        form.add_error(None, "Cette session de paiement a expiré. Vérifiez le panier puis recommencez.")
                    else:
                        form.add_error(None, "La session de paiement n’est pas disponible. Réessayez ou contactez le support.")
                else:
                    session = create_stripe_session(order)
                    # Le panier est masqué pendant le paiement; son instantané permet de le restaurer en cas d’annulation.
                    request.session.pop(CART_SESSION_KEY, None)
                    return redirect(session.url)
            except CheckoutProblem as exc:
                if order and order.pk and not order.stripe_session_id:
                    with transaction.atomic():
                        locked = Order.objects.select_for_update().get(pk=order.pk)
                        release_reserved_stock(locked)
                        locked.status = Order.CANCELLED
                        locked.commercial_status = Order.COMMERCIAL_CANCELLED
                        locked.save(update_fields=["stock_reserved", "status", "commercial_status", "updated_at"])
                        locked.payment_attempts.filter(status__in=[PaymentAttempt.CREATED, PaymentAttempt.OPEN]).update(status=PaymentAttempt.FAILED)
                    if not request.session.get(CART_SESSION_KEY):
                        request.session[CART_SESSION_KEY] = order.cart_snapshot or {}
                request.session.pop("checkout_attempt_key", None)
                form.add_error(None, str(exc))
            except stripe.error.StripeError:
                logger.warning("Stripe retrieval failed during checkout retry")
                form.add_error(None, "Impossible de reprendre cette session de paiement. Réessayez dans quelques instants.")
    context = {
        "form": form, "cart_items": cart_items, "subtotal": subtotal,
        "promo": promo, "promo_discount": promo_discount, "discounted_subtotal": discounted_subtotal,
        "promo_notice": promo_notice, "promo_error": promo_error,
        "estimated_total": estimated_total, "estimated_shipping": estimated_shipping,
        "free_shipping_threshold": str(FREE_SHIPPING_THRESHOLD),
        "standard_shipping": str(SHIPPING_PRICES["standard"]),
        "express_shipping": str(SHIPPING_PRICES["express"]),
        "stripe_configured": stripe_configured(), "cart_error": cart_error,
        "free_shipping": discounted_subtotal is not None and discounted_subtotal >= FREE_SHIPPING_THRESHOLD,
        "shipping_pending": preserve_fields and not ShippingQuoteForm(request.POST).is_valid(),
    }
    if async_update:
        # Cette validation ne dépend ni du nom, ni des autres coordonnées.
        quote_form = ShippingQuoteForm(request.POST)
        quote_valid = quote_form.is_valid() and not cart_error and bool(cart_items)
        options = []
        if quote_valid:
            for method, label in form.fields["shipping_method"].choices:
                amount = shipping_price(method, discounted_subtotal)
                options.append({"method": method, "label": label, "amount": f"{amount:.2f}",
                                "total": f"{discounted_subtotal + amount:.2f}"})
        context["shipping_pending"] = not quote_valid
        response = JsonResponse({
            "summary_html": render_to_string("checkout/_summary.html", context, request=request),
            "options": options, "quote_valid": quote_valid,
            "errors": quote_form.errors.get_json_data(), "cart_error": cart_error,
            "can_pay": quote_valid and public_information()["sales_ready"] and stripe_configured(),
            "promo_error": promo_error,
        })
    else:
        response = render(request, "checkout.html", context)
    response["Cache-Control"] = "private, no-store"
    return response


@require_GET
def shipping_quote(request):
    """Tarifs indicatifs issus du panier et des règles serveur, jamais du sous-total client."""
    country = request.GET.get("country", "")[:3]
    postal_code = request.GET.get("postal_code", "").strip()[:21]
    if country not in dict(COUNTRIES) or not postal_code or len(postal_code) > 20:
        return JsonResponse({"error": "Renseignez un pays et un code postal valides."}, status=400)
    try:
        _, _, subtotal = validated_cart(request)
        promo_code = request.session.get("checkout_promo_code", "")
        _, discount = apply_promo_code(promo_code, subtotal)
    except CheckoutProblem as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    discounted = max(Decimal("0.00"), subtotal - discount)
    form = CheckoutForm(subtotal=discounted)
    options = []
    for method, label in form.fields["shipping_method"].choices:
        fee = shipping_price(method, discounted)
        options.append({
            "method": method, "label": label, "amount": f"{fee:.2f}",
            "total": f"{discounted + fee:.2f}",
        })
    response = JsonResponse({"options": options, "discounted_subtotal": f"{discounted:.2f}"})
    response["Cache-Control"] = "no-store"
    return response


@require_GET
def order_result(request, public_id):
    order = get_object_or_404(Order.objects.prefetch_related("lines"), public_id=public_id)
    session_id = request.GET.get("session_id", "")
    if session_id and session_id != order.stripe_session_id:
        return HttpResponseNotFound("Commande introuvable.")

    # UUID seul ne suffit pas à autoriser l’accès à une commande invitée.
    owns_order = bool(request.user.is_authenticated and order.customer_id == request.user.pk)
    checkout_key_matches = request.session.get("checkout_attempt_key", "") == str(order.checkout_key)
    stripe_return_matches = bool(session_id and session_id == order.stripe_session_id)
    if not (owns_order or checkout_key_matches or stripe_return_matches):
        return HttpResponseNotFound("Commande introuvable.")

    cancelled_return = request.GET.get("cancelled") == "1"
    # Le navigateur ne confirme jamais le paiement; seul le webhook signé le fait.
    if order.status == Order.PAID:
        # Effacer uniquement le panier qui a servi à cette commande. Si le client
        # a commencé une nouvelle sélection entre-temps, ne pas la supprimer.
        current_cart = _cart_state(request)
        if not current_cart or current_cart == (order.cart_snapshot or {}):
            request.session.pop(CART_SESSION_KEY, None)
        request.session.pop("checkout_attempt_key", None)
        request.session.pop("checkout_promo_code", None)
    elif order.status in (Order.CANCELLED, Order.EXPIRED):
        if not request.session.get(CART_SESSION_KEY):
            request.session[CART_SESSION_KEY] = order.cart_snapshot or {}
        request.session.pop("checkout_attempt_key", None)
    elif cancelled_return:
        if not request.session.get(CART_SESSION_KEY):
            request.session[CART_SESSION_KEY] = order.cart_snapshot or {}
        else:
            request.session.pop("checkout_attempt_key", None)

    response = render(request, "checkout_result.html", {"order": order, "cancelled_return": cancelled_return})
    response["Cache-Control"] = "private, no-store"
    response["Referrer-Policy"] = "no-referrer"
    return response


@csrf_exempt
@require_POST
def stripe_webhook(request):
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()
    signature = request.headers.get("Stripe-Signature", "")
    if not secret or not signature:
        return HttpResponseBadRequest("Webhook Stripe non configuré.")
    try:
        event = stripe.Webhook.construct_event(request.body, signature, secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponseBadRequest("Signature webhook invalide.")
    try:
        process_stripe_event(event)
    except RetryableWebhookError:
        # Une réponse 5xx laisse Stripe réessayer après la sauvegarde de la commande.
        return HttpResponse(status=500)
    except Exception:
        logger.exception("Stripe webhook processing failed; Stripe may retry the event")
        return HttpResponse(status=500)
    return HttpResponse(status=200)


@ensure_csrf_cookie
@require_http_methods(["GET", "POST"])
def order_tracking_lookup(request):
    """Recherche une commande à partir de sa référence publique, sans compte client."""
    if request.method == "POST":
        remote_addr = request.META.get("REMOTE_ADDR", "unknown")
        rate_key = "order-tracking-lookup:" + hashlib.sha256(remote_addr.encode("utf-8")).hexdigest()
        attempts = _increment_rate_limit(rate_key, 300)
        if attempts > 10:
            return render(request, "order_tracking_lookup.html", {
                "error": "Trop de tentatives. Réessayez dans quelques minutes.",
            }, status=429)

        reference = request.POST.get("reference", "").strip().removeprefix("#").strip()
        try:
            public_id = uuid.UUID(reference)
        except (ValueError, AttributeError, TypeError):
            public_id = None

        if public_id is not None and Order.objects.filter(public_id=public_id).exists():
            return redirect("checkout:tracking", public_id=public_id)

        return render(request, "order_tracking_lookup.html", {
            "error": "Référence introuvable. Vérifiez la référence reçue par e-mail.",
        }, status=200)

    return render(request, "order_tracking_lookup.html")


@require_GET
def order_tracking(request, public_id):
    """La référence UUID agit comme un secret de capacité ; aucun compte client requis."""
    order = Order.objects.prefetch_related(
        "lines", "shipments__events", "return_requests__lines__order_line"
    ).filter(public_id=public_id).first()
    if order is None:
        remote_addr = request.META.get("REMOTE_ADDR", "unknown")
        rate_key = "order-tracking-invalid:" + hashlib.sha256(remote_addr.encode("utf-8")).hexdigest()
        attempts = _increment_rate_limit(rate_key, 300)
        if attempts > 30:
            return HttpResponse("Trop de requêtes. Réessayez dans quelques minutes.", status=429)
        raise Http404

    response = render(request, "order_tracking.html", {"order": order})
    response["Referrer-Policy"] = "same-origin"
    response["Cache-Control"] = "private, no-store"
    return response

@require_POST
def order_return_request(request, public_id):
    """Enregistre une demande de retour depuis la référence publique de commande."""
    order = get_object_or_404(Order, public_id=public_id)
    if order.status != Order.PAID:
        raise Http404

    remote_addr = request.META.get("REMOTE_ADDR", "unknown")
    rate_material = f"{remote_addr}:{public_id}".encode("utf-8")
    rate_key = "order-return-submit:" + hashlib.sha256(rate_material).hexdigest()
    attempts = _increment_rate_limit(rate_key, 900)
    if attempts > 5:
        order = Order.objects.prefetch_related(
            "lines", "shipments__events", "return_requests__lines__order_line"
        ).get(pk=order.pk)
        response = render(request, "order_tracking.html", {
            "order": order,
            "return_error": "Trop de demandes depuis cette connexion. Réessayez dans quelques minutes.",
        }, status=429)
        response["Cache-Control"] = "private, no-store"
        response["Referrer-Policy"] = "same-origin"
        return response
    lines = {}
    for line in order.lines.all():
        raw = request.POST.get(f"line_{line.pk}", "").strip()
        if raw:
            lines[line.pk] = raw
    try:
        create_return_request(
            order.pk, reason_category=request.POST.get("reason_category", ""),
            reason=request.POST.get("reason", ""), lines=lines,
            customer=None, customer_note=request.POST.get("customer_note", ""),
        )
    except LifecycleProblem as exc:
        order = Order.objects.prefetch_related(
            "lines", "shipments__events", "return_requests__lines__order_line"
        ).get(pk=order.pk)
        response = render(request, "order_tracking.html", {
            "order": order, "return_error": str(exc),
        }, status=400)
        response["Cache-Control"] = "private, no-store"
        response["Referrer-Policy"] = "same-origin"
        return response
    return redirect("checkout:tracking", public_id=order.public_id)
