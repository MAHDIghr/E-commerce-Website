"""Parcours de commande et endpoint webhook Stripe."""
import logging
import os
import uuid
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decimal import Decimal
import stripe
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.shortcuts import get_object_or_404, redirect, render
from django.core import signing
from django.http import Http404
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from shop.views import CART_SESSION_KEY, _cart_state
from .forms import CheckoutForm
from .models import Order, PaymentAttempt, ReturnRequest
from .lifecycle import create_return_request, LifecycleProblem
from .services import CheckoutProblem, RetryableWebhookError, apply_promo_code, create_order_and_reserve, create_stripe_session, process_stripe_event, release_reserved_stock, stripe_configured, validated_cart
from .lifecycle import LifecycleProblem, create_return_request

logger = logging.getLogger(__name__)


def checkout(request):
    cart_items, subtotal, cart_error = [], None, ""
    try:
        lines, _, subtotal = validated_cart(request)
        cart_items = [{**details, "quantity": quantity} for details, quantity in lines]
    except CheckoutProblem as exc:
        cart_error = str(exc)

    if request.method == "POST" and request.POST.get("promo_action") in {"apply", "remove"}:
        action = request.POST.get("promo_action")
        if action == "remove":
            request.session.pop("checkout_promo_code", None)
            request.session.pop("checkout_attempt_key", None)
            request.session["checkout_promo_notice"] = "Code promo retiré."
        elif cart_error:
            request.session["checkout_promo_notice"] = cart_error
        else:
            try:
                promo, _discount = apply_promo_code(request.POST.get("promo_code", ""), subtotal)
                request.session["checkout_promo_code"] = promo.code
                request.session.pop("checkout_attempt_key", None)
                request.session["checkout_promo_notice"] = f"Code {promo.code} appliqué. La remise sera recalculée avant le paiement."
            except CheckoutProblem as exc:
                request.session["checkout_promo_notice"] = str(exc)
        return redirect("checkout:checkout")

    promo_notice = request.session.pop("checkout_promo_notice", "")
    promo, promo_discount, promo_error = None, Decimal("0.00"), ""
    if subtotal is not None and request.session.get("checkout_promo_code"):
        try:
            promo, promo_discount = apply_promo_code(request.session["checkout_promo_code"], subtotal)
        except CheckoutProblem as exc:
            promo_error = str(exc)
            request.session.pop("checkout_promo_code", None)
    discounted_subtotal = max(Decimal("0.00"), subtotal - promo_discount) if subtotal is not None else None
    form = CheckoutForm(request.POST or None, subtotal=discounted_subtotal)
    if request.method == "POST":
        if not form.is_valid():
            pass
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
                            locked.save(update_fields=["stock_reserved", "status", "updated_at"])
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
                        locked.save(update_fields=["stock_reserved", "status", "updated_at"])
                        locked.payment_attempts.filter(status__in=[PaymentAttempt.CREATED, PaymentAttempt.OPEN]).update(status=PaymentAttempt.FAILED)
                    if not request.session.get(CART_SESSION_KEY):
                        request.session[CART_SESSION_KEY] = order.cart_snapshot or {}
                request.session.pop("checkout_attempt_key", None)
                form.add_error(None, str(exc))
            except stripe.error.StripeError:
                logger.warning("Stripe retrieval failed during checkout retry")
                form.add_error(None, "Impossible de reprendre cette session de paiement. Réessayez dans quelques instants.")
    return render(request, "checkout.html", {
        "form": form, "cart_items": cart_items, "subtotal": subtotal,
        "promo_code": promo, "promo_discount": promo_discount, "discounted_subtotal": discounted_subtotal,
        "promo_notice": promo_notice, "promo_error": promo_error,
        "free_shipping_threshold": os.environ.get("CHECKOUT_FREE_SHIPPING_THRESHOLD", "80.00"),
        "standard_shipping": os.environ.get("CHECKOUT_STANDARD_SHIPPING", "4.90"),
        "express_shipping": os.environ.get("CHECKOUT_EXPRESS_SHIPPING", "9.90"),
        "stripe_configured": stripe_configured(), "cart_error": cart_error,
        "free_shipping": discounted_subtotal is not None and discounted_subtotal >= Decimal(os.environ.get("CHECKOUT_FREE_SHIPPING_THRESHOLD", "80.00")),
    })


