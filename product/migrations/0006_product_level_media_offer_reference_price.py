from decimal import Decimal

from django.db import migrations, models
import django.core.validators
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("product", "0005_offer_only_pricing"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="productmedia",
            name="media_product_variant_pos_idx",
        ),
        migrations.AddIndex(
            model_name="productmedia",
            index=models.Index(fields=["product", "position"], name="media_product_position_idx"),
        ),
        migrations.AddField(
            model_name="productoffer",
            name="reference_price",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Facultatif. Saisissez un prix supérieur au prix de l'offre pour afficher une réduction.",
                max_digits=10,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal("0.00"))],
                verbose_name="Prix de référence (€)",
            ),
        ),
        migrations.AddConstraint(
            model_name="productoffer",
            constraint=models.CheckConstraint(
                condition=Q(reference_price__isnull=True) | Q(reference_price__gt=models.F("price")),
                name="offer_reference_price_gt_price",
            ),
        ),
        migrations.RemoveField(
            model_name="productmedia",
            name="variant",
        ),
    ]
