import uuid
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from checkout.lifecycle import (
    LifecycleProblem, create_return_request, create_shipment, transition_shipment, request_refund, transition_order_commercial_status,
)
from checkout.models import Order, OrderLine, ReturnRequest, Shipment


class OrderLifecycleServiceTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username="lifecycle-admin", email="lifecycle-admin@example.test",
            password="StrongTestPassword!2026",
        )
        self.order = Order.objects.create(
            checkout_key=uuid.uuid4(), email="customer@example.test",
            full_name="Client Test", address_line1="1 rue de Test",
            postal_code="75001", city="Paris", country="FR",
            shipping_method="standard", subtotal=Decimal("40.00"),
            shipping_amount=Decimal("4.90"), total=Decimal("44.90"),
            status=Order.PAID, stripe_payment_intent_id="pi_test_only",
        )
        self.line = OrderLine.objects.create(
            order=self.order, offer_id_snapshot=1, product_name="Sac test",
            variant_name="Noir", quantity=2, unit_price=Decimal("20.00"),
            line_total=Decimal("40.00"),
        )

    def test_shipment_creation_does_not_mark_order_shipped(self):
        shipment = create_shipment(
            self.order.pk, actor=self.admin, carrier="Transport manuel",
            line_quantities={self.line.pk: 1},
        )
        self.order.refresh_from_db()
        self.assertEqual(shipment.status, Shipment.DRAFT)
        self.assertEqual(self.order.fulfillment_status, Order.FULFILLMENT_UNFULFILLED)

    def test_shipment_transition_requires_allowed_state(self):
        shipment = create_shipment(
            self.order.pk, actor=self.admin, line_quantities={self.line.pk: 1},
        )
        with self.assertRaises(LifecycleProblem):
            transition_shipment(shipment.pk, Shipment.DELIVERED, actor=self.admin)
        transition_shipment(shipment.pk, Shipment.READY, actor=self.admin)
        transition_shipment(shipment.pk, Shipment.ACCEPTED, actor=self.admin)
        self.order.refresh_from_db()
        self.assertEqual(self.order.fulfillment_status, Order.FULFILLMENT_SHIPPED)

    def test_shipment_allocations_cannot_exceed_ordered_quantity(self):
        create_shipment(self.order.pk, actor=self.admin, line_quantities={self.line.pk: 2})
        with self.assertRaises(LifecycleProblem):
            create_shipment(self.order.pk, actor=self.admin, line_quantities={self.line.pk: 1})

    def test_return_request_requires_owned_lines_and_positive_quantity(self):
        request = create_return_request(
            self.order.pk, reason_category="defective",
            reason="Produit abîmé", customer=self.order.customer,
            lines={self.line.pk: 1},
        )
        self.assertEqual(request.status, ReturnRequest.RECEIVED)
        with self.assertRaises(LifecycleProblem):
            create_return_request(
                self.order.pk, reason_category="defective",
                reason="Deuxième demande excédentaire", customer=None,
                lines={self.line.pk: 2},
            )

    def test_unpaid_order_cannot_be_shipped(self):
        self.order.status = Order.PENDING
        self.order.save(update_fields=["status"])
        with self.assertRaises(LifecycleProblem):
            create_shipment(self.order.pk, actor=self.admin, line_quantities={self.line.pk: 1})

    @patch.dict("os.environ", {"STRIPE_LIVE_MODE": "False"})
    @override_settings(STRIPE_SECRET_KEY="sk_test_fake", DEBUG=False)
    def test_refund_request_is_idempotent(self):
        request_key = uuid.uuid4()
        provider_refund = SimpleNamespace(id="re_test_123", status="succeeded")
        with patch("checkout.lifecycle.stripe.Refund.create", return_value=provider_refund) as create:
            first = request_refund(
                self.order.pk, amount="10.00", reason="Retour validé",
                actor=self.admin, idempotency_key=request_key,
            )
            second = request_refund(
                self.order.pk, amount="10.00", reason="Retour validé",
                actor=self.admin, idempotency_key=request_key,
            )
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(create.call_count, 1)
        self.assertEqual(first.status, "succeeded")

    def test_commercial_state_machine_requires_verified_delivery(self):
        transition_order_commercial_status(self.order.pk, Order.COMMERCIAL_CONFIRMED, actor=self.admin)
        transition_order_commercial_status(self.order.pk, Order.COMMERCIAL_PROCESSING, actor=self.admin)
        transition_order_commercial_status(self.order.pk, Order.COMMERCIAL_PREPARING, actor=self.admin)
        transition_order_commercial_status(self.order.pk, Order.COMMERCIAL_READY_TO_SHIP, actor=self.admin)
        with self.assertRaises(LifecycleProblem):
            transition_order_commercial_status(self.order.pk, Order.COMMERCIAL_SHIPPED, actor=self.admin)

        shipment = create_shipment(
            self.order.pk, actor=self.admin, line_quantities={self.line.pk: 1},
        )
        for status in (Shipment.READY, Shipment.ACCEPTED, Shipment.IN_TRANSIT, Shipment.DELIVERED):
            transition_shipment(shipment.pk, status, actor=self.admin)
        self.order.refresh_from_db()
        self.assertEqual(self.order.commercial_status, Order.COMMERCIAL_DELIVERED)
        transition_order_commercial_status(self.order.pk, Order.COMMERCIAL_COMPLETED, actor=self.admin)
        self.order.refresh_from_db()
        self.assertEqual(self.order.commercial_status, Order.COMMERCIAL_COMPLETED)
