from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from product.models import (
    Category, Product, ProductOffer, ProductOfferItem, ProductVariant,
)


class DashboardAccessTests(TestCase):
    def test_dashboard_redirects_anonymous_visitors_to_login(self):
        response = self.client.get(reverse("dashboard:home"))
        self.assertRedirects(
            response,
            f"{reverse('dashboard:login')}?next={reverse('dashboard:home')}",
            fetch_redirect_response=False,
        )

    def test_active_superuser_can_open_dashboard(self):
        admin_user = get_user_model().objects.create_superuser(
            username="site-admin", email="admin@example.test", password="StrongTestPassword!2026"
        )
        self.client.force_login(admin_user)
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Vue d’ensemble")

    def test_staff_user_without_superuser_flag_cannot_sign_in(self):
        user = get_user_model().objects.create_user(
            username="staff-only", password="StrongTestPassword!2026", is_staff=True,
        )
        response = self.client.post(reverse("dashboard:login"), {
            "username": "staff-only",
            "password": "StrongTestPassword!2026",
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertFalse(user.is_superuser)


class AutomaticOfferTests(TestCase):
    def test_new_product_gets_inactive_essential_offer_and_main_item(self):
        category = Category.objects.create(name="Sacs", slug="sacs-auto-offer")
        product = Product.objects.create(
            category=category, name="Sac test", slug="sac-test-auto-offer",
        )

        offer = ProductOffer.objects.get(product=product, badge=ProductOffer.BADGE_ESSENTIAL)
        item = ProductOfferItem.objects.get(offer=offer)

        self.assertFalse(offer.is_active)
        self.assertEqual(offer.price, Decimal("0.00"))
        self.assertEqual(item.product, product)
        self.assertTrue(item.use_selected_variant)
        self.assertIsNone(item.variant_id)

    def test_first_active_variant_initializes_automatic_essential_offer(self):
        category = Category.objects.create(name="Accessoires", slug="accessoires-auto-offer")
        product = Product.objects.create(
            category=category, name="Portefeuille test", slug="portefeuille-test-auto-offer",
        )
        variant = ProductVariant.objects.create(
            product=product, sku="PORTEFEUILLE-AUTO-001",
            price=Decimal("24.90"), stock_quantity=3, is_active=True,
        )

        offer = ProductOffer.objects.get(product=product, badge=ProductOffer.BADGE_ESSENTIAL)
        self.assertTrue(offer.is_active)
        self.assertEqual(offer.price, variant.price)
        self.assertEqual(offer.title, "Essentiel")
        self.assertTrue(offer.items.filter(product=product, use_selected_variant=True).exists())
