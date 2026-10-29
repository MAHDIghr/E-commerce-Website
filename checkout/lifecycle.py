"""Services explicites pour les opérations du cycle de vie des commandes.

Les appels externes Stripe/e-mail sont séparés des transactions de base de données.
Les transporteurs restent manuels tant qu'aucune intégration réelle n'est configurée.
"""
import logging
import os
import uuid
from decimal import Decimal
from urllib.parse import urlparse

import stripe
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone

from product.models import ProductVariant

from .models import (
    Order, OrderEvent, OrderIncident, OrderNotification, Refund, ReturnLine,
    ReturnRequest, Shipment, ShipmentEvent, ShipmentLine,
)

logger = logging.getLogger(__name__)

SHIPMENT_TRANSITIONS = {
    Shipment.DRAFT: {Shipment.LABEL_CREATED, Shipment.READY},
    Shipment.LABEL_CREATED: {Shipment.READY},
    Shipment.READY: {Shipment.ACCEPTED},
    Shipment.ACCEPTED: {Shipment.IN_TRANSIT, Shipment.INCIDENT},
    Shipment.IN_TRANSIT: {Shipment.OUT_FOR_DELIVERY, Shipment.PICKUP_POINT, Shipment.DELIVERY_FAILED, Shipment.DELIVERED, Shipment.INCIDENT, Shipment.RETURNING, Shipment.LOST},
    Shipment.OUT_FOR_DELIVERY: {Shipment.DELIVERED, Shipment.DELIVERY_FAILED, Shipment.PICKUP_POINT, Shipment.INCIDENT},
    Shipment.DELIVERY_FAILED: {Shipment.IN_TRANSIT, Shipment.PICKUP_POINT, Shipment.RETURNING, Shipment.INCIDENT},
    Shipment.PICKUP_POINT: {Shipment.DELIVERED, Shipment.RETURNING, Shipment.INCIDENT},
    Shipment.INCIDENT: {Shipment.IN_TRANSIT, Shipment.DELIVERY_FAILED, Shipment.RETURNING, Shipment.LOST},
    Shipment.LOST: set(),
    Shipment.DELIVERED: set(),
    Shipment.RETURNING: {Shipment.RETURNED},
    Shipment.RETURNED: set(),
}


class LifecycleProblem(Exception):
    """Violation d'une règle métier de cycle de vie."""



SHIPMENT_HANDED_OVER_STATUSES = {
    Shipment.ACCEPTED, Shipment.IN_TRANSIT, Shipment.OUT_FOR_DELIVERY,
    Shipment.PICKUP_POINT, Shipment.DELIVERY_FAILED, Shipment.INCIDENT,
    Shipment.LOST, Shipment.DELIVERED, Shipment.RETURNING, Shipment.RETURNED,
}


def all_order_quantities_covered(order, shipment_statuses):
    """Return True only when shipments in the given states cover every ordered unit."""
    ordered_lines = list(order.lines.values_list("pk", "quantity"))
    if not ordered_lines:
        return False
    shipped_totals = dict(
        ShipmentLine.objects.filter(
            shipment__order=order,
            shipment__status__in=shipment_statuses,
        ).values("order_line_id").annotate(total=Sum("quantity")).values_list("order_line_id", "total")
    )
    return all(shipped_totals.get(line_id, 0) >= quantity for line_id, quantity in ordered_lines)


