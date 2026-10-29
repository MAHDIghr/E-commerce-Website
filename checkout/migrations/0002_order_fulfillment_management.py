from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("checkout", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="order",
            name="fulfillment_status",
            field=models.CharField(
                choices=[
                    ("unfulfilled", "À préparer"),
                    ("preparing", "En préparation"),
                    ("shipped", "Expédiée"),
                    ("delivered", "Livrée"),
                    ("on_hold", "En attente logistique"),
                ],
                db_index=True,
                default="unfulfilled",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="shipping_carrier",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="order",
            name="tracking_number",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="order",
            name="shipped_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="order",
            name="delivered_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="order",
            name="internal_note",
            field=models.TextField(blank=True),
        ),
    ]
