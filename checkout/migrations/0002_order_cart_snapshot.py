from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("checkout", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="cart_snapshot",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
