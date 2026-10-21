import base64
import tempfile
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

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
        ProductVariant.objects.create(
            product=self.product, sku="CABAS-CAMEL", color_name="Camel",
            color_slug="camel", color_code="#B07A4A",
            price=Decimal("89.90"), stock_quantity=4,
        )
        ProductMedia.objects.create(
            product=self.product, media_type=ProductMedia.IMAGE,
            source_url="https://cdn.example.test/cabas.webp",
            alt_text="Cabas camel de face", is_primary=True,
        )

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

    def test_catalog_links_to_the_database_backed_product_detail(self):
        response = self.client.get(reverse("shop:catalog"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            reverse("product:detail", kwargs={"slug": self.product.slug}),
        )
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


