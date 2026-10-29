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
