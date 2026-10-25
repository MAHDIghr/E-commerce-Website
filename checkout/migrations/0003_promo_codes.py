import decimal
from django.db import migrations, models


def create_welcome_code(apps, schema_editor):
    PromoCode = apps.get_model("checkout", "PromoCode")
    PromoCode.objects.get_or_create(code="BIENVENUE", defaults={
        "discount_type": "percent", "value": decimal.Decimal("15.00"),
        "minimum_subtotal": decimal.Decimal("20.00"), "maximum_discount": None,
        "is_active": True, "once_per_email": True,
    })


def remove_welcome_code(apps, schema_editor):
    apps.get_model("checkout", "PromoCode").objects.filter(code="BIENVENUE").delete()


class Migration(migrations.Migration):
    dependencies = [("checkout", "0002_order_cart_snapshot")]
    operations = [
        migrations.CreateModel(name="PromoCode", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("code", models.CharField(max_length=32, unique=True)),
            ("discount_type", models.CharField(choices=[("percent", "Pourcentage"), ("fixed", "Montant fixe")], default="percent", max_length=8)),
            ("value", models.DecimalField(decimal_places=2, max_digits=8)),
            ("minimum_subtotal", models.DecimalField(decimal_places=2, default=decimal.Decimal("0.00"), max_digits=10)),
            ("maximum_discount", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
            ("starts_at", models.DateTimeField(blank=True, null=True)),
            ("ends_at", models.DateTimeField(blank=True, null=True)),
            ("is_active", models.BooleanField(db_index=True, default=True)),
            ("once_per_email", models.BooleanField(default=True)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
        ], options={"ordering": ("code",)}),
        migrations.AddConstraint(model_name="promocode", constraint=models.CheckConstraint(condition=models.Q(("value__gt", 0)), name="promo_value_positive")),
        migrations.AddConstraint(model_name="promocode", constraint=models.CheckConstraint(condition=models.Q(("minimum_subtotal__gte", 0)), name="promo_min_subtotal_nonnegative")),
        migrations.AddField(model_name="order", name="promo_code_snapshot", field=models.CharField(blank=True, max_length=32)),
        migrations.AddField(model_name="order", name="discount_amount", field=models.DecimalField(decimal_places=2, default=decimal.Decimal("0.00"), max_digits=10)),
        migrations.AddConstraint(model_name="order", constraint=models.CheckConstraint(condition=models.Q(("discount_amount__gte", 0)), name="order_discount_nonnegative")),
        migrations.RunPython(create_welcome_code, remove_welcome_code),
    ]
