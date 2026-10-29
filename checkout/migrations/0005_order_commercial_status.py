from django.db import migrations, models


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
    ]
