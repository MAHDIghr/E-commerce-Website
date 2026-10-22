from django.db import migrations, models


def normalize_offer_choices(apps, schema_editor):
    ProductOffer = apps.get_model("product", "ProductOffer")
    aliases = {
        "essentiel": "essential",
        "essential": "essential",
        "moyen": "medium",
        "medium": "medium",
        "premium": "premium",
    }
    delivery_aliases = {
        "livraison gratuite": "free",
        "gratuite": "free",
        "free": "free",
        "livraison payante": "paid",
        "payante": "paid",
        "paid": "paid",
    }
    for offer in ProductOffer.objects.all().iterator():
        raw_badge = (offer.badge or "").strip().lower()
        offer.badge = aliases.get(raw_badge, "essential")
        raw_delivery = (offer.display_delivery_label or "").strip().lower()
        offer.display_delivery_label = delivery_aliases.get(raw_delivery, "paid")
        offer.position = {"essential": 0, "medium": 1, "premium": 2}[offer.badge]
        offer.save(update_fields=["badge", "display_delivery_label", "position"])


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
    ]
