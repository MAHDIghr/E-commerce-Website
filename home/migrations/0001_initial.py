# Migration for the admin-managed homepage signature carousel.
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("product", "0004_review_featured"),
    ]

    operations = [
        migrations.CreateModel(
            name="SignatureSelection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(help_text="Image propre à la sélection signature ; ne remplace pas les médias du produit.", upload_to="home/signature/%Y/%m/", verbose_name="Image de la carte")),
                ("alt_text", models.CharField(max_length=240, verbose_name="Texte alternatif")),
                ("position", models.PositiveSmallIntegerField(db_index=True, default=0, verbose_name="Ordre d'affichage")),
                ("is_active", models.BooleanField(db_index=True, default=True, verbose_name="Afficher sur l'accueil")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="signature_selections", to="product.product", verbose_name="Produit associé")),
            ],
            options={
                "verbose_name": "carte de la sélection signature",
                "verbose_name_plural": "sélection signature",
                "ordering": ("position", "pk"),
            },
        ),
        migrations.AddConstraint(
            model_name="signatureselection",
            constraint=models.UniqueConstraint(fields=("product",), name="unique_signature_product"),
        ),
    ]
