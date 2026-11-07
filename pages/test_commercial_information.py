"""Tests du contrat de publication et du verrou serveur, sans appel réseau Stripe."""
from copy import deepcopy
from decimal import Decimal
from html.parser import HTMLParser
from types import SimpleNamespace
from unittest.mock import patch
import uuid

from django.test import TestCase, override_settings
from django.urls import reverse

from config.commercial import (
    public_information, REQUIRED_INFORMATION_PAGES, SALES_UNAVAILABLE,
    shipping_configuration, shipping_message,
)
from checkout.forms import CheckoutForm
from checkout.models import Order
from checkout.services import CheckoutProblem, create_order_and_reserve, create_stripe_session
from product.models import Category, Product, ProductMedia, ProductOffer, ProductOfferItem, ProductVariant
from shop.views import CART_SESSION_KEY


def approved_information():
    """Contenu fictif réservé aux tests ; ne constitue pas une politique publiable."""
    return {
        "approved": True, "approval_reference": "TEST ONLY — not legal approval",
        "contact_email": "contact@example.test", "shipping": shipping_configuration(),
        "pages": {name: [("Texte de test", ["Contenu fictif réservé aux tests."])]
                  for name in REQUIRED_INFORMATION_PAGES},
    }


class PublicInformationContractTests(TestCase):
    def test_default_and_partial_approval_keep_sales_closed(self):
        self.assertFalse(public_information()["sales_ready"])
        cases = [{}, {"approved": True}, approved_information()]
        del cases[-1]["pages"]["terms"]
        for data in cases:
            with self.subTest(data=data), override_settings(COMMERCIAL_INFORMATION=data):
                self.assertEqual(public_information(), {"sales_ready": False, "contact_email": "", "pages": {}})

    def test_full_explicit_approval_allows_publication(self):
        with override_settings(COMMERCIAL_INFORMATION=approved_information()):
            self.assertTrue(public_information()["sales_ready"])
            response = self.client.get(reverse("pages:terms"))
            self.assertContains(response, "Contenu fictif réservé aux tests.")
            self.assertNotContains(response, "Ces informations ne sont pas disponibles")
            self.assertContains(response, 'href="mailto:contact@example.test"')

    def test_placeholder_invalid_email_and_stale_shipping_close_publication(self):
        valid = approved_information()
        bad_email = deepcopy(valid); bad_email["contact_email"] = ""
        bad_placeholder = deepcopy(valid); bad_placeholder["pages"]["terms"][0][1][0] = "[À COMPLÉTER : vendeur]"
        stale_shipping = deepcopy(valid); stale_shipping["shipping"]["prices"]["standard"] = "0.01"
        not_approved = deepcopy(valid); not_approved["approved"] = False
        no_reference = deepcopy(valid); no_reference["approval_reference"] = ""
        for data in (bad_email, bad_placeholder, stale_shipping, not_approved, no_reference):
            with self.subTest(data=data), override_settings(COMMERCIAL_INFORMATION=data):
                self.assertFalse(public_information()["sales_ready"])
                self.assertEqual(public_information()["pages"], {})

    def test_confirmed_paragraphs_are_escaped_not_interpreted_as_html(self):
        data = approved_information()
        data["pages"]["terms"] = [("Conditions", ['<script>alert("test")</script>'])]
        with override_settings(COMMERCIAL_INFORMATION=data):
            response = self.client.get(reverse("pages:terms"))
            self.assertContains(response, "&lt;script&gt;")
            self.assertNotContains(response, '<script>alert("test")</script>')


