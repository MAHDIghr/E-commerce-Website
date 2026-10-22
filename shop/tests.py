import json
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from product.models import Category, Product, ProductMedia, ProductOffer, ProductOfferItem, ProductVariant


class CartAndSearchTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Sacs à main", slug="sacs-a-main")
        self.product = Product.objects.create(
            category=self.category,
            name="Sac cabas camel",
            slug="sac-cabas-camel",
            short_description="Un sac élégant pour tous les jours",
            is_active=True,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product, sku="CABAS-CAMEL-TEST", color_name="Camel",
            color_slug="camel", color_code="#B07A4A",
            price=Decimal("89.90"), stock_quantity=4,
        )
        ProductMedia.objects.create(
            product=self.product, media_type=ProductMedia.IMAGE,
            source_url="https://cdn.example.test/cabas.webp",
            alt_text="Sac cabas camel", is_primary=True,
        )
        offer = ProductOffer.objects.create(
            product=self.product, title="Essentiel", badge=ProductOffer.BADGE_ESSENTIAL,
            price=Decimal("89.90"), is_active=True,
        )
        ProductOfferItem.objects.create(
            offer=offer, product=self.product, use_selected_variant=True, quantity=1,
        )
        self.offer = offer

    def test_cart_uses_server_price_and_ignores_client_price(self):
        response = self.client.post(
            reverse("shop:cart_mutation"),
            data=json.dumps({
                "action": "add", "variant_id": self.variant.pk,
                "offer_id": 0, "quantity": 1, "price": "0.01",
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["subtotal"], "89.90")
        self.assertEqual(payload["items"][0]["unit_price"], "89.90")

    def test_cart_rejects_unknown_variant(self):
        response = self.client.post(
            reverse("shop:cart_mutation"),
            data=json.dumps({"action": "add", "variant_id": 999999, "quantity": 1}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_cart_enforces_stock_limit(self):
        response = self.client.post(
            reverse("shop:cart_mutation"),
            data=json.dumps({"action": "add", "variant_id": self.variant.pk, "quantity": 5}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.client.get(reverse("shop:cart_api")).json()["count"], 0)

    def test_search_suggestions_only_return_published_products(self):
        response = self.client.get(reverse("shop:search_suggestions"), {"q": "cabas camel"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["results"]), 1)
        self.assertEqual(payload["results"][0]["name"], "Sac cabas camel")
        self.assertEqual(payload["results"][0]["url"], "/produit/sac-cabas-camel/")

    def test_catalog_search_filters_products(self):
        response = self.client.get(reverse("shop:catalog"), {"q": "camel"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Résultats pour")
        self.assertContains(response, "sac-cabas-camel")
