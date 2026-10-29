# Generated migration for consent-aware newsletter subscriptions.
import django.utils.timezone
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="NewsletterSubscription",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email", models.EmailField(max_length=254, unique=True)),
                ("is_confirmed", models.BooleanField(db_index=True, default=False)),
                ("is_active", models.BooleanField(db_index=True, default=False)),
                ("consent_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("consent_version", models.CharField(default="newsletter-v1", max_length=32)),
                ("confirmation_token_hash", models.CharField(blank=True, max_length=64)),
                ("confirmation_expires_at", models.DateTimeField(blank=True, null=True)),
                ("unsubscribe_token", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("confirmed_at", models.DateTimeField(blank=True, null=True)),
                ("unsubscribed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "inscription à la newsletter",
                "verbose_name_plural": "inscriptions à la newsletter",
                "ordering": ("-created_at",),
            },
        ),
    ]
