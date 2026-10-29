"""Gestion privée des commandes et de leur préparation logistique."""
import uuid
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from checkout.models import Order, OrderLine, PaymentAttempt
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
    queryset = Order.objects.annotate(line_count=Count("lines")).order_by("-created_at")
    if query:
        search = Q(full_name__icontains=query) | Q(email__icontains=query) | Q(city__icontains=query)
        try:
            search |= Q(public_id=uuid.UUID(query))
        except (ValueError, TypeError, AttributeError):
            pass
        queryset = queryset.filter(search)
    if payment_status in dict(Order.STATUS_CHOICES):
        queryset = queryset.filter(status=payment_status)
    else:
        payment_status = ""
    if fulfillment_status in dict(Order.FULFILLMENT_CHOICES):
        queryset = queryset.filter(fulfillment_status=fulfillment_status)
    else:
        fulfillment_status = ""

    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "dashboard/orders.html", {
        "page_obj": page_obj,
        "orders": page_obj.object_list,
        "query": query,
        "selected_payment": payment_status,
        "selected_fulfillment": fulfillment_status,
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
        if len(carrier) > 80 or len(tracking_number) > 120 or len(internal_note) > 4000:
            messages.error(request, "Un des champs dépasse la longueur maximale autorisée.")
            return redirect("dashboard:order_detail", pk=order.pk)

        now = timezone.now()
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

    messages.success(request, "Suivi de commande enregistré.")
    return redirect("dashboard:order_detail", pk=order.pk)
