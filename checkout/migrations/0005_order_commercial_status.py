from django.db import migrations, models


def backfill_commercial_status(apps, schema_editor):
    Order = apps.get_model("checkout", "Order")
    Order.objects.filter(status="paid").update(commercial_status="confirmed")
    Order.objects.filter(status="payment_review").update(commercial_status="on_hold")
    Order.objects.filter(status__in=["cancelled", "expired"]).update(commercial_status="cancelled")
    Order.objects.filter(status="paid", fulfillment_status="preparing").update(commercial_status="preparing")
    Order.objects.filter(status="paid", fulfillment_status="shipped").update(commercial_status="shipped")
    Order.objects.filter(status="paid", fulfillment_status="delivered").update(commercial_status="delivered")
    Order.objects.filter(status="paid", fulfillment_status="on_hold").update(commercial_status="on_hold")


class Migration(migrations.Migration):
    dependencies = [
        ("checkout", "0004_order_lifecycle"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="commercial_status",
            field=models.CharField(
                choices=[
                    ("pending_payment", "En attente de paiement"),
                    ("confirmed", "Confirmée"),
                    ("processing", "En traitement"),
                    ("preparing", "En préparation"),
                    ("ready_to_ship", "Prête à expédier"),
                    ("shipped", "Expédiée"),
                    ("delivered", "Livrée"),
                    ("completed", "Terminée"),
                    ("cancelled", "Annulée"),
                    ("on_hold", "Suspendue"),
                ],
                db_index=True,
                default="pending_payment",
                max_length=24,
            ),
        ),
        migrations.RunPython(backfill_commercial_status, migrations.RunPython.noop),
    ]