COMMERCIAL_TRANSITIONS = {
    Order.COMMERCIAL_PENDING_PAYMENT: {Order.COMMERCIAL_CONFIRMED, Order.COMMERCIAL_ON_HOLD},
    Order.COMMERCIAL_CONFIRMED: {Order.COMMERCIAL_PROCESSING, Order.COMMERCIAL_PREPARING, Order.COMMERCIAL_ON_HOLD},
    Order.COMMERCIAL_PROCESSING: {Order.COMMERCIAL_CONFIRMED, Order.COMMERCIAL_PREPARING, Order.COMMERCIAL_ON_HOLD},
    Order.COMMERCIAL_PREPARING: {Order.COMMERCIAL_PROCESSING, Order.COMMERCIAL_READY_TO_SHIP, Order.COMMERCIAL_ON_HOLD},
    Order.COMMERCIAL_READY_TO_SHIP: {Order.COMMERCIAL_PREPARING, Order.COMMERCIAL_ON_HOLD},
    Order.COMMERCIAL_SHIPPED: {Order.COMMERCIAL_DELIVERED, Order.COMMERCIAL_ON_HOLD},
    Order.COMMERCIAL_DELIVERED: {Order.COMMERCIAL_COMPLETED, Order.COMMERCIAL_ON_HOLD},
    Order.COMMERCIAL_ON_HOLD: {
        Order.COMMERCIAL_CONFIRMED, Order.COMMERCIAL_PROCESSING,
        Order.COMMERCIAL_PREPARING, Order.COMMERCIAL_READY_TO_SHIP,
        Order.COMMERCIAL_SHIPPED, Order.COMMERCIAL_DELIVERED,
    },
    Order.COMMERCIAL_COMPLETED: set(),
    Order.COMMERCIAL_CANCELLED: set(),
}


@transaction.atomic
def transition_order_commercial_status(order_id, new_status, *, actor=None, reason=""):
    """Apply an explicit commercial-state transition with payment/logistics preconditions."""
    order = Order.objects.select_for_update().get(pk=order_id)
    if new_status not in dict(Order.COMMERCIAL_STATUS_CHOICES):
        raise LifecycleProblem("État commercial inconnu.")
    if new_status == order.commercial_status:
        return order
    if new_status not in COMMERCIAL_TRANSITIONS.get(order.commercial_status, set()):
        raise LifecycleProblem("Cette transition commerciale n'est pas autorisée.")
    paid_required = {
        Order.COMMERCIAL_CONFIRMED, Order.COMMERCIAL_PROCESSING,
        Order.COMMERCIAL_PREPARING, Order.COMMERCIAL_READY_TO_SHIP,
        Order.COMMERCIAL_SHIPPED, Order.COMMERCIAL_DELIVERED,
        Order.COMMERCIAL_COMPLETED,
    }
    if new_status in paid_required and order.status != Order.PAID:
        raise LifecycleProblem("Le paiement doit être confirmé avant cette étape commerciale.")
    if new_status == Order.COMMERCIAL_SHIPPED and not _all_order_quantities_covered(
        order, SHIPMENT_HANDED_OVER_STATUSES
    ):
        raise LifecycleProblem(
            "La commande ne peut être marquée expédiée que lorsque toutes les quantités "
            "commandées ont été prises en charge par le transporteur."
        )
    if new_status == Order.COMMERCIAL_DELIVERED and (
        not order.shipments.exists()
        or order.shipments.exclude(status=Shipment.DELIVERED).exists()
        or not _all_order_quantities_covered(order, {Shipment.DELIVERED})
    ):
        raise LifecycleProblem(
            "Tous les colis et toutes les quantités commandées doivent être attestés livrés avant cette transition."
        )
    if new_status == Order.COMMERCIAL_COMPLETED:
        if order.commercial_status != Order.COMMERCIAL_DELIVERED:
            raise LifecycleProblem("Seule une commande livrée peut être terminée.")
        if order.incidents.filter(status__in=[OrderIncident.OPEN, OrderIncident.INVESTIGATING]).exists():
            raise LifecycleProblem("Résolvez les incidents ouverts avant de terminer la commande.")
        if order.return_requests.filter(status__in=[
            ReturnRequest.RECEIVED, ReturnRequest.REVIEW, ReturnRequest.ACCEPTED,
            ReturnRequest.IN_TRANSIT, ReturnRequest.ARRIVED, ReturnRequest.INSPECTING,
        ]).exists():
            raise LifecycleProblem("Les dossiers de retour en cours doivent être résolus avant de terminer la commande.")
    previous = order.commercial_status
    order.commercial_status = new_status
    order.save(update_fields=["commercial_status", "updated_at"])
    record_order_event(
        order, "commercial_status", from_value=previous, to_value=new_status,
        source="admin", actor=actor, reason=reason,
    )
    if new_status in {Order.COMMERCIAL_ON_HOLD, Order.COMMERCIAL_COMPLETED}:
        from .services import _queue_order_email
        _queue_order_email(
            order, f"commercial_status_{new_status}",
            f"Mise à jour de votre commande {str(order.public_id)[:8]}",
            f"Bonjour {order.full_name},\\n\\nL'état de votre commande est désormais : {order.get_commercial_status_display()}.\\nRéférence : {order.public_id}\\n{reason}\\n\\nMy Line Collection",
        )
    return order


