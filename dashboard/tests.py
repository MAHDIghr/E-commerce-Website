from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from product.models import (
    Category, Product, ProductOffer, ProductOfferItem, ProductVariant,
)
from .services import ensure_default_offer


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

        offer = ensure_default_offer(product)
        item = ProductOfferItem.objects.get(offer=offer)

        self.assertFalse(offer.is_active)
        self.assertEqual(offer.price, Decimal("0.00"))
        self.assertEqual(item.product, product)
        self.assertTrue(item.use_selected_variant)
        self.assertIsNone(item.variant_id)

    def test_active_variant_does_not_create_a_variant_price(self):
        category = Category.objects.create(name="Accessoires", slug="accessoires-auto-offer")
        product = Product.objects.create(
            category=category, name="Portefeuille test", slug="portefeuille-test-auto-offer",
        )
        variant = ProductVariant.objects.create(
            product=product, sku="PORTEFEUILLE-AUTO-001",
            stock_quantity=3, is_active=True,
        )

        offer = ensure_default_offer(product)
        self.assertFalse(offer.is_active)
        self.assertEqual(offer.price, Decimal("0.00"))
        self.assertEqual(offer.title, "Essentiel")
        self.assertTrue(offer.items.filter(product=product, use_selected_variant=True).exists())


class DashboardCatalogManagementTests(TestCase):
    def setUp(self):
        admin_user = get_user_model().objects.create_superuser(
            username="catalog-admin", email="catalog@example.test", password="StrongTestPassword!2026"
        )
        self.client.force_login(admin_user)
        self.category = Category.objects.create(name="Sacs test", slug="sacs-dashboard-test")
        self.product = Product.objects.create(
            category=self.category, name="Cabas dashboard", slug="cabas-dashboard-test",
        )

    def test_category_cannot_be_deleted_while_products_are_attached(self):
        response = self.client.post(reverse("dashboard:category_delete", args=[self.category.pk]))
        self.assertRedirects(response, reverse("dashboard:categories"), fetch_redirect_response=False)
        self.assertTrue(Category.objects.filter(pk=self.category.pk).exists())

    def test_empty_category_can_be_deleted(self):
        empty = Category.objects.create(name="Catégorie vide", slug="categorie-vide-dashboard")
        response = self.client.post(reverse("dashboard:category_delete", args=[empty.pk]))
        self.assertRedirects(response, reverse("dashboard:categories"), fetch_redirect_response=False)
        self.assertFalse(Category.objects.filter(pk=empty.pk).exists())

    def test_product_can_be_deleted_with_its_own_offers(self):
        offer = ProductOffer.objects.create(
            product=self.product, title="Essentiel", badge=ProductOffer.BADGE_ESSENTIAL,
            price=Decimal("35.00"), is_active=False,
        )
        ProductOfferItem.objects.create(
            offer=offer, product=self.product, use_selected_variant=True, quantity=1,
        )
        response = self.client.post(reverse("dashboard:product_delete", args=[self.product.pk]))
        self.assertRedirects(response, reverse("dashboard:products"), fetch_redirect_response=False)
        self.assertFalse(Product.objects.filter(pk=self.product.pk).exists())

    def test_offers_page_filters_by_product_and_badge(self):
        offer = ProductOffer.objects.create(
            product=self.product, title="Medium", badge=ProductOffer.BADGE_MEDIUM,
            price=Decimal("45.00"), is_active=False,
        )
        response = self.client.get(reverse("dashboard:offers"), {
            "product": self.product.pk, "badge": ProductOffer.BADGE_MEDIUM, "state": "inactive",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "45,00 €")
        self.assertEqual(list(response.context["offers"]), [offer])
        self.assertEqual(response.context["offers"][0].price, Decimal("45.00"))
