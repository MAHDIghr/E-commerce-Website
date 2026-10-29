"""Commandes persistantes, réservations de stock et événements Stripe idempotents."""
import uuid
from decimal import Decimal
from django.conf import settings
from django.db import models
from django.db.models import Q


class PromoCode(models.Model):
    PERCENT = "percent"
    FIXED = "fixed"
    DISCOUNT_TYPES = ((PERCENT, "Pourcentage"), (FIXED, "Montant fixe"))
    code = models.CharField(max_length=32, unique=True)
    discount_type = models.CharField(max_length=8, choices=DISCOUNT_TYPES, default=PERCENT)
    value = models.DecimalField(max_digits=8, decimal_places=2)
    minimum_subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    maximum_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    once_per_email = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("code",)
        constraints = [
            models.CheckConstraint(condition=Q(value__gt=0), name="promo_value_positive"),
            models.CheckConstraint(condition=Q(minimum_subtotal__gte=0), name="promo_min_subtotal_nonnegative"),
        ]

    def save(self, *args, **kwargs):
        self.code = (self.code or "").strip().upper()
        super().save(*args, **kwargs)

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.discount_type == self.PERCENT and self.value > 100:
            raise ValidationError({"value": "Le pourcentage ne peut pas dépasser 100 %."})
        if self.maximum_discount is not None and self.maximum_discount < 0:
            raise ValidationError({"maximum_discount": "Le plafond ne peut pas être négatif."})
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError({"ends_at": "La fin doit être postérieure au début."})

    def __str__(self):
        return self.code


class Order(models.Model):
    PENDING = "pending_payment"
    AWAITING = "awaiting_payment"
    PAID = "paid"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    REVIEW = "payment_review"
    STATUS_CHOICES = [
        (PENDING, "En attente de paiement"), (AWAITING, "Paiement en cours"),
        (PAID, "Payée"), (CANCELLED, "Annulée"), (EXPIRED, "Expirée"),
        (REVIEW, "Paiement à vérifier"),
    ]

    FULFILLMENT_UNFULFILLED = "unfulfilled"
    FULFILLMENT_PREPARING = "preparing"
    FULFILLMENT_SHIPPED = "shipped"
    FULFILLMENT_DELIVERED = "delivered"
    FULFILLMENT_ON_HOLD = "on_hold"
    FULFILLMENT_CHOICES = [
        (FULFILLMENT_UNFULFILLED, "À préparer"),
        (FULFILLMENT_PREPARING, "En préparation"),
        (FULFILLMENT_SHIPPED, "Expédiée"),
        (FULFILLMENT_DELIVERED, "Livrée"),
        (FULFILLMENT_ON_HOLD, "En attente logistique"),
    ]

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    checkout_key = models.UUIDField(unique=True, editable=False)
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="store_orders")
    email = models.EmailField()
    full_name = models.CharField(max_length=160)
    phone = models.CharField(max_length=40, blank=True)
    address_line1 = models.CharField(max_length=180)
    address_line2 = models.CharField(max_length=180, blank=True)
    postal_code = models.CharField(max_length=20)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=2, default="FR")
    shipping_method = models.CharField(max_length=20)
    currency = models.CharField(max_length=3, default="eur")
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    promo_code_snapshot = models.CharField(max_length=32, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    shipping_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default=PENDING, db_index=True)
    fulfillment_status = models.CharField(
        max_length=20, choices=FULFILLMENT_CHOICES,
        default=FULFILLMENT_UNFULFILLED, db_index=True,
    )
    shipping_carrier = models.CharField(max_length=80, blank=True)
    tracking_number = models.CharField(max_length=120, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    internal_note = models.TextField(blank=True)
    stock_reserved = models.BooleanField(default=False, db_index=True)
    stock_committed = models.BooleanField(default=False)
    stock_requirements_snapshot = models.JSONField(default=dict, blank=True)
    cart_snapshot = models.JSONField(default=dict, blank=True)
    stripe_session_id = models.CharField(max_length=255, blank=True, db_index=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("status", "created_at"), name="order_status_created_idx")]
        constraints = [
            models.CheckConstraint(condition=Q(subtotal__gte=0), name="order_subtotal_nonnegative"),
            models.CheckConstraint(condition=Q(discount_amount__gte=0), name="order_discount_nonnegative"),
            models.CheckConstraint(condition=Q(shipping_amount__gte=0), name="order_shipping_nonnegative"),
            models.CheckConstraint(condition=Q(total__gte=0), name="order_total_nonnegative"),
        ]

    def __str__(self):
        return f"Commande {self.public_id} — {self.get_status_display()}"


