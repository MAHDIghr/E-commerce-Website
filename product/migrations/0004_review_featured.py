from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("product", "0003_offer_choices_and_order"),
    ]

    operations = [
        migrations.AddField(
            model_name="review",
            name="is_featured",
            field=models.BooleanField(db_index=True, default=False, verbose_name="Mis en avant sur l’accueil"),
        ),
        migrations.AddConstraint(
            model_name="review",
            constraint=models.CheckConstraint(
                condition=models.Q(is_featured=False) | models.Q(is_approved=True),
                name="featured_review_must_be_approved",
            ),
        ),
    ]
