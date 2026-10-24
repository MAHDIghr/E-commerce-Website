from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("product", "0006_product_media_and_offer_reference_price")]

    operations = [
        migrations.AlterField(
            model_name="productoffer",
            name="is_featured",
            field=models.BooleanField(
                default=False,
                help_text="Sélectionne cette offre au chargement de la fiche ; les autres offres actives restent visibles.",
                verbose_name="Sélectionnée par défaut sur la fiche produit",
            ),
        ),
    ]