def record_order_event(order, event_type, *, from_value="", to_value="", source="system",
                       reason="", actor=None, external_reference="", metadata=None):
    return OrderEvent.objects.create(
        order=order, event_type=event_type, from_value=from_value, to_value=to_value,
        source=source, reason=reason, actor=actor, external_reference=external_reference,
        metadata=metadata or {},
    )


@transaction.atomic
def create_shipment(order_id, *, actor=None, carrier="", service="", tracking_number="",
                    tracking_url="", notes="", line_quantities=None):
    order = Order.objects.select_for_update().get(pk=order_id)
    if order.status != Order.PAID or order.commercial_status in {Order.COMMERCIAL_CANCELLED, Order.COMMERCIAL_ON_HOLD, Order.COMMERCIAL_COMPLETED}:
        raise LifecycleProblem("Une expédition exige une commande payée, active et non suspendue.")
    if tracking_url:
        parsed = urlparse(tracking_url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise LifecycleProblem("Le lien de suivi doit être une URL HTTPS valide.")
    shipment = Shipment.objects.create(
        order=order, created_by=actor, carrier=carrier.strip()[:80],
        service=service.strip()[:80], tracking_number=tracking_number.strip()[:120],
        tracking_url=tracking_url.strip(), notes=notes.strip(),
        status=Shipment.DRAFT,
    )
    line_quantities = line_quantities or {}
    if not line_quantities:
        raise LifecycleProblem("Affectez au moins une ligne de commande à ce colis.")
    for line_id, raw_quantity in line_quantities.items():
        line = order.lines.select_for_update().filter(pk=line_id).first()
        if not line:
            raise LifecycleProblem("Une ligne sélectionnée n'appartient pas à cette commande.")
        try:
            quantity = int(raw_quantity)
        except (TypeError, ValueError):
            raise LifecycleProblem("Quantité d'expédition invalide.")
        if quantity < 1:
            raise LifecycleProblem("La quantité expédiée doit être positive.")
        already_allocated = ShipmentLine.objects.filter(order_line=line).exclude(
            shipment__status=Shipment.RETURNED
        ).aggregate(total=Sum("quantity"))["total"] or 0
        if quantity + already_allocated > line.quantity:
            raise LifecycleProblem("La quantité totale expédiée dépasserait la quantité commandée.")
        ShipmentLine.objects.create(shipment=shipment, order_line=line, quantity=quantity)
    ShipmentEvent.objects.create(
        shipment=shipment, status=Shipment.DRAFT, source="manual",
        description="Expédition créée depuis le dashboard.", created_by=actor,
    )
    record_order_event(order, "shipment_created", source="admin", actor=actor,
                       metadata={"shipment_id": str(shipment.public_id)})
    return shipment


@transaction.atomic
def transition_shipment(shipment_id, new_status, *, actor=None, reason="", external_event_id="",
                        source="manual", occurred_at=None, payload=None):
    shipment = Shipment.objects.select_for_update().select_related("order").get(pk=shipment_id)
    if new_status not in dict(Shipment.STATUS_CHOICES):
        raise LifecycleProblem("État d'expédition inconnu.")
    if new_status == shipment.status:
        return shipment
    if new_status not in SHIPMENT_TRANSITIONS.get(shipment.status, set()):
        raise LifecycleProblem("Cette transition d'expédition n'est pas autorisée.")
    if external_event_id and ShipmentEvent.objects.filter(external_event_id=external_event_id).exists():
        return shipment
    previous = shipment.status
    shipment.status = new_status
    if new_status == Shipment.ACCEPTED:
        shipment.handed_over_at = occurred_at or timezone.now()
    if new_status == Shipment.DELIVERED:
        shipment.delivered_at = occurred_at or timezone.now()
    shipment.save(update_fields=["status", "handed_over_at", "delivered_at", "updated_at"])
    ShipmentEvent.objects.create(
        shipment=shipment, status=new_status, source=source,
        external_event_id=external_event_id or None, description=reason,
        occurred_at=occurred_at, payload=payload or {}, created_by=actor,
    )
    record_order_event(shipment.order, "shipment_status", from_value=previous,
                       to_value=new_status, source=source, reason=reason, actor=actor,
                       external_reference=external_event_id,
                       metadata={"shipment_id": str(shipment.public_id)})
    if new_status in {Shipment.ACCEPTED, Shipment.DELIVERED}:
        from .services import _queue_order_email
        if new_status == Shipment.ACCEPTED:
            _queue_order_email(
                shipment.order, f"shipment_handed_over_{shipment.pk}",
                f"Un colis de votre commande {str(shipment.order.public_id)[:8]} a été pris en charge",
                f"Bonjour {shipment.order.full_name},\n\nUn colis de votre commande a été pris en charge par le transporteur.\nRéférence de commande : {shipment.order.public_id}\nNuméro de suivi : {shipment.tracking_number or 'en cours de saisie'}\n\nMy Line Collection",
            )
        else:
            _queue_order_email(
                shipment.order, f"shipment_delivered_{shipment.pk}",
                f"Un colis de votre commande {str(shipment.order.public_id)[:8]} a été livré",
                f"Bonjour {shipment.order.full_name},\n\nLe suivi indique que ce colis a été livré. Si vous constatez un problème, consultez la page de suivi de commande avec votre référence.\nRéférence de commande : {shipment.order.public_id}\n\nMy Line Collection",
            )
    if new_status == Shipment.ACCEPTED:
        order = shipment.order
        if order.status != Order.PAID or order.commercial_status != Order.COMMERCIAL_READY_TO_SHIP:
            raise LifecycleProblem(
                "Le colis ne peut être remis au transporteur que pour une commande payée et prête à expédier."
            )
        old = order.fulfillment_status
        all_units_handed_over = _all_order_quantities_covered(
            order, SHIPMENT_HANDED_OVER_STATUSES
        )
        order.fulfillment_status = (
            Order.FULFILLMENT_SHIPPED if all_units_handed_over
            else Order.FULFILLMENT_PREPARING
        )
        order.shipped_at = order.shipped_at or shipment.handed_over_at
        order.save(update_fields=["fulfillment_status", "shipped_at", "updated_at"])
        record_order_event(
            order, "fulfillment_status", from_value=old,
            to_value=order.fulfillment_status, source=source,
            reason=(
                "Toutes les quantités commandées ont été prises en charge."
                if all_units_handed_over
                else "Une partie des colis a été prise en charge ; la préparation continue."
            ), actor=actor,
        )
        if all_units_handed_over:
            transition_order_commercial_status(
                order.pk, Order.COMMERCIAL_SHIPPED, actor=actor,
                reason="Toutes les quantités commandées ont été remises au transporteur.",
            )

    if new_status == Shipment.DELIVERED:
        order = shipment.order
        all_shipments_delivered = not order.shipments.exclude(status=Shipment.DELIVERED).exists()
        all_units_delivered = _all_order_quantities_covered(order, {Shipment.DELIVERED})
        if all_shipments_delivered and all_units_delivered:
            old = order.fulfillment_status
            order.fulfillment_status = Order.FULFILLMENT_DELIVERED
            order.delivered_at = shipment.delivered_at
            order.save(update_fields=["fulfillment_status", "delivered_at", "updated_at"])
            record_order_event(
                order, "fulfillment_status", from_value=old,
                to_value=Order.FULFILLMENT_DELIVERED, source=source,
                reason="Tous les colis et toutes les quantités commandées sont déclarés livrés.",
                actor=actor,
            )
            transition_order_commercial_status(
                order.pk, Order.COMMERCIAL_DELIVERED, actor=actor,
                reason="Tous les colis et toutes les quantités commandées sont déclarés livrés.",
            )
        else:
            old = order.fulfillment_status
            all_units_handed_over = _all_order_quantities_covered(
                order, SHIPMENT_HANDED_OVER_STATUSES
            )
            summary_status = (
                Order.FULFILLMENT_SHIPPED if all_units_handed_over
                else Order.FULFILLMENT_PREPARING
            )
            if old != summary_status:
                order.fulfillment_status = summary_status
                order.save(update_fields=["fulfillment_status", "updated_at"])
                record_order_event(
                    order, "fulfillment_status", from_value=old,
                    to_value=summary_status, source=source,
                    reason="Le suivi d'un colis a évolué ; la commande complète n'est pas encore livrée.",
                    actor=actor,
                )
    return shipment


@transaction.atomic
def create_return_request(order_id, *, reason_category, reason, lines, customer=None, customer_note="", source="customer"):
    order = Order.objects.select_for_update().get(pk=order_id)
    if order.status != Order.PAID or order.commercial_status == Order.COMMERCIAL_CANCELLED:
        raise LifecycleProblem("Une demande de retour exige une commande payée et non annulée.")
    if reason_category not in dict(ReturnRequest.REASONS):
        raise LifecycleProblem("Le motif de retour n'est pas valide.")
    reason = (reason or "").strip()
    customer_note = (customer_note or "").strip()
    if not reason:
        raise LifecycleProblem("Le motif détaillé est obligatoire.")
    if len(reason) > 2000:
        raise LifecycleProblem("Le motif détaillé ne peut pas dépasser 2 000 caractères.")
    if len(customer_note) > 2000:
        raise LifecycleProblem("Le commentaire ne peut pas dépasser 2 000 caractères.")
    request = ReturnRequest.objects.create(
        order=order, customer=customer, reason_category=reason_category,
        reason=reason, customer_note=customer_note,
    )
    seen = set()
    for line_id, raw_quantity in lines.items():
        if str(line_id) in seen:
            raise LifecycleProblem("Une ligne de commande est sélectionnée plusieurs fois.")
        seen.add(str(line_id))
        line = order.lines.select_for_update().filter(pk=line_id).first()
        if not line:
            raise LifecycleProblem("Une ligne sélectionnée n'appartient pas à cette commande.")
        try:
            quantity = int(raw_quantity)
        except (TypeError, ValueError):
            raise LifecycleProblem("Quantité de retour invalide.")
        returned = ReturnLine.objects.filter(
            order_line=line,
            return_request__status__in=[
                ReturnRequest.RECEIVED, ReturnRequest.REVIEW, ReturnRequest.ACCEPTED,
                ReturnRequest.IN_TRANSIT, ReturnRequest.ARRIVED, ReturnRequest.INSPECTING,
                ReturnRequest.RESOLVED, ReturnRequest.CLOSED,
            ],
        ).aggregate(total=Sum("quantity"))["total"] or 0
        if quantity < 1 or returned + quantity > line.quantity:
            raise LifecycleProblem("La quantité de retour dépasse la quantité commandée ou déjà déclarée.")
        ReturnLine.objects.create(return_request=request, order_line=line, quantity=quantity)
    if not request.lines.exists():
        raise LifecycleProblem("Sélectionnez au moins un article à retourner.")
    record_order_event(order, "return_requested", source=source,
                       actor=customer, metadata={"return_id": str(request.public_id)})
    from .services import _queue_order_email
    _queue_order_email(
        order, f"return_requested_{request.public_id}",
        f"Demande de retour reçue pour la commande {str(order.public_id)[:8]}",
        f"Bonjour {order.full_name},\n\nNous avons reçu votre demande de retour. Elle sera examinée séparément de l'état de votre commande.\nRéférence de commande : {order.public_id}\nRéférence de demande : {request.public_id}\n\nMy Line Collection",
    )
    return request


@transaction.atomic
def decide_return(return_id, *, new_status, actor, note=""):
    request = ReturnRequest.objects.select_for_update().select_related("order").get(pk=return_id)
    allowed = {
        ReturnRequest.RECEIVED: {ReturnRequest.REVIEW, ReturnRequest.ACCEPTED, ReturnRequest.REJECTED},
        ReturnRequest.REVIEW: {ReturnRequest.ACCEPTED, ReturnRequest.REJECTED},
        ReturnRequest.ACCEPTED: {ReturnRequest.IN_TRANSIT, ReturnRequest.ARRIVED},
        ReturnRequest.IN_TRANSIT: {ReturnRequest.ARRIVED},
        ReturnRequest.ARRIVED: {ReturnRequest.INSPECTING},
        ReturnRequest.INSPECTING: {ReturnRequest.RESOLVED},
        ReturnRequest.RESOLVED: {ReturnRequest.CLOSED},
    }
    if new_status not in allowed.get(request.status, set()):
        raise LifecycleProblem("Cette transition de retour n'est pas autorisée.")
    previous = request.status
    request.status = new_status
    request.admin_note = note.strip()
    if new_status in {ReturnRequest.ACCEPTED, ReturnRequest.REJECTED}:
        request.decided_at, request.decided_by = timezone.now(), actor
    if new_status == ReturnRequest.ARRIVED:
        request.received_at = timezone.now()
    if new_status in {ReturnRequest.RESOLVED, ReturnRequest.CLOSED}:
        request.resolved_at = timezone.now()
    request.save()
    record_order_event(request.order, "return_status", from_value=previous,
                       to_value=new_status, source="admin", reason=note, actor=actor,
                       metadata={"return_id": str(request.public_id)})
    from .services import _queue_order_email
    if new_status in {ReturnRequest.ACCEPTED, ReturnRequest.REJECTED, ReturnRequest.RESOLVED, ReturnRequest.CLOSED}:
        _queue_order_email(
            request.order, f"return_status_{request.public_id}_{new_status}",
            f"Mise à jour de votre demande de retour {str(request.public_id)[:8]}",
            f"Bonjour {request.order.full_name},\n\nL'état de votre demande de retour est désormais : {request.get_status_display()}.\nRéférence de commande : {request.order.public_id}\n{note}\n\nMy Line Collection",
        )
    return request


def request_refund(order_id, *, amount, reason, actor=None, return_request=None, idempotency_key=None):
    """Demande un remboursement Stripe idempotent; jamais de succès local sans preuve Stripe."""
    try:
        amount = Decimal(str(amount)).quantize(Decimal("0.01"))
    except Exception as exc:
        raise LifecycleProblem("Montant de remboursement invalide.") from exc
    if amount <= 0:
        raise LifecycleProblem("Le montant du remboursement doit être positif.")
    if not reason or not reason.strip():
        raise LifecycleProblem("Le motif du remboursement est obligatoire.")
    try:
        request_key = uuid.UUID(str(idempotency_key)) if idempotency_key else None
    except (ValueError, TypeError, AttributeError) as exc:
        raise LifecycleProblem("Clé d'idempotence invalide.") from exc
    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order_id)
        if request_key:
            existing_request = Refund.objects.select_for_update().filter(idempotency_key=request_key).first()
            if existing_request:
                if existing_request.order_id != order.pk or existing_request.amount != amount:
                    raise LifecycleProblem("Cette clé d'idempotence est déjà utilisée pour une autre opération.")
                return existing_request
        if order.status != Order.PAID or not order.stripe_payment_intent_id:
            raise LifecycleProblem("Aucun paiement Stripe confirmé n'est disponible pour cette commande.")
        if return_request and return_request.order_id != order.pk:
            raise LifecycleProblem("Le dossier de retour ne correspond pas à cette commande.")
        existing = Refund.objects.filter(order=order, status__in=[Refund.PENDING, Refund.PROCESSING, Refund.SUCCEEDED]).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        if existing + amount > order.total:
            raise LifecycleProblem("Le montant demandé dépasse le solde remboursable.")
        refund = Refund.objects.create(
            order=order, return_request=return_request, amount=amount,
            currency=order.currency, reason=reason.strip(), initiated_by=actor,
            external_payment_reference=order.stripe_payment_intent_id,
            idempotency_key=request_key or uuid.uuid4(), status=Refund.PROCESSING,
        )
        record_order_event(order, "refund_requested", source="admin", actor=actor,
                           reason=reason, metadata={"refund_id": refund.pk, "amount": str(amount)})
    secret = getattr(settings, "STRIPE_SECRET_KEY", "") or __import__("os").environ.get("STRIPE_SECRET_KEY", "")
    live_mode = os.environ.get("STRIPE_LIVE_MODE", "False").strip().lower() in {"1", "true", "yes", "on"}
    if not secret or (live_mode and not secret.startswith("sk_live_")) or (not live_mode and not secret.startswith("sk_test_")):
        refund.status = Refund.FAILED
        refund.failure_reason = "Configuration Stripe absente ou incohérente avec STRIPE_LIVE_MODE."
        refund.save(update_fields=["status", "failure_reason"])
        raise LifecycleProblem("La configuration Stripe est absente ou incohérente. Aucun remboursement n'a été envoyé.")
    if live_mode and settings.DEBUG:
        refund.status = Refund.FAILED
        refund.failure_reason = "Les remboursements en mode live sont interdits lorsque DEBUG est actif."
        refund.save(update_fields=["status", "failure_reason"])
        raise LifecycleProblem("Le mode Stripe live est interdit avec DEBUG actif.")
    try:
        stripe.api_key = secret
        result = stripe.Refund.create(
            payment_intent=refund.external_payment_reference,
            amount=int(amount * 100),
            reason="requested_by_customer",
            metadata={"local_refund_id": str(refund.pk), "order_id": str(order.public_id)},
            idempotency_key=str(refund.idempotency_key),
        )
    except stripe.error.StripeError as exc:
        http_status = getattr(exc, "http_status", None)
        # En cas de timeout, erreur réseau, rate-limit ou 5xx, Stripe peut avoir
        # accepté la demande sans que la réponse soit parvenue à l'application.
        # Garder le montant réservé en PROCESSING évite un second remboursement.
        if http_status is None or http_status == 429 or http_status >= 500:
            refund.failure_reason = (
                "Résultat Stripe incertain ; vérifier le tableau de bord et les webhooks "
                "avant toute nouvelle action."
            )
            refund.save(update_fields=["failure_reason"])
            raise LifecycleProblem(
                "Le résultat du remboursement est incertain. Il reste en vérification ; "
                "ne relancez pas un autre remboursement avant réconciliation."
            ) from exc
        refund.status = Refund.FAILED
        refund.failure_reason = str(getattr(exc, "user_message", None) or "Erreur Stripe")[:2000]
        refund.save(update_fields=["status", "failure_reason"])
        raise LifecycleProblem("Stripe a refusé le remboursement. Consultez le détail avant une nouvelle tentative.") from exc
    with transaction.atomic():
        refund = Refund.objects.select_for_update().get(pk=refund.pk)
        previous_status = refund.status
        if not refund.stripe_refund_id:
            refund.stripe_refund_id = result.id
        # A webhook can beat the synchronous API response; never downgrade its state.
        if refund.status != Refund.SUCCEEDED:
            refund.status = Refund.SUCCEEDED if result.status == "succeeded" else Refund.PROCESSING
            if refund.status == Refund.SUCCEEDED:
                refund.confirmed_at = timezone.now()
        refund.save(update_fields=["stripe_refund_id", "status", "confirmed_at"])
        if refund.status == Refund.SUCCEEDED and previous_status != Refund.SUCCEEDED:
            record_order_event(order, "refund_confirmed", source="stripe", external_reference=result.id,
                               metadata={"refund_id": refund.pk, "amount": str(amount)})
            from .services import _queue_order_email
            _queue_order_email(
                order, f"refund_confirmed_{refund.pk}",
                f"Remboursement confirmé pour la commande {str(order.public_id)[:8]}",
                f"Bonjour {order.full_name},\\n\\nStripe a confirmé un remboursement de {refund.amount} {refund.currency.upper()}.\\nRéférence de commande : {order.public_id}\\n\\nMy Line Collection",
            )
    return refund


