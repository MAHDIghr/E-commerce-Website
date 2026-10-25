"""Parcours de commande et endpoint webhook Stripe."""
import logging
import os
import uuid
import stripe
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from shop.views import CART_SESSION_KEY
from .forms import CheckoutForm
from .models import Order, PaymentAttempt
from .services import CheckoutProblem, create_order_and_reserve, create_stripe_session, process_stripe_event, release_reserved_stock, stripe_configured, validated_cart

logger = logging.getLogger(__name__)


def checkout(request):
    form = CheckoutForm(request.POST or None)
    cart_items, subtotal, cart_error = [], None, ""
    try:
        lines, _, subtotal = validated_cart(request)
        cart_items = [{**details, "quantity": quantity} for details, quantity in lines]
    except CheckoutProblem as exc:
        cart_error = str(exc)
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
                        return redirect(session.url)
                    if session.status == "complete":
                        return redirect(f"{reverse('checkout:result', kwargs={'public_id': order.public_id})}?session_id={session.id}")
                    if session.status == "expired":
                        with transaction.atomic():
                            locked = Order.objects.select_for_update().get(pk=order.pk)
                            release_reserved_stock(locked)
                            locked.status = Order.EXPIRED
                            locked.save(update_fields=["stock_reserved", "status", "updated_at"])
                        request.session.pop("checkout_attempt_key", None)
                        form.add_error(None, "Cette session de paiement a expiré. Vérifiez le panier puis recommencez.")
                    else:
                        form.add_error(None, "La session de paiement n’est pas disponible. Réessayez ou contactez le support.")
                else:
                    session = create_stripe_session(order)
                    request.session.pop(CART_SESSION_KEY, None)
                    request.session.pop("checkout_attempt_key", None)
                    return redirect(session.url)
            except CheckoutProblem as exc:
                if order and order.pk and not order.stripe_session_id:
                    with transaction.atomic():
                        locked = Order.objects.select_for_update().get(pk=order.pk)
                        release_reserved_stock(locked)
                        locked.status = Order.CANCELLED
                        locked.save(update_fields=["stock_reserved", "status", "updated_at"])
                        locked.payment_attempts.filter(status__in=[PaymentAttempt.CREATED, PaymentAttempt.OPEN]).update(status=PaymentAttempt.FAILED)
                request.session.pop("checkout_attempt_key", None)
                form.add_error(None, str(exc))
            except stripe.error.StripeError:
                logger.warning("Stripe retrieval failed during checkout retry")
                form.add_error(None, "Impossible de reprendre cette session de paiement. Réessayez dans quelques instants.")
    return render(request, "checkout.html", {
        "form": form, "cart_items": cart_items, "subtotal": subtotal,
        "free_shipping_threshold": os.environ.get("CHECKOUT_FREE_SHIPPING_THRESHOLD", "80.00"),
        "standard_shipping": os.environ.get("CHECKOUT_STANDARD_SHIPPING", "4.90"),
        "express_shipping": os.environ.get("CHECKOUT_EXPRESS_SHIPPING", "9.90"),
        "stripe_configured": stripe_configured(), "cart_error": cart_error,
    })


@require_GET
def order_result(request, public_id):
    order = get_object_or_404(Order.objects.prefetch_related("lines"), public_id=public_id)
    session_id = request.GET.get("session_id", "")
    if session_id and session_id != order.stripe_session_id:
        return HttpResponseNotFound("Commande introuvable.")
    # Cette page ne modifie jamais le statut : seul le webhook signé confirme le paiement.
    return render(request, "checkout_result.html", {"order": order, "cancelled_return": request.GET.get("cancelled") == "1"})


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
    except Exception:
        logger.exception("Stripe webhook processing failed; Stripe may retry the event")
        return HttpResponse(status=500)
    return HttpResponse(status=200)
