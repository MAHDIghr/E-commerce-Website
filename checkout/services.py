"""Services métier Stripe Checkout. Le serveur est la source de vérité des montants."""
import logging
import os
from decimal import Decimal, ROUND_HALF_UP
from urllib.parse import urljoin, urlparse

import stripe
from django.conf import settings
from django.core import signing
from django.db import transaction
from django.db.models import F
from django.urls import reverse
from django.utils import timezone

from product.models import ProductVariant
from shop.views import _cart_key_parts, _cart_state
from .models import Order, OrderLine, PaymentAttempt, PromoCode, StripeWebhookEvent, OrderEvent, OrderNotification, Refund

logger = logging.getLogger(__name__)
CENT = Decimal("0.01")
SHIPPING = {
    "standard": Decimal(os.environ.get("CHECKOUT_STANDARD_SHIPPING", "4.90")).quantize(CENT),
    "express": Decimal(os.environ.get("CHECKOUT_EXPRESS_SHIPPING", "9.90")).quantize(CENT),
}
FREE_SHIPPING_THRESHOLD = Decimal(os.environ.get("CHECKOUT_FREE_SHIPPING_THRESHOLD", "80.00")).quantize(CENT)


class CheckoutProblem(Exception):
    """Erreur métier contrôlée, affichable au client."""


class RetryableWebhookError(Exception):
    """Événement valide reçu avant que sa session soit associée à une commande."""


def money(value):
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def stripe_configured():
    return bool(os.environ.get("STRIPE_SECRET_KEY", "").strip()
                and os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()
                and os.environ.get("SITE_BASE_URL", "").strip())


def stripe_currency():
    value = os.environ.get("STRIPE_CURRENCY", "eur").strip().lower()
    return value if len(value) == 3 and value.isalpha() else "eur"


def apply_promo_code(code, subtotal, email="", *, lock=False):
    """Valide le code en base et calcule une remise monétaire côté serveur."""
    normalized = (code or "").strip().upper()
    if not normalized:
        return None, Decimal("0.00")
    if len(normalized) > 32 or not normalized.isascii():
        raise CheckoutProblem("Ce code promo n’est pas valide.")
    promo_query = PromoCode.objects.filter(code=normalized, is_active=True)
    if lock:
        promo_query = promo_query.select_for_update()
    promo = promo_query.first()
    now = timezone.now()
    if not promo or (promo.starts_at and promo.starts_at > now) or (promo.ends_at and promo.ends_at <= now):
        raise CheckoutProblem("Ce code promo est invalide ou n’est plus disponible.")
    if subtotal < promo.minimum_subtotal:
        raise CheckoutProblem(f"Ce code nécessite un sous-total d’au moins {promo.minimum_subtotal:.2f} €.")
    if promo.once_per_email and email and Order.objects.filter(
        email__iexact=email.strip(), promo_code_snapshot=promo.code,
        status__in=(Order.PENDING, Order.AWAITING, Order.PAID, Order.REVIEW),
    ).exists():
        raise CheckoutProblem("Ce code de bienvenue a déjà été utilisé avec cette adresse e-mail.")
    discount = money(subtotal * promo.value / Decimal("100")) if promo.discount_type == PromoCode.PERCENT else money(promo.value)
    if promo.maximum_discount is not None:
        discount = min(discount, money(promo.maximum_discount))
    discount = min(discount, money(subtotal))
    if discount <= 0:
        raise CheckoutProblem("Ce code ne peut pas être appliqué à cette commande.")
    return promo, discount


def shipping_price(method, subtotal):
    if subtotal >= FREE_SHIPPING_THRESHOLD:
        if method != "free":
            raise CheckoutProblem("La livraison est offerte pour ce montant. Rechargez le checkout puis réessayez.")
        return Decimal("0.00")
    if method not in SHIPPING:
        raise CheckoutProblem("Le mode de livraison sélectionné n’est pas valide.")
    return SHIPPING[method]