class OrderLine(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey("product.Product", null=True, blank=True, on_delete=models.SET_NULL)
    variant = models.ForeignKey("product.ProductVariant", null=True, blank=True, on_delete=models.SET_NULL)
    offer_id_snapshot = models.PositiveBigIntegerField()
    product_name = models.CharField(max_length=220)
    variant_name = models.CharField(max_length=120, blank=True)
    quantity = models.PositiveSmallIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)
    components_snapshot = models.JSONField(default=list, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gte=1), name="order_line_quantity_positive"),
            models.CheckConstraint(condition=Q(unit_price__gte=0), name="order_line_unit_price_nonnegative"),
            models.CheckConstraint(condition=Q(line_total__gte=0), name="order_line_total_nonnegative"),
        ]


class PaymentAttempt(models.Model):
    CREATED = "created"
    OPEN = "open"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    EXPIRED = "expired"
    REVIEW = "requires_review"
    STATUS_CHOICES = [(v, v.replace("_", " ").title()) for v in (CREATED, OPEN, PROCESSING, SUCCEEDED, FAILED, EXPIRED, REVIEW)]
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="payment_attempts")
    provider = models.CharField(max_length=20, default="stripe")
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default=CREATED, db_index=True)
    stripe_session_id = models.CharField(max_length=255, blank=True, db_index=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="eur")
    failure_code = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)


class StripeWebhookEvent(models.Model):
    event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=120)
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-processed_at",)


class OrderEvent(models.Model):
    """Historique immuable des changements métier importants d'une commande."""
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="lifecycle_events")
    event_type = models.CharField(max_length=40, db_index=True)
    from_value = models.CharField(max_length=40, blank=True)
    to_value = models.CharField(max_length=40, blank=True)
    source = models.CharField(max_length=24, default="system")
    reason = models.TextField(blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    external_reference = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at", "-pk")


class Shipment(models.Model):
    """Un colis physique. Une commande peut avoir plusieurs expéditions."""
    DRAFT = "draft"
    LABEL_CREATED = "label_created"
    READY = "ready"
    ACCEPTED = "accepted"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERY_FAILED = "delivery_failed"
    PICKUP_POINT = "pickup_point"
    DELIVERED = "delivered"
    INCIDENT = "incident"
    LOST = "lost"
    RETURNING = "returning"
    RETURNED = "returned"
    STATUS_CHOICES = [
        (DRAFT, "Brouillon"), (LABEL_CREATED, "Étiquette créée"),
        (READY, "Prêt à collecter"), (ACCEPTED, "Pris en charge"),
        (IN_TRANSIT, "En transit"), (OUT_FOR_DELIVERY, "En cours de livraison"),
        (DELIVERY_FAILED, "Échec de livraison"), (PICKUP_POINT, "En point relais"),
        (DELIVERED, "Livré"), (INCIDENT, "Incident"), (LOST, "Perdu après investigation"),
        (RETURNING, "Retour expéditeur"), (RETURNED, "Retour reçu"),
    ]
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="shipments")
    carrier = models.CharField(max_length=80, blank=True)
    service = models.CharField(max_length=80, blank=True)
    shipping_method = models.CharField(max_length=40, blank=True)
    tracking_number = models.CharField(max_length=120, blank=True, db_index=True)
    tracking_url = models.URLField(max_length=500, blank=True)
    label_reference = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default=DRAFT, db_index=True)
    weight_grams = models.PositiveIntegerField(null=True, blank=True)
    length_cm = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    width_cm = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    height_cm = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    actual_shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    customer_shipping_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_shipments")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    handed_over_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.CheckConstraint(condition=Q(customer_shipping_amount__gte=0), name="shipment_customer_shipping_nonnegative"),
        ]


class ShipmentLine(models.Model):
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name="lines")
    order_line = models.ForeignKey(OrderLine, on_delete=models.PROTECT, related_name="shipment_allocations")
    quantity = models.PositiveSmallIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("shipment", "order_line"), name="shipment_line_unique"),
            models.CheckConstraint(condition=Q(quantity__gte=1), name="shipment_line_quantity_positive"),
        ]


