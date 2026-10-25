# Generated for the first persistent checkout implementation.
import uuid
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("product", "0005_offer_only_pricing"),
    ]
    operations = [
        migrations.CreateModel(
            name="Order",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("checkout_key", models.UUIDField(editable=False, unique=True)),
                ("email", models.EmailField(max_length=254)),
                ("full_name", models.CharField(max_length=160)),
                ("phone", models.CharField(blank=True, max_length=40)),
                ("address_line1", models.CharField(max_length=180)),
                ("address_line2", models.CharField(blank=True, max_length=180)),
                ("postal_code", models.CharField(max_length=20)),
                ("city", models.CharField(max_length=100)),
                ("country", models.CharField(max_length=2, default="FR")),
                ("shipping_method", models.CharField(max_length=20)),
                ("currency", models.CharField(default="eur", max_length=3)),
                ("subtotal", models.DecimalField(decimal_places=2, max_digits=12)),
                ("shipping_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=10)),
                ("total", models.DecimalField(decimal_places=2, max_digits=12)),
                ("status", models.CharField(choices=[("pending_payment", "En attente de paiement"), ("awaiting_payment", "Paiement en cours"), ("paid", "Payée"), ("cancelled", "Annulée"), ("expired", "Expirée"), ("payment_review", "Paiement à vérifier")], db_index=True, default="pending_payment", max_length=24)),
                ("stock_reserved", models.BooleanField(db_index=True, default=False)),
                ("stock_committed", models.BooleanField(default=False)),
                ("stock_requirements_snapshot", models.JSONField(blank=True, default=dict)),
                ("stripe_session_id", models.CharField(blank=True, db_index=True, max_length=255)),
                ("stripe_payment_intent_id", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("customer", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="store_orders", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-created_at",), "indexes": [models.Index(fields=["status", "created_at"], name="order_status_created_idx")], "constraints": [models.CheckConstraint(condition=models.Q(("subtotal__gte", 0)), name="order_subtotal_nonnegative"), models.CheckConstraint(condition=models.Q(("shipping_amount__gte", 0)), name="order_shipping_nonnegative"), models.CheckConstraint(condition=models.Q(("total__gte", 0)), name="order_total_nonnegative")]},
        ),
        migrations.CreateModel(
            name="OrderLine",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("offer_id_snapshot", models.PositiveBigIntegerField()),
                ("product_name", models.CharField(max_length=220)),
                ("variant_name", models.CharField(blank=True, max_length=120)),
                ("quantity", models.PositiveSmallIntegerField()),
                ("unit_price", models.DecimalField(decimal_places=2, max_digits=10)),
                ("line_total", models.DecimalField(decimal_places=2, max_digits=12)),
                ("components_snapshot", models.JSONField(blank=True, default=list)),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lines", to="checkout.order")),
                ("product", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="product.product")),
                ("variant", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="product.productvariant")),
            ],
            options={"constraints": [models.CheckConstraint(condition=models.Q(("quantity__gte", 1)), name="order_line_quantity_positive"), models.CheckConstraint(condition=models.Q(("unit_price__gte", 0)), name="order_line_unit_price_nonnegative"), models.CheckConstraint(condition=models.Q(("line_total__gte", 0)), name="order_line_total_nonnegative")]},
        ),
        migrations.CreateModel(
            name="PaymentAttempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider", models.CharField(default="stripe", max_length=20)),
                ("status", models.CharField(choices=[("created", "Created"), ("open", "Open"), ("processing", "Processing"), ("succeeded", "Succeeded"), ("failed", "Failed"), ("expired", "Expired"), ("requires_review", "Requires Review")], db_index=True, default="created", max_length=24)),
                ("stripe_session_id", models.CharField(blank=True, db_index=True, max_length=255)),
                ("stripe_payment_intent_id", models.CharField(blank=True, max_length=255)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("currency", models.CharField(default="eur", max_length=3)),
                ("failure_code", models.CharField(blank=True, max_length=80)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payment_attempts", to="checkout.order")),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.CreateModel(
            name="StripeWebhookEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_id", models.CharField(max_length=255, unique=True)),
                ("event_type", models.CharField(max_length=120)),
                ("processed_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ("-processed_at",)},
        ),
    ]
