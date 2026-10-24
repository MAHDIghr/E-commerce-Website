from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("product", "0005_offer_only_pricing")]

    operations = [
        migrations.RemoveIndex(
            model_name="productmedia",
            name="media_product_variant_pos_idx",
        ),
        migrations.RemoveField(
            model_name="productmedia",
            name="variant",
        ),
        migrations.AddIndex(
            model_name="productmedia",
            index=models.Index(fields=["product", "position"], name="media_product_pos_idx"),
        ),
        migrations.AddField(
            model_name="productoffer",
            name="reference_price",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=10,
                null=True,
                validators=[MinValueValidator(Decimal("0.00"))],
                verbose_name="Prix de référence (€)",
                help_text="Facultatif. À renseigner uniquement si une réduction réelle est applicable ; doit être supérieur au prix de l'offre.",
            ),
        ),
        migrations.AddConstraint(
            model_name="productoffer",
            constraint=models.CheckConstraint(
                condition=models.Q(("reference_price__isnull", True))
                | models.Q(("reference_price__gt", models.F("price"))),
                name="offer_reference_gt_price",
            ),
        ),
    ]
