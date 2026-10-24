from decimal import Decimal

from django.db import migrations


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
        migrations.RemoveConstraint(model_name="productvariant", name="variant_price_nonnegative"),
        migrations.RemoveConstraint(model_name="productvariant", name="variant_ref_price_gt_sale"),
        migrations.RemoveField(model_name="productvariant", name="compare_at_price"),
        migrations.RemoveField(model_name="productvariant", name="price"),
    ]
