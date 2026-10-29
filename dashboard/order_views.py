"""Gestion privée des commandes et de leur préparation logistique."""
import uuid
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_GET, require_POST

from checkout.models import (Order, OrderLine, PaymentAttempt, OrderEvent, Shipment, ShipmentEvent, ReturnRequest, Refund, OrderIncident, OrderNotification)
from checkout.lifecycle import LifecycleProblem, create_shipment, transition_shipment, decide_return, request_refund, deliver_notification
from .views import is_dashboard_admin


def dashboard_admin_required(view_func):
    return user_passes_test(is_dashboard_admin, login_url="dashboard:login")(view_func)


FULFILLMENT_TRANSITIONS = {
    Order.FULFILLMENT_UNFULFILLED: {Order.FULFILLMENT_PREPARING, Order.FULFILLMENT_ON_HOLD},
    Order.FULFILLMENT_PREPARING: {Order.FULFILLMENT_UNFULFILLED, Order.FULFILLMENT_SHIPPED, Order.FULFILLMENT_ON_HOLD},
    Order.FULFILLMENT_ON_HOLD: {Order.FULFILLMENT_UNFULFILLED, Order.FULFILLMENT_PREPARING},
    Order.FULFILLMENT_SHIPPED: {Order.FULFILLMENT_DELIVERED},
    Order.FULFILLMENT_DELIVERED: set(),
}


@dashboard_admin_required
@require_GET
def orders(request):
    query = " ".join(request.GET.get("q", "").split())[:160]
    payment_status = request.GET.get("payment", "").strip()
    fulfillment_status = request.GET.get("fulfillment", "").strip()
    carrier = " ".join(request.GET.get("carrier", "").split())[:80]
    date_from_raw = request.GET.get("date_from", "").strip()
    date_to_raw = request.GET.get("date_to", "").strip()
    date_from, date_to = parse_date(date_from_raw), parse_date(date_to_raw)
    queryset = Order.objects.annotate(line_count=Count("lines")).order_by("-created_at")
    if query:
        search = (Q(full_name__icontains=query) | Q(email__icontains=query) | Q(city__icontains=query) | Q(tracking_number__icontains=query) | Q(shipping_carrier__icontains=query) | Q(shipments__tracking_number__icontains=query) | Q(shipments__carrier__icontains=query))
        try:
            search |= Q(public_id=uuid.UUID(query))
        except (ValueError, TypeError, AttributeError):
            pass
        queryset = queryset.filter(search).distinct()
    if payment_status in dict(Order.STATUS_CHOICES):
        queryset = queryset.filter(status=payment_status)
    else:
        payment_status = ""
    if fulfillment_status in dict(Order.FULFILLMENT_CHOICES):
        queryset = queryset.filter(fulfillment_status=fulfillment_status)
    else:
        fulfillment_status = ""

    if carrier:
        queryset = queryset.filter(Q(shipping_carrier__icontains=carrier) | Q(shipments__carrier__icontains=carrier)).distinct()
    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)

    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "dashboard/orders.html", {
        "page_obj": page_obj,
        "orders": page_obj.object_list,
        "query": query,
        "selected_payment": payment_status,
        "selected_fulfillment": fulfillment_status,
        "carrier": carrier,
        "date_from": date_from_raw if date_from else "",
        "date_to": date_to_raw if date_to else "",
        "payment_choices": Order.STATUS_CHOICES,
        "fulfillment_choices": Order.FULFILLMENT_CHOICES,
        "total_orders": Order.objects.count(),
        "awaiting_payment_count": Order.objects.filter(status__in=(Order.PENDING, Order.AWAITING)).count(),
        "paid_to_prepare_count": Order.objects.filter(status=Order.PAID, fulfillment_status=Order.FULFILLMENT_UNFULFILLED).count(),
        "shipped_count": Order.objects.filter(fulfillment_status=Order.FULFILLMENT_SHIPPED).count(),
    })


@dashboard_admin_required
@require_GET
def order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.prefetch_related("lines", "payment_attempts"),
        pk=pk,
    )
    return render(request, "dashboard/order_detail.html", {
        "order": order,
        "can_manage_fulfillment": order.status == Order.PAID,
        "shipments": order.shipments.prefetch_related("lines__order_line", "events").all(),
        "return_requests": order.return_requests.prefetch_related("lines__order_line", "refunds").all(),
        "refunds": order.refunds.all(),
        "incidents": order.incidents.select_related("shipment").all(),
        "lifecycle_events": order.lifecycle_events.select_related("actor").all()[:50],
        "notifications": order.notifications.all()[:30],
        "shipment_choices": Shipment.STATUS_CHOICES,
        "return_choices": ReturnRequest.STATUS_CHOICES,
        "incident_categories": OrderIncident.CATEGORIES,\n        "incident_status_choices": OrderIncident.STATUS_CHOICES,\n        "refund_request_key": uuid.uuid4(),
        "payment_attempts": order.payment_attempts.all(),
        "fulfillment_choices": Order.FULFILLMENT_CHOICES,
        "allowed_transitions": FULFILLMENT_TRANSITIONS.get(order.fulfillment_status, set()),
    })


