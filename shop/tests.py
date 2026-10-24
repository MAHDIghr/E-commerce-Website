import json
from decimal import Decimal

from django.test import Client, TestCase
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
            stock_quantity=4,
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

    def test_cart_api_exposes_fields_consumed_by_cart_bar(self):
        response = self.client.post(
            reverse("shop:cart_mutation"),
            data=json.dumps({
                "action": "add", "variant_id": self.variant.pk,
                "offer_id": self.offer.pk, "quantity": 2,
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        item = response.json()["items"][0]
        self.assertEqual(item["quantity"], 2)
        self.assertEqual(item["unit_price"], "89.90")
        self.assertEqual(item["line_total"], "179.80")

    def test_cart_uses_server_price_and_ignores_client_price(self):
        response = self.client.post(
            reverse("shop:cart_mutation"),
            data=json.dumps({
                "action": "add", "variant_id": self.variant.pk,
                "offer_id": self.offer.pk, "quantity": 1, "price": "0.01",
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["subtotal"], "89.90")
        self.assertEqual(payload["items"][0]["unit_price"], "89.90")

    def test_offer_options_returns_the_single_available_offer_for_quick_add(self):
        response = self.client.get(
            reverse("shop:offer_options", kwargs={"slug": self.product.slug}),
            {"variant_id": self.variant.pk},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["product"]["slug"], self.product.slug)
        self.assertEqual(len(payload["offers"]), 1)
        self.assertEqual(payload["offers"][0]["id"], self.offer.pk)
        self.assertEqual(payload["offers"][0]["price"], "89.90")
        self.assertEqual(payload["offers"][0]["component_count"], 1)

    def test_quick_add_offer_lookup_sets_csrf_cookie_and_accepts_server_validated_add(self):
        client = Client(enforce_csrf_checks=True)
        response = client.get(
            reverse("shop:offer_options", kwargs={"slug": self.product.slug}),
            {"variant_id": self.variant.pk},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", client.cookies)
        token = client.cookies["csrftoken"].value

        added = client.post(
            reverse("shop:cart_mutation"),
            data=json.dumps({
                "action": "add", "variant_id": self.variant.pk,
                "offer_id": self.offer.pk, "quantity": 1,
            }),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(added.status_code, 200)
        self.assertEqual(added.json()["count"], 1)

    def test_offer_options_lists_multiple_active_offers_with_server_prices(self):
        second_offer = ProductOffer.objects.create(
            product=self.product, title="Medium", badge=ProductOffer.BADGE_MEDIUM,
            price=Decimal("79.90"), is_active=True,
        )
        ProductOfferItem.objects.create(
            offer=second_offer, product=self.product, use_selected_variant=True, quantity=1,
        )
        response = self.client.get(
            reverse("shop:offer_options", kwargs={"slug": self.product.slug}),
            {"variant_id": self.variant.pk},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual([offer["id"] for offer in payload["offers"]], [self.offer.pk, second_offer.pk])
        self.assertEqual(payload["offers"][1]["price"], "79.90")

    def test_offer_options_rejects_variant_from_another_product(self):
        other = Product.objects.create(
            category=self.category, name="Autre sac", slug="autre-sac", is_active=True,
        )
        other_variant = ProductVariant.objects.create(
            product=other, sku="AUTRE-SAC-TEST", stock_quantity=2,
        )
        response = self.client.get(
            reverse("shop:offer_options", kwargs={"slug": self.product.slug}),
            {"variant_id": other_variant.pk},
        )
        self.assertEqual(response.status_code, 404)

    def test_configured_offer_price_is_independent_of_selected_color(self):
        self.variant.color_name = "Noir"
        self.variant.save(update_fields=["color_name"])
        response = self.client.post(
            reverse("shop:cart_mutation"),
            data=json.dumps({
                "action": "add", "variant_id": self.variant.pk,
                "offer_id": self.offer.pk, "quantity": 1,
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["subtotal"], "89.90")
        self.assertEqual(response.json()["items"][0]["unit_price"], "89.90")
        self.assertEqual(response.json()["items"][0]["components"], [])
        self.assertIn(self.product.name, response.json()["items"][0]["name"])

    def test_cart_mutations_require_csrf(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.get(reverse("shop:cart_api")).status_code, 200)
        response = client.post(
            reverse("shop:cart_mutation"),
            data=json.dumps({"action": "add", "variant_id": self.variant.pk, "offer_id": self.offer.pk, "quantity": 1}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_cart_add_requires_an_explicit_offer(self):
        response = self.client.post(
            reverse("shop:cart_mutation"),
            data=json.dumps({
                "action": "add", "variant_id": self.variant.pk, "quantity": 1,
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("offre", response.json()["error"].lower())
        self.assertEqual(self.client.get(reverse("shop:cart_api")).json()["count"], 0)

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
            data=json.dumps({"action": "add", "variant_id": self.variant.pk, "offer_id": self.offer.pk, "quantity": 5}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.client.get(reverse("shop:cart_api")).json()["count"], 0)

    def test_cart_rejects_addition_that_would_exceed_line_limit(self):
        self.variant.stock_quantity = 20
        self.variant.save(update_fields=["stock_quantity"])
        first = self.client.post(
            reverse("shop:cart_mutation"),
            data=json.dumps({"action": "add", "variant_id": self.variant.pk, "offer_id": self.offer.pk, "quantity": 8}),
            content_type="application/json",
        )
        self.assertEqual(first.status_code, 200)
        second = self.client.post(
            reverse("shop:cart_mutation"),
            data=json.dumps({"action": "add", "variant_id": self.variant.pk, "offer_id": self.offer.pk, "quantity": 3}),
            content_type="application/json",
        )
        self.assertEqual(second.status_code, 400)
        self.assertEqual(self.client.get(reverse("shop:cart_api")).json()["count"], 8)

    def test_cart_quantity_can_be_reduced_after_stock_decreases(self):
        add = self.client.post(
            reverse("shop:cart_mutation"),
            data=json.dumps({"action": "add", "variant_id": self.variant.pk, "offer_id": self.offer.pk, "quantity": 4}),
            content_type="application/json",
        )
        self.assertEqual(add.status_code, 200)
        self.variant.stock_quantity = 2
        self.variant.save(update_fields=["stock_quantity"])

        reduce_once = self.client.post(
            reverse("shop:cart_mutation"),
            data=json.dumps({"action": "update", "variant_id": self.variant.pk, "offer_id": self.offer.pk, "quantity": 3}),
            content_type="application/json",
        )
        self.assertEqual(reduce_once.status_code, 200)
        self.assertFalse(reduce_once.json()["items"][0]["available"])
        reduce_to_stock = self.client.post(
            reverse("shop:cart_mutation"),
            data=json.dumps({"action": "update", "variant_id": self.variant.pk, "offer_id": self.offer.pk, "quantity": 2}),
            content_type="application/json",
        )
        self.assertEqual(reduce_to_stock.status_code, 200)
        self.assertTrue(reduce_to_stock.json()["items"][0]["available"])

    def test_stock_is_shared_across_different_offers_for_the_same_variant(self):
        self.variant.stock_quantity = 3
        self.variant.save(update_fields=["stock_quantity"])
        second_offer = ProductOffer.objects.create(
            product=self.product, title="Medium", badge=ProductOffer.BADGE_MEDIUM,
            price=Decimal("99.90"), is_active=True,
        )
        ProductOfferItem.objects.create(
            offer=second_offer, product=self.product, use_selected_variant=True, quantity=1,
        )

        first = self.client.post(
            reverse("shop:cart_mutation"),
            data=json.dumps({
                "action": "add", "variant_id": self.variant.pk,
                "offer_id": self.offer.pk, "quantity": 2,
            }),
            content_type="application/json",
        )
        self.assertEqual(first.status_code, 200)
        second = self.client.post(
            reverse("shop:cart_mutation"),
            data=json.dumps({
                "action": "add", "variant_id": self.variant.pk,
                "offer_id": second_offer.pk, "quantity": 2,
            }),
            content_type="application/json",
        )
        self.assertEqual(second.status_code, 409)
        self.assertIn("error", second.json())
        # L'ajout refusé ne doit pas modifier la ligne déjà présente dans le panier.
        cart = self.client.get(reverse("shop:cart_api")).json()
        self.assertEqual(cart["count"], 2)
        self.assertEqual(len(cart["items"]), 1)
        self.assertEqual(cart["items"][0]["quantity"], 2)

    def test_stock_is_shared_across_offer_accessories(self):
        self.variant.stock_quantity = 5
        self.variant.save(update_fields=["stock_quantity"])
        accessory, accessory_variant, first_item = self._create_offer_accessory(stock=2)
        second_offer = ProductOffer.objects.create(
            product=self.product, title="Medium", badge=ProductOffer.BADGE_MEDIUM,
            price=Decimal("99.90"), is_active=True,
        )
        ProductOfferItem.objects.create(
            offer=second_offer, product=self.product, use_selected_variant=True, quantity=1,
        )
        second_item = ProductOfferItem.objects.create(
            offer=second_offer, product=accessory, variant=accessory_variant, quantity=1,
        )

        first = self.client.post(
            reverse("shop:cart_mutation"),
            data=json.dumps({
                "action": "add", "variant_id": self.variant.pk,
                "offer_id": self.offer.pk, "selected_item_ids": [first_item.pk],
                "quantity": 1,
            }),
            content_type="application/json",
        )
        self.assertEqual(first.status_code, 200)
        second = self.client.post(
            reverse("shop:cart_mutation"),
            data=json.dumps({
                "action": "add", "variant_id": self.variant.pk,
                "offer_id": second_offer.pk, "selected_item_ids": [second_item.pk],
                "quantity": 2,
            }),
            content_type="application/json",
        )
        self.assertEqual(second.status_code, 409)
        self.assertIn("error", second.json())
        # Le panier conserve uniquement l'offre acceptée, avec son cadeau sélectionné.
        cart = self.client.get(reverse("shop:cart_api")).json()
        self.assertEqual(cart["count"], 1)
        self.assertEqual(len(cart["items"]), 1)
        self.assertEqual(cart["items"][0]["quantity"], 1)
        self.assertEqual(len(cart["items"][0]["components"]), 1)

    def test_cart_rejects_fractional_quantity(self):
        response = self.client.post(
            reverse("shop:cart_mutation"),
            data=json.dumps({"action": "add", "variant_id": self.variant.pk, "offer_id": self.offer.pk, "quantity": 1.5}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get(reverse("shop:cart_api")).json()["count"], 0)

    def test_cart_can_be_cleared_without_product_identifiers(self):
        self.client.post(
            reverse("shop:cart_mutation"),
            data=json.dumps({"action": "add", "variant_id": self.variant.pk, "offer_id": self.offer.pk, "quantity": 1}),
            content_type="application/json",
        )
        response = self.client.post(
            reverse("shop:cart_mutation"),
            data=json.dumps({"action": "clear"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 0)

    def _create_offer_accessory(self, stock=5):
        accessory = Product.objects.create(
            category=self.category,
            name="Porte-cartes beige",
            slug="porte-cartes-beige-offert",
            is_active=True,
        )
        accessory_variant = ProductVariant.objects.create(
            product=accessory, sku="PORTE-CARTES-BEIGE-OFFER", color_name="Beige",
            stock_quantity=stock,
        )
        ProductMedia.objects.create(
            product=accessory, media_type=ProductMedia.IMAGE,
            source_url="https://cdn.example.test/porte-cartes.webp",
            alt_text="Porte-cartes beige", is_primary=True,
        )
        standalone_offer = ProductOffer.objects.create(
            product=accessory, title="Essentiel", badge=ProductOffer.BADGE_ESSENTIAL,
            price=Decimal("19.90"), reference_price=Decimal("24.90"), is_active=True,
        )
        ProductOfferItem.objects.create(
            offer=standalone_offer, product=accessory,
            use_selected_variant=True, quantity=1,
        )
        offer_item = ProductOfferItem.objects.create(
            offer=self.offer, product=accessory, variant=accessory_variant, quantity=1,
        )
        return accessory, accessory_variant, offer_item

    def test_offer_options_expose_optional_accessory_as_free_with_original_price(self):
        accessory, accessory_variant, offer_item = self._create_offer_accessory()
        response = self.client.get(
            reverse("shop:offer_options", kwargs={"slug": self.product.slug}),
            {"variant_id": self.variant.pk},
        )
        self.assertEqual(response.status_code, 200)
        offer = response.json()["offers"][0]
        self.assertEqual(len(offer["accessories"]), 1)
        gift = offer["accessories"][0]
        self.assertEqual(gift["item_id"], offer_item.pk)
        self.assertEqual(gift["name"], accessory.name)
        self.assertEqual(gift["image"], "https://cdn.example.test/porte-cartes.webp")
        self.assertEqual(gift["original_price"], "24.90")
        self.assertEqual(gift["unit_price"], "0.00")
        self.assertTrue(gift["available"])

    def test_selected_offer_accessory_is_free_and_does_not_change_offer_subtotal(self):
        accessory, accessory_variant, offer_item = self._create_offer_accessory()
        response = self.client.post(
            reverse("shop:cart_mutation"),
            data=json.dumps({
                "action": "add",
                "variant_id": self.variant.pk,
                "offer_id": self.offer.pk,
                "selected_item_ids": [offer_item.pk],
                "quantity": 1,
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["subtotal"], "89.90")
        self.assertEqual(len(payload["items"]), 1)
        gift = payload["items"][0]["components"][0]
        self.assertEqual(gift["name"], accessory.name)
        self.assertEqual(gift["original_price"], "24.90")
        self.assertEqual(gift["unit_price"], "0.00")
        self.assertTrue(gift["is_gift"])
        self.assertEqual(gift["image"], "https://cdn.example.test/porte-cartes.webp")

    def test_accessory_out_of_stock_does_not_block_the_main_offer(self):
        accessory, accessory_variant, offer_item = self._create_offer_accessory(stock=0)
        response = self.client.get(
            reverse("shop:offer_options", kwargs={"slug": self.product.slug}),
            {"variant_id": self.variant.pk},
        )
        self.assertEqual(response.status_code, 200)
        gift = response.json()["offers"][0]["accessories"][0]
        self.assertFalse(gift["available"])
        self.assertEqual(response.json()["offers"][0]["price"], "89.90")

    def test_cart_rejects_accessory_not_configured_for_selected_offer(self):
        other_offer = ProductOffer.objects.create(
            product=self.product, title="Medium", badge=ProductOffer.BADGE_MEDIUM,
            price=Decimal("99.90"), is_active=True,
        )
        ProductOfferItem.objects.create(
            offer=other_offer, product=self.product, use_selected_variant=True, quantity=1,
        )
        accessory, accessory_variant, offer_item = self._create_offer_accessory()
        response = self.client.post(
            reverse("shop:cart_mutation"),
            data=json.dumps({
                "action": "add", "variant_id": self.variant.pk,
                "offer_id": other_offer.pk, "selected_item_ids": [offer_item.pk],
                "quantity": 1,
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
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