def queue_notification(*, order=None, event_key, recipient, payload=None, channel="email"):
    """Crée une notification persistante sans rendre la commande dépendante du serveur e-mail."""
    notification, created = OrderNotification.objects.get_or_create(
        order=order, event_key=event_key, recipient=recipient, channel=channel,
        defaults={"payload": payload or {}},
    )
    return notification, created


def deliver_notification(notification_id):
    """Envoi avec réservation atomique pour limiter les doubles envois concurrents.

    L'appel réseau reste hors transaction. La commande
    process_order_notifications récupère les états « sending » devenus obsolètes.
    Une reprise après arrêt brutal peut occasionner un doublon si le prestataire
    a accepté l'e-mail sans que l'application ait pu enregistrer le résultat.
    """
    with transaction.atomic():
        notification = OrderNotification.objects.select_for_update().get(pk=notification_id)
        if notification.status in {OrderNotification.SENT, OrderNotification.SENDING}:
            return notification
        if notification.attempts >= 5:
            notification.status = OrderNotification.FAILED
            notification.error_message = "Nombre maximal de tentatives atteint."
            notification.payload = {}
            notification.save(update_fields=["status", "error_message", "payload", "updated_at"])
            return notification
        notification.attempts += 1
        notification.status = OrderNotification.SENDING
        notification.error_message = ""
        notification.save(update_fields=["attempts", "status", "error_message", "updated_at"])
        recipient = notification.recipient
        payload = notification.payload or {}
        subject = str(payload.get("subject") or "Mise à jour de votre commande My Line Collection")[:200]
        message = str(payload.get("message") or "Votre commande a été mise à jour.")[:10000]

    try:
        sent = send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[recipient],
            fail_silently=False,
        )
        if sent != 1:
            raise RuntimeError("Le backend e-mail n'a pas confirmé l'envoi.")
    except Exception as exc:
        logger.warning("Order notification %s failed: %s", notification_id, type(exc).__name__)
        status = OrderNotification.FAILED
        error_message = type(exc).__name__[:200]
        sent_at = None
    else:
        status = OrderNotification.SENT
        error_message = ""
        sent_at = timezone.now()

    # Only finalize the attempt still marked as sending. This avoids overwriting
    # an administrative decision made while the provider call was in progress.
    updates = {
        "status": status, "sent_at": sent_at, "error_message": error_message,
        "updated_at": timezone.now(),
    }
    if status == OrderNotification.SENT:
        # Do not retain signed tracking tokens or full email bodies after delivery.
        updates["payload"] = {}
    OrderNotification.objects.filter(pk=notification_id, status=OrderNotification.SENDING).update(**updates)
    return OrderNotification.objects.get(pk=notification_id)


