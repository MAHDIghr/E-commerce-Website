from io import BytesIO
import tempfile
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from checkout.models import PromoCode
from checkout.services import CheckoutProblem, apply_promo_code

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

    def test_home_signature_uses_product_image_and_product_link(self):
        response = self.client.get(reverse("home:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("product:detail", kwargs={"slug": self.product.slug}))
        self.assertContains(response, "https://cdn.example.test/product.webp")
        self.assertContains(response, "Sac signature test — Noir</strong>")
        self.assertContains(response, "59,90 €")
        self.assertNotContains(response, self.selection.image.url)

    def test_inactive_signature_selection_is_not_rendered(self):
        self.selection.is_active = False
        self.selection.save(update_fields=["is_active"])

        response = self.client.get(reverse("home:home"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse("product:detail", kwargs={"slug": self.product.slug}))


class FlashCampaignTests(TestCase):
    def test_admin_campaign_uses_real_promo_deadline_and_can_be_disabled(self):
        now = timezone.now()
        promo = PromoCode.objects.create(
            code="FLASH-TEST", discount_type=PromoCode.PERCENT,
            value=Decimal("10.00"), minimum_subtotal=Decimal("30.00"),
            starts_at=now - timedelta(minutes=1), ends_at=now + timedelta(minutes=5),
            is_active=True, is_flash_campaign=True, once_per_email=False,
        )
        response = self.client.get(reverse("home:home"))
        self.assertContains(response, 'id="flash-campaign"')
        self.assertContains(response, 'data-ends-at="' + promo.ends_at.isoformat() + '"')
        self.assertContains(response, "FLASH-TEST")
        self.assertNotContains(response, "social-toast")
        self.assertEqual(apply_promo_code("FLASH-TEST", Decimal("50.00"))[1], Decimal("5.00"))
        status_url = reverse("home:flash_campaign_status", kwargs={"promo_id": promo.pk})
        self.assertTrue(self.client.get(status_url).json()["active"])

        promo.is_active = False
        promo.save(update_fields=["is_active"])
        self.assertFalse(self.client.get(status_url).json()["active"])
        self.assertNotContains(self.client.get(reverse("home:home")), 'id="flash-campaign"')
        with self.assertRaises(CheckoutProblem):
            apply_promo_code("FLASH-TEST", Decimal("50.00"))

        promo.is_active = True
        promo.ends_at = now - timedelta(seconds=1)
        promo.save(update_fields=["is_active", "ends_at"])
        self.assertFalse(self.client.get(status_url).json()["active"])
        with self.assertRaises(CheckoutProblem):
            apply_promo_code("FLASH-TEST", Decimal("50.00"))

    def test_flash_campaign_requires_real_dates(self):
        promo = PromoCode(code="FLASH-NO-DATES", value=Decimal("10.00"), is_flash_campaign=True)
        with self.assertRaises(ValidationError):
            promo.full_clean()
