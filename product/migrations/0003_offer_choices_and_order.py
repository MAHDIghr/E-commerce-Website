from django.db import migrations, models


def normalize_offer_choices(apps, schema_editor):
    ProductOffer = apps.get_model("product", "ProductOffer")
    delivery_aliases = {
        "livraison gratuite": "free",
        "gratuite": "free",
        "free": "free",
        "livraison payante": "paid",
        "payante": "paid",
        "paid": "paid",
    }
    product_ids = ProductOffer.objects.order_by().values_list("product_id", flat=True).distinct()
    for product_id in product_ids:
        offers = ProductOffer.objects.filter(product_id=product_id).order_by("position", "pk")
        for index, offer in enumerate(offers):
            if index == 0:
                offer.badge = "essential"
                offer.position = 0
            elif index == 1:
                offer.badge = "medium"
                offer.position = 1
            elif index == 2:
                offer.badge = "premium"
                offer.position = 2
            else:
                # Keep historical data, but deactivate offers beyond the supported three tiers.
                offer.badge = "premium"
                offer.position = 2
                offer.is_active = False
            offer.title = {"essential": "Essentiel", "medium": "Medium", "premium": "Premium"}[offer.badge]
            raw_delivery = (offer.display_delivery_label or "").strip().lower()
            offer.display_delivery_label = delivery_aliases.get(raw_delivery, "paid")
            offer.save(update_fields=["badge", "title", "display_delivery_label", "position", "is_active"])


class Migration(migrations.Migration):
    dependencies = [
        ("product", "0002_uploaded_media"),
    ]

    operations = [
        migrations.RunPython(normalize_offer_choices, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="productoffer",
            name="badge",
            field=models.CharField(
                choices=[("essential", "Essentiel"), ("medium", "Medium"), ("premium", "Premium")],
                default="essential",
                max_length=20,
                verbose_name="Badge",
            ),
        ),
        migrations.AlterField(
            model_name="productoffer",
            name="display_delivery_label",
            field=models.CharField(
                choices=[("paid", "Livraison payante"), ("free", "Livraison gratuite")],
                default="paid",
                help_text="Ce choix décrit l'offre et ne calcule pas les frais de livraison.",
                max_length=10,
                verbose_name="Type de livraison",
            ),
        ),
        migrations.AlterField(
            model_name="productoffer",
            name="position",
            field=models.PositiveIntegerField(default=0, editable=False, verbose_name="Ordre automatique"),
        ),
        migrations.AddConstraint(
            model_name="productoffer",
            constraint=models.UniqueConstraint(
                condition=models.Q(is_active=True),
                fields=("product", "badge"),
                name="unique_active_offer_badge",
            ),
        ),
    ]