@transaction.atomic
def restock_unshipped_cancelled_order(order_id, *, actor=None):
    """Restores stock only after a fully refunded, paid order is cancelled before handover."""
    order = Order.objects.select_for_update().get(pk=order_id)
    if not order.stock_committed:
        return order
    if order.shipments.exists():
        raise LifecycleProblem("Le stock ne peut pas être remis en vente tant qu'une expédition existe.")
    requirements = order.stock_requirements_snapshot or {}
    variants = []
    for variant_id, raw_quantity in requirements.items():
        try:
            quantity = int(raw_quantity)
            variant = ProductVariant.objects.select_for_update().filter(pk=int(variant_id)).first()
        except (TypeError, ValueError):
            raise LifecycleProblem("L'instantané de stock de cette commande est invalide.")
        if quantity < 1 or not variant:
            raise LifecycleProblem("Une variante de cette commande n'est plus disponible pour la remise en stock.")
        variants.append((variant, quantity))
    for variant, quantity in variants:
        ProductVariant.objects.filter(pk=variant.pk).update(stock_quantity=F("stock_quantity") + quantity)
    order.stock_committed = False
    order.save(update_fields=["stock_committed", "updated_at"])
    record_order_event(
        order, "stock_restored_after_cancellation", source="admin", actor=actor,
        reason="Remboursement total confirmé et commande annulée avant expédition.",
        metadata={"variants": [{"variant_id": variant.pk, "quantity": quantity} for variant, quantity in variants]},
    )
    return order