class ShipmentEvent(models.Model):
    shipment = models.ForeignKey(Shipment, on_delete=models.PROTECT, related_name="events")
    status = models.CharField(max_length=24, choices=Shipment.STATUS_CHOICES)
    source = models.CharField(max_length=24, default="manual")
    external_event_id = models.CharField(max_length=255, blank=True, unique=True)
    description = models.TextField(blank=True)
    occurred_at = models.DateTimeField(null=True, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-occurred_at", "-created_at")


class ReturnRequest(models.Model):
    RECEIVED = "received"
    REVIEW = "under_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    IN_TRANSIT = "in_transit"
    ARRIVED = "arrived"
    INSPECTING = "inspecting"
    RESOLVED = "resolved"
    CLOSED = "closed"
    STATUS_CHOICES = [
        (RECEIVED, "Demande reçue"), (REVIEW, "En examen"), (ACCEPTED, "Acceptée"),
        (REJECTED, "Refusée"), (IN_TRANSIT, "Retour expédié"),
        (ARRIVED, "Retour reçu"), (INSPECTING, "Inspection"),
        (RESOLVED, "Résolue"), (CLOSED, "Clôturée"),
    ]
    REASONS = [
        ("withdrawal", "Rétractation"), ("non_conformity", "Non-conformité"),
        ("defective", "Produit défectueux"), ("transport_damage", "Dommage de transport"),
        ("missing_item", "Article manquant"), ("other", "Autre / geste commercial"),
    ]
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="return_requests")
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=RECEIVED, db_index=True)
    reason_category = models.CharField(max_length=24, choices=REASONS)
    reason = models.TextField()
    customer_note = models.TextField(blank=True)
    admin_note = models.TextField(blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="decided_returns")

    class Meta:
        ordering = ("-requested_at",)


class ReturnLine(models.Model):
    return_request = models.ForeignKey(ReturnRequest, on_delete=models.CASCADE, related_name="lines")
    order_line = models.ForeignKey(OrderLine, on_delete=models.PROTECT, related_name="return_allocations")
    quantity = models.PositiveSmallIntegerField()
    disposition = models.CharField(max_length=24, blank=True)
    inspected = models.BooleanField(default=False)
    restock_approved = models.BooleanField(default=False)
    inspected_at = models.DateTimeField(null=True, blank=True)
    inspection_note = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("return_request", "order_line"), name="return_line_unique"),
            models.CheckConstraint(condition=Q(quantity__gte=1), name="return_line_quantity_positive"),
        ]


class Refund(models.Model):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (PENDING, "En attente"), (PROCESSING, "En cours"),
        (SUCCEEDED, "Confirmé"), (FAILED, "Échec"), (CANCELLED, "Annulé"),
    ]
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="refunds")
    return_request = models.ForeignKey(ReturnRequest, null=True, blank=True, on_delete=models.PROTECT, related_name="refunds")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="eur")
    reason = models.TextField()
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=PENDING, db_index=True)
    stripe_refund_id = models.CharField(max_length=255, blank=True, unique=True)
    idempotency_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    external_payment_reference = models.CharField(max_length=255, blank=True)
    initiated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    requested_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)

    class Meta:
        ordering = ("-requested_at",)
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0), name="refund_amount_positive")]


class OrderIncident(models.Model):
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    CLOSED = "closed"
    STATUS_CHOICES = [(OPEN, "Ouvert"), (INVESTIGATING, "En cours"), (RESOLVED, "Résolu"), (CLOSED, "Clôturé")]
    CATEGORIES = [
        ("delay", "Retard"), ("failed_delivery", "Livraison échouée"),
        ("address", "Adresse incorrecte"), ("lost", "Colis perdu"),
        ("not_received", "Non-réception"), ("damage", "Article endommagé"),
        ("missing", "Article manquant"), ("other", "Autre"),
    ]
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="incidents")
    shipment = models.ForeignKey(Shipment, null=True, blank=True, on_delete=models.PROTECT, related_name="incidents")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=OPEN, db_index=True)
    category = models.CharField(max_length=24, choices=CATEGORIES)
    description = models.TextField()
    resolution = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_order_incidents")
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="resolved_order_incidents")
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)


class OrderNotification(models.Model):
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    STATUS_CHOICES = [(PENDING, "En attente"), (SENDING, "En cours"), (SENT, "Acceptée par le prestataire"), (FAILED, "Échec")]
    order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.PROTECT, related_name="notifications")
    event_key = models.CharField(max_length=100)
    recipient = models.EmailField()
    channel = models.CharField(max_length=16, default="email")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=PENDING, db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    external_id = models.CharField(max_length=255, blank=True)
    error_message = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("order", "event_key", "recipient", "channel"), name="order_notification_dedupe"),
        ]
        ordering = ("-created_at",)