def validated_cart(request):
    """Revalide chaque ligne du panier session via le catalogue et les offres en base."""
    from shop.views import _line_details
    state = _cart_state(request)
    if not state:
        raise CheckoutProblem("Votre panier est vide. Ajoutez un article avant de continuer.")
    lines, usage = [], {}
    for key, quantity in state.items():
        try:
            variant_id, offer_id, selected_ids = _cart_key_parts(key)
        except (TypeError, ValueError):
            raise CheckoutProblem("Votre panier contient une ligne invalide. Vérifiez-le avant de continuer.")
        details = _line_details(variant_id, offer_id, quantity, selected_ids)
        if details is None or not details["available"]:
            raise CheckoutProblem("Un article, une offre ou un accessoire inclus n’est plus disponible. Vérifiez votre panier.")
        for variant_id_key, required in details["stock_requirements"].items():
            pk = int(variant_id_key)
            usage[pk] = usage.get(pk, 0) + int(required)
        lines.append((details, quantity))
    if len(lines) > 30:
        raise CheckoutProblem("Votre panier contient trop de lignes.")
    subtotal = money(sum((Decimal(details["line_total"]) for details, _ in lines), Decimal("0.00")))
    return lines, usage, subtotal


def _snapshot_components(details):
    return [
        {"name": c["name"], "variant": c["variant_name"], "variant_id": c["variant_id"],
         "quantity_per_offer": c["quantity"], "unit_price": "0.00", "is_gift": True}
        for c in details["components"]
    ]


def create_order_and_reserve(request, form, checkout_key):
    """Crée l'instantané et réserve les stocks avec mises à jour conditionnelles atomiques."""
    with transaction.atomic():
        existing = Order.objects.select_for_update().filter(checkout_key=checkout_key).first()
        if existing:
            if existing.status in (Order.CANCELLED, Order.EXPIRED, Order.REVIEW):
                raise CheckoutProblem("Cette tentative de commande n’est plus réutilisable. Rechargez la page et réessayez.")
            return existing, bool(existing.stripe_session_id)

        lines, usage, subtotal = validated_cart(request)
        try:
            promo, discount = apply_promo_code(
                request.session.get("checkout_promo_code", ""), subtotal,
                form.cleaned_data["email"], lock=True,
            )
        except CheckoutProblem:
            request.session.pop("checkout_promo_code", None)
            raise
        discounted_subtotal = money(subtotal - discount)
        shipping = shipping_price(form.cleaned_data["shipping_method"], discounted_subtotal)
        total = money(discounted_subtotal + shipping)
        variant_ids = sorted(usage)
        locked = {v.pk: v for v in ProductVariant.objects.select_for_update().filter(pk__in=variant_ids).order_by("pk")}
        if len(locked) != len(variant_ids):
            raise CheckoutProblem("Le stock a changé. Vérifiez votre panier.")
        for pk, required in usage.items():
            if locked[pk].stock_quantity < required:
                raise CheckoutProblem("Le stock vient de changer. Réduisez les quantités puis réessayez.")

        order = Order.objects.create(
            checkout_key=checkout_key,
            cart_snapshot=dict(_cart_state(request)),
            customer=request.user if request.user.is_authenticated else None,
            email=form.cleaned_data["email"], full_name=form.cleaned_data["full_name"],
            phone=form.cleaned_data["phone"], address_line1=form.cleaned_data["address_line1"],
            address_line2=form.cleaned_data["address_line2"], postal_code=form.cleaned_data["postal_code"],
            city=form.cleaned_data["city"], country=form.cleaned_data["country"],
            shipping_method=form.cleaned_data["shipping_method"], currency=stripe_currency(),
            subtotal=subtotal, promo_code_snapshot=promo.code if promo else "",
            discount_amount=discount, shipping_amount=shipping, total=total, stock_reserved=True,
            stock_requirements_snapshot={str(pk): qty for pk, qty in usage.items()},
        )
        for details, quantity in lines:
            OrderLine.objects.create(
                order=order, product_id=details["product_id"], variant_id=details["variant_id"],
                offer_id_snapshot=details["offer_id"], product_name=details["name"],
                variant_name=details["variant_name"], quantity=quantity,
                unit_price=money(details["unit_price"]), line_total=money(details["line_total"]),
                components_snapshot=_snapshot_components(details),
            )
        for pk in variant_ids:
            updated = ProductVariant.objects.filter(pk=pk, stock_quantity__gte=usage[pk]).update(
                stock_quantity=F("stock_quantity") - usage[pk])
            if updated != 1:
                raise CheckoutProblem("Le stock vient de changer. Vérifiez votre panier puis réessayez.")
        PaymentAttempt.objects.create(order=order, amount=total, currency=order.currency)
        return order, False


def release_reserved_stock(order):
    """Libère une réservation au plus une fois, y compris les composants offerts."""
    if not order.stock_reserved:
        return
    for variant_id, quantity in (order.stock_requirements_snapshot or {}).items():
        ProductVariant.objects.filter(pk=int(variant_id)).update(stock_quantity=F("stock_quantity") + int(quantity))
    order.stock_reserved = False


