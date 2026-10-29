import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from checkout.lifecycle import (
    LifecycleProblem, create_return_request, create_shipment, transition_shipment,
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
