"""Merge the existing promo-code migration with order fulfillment fields.

PromoCode and the order discount snapshot are already created by
0003_promo_codes. This migration only joins that branch with the
independent fulfillment migration; it deliberately performs no schema
operations to avoid creating duplicate tables or columns.
"""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("checkout", "0003_promo_codes"),
        ("checkout", "0002_order_fulfillment_management"),
    ]

    operations = []