def create_stripe_session(order, request=None):
    """Crée une session hébergée depuis l'instantané immuable de la commande."""
    if not stripe_configured():
        raise CheckoutProblem("Le paiement en ligne n’est pas configuré. Aucun paiement ne sera simulé.")
    secret_key = os.environ["STRIPE_SECRET_KEY"].strip()
    live_mode = os.environ.get("STRIPE_LIVE_MODE", "False").strip().lower() in {"1", "true", "yes", "on"}
    if (live_mode and not secret_key.startswith("sk_live_")) or (not live_mode and not secret_key.startswith("sk_test_")):
        raise CheckoutProblem("La clé Stripe ne correspond pas au mode configuré. Vérifiez la configuration hors du dépôt.")
    stripe.api_key = secret_key
    base_url = os.environ["SITE_BASE_URL"].rstrip("/") + "/"
    parsed = urlparse(base_url)
    if not parsed.netloc or parsed.scheme not in ("http", "https") or (not settings.DEBUG and parsed.scheme != "https"):
        raise CheckoutProblem("SITE_BASE_URL doit être un domaine canonique valide et utiliser HTTPS en production.")
    result_path = reverse("checkout:result", kwargs={"public_id": order.public_id})
    success_url = urljoin(base_url, result_path.lstrip("/")) + "?session_id={CHECKOUT_SESSION_ID}"
    cancel_url = urljoin(base_url, result_path.lstrip("/")) + "?cancelled=1"
    line_items = []
    for line in order.lines.all():
        gifts = [c for c in line.components_snapshot if c.get("is_gift")]
        description = "Inclus sans supplément : " + ", ".join(
            f'{gift["name"]} ({gift["variant"]})' for gift in gifts
        ) if gifts else ""
        unit_amount = int((line.unit_price * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        product_data = {"name": line.product_name[:250]}
        if description:
            product_data["description"] = description[:350]
        line_items.append({"price_data": {"currency": order.currency, "unit_amount": unit_amount,
                                          "product_data": product_data}, "quantity": line.quantity})
    if order.shipping_amount > 0:
        line_items.append({"price_data": {"currency": order.currency,
            "unit_amount": int(order.shipping_amount * 100),
            "product_data": {"name": f"Livraison {order.shipping_method}"}}, "quantity": 1})
    try:
        discounts = []
        if order.discount_amount > 0:
            coupon = stripe.Coupon.create(
                name=f"Code promo {order.promo_code_snapshot}"[:40],
                amount_off=int((order.discount_amount * 100).quantize(Decimal("1"))),
                currency=order.currency, duration="once",
                idempotency_key=f"mlc-promo-{order.checkout_key}",
            )
            discounts = [{"coupon": coupon.id}]
        session = stripe.checkout.Session.create(
            mode="payment", line_items=line_items, discounts=discounts,
            customer_email=order.email,
            client_reference_id=str(order.public_id),
            metadata={"order_id": str(order.pk), "order_public_id": str(order.public_id)},
            payment_intent_data={"metadata": {"order_id": str(order.pk), "order_public_id": str(order.public_id)}},
            success_url=success_url, cancel_url=cancel_url, billing_address_collection="auto",
            idempotency_key=f"mlc-checkout-{order.checkout_key}",
        )
    except stripe.error.StripeError as exc:
        logger.warning("Stripe Checkout creation failed for order %s (%s)", order.public_id, type(exc).__name__)
        raise CheckoutProblem("Le service de paiement est momentanément indisponible. Réessayez dans quelques instants.") from exc
    with transaction.atomic():
        locked_order = Order.objects.select_for_update().get(pk=order.pk)
        locked_order.stripe_session_id = session.id
        locked_order.save(update_fields=["stripe_session_id", "updated_at"])
        locked_order.payment_attempts.filter(status=PaymentAttempt.CREATED).update(
            status=PaymentAttempt.OPEN, stripe_session_id=session.id)
    return session


def _queue_order_email(order, event_key, subject, message):
    """Persiste l'e-mail avant de tenter l'envoi; l'échec n'annule pas le paiement."""
    notification, _created = OrderNotification.objects.get_or_create(
        order=order, event_key=event_key, recipient=order.email, channel="email",
        defaults={"payload": {"subject": subject, "message": message}},
    )
    if notification.status != OrderNotification.SENT:
        def deliver():
            from .lifecycle import deliver_notification
            try:
                deliver_notification(notification.pk)
            except Exception:
                logger.exception("Order email delivery failed for notification %s", notification.pk)
        transaction.on_commit(deliver, robust=True)
    return notification


def process_stripe_event(event):
    """Traite un événement signé une seule fois et protège les transitions de commande."""
    event_id, event_type = event["id"], event["type"]
    obj = event["data"]["object"]
    with transaction.atomic():
        if StripeWebhookEvent.objects.filter(event_id=event_id).exists():
            return "duplicate"
        StripeWebhookEvent.objects.create(event_id=event_id, event_type=event_type)
        # Stripe refund events can arrive independently of Checkout Session events.
        if event_type in ("refund.updated", "refund.failed"):
            refund = Refund.objects.select_for_update().filter(stripe_refund_id=obj.get("id", "")).first()
            if not refund:
                local_refund_id = (obj.get("metadata") or {}).get("local_refund_id")
                if local_refund_id:
                    refund = Refund.objects.select_for_update().filter(pk=local_refund_id).first()
                    if refund and not refund.stripe_refund_id:
                        refund.stripe_refund_id = obj.get("id", "")
                        refund.save(update_fields=["stripe_refund_id"])
                if not refund:
                    if local_refund_id:
                        raise RetryableWebhookError(f"Unknown local refund for Stripe refund {obj.get('id', '')}")
                    return "ignored"
            if obj.get("currency") and obj.get("currency").lower() != refund.currency.lower():
                refund.status = Refund.FAILED
                refund.failure_reason = "La devise du remboursement Stripe ne correspond pas à la demande locale."
                refund.save(update_fields=["status", "failure_reason"])
                return "mismatch"
            if obj.get("amount") is not None and int(obj["amount"]) != int(refund.amount * 100):
                refund.status = Refund.FAILED
                refund.failure_reason = "Le montant du remboursement Stripe ne correspond pas à la demande locale."
                refund.save(update_fields=["status", "failure_reason"])
                return "mismatch"
            previous_status = refund.status
            if previous_status != Refund.SUCCEEDED:
                if obj.get("status") == "succeeded":
                    refund.status = Refund.SUCCEEDED
                    refund.confirmed_at = timezone.now()
                    refund.failure_reason = ""
                elif obj.get("status") == "failed" or event_type == "refund.failed":
                    refund.status = Refund.FAILED
                    refund.failure_reason = str(obj.get("failure_reason") or "Stripe a signalé l'échec du remboursement.")[:2000]
                elif previous_status != Refund.FAILED:
                    refund.status = Refund.PROCESSING
                refund.save(update_fields=["status", "confirmed_at", "failure_reason"])
            if refund.status == Refund.SUCCEEDED and previous_status != Refund.SUCCEEDED:
                OrderEvent.objects.create(
                    order=refund.order, event_type="refund_confirmed", source="stripe",
                    external_reference=refund.stripe_refund_id,
                    metadata={"refund_id": refund.pk, "amount": str(refund.amount)},
                )
                _queue_order_email(
                    refund.order, f"refund_confirmed_{refund.pk}",
                    f"Remboursement confirmé pour la commande {str(refund.order.public_id)[:8]}",
                    f"Bonjour {refund.order.full_name},\n\nStripe a confirmé un remboursement de {refund.amount} {refund.currency.upper()}.\nRéférence de commande : {refund.order.public_id}\n\nMy Line Collection",
                )
            return "processed"
        if obj.get("object") != "checkout.session":
            return "ignored"
        session_id = obj.get("id", "")
        order = Order.objects.select_for_update().filter(stripe_session_id=session_id).first()
        if not order:
            # Ne pas enregistrer définitivement cet événement : Stripe peut livrer le
            # webhook avant la sauvegarde du session_id. Le 500 déclenche une nouvelle tentative.
            logger.warning("Stripe event %s references an unknown Checkout Session; requesting retry", event_type)
            raise RetryableWebhookError(f"Unknown Checkout Session: {session_id}")
        payment = order.payment_attempts.select_for_update().filter(stripe_session_id=session_id).first()
        if event_type in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
            expected_cents = int((order.total * 100).quantize(Decimal("1")))
            if obj.get("currency", "").lower() != order.currency or obj.get("amount_total") != expected_cents:
                order.status = Order.REVIEW
                order.save(update_fields=["status", "updated_at"])
                if payment:
                    payment.status = PaymentAttempt.REVIEW
                    payment.save(update_fields=["status", "updated_at"])
                logger.error("Stripe amount/currency mismatch for order %s", order.public_id)
                return "mismatch"
            paid = obj.get("payment_status") == "paid" or event_type.endswith("async_payment_succeeded")
            if paid:
                # Distinct Stripe event IDs may describe the same successful payment.
                if order.status == Order.PAID and order.stripe_payment_intent_id == (obj.get("payment_intent") or order.stripe_payment_intent_id):
                    if payment and payment.status != PaymentAttempt.SUCCEEDED:
                        payment.status = PaymentAttempt.SUCCEEDED
                        payment.save(update_fields=["status", "updated_at"])
                    return "already_paid"
                if order.stock_reserved and order.status not in (Order.CANCELLED, Order.EXPIRED, Order.REVIEW):
                    order.status = Order.PAID
                    order.stock_reserved = False
                    order.stock_committed = True
                    order.stripe_payment_intent_id = obj.get("payment_intent") or ""
                    order.save(update_fields=["status", "stock_reserved", "stock_committed", "stripe_payment_intent_id", "updated_at"])
                    if payment:
                        payment.status = PaymentAttempt.SUCCEEDED
                        payment.stripe_payment_intent_id = order.stripe_payment_intent_id
                        payment.save(update_fields=["status", "stripe_payment_intent_id", "updated_at"])
                    OrderEvent.objects.create(
                        order=order, event_type="payment_confirmed", source="stripe",
                        external_reference=event_id,
                        metadata={"payment_intent": order.stripe_payment_intent_id},
                    )
                    tracking_token = signing.dumps(
                        {"public_id": str(order.public_id), "email": order.email},
                        salt="checkout.order-tracking",
                    )
                    base_url = os.environ.get("SITE_BASE_URL", "").rstrip("/")
                    tracking_url = (
                        f"{base_url}{reverse('checkout:tracking', kwargs={'public_id': order.public_id})}?token={tracking_token}"
                        if base_url else "Contactez notre support pour obtenir votre lien de suivi sécurisé."
                    )
                    _queue_order_email(
                        order, "payment_confirmed",
                        f"Confirmation de commande {str(order.public_id)[:8]}",
                        f"Bonjour {order.full_name},\n\nNous avons confirmé le paiement de votre commande.\nRéférence : {order.public_id}\nMontant : {order.total} {order.currency.upper()}\n\nConsulter le suivi sécurisé : {tracking_url}\n\nMerci pour votre confiance,\nMy Line Collection",
                    )
                else:
                    order.status = Order.REVIEW
                    order.stripe_payment_intent_id = obj.get("payment_intent") or ""
                    order.save(update_fields=["status", "stripe_payment_intent_id", "updated_at"])
                    if payment:
                        payment.status = PaymentAttempt.REVIEW
                        payment.save(update_fields=["status", "stripe_payment_intent_id", "updated_at"])
                    logger.error("Late Stripe payment requires manual review for order %s", order.public_id)
            else:
                order.status = Order.AWAITING
                order.save(update_fields=["status", "updated_at"])
                if payment:
                    payment.status = PaymentAttempt.PROCESSING
                    payment.save(update_fields=["status", "updated_at"])
        elif event_type in ("checkout.session.async_payment_failed", "checkout.session.expired"):
            if order.status not in (Order.PAID, Order.REVIEW) and order.stock_reserved:
                release_reserved_stock(order)
                order.status = Order.EXPIRED if event_type.endswith("expired") else Order.CANCELLED
                order.save(update_fields=["status", "stock_reserved", "updated_at"])
                if payment:
                    payment.status = PaymentAttempt.EXPIRED if event_type.endswith("expired") else PaymentAttempt.FAILED
                    payment.save(update_fields=["status", "updated_at"])
                OrderEvent.objects.create(
                    order=order, event_type="payment_failed" if event_type.endswith("failed") else "payment_expired",
                    source="stripe", external_reference=event_id,
                )
                _queue_order_email(
                    order, "payment_failed" if event_type.endswith("failed") else "payment_expired",
                    f"Mise à jour de votre commande {str(order.public_id)[:8]}",
                    f"Bonjour {order.full_name},\n\nLe paiement de votre commande n'a pas abouti ou a expiré. Aucun paiement réussi n'est enregistré.\nRéférence : {order.public_id}\n\nMy Line Collection",
                )
        return "processed"