@dashboard_admin_required
@require_POST
def order_update_fulfillment(request, pk):
    with transaction.atomic():
        order = get_object_or_404(Order.objects.select_for_update(), pk=pk)
        if order.status != Order.PAID:
            messages.error(request, "La préparation logistique est réservée aux commandes dont le paiement est confirmé.")
            return redirect("dashboard:order_detail", pk=order.pk)

        new_status = request.POST.get("fulfillment_status", "").strip()
        carrier = request.POST.get("shipping_carrier", "").strip()
        tracking_number = request.POST.get("tracking_number", "").strip()
        internal_note = request.POST.get("internal_note", "").strip()

        if new_status not in dict(Order.FULFILLMENT_CHOICES):
            messages.error(request, "État logistique invalide.")
            return redirect("dashboard:order_detail", pk=order.pk)
        if new_status != order.fulfillment_status and new_status not in FULFILLMENT_TRANSITIONS.get(order.fulfillment_status, set()):
            messages.error(request, "Cette transition logistique n’est pas autorisée.")
            return redirect("dashboard:order_detail", pk=order.pk)
        if new_status == Order.FULFILLMENT_SHIPPED and not order.shipments.filter(status__in=[Shipment.ACCEPTED, Shipment.IN_TRANSIT, Shipment.OUT_FOR_DELIVERY, Shipment.PICKUP_POINT, Shipment.DELIVERED]).exists():
            messages.error(request, "Enregistrez d'abord un colis puis sa prise en charge effective par le transporteur.")
            return redirect("dashboard:order_detail", pk=order.pk)
        if new_status == Order.FULFILLMENT_DELIVERED and (not order.shipments.exists() or order.shipments.exclude(status=Shipment.DELIVERED).exists()):
            messages.error(request, "La livraison doit être attestée pour tous les colis avant de clôturer le suivi.")
            return redirect("dashboard:order_detail", pk=order.pk)
        if len(carrier) > 80 or len(tracking_number) > 120 or len(internal_note) > 4000:
            messages.error(request, "Un des champs dépasse la longueur maximale autorisée.")
            return redirect("dashboard:order_detail", pk=order.pk)

        now = timezone.now()
        previous_status = order.fulfillment_status
        changed_fields = ["fulfillment_status", "shipping_carrier", "tracking_number", "internal_note", "updated_at"]
        order.fulfillment_status = new_status
        order.shipping_carrier = carrier
        order.tracking_number = tracking_number
        order.internal_note = internal_note
        if new_status == Order.FULFILLMENT_SHIPPED and order.shipped_at is None:
            order.shipped_at = now
            changed_fields.append("shipped_at")
        if new_status == Order.FULFILLMENT_DELIVERED and order.delivered_at is None:
            order.delivered_at = now
            changed_fields.append("delivered_at")
        order.save(update_fields=changed_fields)
        if previous_status != new_status:
            OrderEvent.objects.create(
                order=order, event_type="fulfillment_status", source="admin",
                from_value=previous_status, to_value=new_status, actor=request.user,
                reason=internal_note,
                metadata={"carrier": carrier, "tracking_number_present": bool(tracking_number)},
            )

    messages.success(request, "Suivi de commande enregistré.")
    return redirect("dashboard:order_detail", pk=order.pk)


@dashboard_admin_required
@require_POST
def order_create_shipment(request, pk):
    order = get_object_or_404(Order, pk=pk)
    quantities = {}
    for line in order.lines.all():
        raw = request.POST.get(f"line_{line.pk}", "").strip()
        if raw:
            quantities[line.pk] = raw
    try:
        shipment = create_shipment(
            order.pk, actor=request.user,
            carrier=request.POST.get("carrier", ""),
            service=request.POST.get("service", ""),
            tracking_number=request.POST.get("tracking_number", ""),
            tracking_url=request.POST.get("tracking_url", ""),
            notes=request.POST.get("notes", ""),
            line_quantities=quantities,
        )
    except (LifecycleProblem, ValueError) as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, f"Expédition {shipment.public_id} créée en brouillon. Elle n'est pas considérée comme expédiée.")
    return redirect("dashboard:order_detail", pk=pk)


