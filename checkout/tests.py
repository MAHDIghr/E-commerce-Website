import json
import uuid
from types import SimpleNamespace
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from product.models import Category, Product, ProductMedia, ProductOffer, ProductOfferItem, ProductVariant
from .models import Order, OrderLine, PaymentAttempt, StripeWebhookEvent
from .forms import CheckoutForm
from .services import CheckoutProblem, create_stripe_session, process_stripe_event, release_reserved_stock, shipping_price


class CheckoutIntegrationTests(TestCase):
    def setUp(self):
        category = Category.objects.create(name="Sacs", slug="sacs")
        self.product = Product.objects.create(category=category, name="Cabas camel", slug="cabas-camel", is_active=True)
        self.variant = ProductVariant.objects.create(product=self.product, sku="CABAS-TEST", color_name="Camel", color_slug="camel", color_code="#B07A4A", stock_quantity=4)
        ProductMedia.objects.create(product=self.product, media_type=ProductMedia.IMAGE, source_url="https://cdn.example.test/cabas.webp", alt_text="Sac", is_primary=True)
        self.offer = ProductOffer.objects.create(product=self.product, title="Essentiel", badge=ProductOffer.BADGE_ESSENTIAL, price=Decimal("89.90"), is_active=True)
        ProductOfferItem.objects.create(offer=self.offer, product=self.product, use_selected_variant=True, quantity=1)

    def add_to_cart(self):
        return self.client.post(reverse("shop:cart_mutation"), data=json.dumps({
            "action": "add", "variant_id": self.variant.pk, "offer_id": self.offer.pk, "quantity": 1,
        }), content_type="application/json")

    def test_free_shipping_is_automatic_at_threshold_and_paid_delivery_has_two_choices(self):
        free_form = CheckoutForm(subtotal=Decimal("80.00"))
        self.assertEqual(list(free_form.fields["shipping_method"].choices), [("free", "Livraison offerte — 0,00 €")])
        self.assertEqual(shipping_price("free", Decimal("80.00")), Decimal("0.00"))
        with self.assertRaises(CheckoutProblem):
            shipping_price("standard", Decimal("80.00"))

        paid_form = CheckoutForm(subtotal=Decimal("79.99"))
        self.assertEqual([value for value, _label in paid_form.fields["shipping_method"].choices], ["standard", "express"])
        self.assertEqual(shipping_price("standard", Decimal("79.99")), Decimal("4.90"))
        self.assertEqual(shipping_price("express", Decimal("79.99")), Decimal("9.90"))

    @patch.dict("os.environ", {"STRIPE_SECRET_KEY": "", "STRIPE_WEBHOOK_SECRET": "", "SITE_BASE_URL": ""})
    def test_missing_stripe_configuration_does_not_create_order_or_change_stock(self):
        self.add_to_cart()
        response = self.client.post(reverse("checkout:checkout"), data={
            "full_name": "Camille Martin", "email": "camille@example.test", "phone": "",
            "address_line1": "1 rue du Test", "address_line2": "", "postal_code": "75001",
            "city": "Paris", "country": "FR", "shipping_method": "free",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Order.objects.count(), 0)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_quantity, 4)
        self.assertContains(response, "Aucun paiement ne sera simulé")

    def test_return_page_never_marks_order_paid_and_rejects_mismatched_session(self):
        order = Order.objects.create(
            checkout_key=uuid.uuid4(), email="client@example.test", full_name="Client Test",
            address_line1="1 rue Test", postal_code="75001", city="Paris", country="FR",
            shipping_method="standard", subtotal=Decimal("89.90"), shipping_amount=Decimal("4.90"),
            total=Decimal("94.80"), stripe_session_id="cs_test_expected",
        )
        response = self.client.get(reverse("checkout:result", kwargs={"public_id": order.public_id}), {"session_id": "cs_test_other"})
        self.assertEqual(response.status_code, 404)
        response = self.client.get(reverse("checkout:result", kwargs={"public_id": order.public_id}), {"session_id": "cs_test_expected"})
        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.PENDING)

    def test_verified_paid_event_is_idempotent(self):
        order = Order.objects.create(
            checkout_key=uuid.uuid4(), email="client@example.test", full_name="Client Test",
            address_line1="1 rue Test", postal_code="75001", city="Paris", country="FR",
            shipping_method="standard", subtotal=Decimal("89.90"), shipping_amount=Decimal("4.90"),
            total=Decimal("94.80"), status=Order.PENDING, stock_reserved=True,
            stripe_session_id="cs_test_123", stock_requirements_snapshot={str(self.variant.pk): 1},
        )
        payment = PaymentAttempt.objects.create(order=order, amount=order.total, currency="eur", stripe_session_id=order.stripe_session_id)
        event = {"id": "evt_test_once", "type": "checkout.session.completed", "data": {"object": {
            "object": "checkout.session", "id": "cs_test_123", "currency": "eur", "amount_total": 9480,
            "payment_status": "paid", "payment_intent": "pi_test_123",
        }}}
        self.assertEqual(process_stripe_event(event), "processed")
        self.assertEqual(process_stripe_event(event), "duplicate")
        order.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(order.status, Order.PAID)
        self.assertFalse(order.stock_reserved)
        self.assertTrue(order.stock_committed)
        self.assertEqual(payment.status, PaymentAttempt.SUCCEEDED)
        self.assertEqual(StripeWebhookEvent.objects.filter(event_id="evt_test_once").count(), 1)

    def test_releasing_reservation_restores_main_stock_once(self):
        self.variant.stock_quantity = 3
        self.variant.save(update_fields=["stock_quantity"])
        order = Order.objects.create(
            checkout_key=uuid.uuid4(), email="client@example.test", full_name="Client Test",
            address_line1="1 rue Test", postal_code="75001", city="Paris", country="FR",
            shipping_method="standard", subtotal=Decimal("89.90"), shipping_amount=Decimal("4.90"),
            total=Decimal("94.80"), stock_reserved=True,
            stock_requirements_snapshot={str(self.variant.pk): 1},
        )
        release_reserved_stock(order)
        order.save(update_fields=["stock_reserved"])
        release_reserved_stock(order)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_quantity, 4)

    @patch.dict("os.environ", {"STRIPE_WEBHOOK_SECRET": "whsec_test"})
    def test_webhook_rejects_invalid_signature(self):
        response = self.client.post(
            reverse("checkout:stripe_webhook"),
            data=b'{"id":"evt_bad"}',
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="invalid-signature",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(StripeWebhookEvent.objects.count(), 0)

    def test_amount_mismatch_moves_order_to_manual_review(self):
        order = Order.objects.create(
            checkout_key=uuid.uuid4(), email="client@example.test", full_name="Client Test",
            address_line1="1 rue Test", postal_code="75001", city="Paris", country="FR",
            shipping_method="standard", subtotal=Decimal("89.90"), shipping_amount=Decimal("4.90"),
            total=Decimal("94.80"), status=Order.PENDING, stock_reserved=True,
            stripe_session_id="cs_test_mismatch",
        )
        payment = PaymentAttempt.objects.create(order=order, amount=order.total, currency="eur", stripe_session_id=order.stripe_session_id)
        event = {"id": "evt_mismatch", "type": "checkout.session.completed", "data": {"object": {
            "object": "checkout.session", "id": "cs_test_mismatch", "currency": "eur",
            "amount_total": 100, "payment_status": "paid",
        }}}
        self.assertEqual(process_stripe_event(event), "mismatch")
        order.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(order.status, Order.REVIEW)
        self.assertTrue(order.stock_reserved)
        self.assertEqual(payment.status, PaymentAttempt.REVIEW)

    def test_async_payment_failure_releases_reserved_stock_once(self):
        self.variant.stock_quantity = 3
        self.variant.save(update_fields=["stock_quantity"])
        order = Order.objects.create(
            checkout_key=uuid.uuid4(), email="client@example.test", full_name="Client Test",
            address_line1="1 rue Test", postal_code="75001", city="Paris", country="FR",
            shipping_method="standard", subtotal=Decimal("89.90"), shipping_amount=Decimal("4.90"),
            total=Decimal("94.80"), status=Order.AWAITING, stock_reserved=True,
            stripe_session_id="cs_test_failed", stock_requirements_snapshot={str(self.variant.pk): 1},
        )
        PaymentAttempt.objects.create(order=order, amount=order.total, currency="eur", stripe_session_id=order.stripe_session_id)
        event = {"id": "evt_async_failed", "type": "checkout.session.async_payment_failed", "data": {"object": {
            "object": "checkout.session", "id": "cs_test_failed",
        }}}
        self.assertEqual(process_stripe_event(event), "processed")
        self.assertEqual(process_stripe_event(event), "duplicate")
        order.refresh_from_db()
        self.variant.refresh_from_db()
        self.assertEqual(order.status, Order.CANCELLED)
        self.assertFalse(order.stock_reserved)
        self.assertEqual(self.variant.stock_quantity, 4)

    def test_checkout_requires_csrf(self):
        from django.test import Client
        strict_client = Client(enforce_csrf_checks=True)
        response = strict_client.post(reverse("checkout:checkout"), data={})
        self.assertEqual(response.status_code, 403)

    def test_checkout_session_uses_server_snapshot_and_exact_shipping_total(self):
        order = Order.objects.create(
            checkout_key=uuid.uuid4(), email="client@example.test", full_name="Client Test",
            address_line1="1 rue Test", postal_code="75001", city="Paris", country="FR",
            shipping_method="standard", subtotal=Decimal("89.90"), shipping_amount=Decimal("4.90"),
            total=Decimal("94.80"),
        )
        OrderLine.objects.create(
            order=order, product=self.product, variant=self.variant, offer_id_snapshot=self.offer.pk,
            product_name="Cabas camel — Essentiel (Camel)", variant_name="Camel",
            quantity=1, unit_price=Decimal("89.90"), line_total=Decimal("89.90"),
            components_snapshot=[{"name": "Porte-clés offert", "variant": "Beige", "variant_id": 99,
                                  "quantity_per_offer": 1, "unit_price": "0.00", "is_gift": True}],
        )
        with patch.dict("os.environ", {
            "STRIPE_SECRET_KEY": "sk_test_unit_test_only",
            "STRIPE_WEBHOOK_SECRET": "whsec_unit_test_only",
            "STRIPE_LIVE_MODE": "False",
            "SITE_BASE_URL": "https://testserver",
            "STRIPE_CURRENCY": "eur",
        }), patch("checkout.services.stripe.checkout.Session.create",
                  return_value=SimpleNamespace(id="cs_test_unit", url="https://checkout.stripe.test/session")) as create:
            session = create_stripe_session(order)
        self.assertEqual(session.id, "cs_test_unit")
        payload = create.call_args.kwargs
        self.assertEqual(payload["mode"], "payment")
        self.assertEqual([item["price_data"]["unit_amount"] for item in payload["line_items"]], [8990, 490])
        self.assertEqual(sum(item["price_data"]["unit_amount"] * item["quantity"] for item in payload["line_items"]), 9480)
        self.assertEqual(payload["metadata"]["order_public_id"], str(order.public_id))
        order.refresh_from_db()
        self.assertEqual(order.stripe_session_id, "cs_test_unit")
