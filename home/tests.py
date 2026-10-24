from io import BytesIO
from decimal import Decimal
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from product.models import (
    Category, Product, ProductMedia, ProductOffer, ProductOfferItem, ProductVariant,
)
from .models import SignatureSelection


class SignatureSelectionTests(TestCase):
    def setUp(self):
        self.media_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.media_directory.cleanup)
        media_settings = override_settings(MEDIA_ROOT=self.media_directory.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)

        self.category = Category.objects.create(name="Sacs", slug="sacs")
        self.product = Product.objects.create(
            category=self.category,
            name="Sac signature test",
            slug="sac-signature-test",
            is_active=True,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            sku="SIGNATURE-TEST",
            color_name="Noir",
            color_slug="noir",
            stock_quantity=5,
            is_active=True,
        )
        ProductMedia.objects.create(
            product=self.product,
            media_type=ProductMedia.IMAGE,
            source_url="https://cdn.example.test/product.webp",
            alt_text="Photo de la fiche produit",
            is_primary=True,
        )
        offer = ProductOffer.objects.create(
            product=self.product,
            title="Essentiel",
            price="59.90",
            is_active=True,
        )
        self.offer = offer
        ProductOfferItem.objects.create(
            offer=offer,
            product=self.product,
            use_selected_variant=True,
            quantity=1,
        )

        image_buffer = BytesIO()
        Image.new("RGB", (2, 2), (240, 230, 220)).save(image_buffer, format="PNG")
        self.selection = SignatureSelection.objects.create(
            product=self.product,
            image=SimpleUploadedFile(
                "signature-dediee.png",
                image_buffer.getvalue(),
                content_type="image/png",
            ),
            alt_text="Visuel éditorial de la sélection signature",
            position=1,
            is_active=True,
        )

    def test_home_uses_dedicated_signature_image_and_product_link(self):
        response = self.client.get(reverse("home:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("product:detail", kwargs={"slug": self.product.slug}))
        self.assertContains(response, self.selection.image.url)
        self.assertNotContains(response, "cdn.example.test/product.webp")

    def test_homepage_discount_uses_essential_offer_reference_price(self):
        self.product.is_new = True
        self.product.save(update_fields=["is_new"])
        self.offer.reference_price = Decimal("75.00")
        self.offer.save(update_fields=["reference_price"])

        response = self.client.get(reverse("home:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="product-badge product-badge--sale">-20%</span>')
        self.assertContains(response, "75.00 €")
        self.assertContains(response, "59.90 €")

    def test_inactive_signature_selection_is_not_rendered(self):
        self.selection.is_active = False
        self.selection.save(update_fields=["is_active"])

        response = self.client.get(reverse("home:home"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse("product:detail", kwargs={"slug": self.product.slug}))