@dashboard_admin_required
@require_POST
def shipment_update_status(request, pk, shipment_pk):
    shipment = get_object_or_404(Shipment.objects.select_related("order"), pk=shipment_pk, order_id=pk)
    status = request.POST.get("status", "").strip()
    reason = request.POST.get("reason", "").strip()[:2000]
    try:
        transition_shipment(shipment.pk, status, actor=request.user, reason=reason)
    except LifecycleProblem as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "Événement de suivi enregistré.")
    return redirect("dashboard:order_detail", pk=pk)


@dashboard_admin_required
@require_POST
def return_update_status(request, pk, return_pk):
    return_request = get_object_or_404(ReturnRequest, pk=return_pk, order_id=pk)
    try:
        decide_return(
            return_request.pk, new_status=request.POST.get("status", "").strip(),
            actor=request.user, note=request.POST.get("note", "")[:4000],
        )
    except LifecycleProblem as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "Dossier de retour mis à jour.")
    return redirect("dashboard:order_detail", pk=pk)


@dashboard_admin_required
@require_POST
def order_create_refund(request, pk):
    order = get_object_or_404(Order, pk=pk)
    try:
        refund = request_refund(
            order.pk, amount=request.POST.get("amount", ""),
            reason=request.POST.get("reason", ""), actor=request.user,\n            idempotency_key=request.POST.get("idempotency_key", ""),
        )
    except (LifecycleProblem, ValueError) as exc:
        messages.error(request, str(exc))
    else:
        if refund.status == Refund.SUCCEEDED:
            messages.success(request, "Stripe a confirmé le remboursement.")
        else:
            messages.warning(request, "La demande est enregistrée, mais Stripe n'a pas encore confirmé le remboursement.")
    return redirect("dashboard:order_detail", pk=pk)


@dashboard_admin_required
@require_POST
def order_create_incident(request, pk):
    order = get_object_or_404(Order, pk=pk)
    category = request.POST.get("category", "").strip()
    description = request.POST.get("description", "").strip()
    if category not in dict(OrderIncident.CATEGORIES) or not description:
        messages.error(request, "Le type d'incident et sa description sont obligatoires.")
    else:
        incident = OrderIncident.objects.create(
            order=order, category=category, description=description[:5000],
            created_by=request.user,
        )
        OrderEvent.objects.create(
            order=order, event_type="incident_created", source="admin",
            reason=description[:1000], actor=request.user,
            metadata={"incident_id": incident.pk, "category": category},
        )
        messages.success(request, "Incident enregistré dans l'historique.")
    return redirect("dashboard:order_detail", pk=pk)


@dashboard_admin_required
@require_POST
def order_retry_notification(request, pk, notification_pk):
    notification = get_object_or_404(OrderNotification, pk=notification_pk, order_id=pk)
    if notification.attempts >= 5:
        messages.error(request, "Le nombre maximal de tentatives est atteint.")
    else:
        notification.status = OrderNotification.PENDING
        notification.error_message = ""
        notification.save(update_fields=["status", "error_message", "updated_at"])
        try:
            deliver_notification(notification.pk)
        except Exception:
            messages.error(request, "La relance a échoué. Consultez l'état de la notification.")
        else:
            notification.refresh_from_db()
            if notification.status == OrderNotification.SENT:
                messages.success(request, "Le prestataire e-mail a accepté l'envoi.")
            else:
                messages.error(request, "L'envoi n'a pas abouti. Le statut et l'erreur sont conservés.")
    return redirect("dashboard:order_detail", pk=pk)


@dashboard_admin_required
@require_POST
def order_update_incident(request, pk, incident_pk):
    incident = get_object_or_404(OrderIncident, pk=incident_pk, order_id=pk)
    new_status = request.POST.get("status", "").strip()
    resolution = request.POST.get("resolution", "").strip()[:4000]
    if new_status not in dict(OrderIncident.STATUS_CHOICES):
        messages.error(request, "État d'incident invalide.")
        return redirect("dashboard:order_detail", pk=pk)
    incident.status = new_status
    incident.resolution = resolution
    if new_status in {OrderIncident.RESOLVED, OrderIncident.CLOSED}:
        incident.resolved_at = timezone.now()
        incident.resolved_by = request.user
    incident.save(update_fields=["status", "resolution", "resolved_at", "resolved_by"])
    OrderEvent.objects.create(
        order=incident.order, event_type="incident_status", source="admin",
        to_value=new_status, reason=resolution, actor=request.user,
        metadata={"incident_id": incident.pk, "category": incident.category},
    )
    messages.success(request, "Incident mis à jour.")
    return redirect("dashboard:order_detail", pk=pk)
