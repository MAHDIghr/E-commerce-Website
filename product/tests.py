import base64
import json
import tempfile
from decimal import Decimal

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.staticfiles import finders
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .admin import ProductAdmin
from .models import (
    Category, Product, ProductMedia, ProductOffer, ProductOfferItem,
    ProductVariant, Review,
)


class CatalogModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Sacs", slug="sacs")
        self.product = Product.objects.create(
            category=self.category, name="Cabas camel", slug="cabas-camel",
            is_active=True,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product, sku="CABAS-CAMEL", color_name="Camel",
            color_slug="camel", color_code="#B07A4A",
            stock_quantity=4,
        )

    def test_offer_badge_controls_title_and_order(self):
        premium = ProductOffer.objects.create(
            product=self.product, title="Texte libre", badge=ProductOffer.BADGE_PREMIUM,
            price=Decimal("129.90"),
        )
        medium = ProductOffer.objects.create(
            product=self.product, title="Texte libre", badge=ProductOffer.BADGE_MEDIUM,
            price=Decimal("109.90"),
        )
        essential = ProductOffer.objects.create(
            product=self.product, title="Texte libre", badge=ProductOffer.BADGE_ESSENTIAL,
            price=Decimal("89.90"),
        )
        self.assertEqual(essential.title, "Essentiel")
        self.assertEqual(medium.title, "Medium")
        self.assertEqual(premium.title, "Premium")
        self.assertEqual(list(self.product.offers.values_list("badge", flat=True)), [
            ProductOffer.BADGE_ESSENTIAL, ProductOffer.BADGE_MEDIUM, ProductOffer.BADGE_PREMIUM,
        ])

    def test_offer_reference_price_must_exceed_offer_price(self):
        offer = ProductOffer(
            product=self.product, title="Essentiel", badge=ProductOffer.BADGE_ESSENTIAL,
            price=Decimal("89.90"), reference_price=Decimal("119.90"),
        )
        offer.full_clean()
        offer.reference_price = Decimal("89.90")
        with self.assertRaises(ValidationError):
            offer.full_clean()

    def test_catalog_card_price_and_discount_are_anchored_to_essential_offer(self):
        offers = [
            ProductOffer.objects.create(
                product=self.product, title="Essentiel", badge=ProductOffer.BADGE_ESSENTIAL,
                price=Decimal("89.90"), reference_price=Decimal("119.90"),
            ),
            ProductOffer.objects.create(
                product=self.product, title="Medium", badge=ProductOffer.BADGE_MEDIUM,
                price=Decimal("99.90"),
            ),
            ProductOffer.objects.create(
                product=self.product, title="Premium", badge=ProductOffer.BADGE_PREMIUM,
                price=Decimal("109.90"), is_featured=True,
            ),
        ]
        # Une offre n'est valide pour le catalogue que si elle contient son produit principal.
        for offer in offers:
            ProductOfferItem.objects.create(
                offer=offer, product=self.product, use_selected_variant=True, quantity=1,
            )

        self.assertEqual(self.product.display_price, Decimal("89.90"))
        self.assertEqual(self.product.display_reference_price, Decimal("119.90"))
        self.assertEqual(self.product.display_discount_percent, 25)

    def test_offer_item_rejects_variant_from_another_product(self):
        other = Product.objects.create(category=self.category, name="Portefeuille", slug="portefeuille")
        ProductVariant.objects.create(product=other, sku="PORTFOLIO-BEIGE")
        offer = ProductOffer.objects.create(product=self.product, title="Cabas + portefeuille", price=Decimal("99.90"))
        item = ProductOfferItem(offer=offer, product=other, variant=self.variant, quantity=1)
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_product_media_is_independent_of_variants(self):
        media = ProductMedia(
            product=self.product,
            source_url="https://cdn.example.test/cabas.webp",
            alt_text="Cabas camel",
        )
        media.full_clean()
        self.assertFalse(hasattr(media, "variant"))


class CatalogViewTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name="Sacs à main", slug="sacs-a-main",
            image_url="https://cdn.example.test/category.webp",
            alt_text="Sacs à main",
        )
        self.product = Product.objects.create(
            category=self.category, name="Cabas camel", slug="cabas-camel",
            is_active=True, is_new=True,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product, sku="CABAS-CAMEL", color_name="Camel",
            color_slug="camel", color_code="#B07A4A",
            stock_quantity=4,
        )
        ProductMedia.objects.create(
            product=self.product, media_type=ProductMedia.IMAGE,
            source_url="https://cdn.example.test/cabas.webp",
            alt_text="Cabas camel de face", is_primary=True,
        )
        self.offer = ProductOffer.objects.create(
            product=self.product, title="Essentiel", badge=ProductOffer.BADGE_ESSENTIAL,
            display_delivery_label=ProductOffer.DELIVERY_PAID, price=Decimal("89.90"),
            is_featured=True,
        )
        ProductOfferItem.objects.create(
            offer=self.offer, product=self.product, use_selected_variant=True, quantity=1,
        )

    def test_product_javascript_asset_resolves_and_all_add_buttons_have_offer_context(self):
        self.assertIsNotNone(finders.find("js/product.js"))
        response = self.client.get(reverse("product:detail", kwargs={"slug": self.product.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "/static/js/product.js")
        self.assertContains(response, 'id="product-data"')
        self.assertContains(response, 'name="color"')
        self.assertContains(response, 'name="offer"')
        self.assertContains(response, 'class="button button-primary button-block cta js-buy"')
        self.assertContains(response, 'class="button button-secondary cta-icon js-add"')
        self.assertContains(response, 'id="cta-final">Acheter</button>')
        self.assertContains(response, 'class="button button-primary js-buy"')

    def test_product_detail_exposes_configured_accessories_for_the_optional_gift_popup(self):
        accessory = Product.objects.create(
            category=self.category, name="Porte-cartes beige",
            slug="porte-cartes-beige-detail", is_active=True,
        )
        accessory_variant = ProductVariant.objects.create(
            product=accessory, sku="PORTE-CARTES-BEIGE-DETAIL",
            color_name="Beige", stock_quantity=3,
        )
        ProductMedia.objects.create(
            product=accessory, media_type=ProductMedia.IMAGE,
            source_url="https://cdn.example.test/porte-cartes-detail.webp",
            alt_text="Porte-cartes beige", is_primary=True,
        )
        standalone_offer = ProductOffer.objects.create(
            product=accessory, title="Essentiel", badge=ProductOffer.BADGE_ESSENTIAL,
            price=Decimal("19.90"), reference_price=Decimal("24.90"),
        )
        ProductOfferItem.objects.create(
            offer=standalone_offer, product=accessory,
            use_selected_variant=True, quantity=1,
        )
        ProductOfferItem.objects.create(
            offer=self.offer, product=accessory, variant=accessory_variant, quantity=1,
        )

        response = self.client.get(reverse("product:detail", kwargs={"slug": self.product.slug}))
        self.assertEqual(response.status_code, 200)
        gift = response.context["product"]["offers"][0]["accessories"][0]
        self.assertEqual(gift["name"], accessory.name)
        self.assertEqual(gift["original_price"], 24.90)
        self.assertEqual(gift["image"], "https://cdn.example.test/porte-cartes-detail.webp")
        self.assertTrue(gift["available"])
        self.assertContains(response, "Accessoires offerts en option")

    def test_featured_offer_is_selected_without_hiding_other_active_offers(self):
        self.offer.is_featured = False
        self.offer.save(update_fields=["is_featured"])
        medium = ProductOffer.objects.create(
            product=self.product, title="Medium", badge=ProductOffer.BADGE_MEDIUM,
            price=Decimal("99.90"), is_featured=True,
        )
        premium = ProductOffer.objects.create(
            product=self.product, title="Premium", badge=ProductOffer.BADGE_PREMIUM,
            price=Decimal("109.90"),
        )
        for offer in (medium, premium):
            ProductOfferItem.objects.create(
                offer=offer, product=self.product, use_selected_variant=True, quantity=1,
            )

        response = self.client.get(reverse("product:detail", kwargs={"slug": self.product.slug}))
        self.assertEqual(response.status_code, 200)
        displayed_offers = response.context["product"]["offers"]
        self.assertEqual([offer["title"] for offer in displayed_offers], ["Essentiel", "Medium", "Premium"])
        self.assertEqual(next(offer["title"] for offer in displayed_offers if offer["featured"]), "Medium")
        self.assertContains(response, 'name="offer" value="%s"' % self.offer.pk)
        self.assertContains(response, 'name="offer" value="%s"' % medium.pk)
        self.assertContains(response, 'name="offer" value="%s"' % premium.pk)

    def test_product_detail_displays_reference_price_and_discount(self):
        self.offer.reference_price = Decimal("119.90")
        self.offer.save(update_fields=["reference_price"])
        response = self.client.get(reverse("product:detail", kwargs={"slug": self.product.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "119,90 €")
        self.assertContains(response, "-25 %")

    def test_product_detail_sets_csrf_cookie_and_allows_secure_cart_add(self):
        client = Client(enforce_csrf_checks=True)
        response = client.get(reverse("product:detail", kwargs={"slug": self.product.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", client.cookies)
        token = client.cookies["csrftoken"].value
        cart_response = client.post(
            reverse("shop:cart_mutation"),
            data=json.dumps({
                "action": "add", "variant_id": self.variant.pk,
                "offer_id": self.offer.pk, "quantity": 1,
            }),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(cart_response.status_code, 200)
        self.assertEqual(cart_response.json()["count"], 1)

    def test_catalog_receives_database_products_and_categories(self):
        response = self.client.get(reverse("shop:catalog"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "catalog-data")
        self.assertContains(response, "cabas-camel")
        self.assertContains(response, "Sacs à main")

    def test_home_links_connect_categories_and_products_to_their_destinations(self):
        response = self.client.get(reverse("home:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            reverse("shop:catalog") + "?cat=" + self.category.slug,
        )
        self.assertContains(
            response,
            reverse("product:detail", kwargs={"slug": self.product.slug}),
        )
        # La section signature est volontairement préservée hors du raccordement backend.
        self.assertContains(response, "Notre sélection signature")
        self.assertContains(response, reverse("shop:catalog") + "?cat=" + self.category.slug)
        self.assertNotContains(response, "?cat=handbags")

    def test_product_without_linked_offer_is_not_published(self):
        self.product.offers.all().delete()
        response = self.client.get(reverse("shop:catalog"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '"id": "cabas-camel"')
        detail = self.client.get(reverse("product:detail", kwargs={"slug": self.product.slug}))
        self.assertEqual(detail.status_code, 404)

    def test_product_without_common_image_is_not_published(self):
        self.product.media_items.all().delete()
        response = self.client.get(reverse("shop:catalog"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '"id": "cabas-camel"')
        detail = self.client.get(reverse("product:detail", kwargs={"slug": self.product.slug}))
        self.assertEqual(detail.status_code, 404)

    def test_product_without_active_variant_is_not_published(self):
        variant = self.product.variants.first()
        variant.is_active = False
        variant.save(update_fields=["is_active"])
        response = self.client.get(reverse("shop:catalog"))
        self.assertNotContains(response, '"id": "cabas-camel"')

    def test_admin_diagnoses_missing_publication_requirements(self):
        self.product.offers.all().delete()
        self.product.is_active = False
        self.product.is_new = False
        self.product.save(update_fields=["is_active", "is_new"])
        self.category.is_active = False
        self.category.save(update_fields=["is_active"])
        variant = self.product.variants.first()
        variant.is_active = False
        variant.save(update_fields=["is_active"])
        self.product.media_items.all().delete()

        model_admin = ProductAdmin(Product, admin.site)
        diagnostic = str(model_admin.catalog_publication_diagnostics(self.product))
        self.assertIn("Produit désactivé", diagnostic)
        self.assertIn("Catégorie inactive", diagnostic)
        self.assertIn("Aucune variante active", diagnostic)
        self.assertIn("Aucune image produit valide", diagnostic)
        self.assertIn("Aucune offre active valide", diagnostic)
        self.assertIn("cochez « Nouveauté »", diagnostic)

    def test_catalog_provides_a_django_generated_product_url_template(self):
        response = self.client.get(reverse("shop:catalog"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            reverse("product:detail", kwargs={"slug": "__product_slug__"}),
        )
        # Les liens des cartes sont créés côté navigateur à partir de ces données.
        self.assertContains(response, '"id": "cabas-camel"')

    def test_home_new_products_are_filtered_by_is_new(self):
        regular_product = Product.objects.create(
            category=self.category, name="Portefeuille classique",
            slug="portefeuille-classique", is_active=True, is_new=False,
        )
        ProductVariant.objects.create(
            product=regular_product, sku="PORTFOLIO-CLASSIQUE",
            stock_quantity=3,
        )
        ProductMedia.objects.create(
            product=regular_product, media_type=ProductMedia.IMAGE,
            source_url="https://cdn.example.test/portefeuille-classique.webp",
            alt_text="Portefeuille classique",
        )
        response = self.client.get(reverse("home:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cabas camel")
        self.assertNotContains(response, "Portefeuille classique")
        self.assertContains(response, "Notre sélection signature")

    def test_product_detail_uses_published_product(self):
        response = self.client.get(reverse("product:detail", kwargs={"slug": self.product.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cabas camel")
        self.assertContains(response, "89,90")

    def test_inactive_product_is_not_publicly_accessible(self):
        self.product.is_active = False
        self.product.save(update_fields=["is_active"])
        response = self.client.get(reverse("product:detail", kwargs={"slug": self.product.slug}))
        self.assertEqual(response.status_code, 404)

    def test_unapproved_reviews_are_not_exposed(self):
        Review.objects.create(
            product=self.product, author_name="Visiteur privé", rating=5,
            comment="Avis en attente", is_approved=False,
        )
        response = self.client.get(reverse("product:detail", kwargs={"slug": self.product.slug}))
        self.assertNotContains(response, "Avis en attente")
        self.assertNotContains(response, "Visiteur privé")


    def test_public_review_submission_is_disabled_until_checkout_is_ready(self):
        response = self.client.post(
            reverse("product:detail", kwargs={"slug": self.product.slug}),
            {"author_name": "Camille", "rating": "5", "comment": "Très beau sac et finitions soignées."},
        )
        self.assertEqual(response.status_code, 405)
        self.assertFalse(Review.objects.filter(author_name="Camille").exists())

    def test_home_only_displays_approved_featured_reviews_for_published_products(self):
        approved = Review.objects.create(
            product=self.product, author_name="Camille", rating=5,
            comment="Très beau sac et finitions soignées.", is_approved=True, is_featured=True,
        )
        Review.objects.create(
            product=self.product, author_name="En attente", rating=4,
            comment="Cet avis attend la modération.", is_approved=False,
        )
        Review.objects.create(
            product=self.product, author_name="Non mis en avant", rating=3,
            comment="Avis approuvé non sélectionné.", is_approved=True, is_featured=False,
        )
        response = self.client.get(reverse("home:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, approved.comment)
        self.assertContains(response, reverse("product:detail", kwargs={"slug": self.product.slug}))
        self.assertNotContains(response, "Cet avis attend la modération.")
        self.assertNotContains(response, "Avis approuvé non sélectionné.")



class UploadedMediaTests(TestCase):
    def setUp(self):
        self.media_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.media_dir.cleanup)
        settings_override = override_settings(MEDIA_ROOT=self.media_dir.name)
        settings_override.enable()
        self.addCleanup(settings_override.disable)

    @staticmethod
    def png_upload(name="test.png"):
        # Valid 1x1 PNG used only by the upload-path test.
        data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
        return SimpleUploadedFile(name, data, content_type="image/png")

    def test_category_image_is_stored_in_media_categories_folder(self):
        category = Category.objects.create(
            name="Catégorie test",
            slug="categorie-test-upload",
            image=self.png_upload("categorie.png"),
        )
        self.assertTrue(category.image.name.startswith("categories/"))
        self.assertTrue(category.image.storage.exists(category.image.name))

    def test_product_image_is_stored_in_media_products_folder(self):
        category = Category.objects.create(name="Sacs", slug="sacs-upload")
        product = Product.objects.create(
            category=category, name="Sac test", slug="sac-test-upload", is_active=True
        )
        media = ProductMedia.objects.create(
            product=product,
            media_type=ProductMedia.IMAGE,
            image=self.png_upload("sac.png"),
            alt_text="Sac test",
        )
        self.assertTrue(media.image.name.startswith("products/"))
        self.assertTrue(media.image.storage.exists(media.image.name))


