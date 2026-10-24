from decimal import Decimal

from django.db import migrations, models


def normalize_primary_media(apps, schema_editor):
    ProductMedia = apps.get_model("product", "ProductMedia")
    db = schema_editor.connection.alias
    product_ids = ProductMedia.objects.using(db).filter(is_primary=True).values_list("product_id", flat=True).distinct()
    for product_id in product_ids:
        primary_ids = list(
            ProductMedia.objects.using(db).filter(product_id=product_id, is_primary=True)
            .order_by("position", "pk").values_list("pk", flat=True)
        )
        if len(primary_ids) > 1:
            ProductMedia.objects.using(db).filter(pk__in=primary_ids[1:]).update(is_primary=False)


def ensure_offer_prices(apps, schema_editor):
    """Move any legacy variant price into an Essential offer before removing the fields."""
    Product = apps.get_model("product", "Product")
    ProductVariant = apps.get_model("product", "ProductVariant")
    ProductOffer = apps.get_model("product", "ProductOffer")
    ProductOfferItem = apps.get_model("product", "ProductOfferItem")
    db = schema_editor.connection.alias

    for product in Product.objects.using(db).all().iterator():
        offers = ProductOffer.objects.using(db).filter(product_id=product.pk)
        essential = offers.filter(badge="essential").first()
        first_variant = ProductVariant.objects.using(db).filter(
            product_id=product.pk, is_active=True
        ).order_by("position", "pk").first()
        if essential is None:
            essential = ProductOffer.objects.using(db).create(
                product_id=product.pk,
                title="Essentiel",
                badge="essential",
                display_delivery_label="paid",
                price=first_variant.price if first_variant else Decimal("0.00"),
                is_featured=not offers.filter(is_active=True, is_featured=True).exists(),
                is_active=first_variant is not None,
                position=0,
            )
        if not ProductOfferItem.objects.using(db).filter(
            offer_id=essential.pk, product_id=product.pk, use_selected_variant=True
        ).exists():
            ProductOfferItem.objects.using(db).create(
                offer_id=essential.pk,
                product_id=product.pk,
                variant_id=None,
                use_selected_variant=True,
                quantity=1,
                position=0,
            )


class Migration(migrations.Migration):
    dependencies = [("product", "0004_review_featured")]

    operations = [
        migrations.RunPython(ensure_offer_prices, migrations.RunPython.noop),
        migrations.RunPython(normalize_primary_media, migrations.RunPython.noop),
        migrations.RemoveConstraint(model_name="productmedia", name="one_primary_common_media"),
        migrations.RemoveConstraint(model_name="productmedia", name="one_primary_variant_media"),
        migrations.AddConstraint(
            model_name="productmedia",
            constraint=models.UniqueConstraint(
                condition=models.Q(is_primary=True),
                fields=("product",),
                name="one_primary_media_per_product",
            ),
        ),
        migrations.RemoveConstraint(model_name="productvariant", name="variant_price_nonnegative"),
        migrations.RemoveConstraint(model_name="productvariant", name="variant_ref_price_gt_sale"),
        migrations.RemoveField(model_name="productvariant", name="compare_at_price"),
        migrations.RemoveField(model_name="productvariant", name="price"),
        migrations.AlterField(
            model_name="productvariant",
            name="sku",
            field=models.CharField(max_length=80, unique=True, verbose_name="Référence interne de la variante"),
        ),
        migrations.AlterField(
            model_name="category",
            name="position",
            field=models.PositiveIntegerField(db_index=True, default=0, verbose_name="Ordre d'affichage des catégories"),
        ),
        migrations.AlterField(
            model_name="productvariant",
            name="position",
            field=models.PositiveIntegerField(default=0, verbose_name="Ordre d'affichage des couleurs"),
        ),
        migrations.AlterField(
            model_name="productmedia",
            name="position",
            field=models.PositiveIntegerField(default=0, verbose_name="Ordre d'affichage des médias"),
        ),
        migrations.AlterField(
            model_name="productreason",
            name="position",
            field=models.PositiveIntegerField(default=0, verbose_name="Ordre d'affichage des arguments"),
        ),
        migrations.AlterField(
            model_name="productcontentitem",
            name="position",
            field=models.PositiveIntegerField(default=0, verbose_name="Ordre d'affichage des éléments"),
        ),
        migrations.AlterField(
            model_name="productcraftdetail",
            name="position",
            field=models.PositiveIntegerField(default=0, verbose_name="Ordre d'affichage des détails de fabrication"),
        ),
        migrations.AlterField(
            model_name="productusage",
            name="position",
            field=models.PositiveIntegerField(default=0, verbose_name="Ordre d'affichage des situations d'usage"),
        ),
        migrations.AlterField(
            model_name="productfaq",
            name="position",
            field=models.PositiveIntegerField(default=0, verbose_name="Ordre d'affichage des questions fréquentes"),
        ),
        migrations.AlterField(
            model_name="productoffer",
            name="position",
            field=models.PositiveIntegerField(default=0, editable=False, verbose_name="Ordre d'affichage des offres (automatique)"),
        ),
        migrations.AlterField(
            model_name="productofferitem",
            name="position",
            field=models.PositiveIntegerField(default=0, verbose_name="Ordre d'affichage des composants de l'offre"),
        ),
    ]