@require_GET
def order_result(request, public_id):
    order = get_object_or_404(Order.objects.prefetch_related("lines"), public_id=public_id)
    session_id = request.GET.get("session_id", "")
    if session_id and session_id != order.stripe_session_id:
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

    return render(request, "checkout_result.html", {"order": order, "cancelled_return": cancelled_return})


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


@require_GET
def order_tracking(request, public_id):
    token = request.GET.get("token", "").strip()
    if not token:
        raise Http404
    try:
        claims = signing.loads(token, salt="checkout.order-tracking", max_age=90 * 24 * 60 * 60)
    except signing.BadSignature:
        raise Http404
    if claims.get("public_id") != str(public_id) or not claims.get("email"):
        raise Http404
    order = get_object_or_404(
        Order.objects.prefetch_related("lines", "shipments__events", "return_requests__lines__order_line"),
        public_id=public_id, email__iexact=claims["email"],
    )
    return render(request, "checkout/order_tracking.html", {"order": order, "tracking_token": token})


@require_POST
def order_return_request(request, public_id):
    token = request.POST.get("token", "").strip()
    try:
        claims = signing.loads(token, salt="checkout.order-tracking", max_age=90 * 24 * 60 * 60)
    except signing.BadSignature:
        raise Http404
    if claims.get("public_id") != str(public_id) or not claims.get("email"):
        raise Http404
    order = get_object_or_404(Order, public_id=public_id, email__iexact=claims["email"])
    lines = {}
    for line in order.lines.all():
        raw = request.POST.get(f"line_{line.pk}", "").strip()
        if raw:
            lines[line.pk] = raw
    try:
        create_return_request(
            order.pk, reason_category=request.POST.get("reason_category", ""),
            reason=request.POST.get("reason", ""), lines=lines,
            customer=order.customer, customer_note=request.POST.get("customer_note", ""),
        )
    except LifecycleProblem as exc:
        return render(request, "checkout/order_tracking.html", {
            "order": order, "tracking_token": token, "return_error": str(exc),
        }, status=400)
    return redirect(f"{reverse('checkout:tracking', kwargs={'public_id': order.public_id})}?token={token}")


@login_required
@require_GET
def customer_orders(request):
    """Liste privée : une session authentifiée ne voit que ses propres commandes."""
    orders = Order.objects.filter(customer=request.user).prefetch_related("lines", "shipments").order_by("-created_at")
    return render(request, "checkout/my_orders.html", {"orders": orders})


@login_required
@require_GET
def customer_order_detail(request, public_id):
    """Détail et suivi accessibles uniquement au propriétaire authentifié."""
    order = get_object_or_404(
        Order.objects.filter(customer=request.user).prefetch_related(
            "lines", "shipments__events", "return_requests__lines__order_line",
            "refunds", "lifecycle_events",
        ),
        public_id=public_id,
    )
    return render(request, "checkout/customer_order_detail.html", {
        "order": order,
        "return_choices": ReturnRequest.REASONS,
    })


@login_required
@require_POST
def customer_return_request(request, public_id):
    """Crée une demande de retour sans jamais accepter un order_id fourni comme autorité."""
    order = get_object_or_404(Order.objects.filter(customer=request.user), public_id=public_id)
    quantities = {}
    for line in order.lines.all():
        raw = request.POST.get(f"line_{line.pk}", "").strip()
        if raw:
            quantities[line.pk] = raw
    try:
        return_request = create_return_request(
            order.pk,
            reason_category=request.POST.get("reason_category", "").strip(),
            reason=request.POST.get("reason", ""),
            customer_note=request.POST.get("customer_note", "")[:2000],
            lines=quantities,
            customer=request.user,
        )
    except (LifecycleProblem, ValueError) as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "Votre demande de retour a été enregistrée. Elle sera examinée par notre équipe.")
        return redirect("checkout:customer_order_detail", public_id=order.public_id)
    return redirect("checkout:customer_order_detail", public_id=order.public_id)
