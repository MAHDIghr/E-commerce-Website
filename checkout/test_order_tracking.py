import uuid
from decimal import Decimal

from django.core import signing
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from checkout.models import Order, OrderLine, ReturnRequest, OrderNotification


class SignedOrderTrackingTests(TestCase):
    def setUp(self):
        cache.clear()
        self.order = Order.objects.create(
            checkout_key=uuid.uuid4(), email="private-client@example.test",
            full_name="Client Privé", address_line1="1 rue de Test",
            postal_code="75001", city="Paris", country="FR",
            shipping_method="standard", subtotal=Decimal("20.00"),
            shipping_amount=Decimal("4.90"), total=Decimal("24.90"),
            status=Order.PAID,
        )
        self.line = OrderLine.objects.create(
            order=self.order, offer_id_snapshot=1, product_name="Sac test",
            quantity=1, unit_price=Decimal("20.00"), line_total=Decimal("20.00"),
        )
        self.token = signing.dumps(
            {"public_id": str(self.order.public_id), "email": self.order.email},
            salt="checkout.order-tracking",
        )

    def test_order_is_not_accessible_by_public_id_alone(self):
        response = self.client.get(reverse("checkout:tracking", args=[self.order.public_id]))
        self.assertEqual(response.status_code, 404)

    def test_valid_signed_link_shows_only_its_order(self):
        response = self.client.get(
            reverse("checkout:tracking", args=[self.order.public_id]), {"token": self.token},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Client Privé")
        self.assertContains(response, "Sac test")

    def test_token_cannot_be_used_for_another_order(self):
        another_order = Order.objects.create(
            checkout_key=uuid.uuid4(), email="another@example.test",
            full_name="Autre client", address_line1="2 rue de Test",
            postal_code="75002", city="Paris", country="FR",
            shipping_method="standard", subtotal=Decimal("10.00"),
            shipping_amount=Decimal("4.90"), total=Decimal("14.90"),
            status=Order.PAID,
        )
        response = self.client.get(
            reverse("checkout:tracking", args=[another_order.public_id]), {"token": self.token},
        )
        self.assertEqual(response.status_code, 404)

    def test_customer_can_submit_partial_return_request(self):
        response = self.client.post(
            reverse("checkout:return_request", args=[self.order.public_id]),
            {
                "token": self.token, "reason_category": "defective",
                "reason": "Le produit présente un défaut.", f"line_{self.line.pk}": "1",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ReturnRequest.objects.filter(order=self.order).count(), 1)

    @patch("checkout.lifecycle.send_mail", return_value=1)
    def test_tracking_lookup_sends_signed_link_without_revealing_order_details(self, send_mail_mock):
        response = self.client.post(reverse("checkout:tracking_lookup"), {
            "reference": str(self.order.public_id), "email": self.order.email,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "un lien privé de suivi")
        notification = OrderNotification.objects.get(order=self.order, recipient=self.order.email)
        self.assertEqual(notification.status, OrderNotification.SENT)
        self.assertIn("token=", send_mail_mock.call_args.kwargs["message"])
        self.assertEqual(notification.payload, {})
        send_mail_mock.assert_called_once()

    @patch("checkout.lifecycle.send_mail", return_value=1)
    def test_tracking_lookup_does_not_disclose_when_email_does_not_match(self, send_mail_mock):
        response = self.client.post(reverse("checkout:tracking_lookup"), {
            "reference": str(self.order.public_id), "email": "wrong@example.test",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "un lien privé de suivi")
        self.assertFalse(OrderNotification.objects.filter(order=self.order).exists())
        send_mail_mock.assert_not_called()
