import base64
import tempfile
from decimal import Decimal

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
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
            price=Decimal("89.90"), stock_quantity=4,
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

    def test_variant_rejects_reference_price_not_above_sale_price(self):
        variant = ProductVariant(
            product=self.product, sku="CABAS-CAMEL-INVALID",
            price=Decimal("89.90"), compare_at_price=Decimal("79.90"),
        )
        with self.assertRaises(ValidationError):
            variant.full_clean()

    def test_offer_item_rejects_variant_from_another_product(self):
        other = Product.objects.create(category=self.category, name="Portefeuille", slug="portefeuille")
        ProductVariant.objects.create(product=other, sku="PORTFOLIO-BEIGE", price=Decimal("20.00"))
        offer = ProductOffer.objects.create(product=self.product, title="Cabas + portefeuille", price=Decimal("99.90"))
        item = ProductOfferItem(offer=offer, product=other, variant=self.variant, quantity=1)
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_media_variant_must_belong_to_same_product(self):
        other = Product.objects.create(category=self.category, name="Portefeuille", slug="portefeuille")
        media = ProductMedia(
            product=other, variant=self.variant,
            source_url="https://cdn.example.test/portefeuille.webp",
            alt_text="Portefeuille beige",
        )
        with self.assertRaises(ValidationError):
            media.full_clean()


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
            price=Decimal("89.90"), stock_quantity=4,
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

    def test_product_detail_sets_csrf_cookie_and_allows_secure_cart_add(self):
        client = Client(enforce_csrf_checks=True)
        response = client.get(reverse("product:detail", kwargs={"slug": self.product.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", client.cookies)
        token = client.cookies["csrftoken"].value
        cart_response = client.post(
            reverse("shop:cart_mutation"),
            data=__import__("json").dumps({
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
        variant = self.product.variants.first()
        media = self.product.media_items.get()
        media.variant = variant
        media.save(update_fields=["variant"])
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
        media = self.product.media_items.get()
        media.variant = variant
        media.save(update_fields=["variant"])

        model_admin = ProductAdmin(Product, admin.site)
        diagnostic = str(model_admin.catalog_publication_diagnostics(self.product))
        self.assertIn("Produit désactivé", diagnostic)
        self.assertIn("Catégorie inactive", diagnostic)
        self.assertIn("Aucune variante active", diagnostic)
        self.assertIn("Aucune image commune valide", diagnostic)
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
            price=Decimal("24.90"), stock_quantity=3,
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