class CommercialSalesGateTests(TestCase):
    def setUp(self):
        category = Category.objects.create(name="Sacs", slug="sacs")
        self.product = Product.objects.create(category=category, name="Sac test", slug="sac-test", is_new=True, is_active=True)
        self.variant = ProductVariant.objects.create(product=self.product, sku="INFORMATION-TEST", stock_quantity=3)
        ProductMedia.objects.create(product=self.product, source_url="https://cdn.example.test/sac.webp", alt_text="Sac test")
        self.offer = ProductOffer.objects.create(product=self.product, price=Decimal("49.90"))
        ProductOfferItem.objects.create(offer=self.offer, product=self.product, use_selected_variant=True)
        session = self.client.session
        session[CART_SESSION_KEY] = {f"{self.variant.pk}:{self.offer.pk}": 1}
        session.save()
        with override_settings(COMMERCIAL_INFORMATION=approved_information()):
            self.form = CheckoutForm({
                "first_name": "Test", "last_name": "Client", "email": "client@example.test",
                "address_line1": "Adresse de test", "postal_code": "75001", "city": "Paris",
                "country": "FR", "shipping_method": "standard", "billing_same_as_shipping": "on",
                "accept_terms": "on",
            }, subtotal=Decimal("49.90"))
            self.assertTrue(self.form.is_valid(), self.form.errors)

    def test_direct_payment_post_and_service_calls_cannot_bypass_gate(self):
        with patch("checkout.views.create_order_and_reserve") as create, patch("checkout.services.stripe.checkout.Session.create") as stripe:
            response = self.client.post(reverse("checkout:checkout"), self.form.data)
            self.assertContains(response, SALES_UNAVAILABLE)
            create.assert_not_called()
            request = SimpleNamespace(session=self.client.session, user=SimpleNamespace(is_authenticated=False))
            with self.assertRaisesMessage(CheckoutProblem, SALES_UNAVAILABLE):
                create_order_and_reserve(request, self.form, uuid.uuid4())
            with self.assertRaisesMessage(CheckoutProblem, SALES_UNAVAILABLE):
                create_stripe_session(SimpleNamespace())
            stripe.assert_not_called()
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_quantity, 3)
        self.assertFalse(Order.objects.exists())
        self.assertNotIn("checkout_attempt_key", self.client.session)

    def test_all_supports_share_information_links_and_remove_unconfirmed_claims(self):
        urls = [reverse("home:home"), reverse("shop:catalog"),
                reverse("product:detail", kwargs={"slug": self.product.slug}),
                reverse("shop:cart_page"), reverse("checkout:checkout")]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, SALES_UNAVAILABLE)
                for name in ("delivery", "returns", "terms", "contact"):
                    self.assertContains(response, f'href="{reverse("pages:" + name)}"')
                for text in ("[À COMPLÉTER", "30 jours", "Sans condition", "7j/7", "@maboutique", "#maboutique", "Cuirs sélectionnés"):
                    self.assertNotContains(response, text)
                self.assertNotContains(response, 'href="mailto:"')
                self.assertNotContains(response, 'href="tel:"')
        self.assertContains(self.client.get(urls[-1]), 'id="checkout-submit" disabled')

    def test_approved_shipping_message_matches_in_pages_and_offer_api(self):
        with override_settings(COMMERCIAL_INFORMATION=approved_information()):
            expected = shipping_message()
            for url in (reverse("home:home"), reverse("shop:catalog"), reverse("product:detail", kwargs={"slug": self.product.slug}), reverse("shop:cart_page"), reverse("checkout:checkout")):
                self.assertContains(self.client.get(url), expected)
            response = self.client.get(reverse("shop:offer_options", kwargs={"slug": self.product.slug}), {"variant_id": self.variant.pk})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["offers"][0]["delivery_label"], expected)

    def test_checkout_information_links_are_real_and_do_not_lose_cart(self):
        class Links(HTMLParser):
            def __init__(self):
                super().__init__(); self.paths = set()
            def handle_starttag(self, tag, attrs):
                href = dict(attrs).get("href", "")
                if tag == "a" and href.startswith("/") and not href.startswith("//"):
                    self.paths.add(href)
        parser = Links(); parser.feed(self.client.get(reverse("checkout:checkout")).content.decode())
        before = self.client.session[CART_SESSION_KEY]
        for url in sorted(parser.paths):
            with self.subTest(url=url):
                response = self.client.get(url, follow=True)
                self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.session[CART_SESSION_KEY], before)
