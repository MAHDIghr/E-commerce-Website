import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from checkout.models import Order, OrderLine, PaymentAttempt, Refund
from .order_views import FULFILLMENT_TRANSITIONS


class DashboardOrderManagementTests(TestCase):
    def setUp(self):
        admin = get_user_model().objects.create_superuser(
            username="orders-admin", email="orders-admin@example.test",
            password="StrongTestPassword!2026",
        )
        self.client.force_login(admin)
        self.order = Order.objects.create(
            checkout_key=uuid.uuid4(), email="client@example.test",
            full_name="Camille Martin", phone="0600000000",
            address_line1="1 rue du Test", postal_code="75001", city="Paris",
            country="FR", shipping_method="standard",
            subtotal=Decimal("89.90"), shipping_amount=Decimal("4.90"),
            total=Decimal("94.80"), status=Order.PAID,
        )

    def test_orders_page_is_admin_only(self):
        self.client.logout()
        response = self.client.get(reverse("dashboard:orders"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("dashboard:login"), response.url)

    def test_staff_without_superuser_cannot_view_orders(self):
        self.client.logout()
        staff = get_user_model().objects.create_user(
            username="orders-staff", email="orders-staff@example.test",
            password="StrongTestPassword!2026", is_staff=True,
        )
        self.client.force_login(staff)
        response = self.client.get(reverse("dashboard:orders"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("dashboard:login"), response.url)
        response = self.client.get(reverse("dashboard:order_detail", args=[self.order.pk]))
        self.assertEqual(response.status_code, 302)

    def test_orders_list_shows_all_payment_states_and_filters(self):
        unpaid = Order.objects.create(
            checkout_key=uuid.uuid4(), email="other@example.test",
            full_name="Alex Dupont", address_line1="2 rue Test",
            postal_code="75002", city="Lyon", country="FR",
            shipping_method="standard", subtotal=Decimal("20.00"),
            shipping_amount=Decimal("4.90"), total=Decimal("24.90"),
            status=Order.PENDING,
        )
        response = self.client.get(reverse("dashboard:orders"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Camille Martin")
        self.assertContains(response, "Alex Dupont")
        response = self.client.get(reverse("dashboard:orders"), {"payment": Order.PENDING})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alex Dupont")
        self.assertNotContains(response, "Camille Martin")
        self.assertEqual(response.context["page_obj"].paginator.count, 1)

    def test_order_detail_displays_snapshot_amounts_and_customer(self):
        OrderLine.objects.create(
            order=self.order, product_name="Cabas camel", offer_id_snapshot=1,
            variant_name="Camel", quantity=1, unit_price=Decimal("89.90"),
            line_total=Decimal("89.90"), components_snapshot=[],
        )
        PaymentAttempt.objects.create(
            order=self.order, amount=self.order.total, currency="eur",
            status=PaymentAttempt.SUCCEEDED,
        )
        response = self.client.get(reverse("dashboard:order_detail", args=[self.order.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cabas camel")
        self.assertContains(response, "Camille Martin")
        self.assertContains(response, "Historique de paiement")
        self.assertContains(response, "89,90")

    def test_unpaid_order_cannot_be_marked_as_preparing(self):
        self.order.status = Order.PENDING
        self.order.save(update_fields=["status"])
        response = self.client.post(
            reverse("dashboard:order_update_fulfillment", args=[self.order.pk]),
            {"fulfillment_status": Order.FULFILLMENT_PREPARING},
        )
        self.assertRedirects(response, reverse("dashboard:order_detail", args=[self.order.pk]), fetch_redirect_response=False)
        self.order.refresh_from_db()
        self.assertEqual(self.order.fulfillment_status, Order.FULFILLMENT_UNFULFILLED)

    def test_paid_order_requires_a_real_shipment_before_shipped_or_delivered(self):
        url = reverse("dashboard:order_update_fulfillment", args=[self.order.pk])
        response = self.client.post(url, {
            "fulfillment_status": Order.FULFILLMENT_PREPARING,
            "shipping_carrier": "Colissimo", "tracking_number": "TEST-123",
            "internal_note": "Emballage contrôlé",
        })
        self.assertEqual(response.status_code, 302)
        self.order.refresh_from_db()
        self.assertEqual(self.order.fulfillment_status, Order.FULFILLMENT_PREPARING)
        self.assertEqual(self.order.internal_note, "Emballage contrôlé")

        response = self.client.post(url, {
            "fulfillment_status": Order.FULFILLMENT_SHIPPED,
            "shipping_carrier": "Colissimo", "tracking_number": "TEST-123",
        })
        self.order.refresh_from_db()
        self.assertEqual(self.order.fulfillment_status, Order.FULFILLMENT_PREPARING)

        line = OrderLine.objects.create(
            order=self.order, product_name="Cabas camel", offer_id_snapshot=1,
            variant_name="Camel", quantity=1, unit_price=Decimal("89.90"),
            line_total=Decimal("89.90"), components_snapshot=[],
        )
        response = self.client.post(
            reverse("dashboard:order_create_shipment", args=[self.order.pk]),
            {"carrier": "Colissimo", "tracking_number": "TEST-123", f"line_{line.pk}": "1"},
        )
        self.assertEqual(response.status_code, 302)
        from checkout.models import Shipment
        shipment = self.order.shipments.get()
        status_url = reverse("dashboard:shipment_update_status", args=[self.order.pk, shipment.pk])
        for status in (Shipment.READY, Shipment.ACCEPTED, Shipment.IN_TRANSIT, Shipment.OUT_FOR_DELIVERY, Shipment.DELIVERED):
            response = self.client.post(status_url, {"status": status, "reason": "Événement de test"})
            self.assertEqual(response.status_code, 302)
        self.order.refresh_from_db()
        self.assertEqual(self.order.fulfillment_status, Order.FULFILLMENT_DELIVERED)
        self.assertIsNotNone(self.order.shipped_at)
        self.assertIsNotNone(self.order.delivered_at)

    def test_invalid_transition_is_rejected_and_payment_status_is_unchanged(self):
        self.order.fulfillment_status = Order.FULFILLMENT_DELIVERED
        self.order.save(update_fields=["fulfillment_status"])
        response = self.client.post(
            reverse("dashboard:order_update_fulfillment", args=[self.order.pk]),
            {"fulfillment_status": Order.FULFILLMENT_PREPARING},
        )
        self.assertEqual(response.status_code, 302)
        self.order.refresh_from_db()
        self.assertEqual(self.order.fulfillment_status, Order.FULFILLMENT_DELIVERED)
        self.assertEqual(self.order.status, Order.PAID)

    def test_transition_graph_has_no_direct_unfulfilled_to_delivered(self):
        self.assertNotIn(Order.FULFILLMENT_DELIVERED, FULFILLMENT_TRANSITIONS[Order.FULFILLMENT_UNFULFILLED])

    def test_unpaid_order_can_be_cancelled_and_audited(self):
        self.order.status = Order.PENDING
        self.order.save(update_fields=["status"])
        response = self.client.post(
            reverse("dashboard:order_cancel", args=[self.order.pk]),
            {"reason": "Client n'a pas finalisé le paiement"},
        )
        self.assertEqual(response.status_code, 302)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.CANCELLED)
        self.assertTrue(self.order.lifecycle_events.filter(event_type="order_cancelled").exists())

    def test_paid_order_cannot_use_unpaid_cancellation_action(self):
        response = self.client.post(
            reverse("dashboard:order_cancel", args=[self.order.pk]),
            {"reason": "Tentative interdite"},
        )
        self.assertEqual(response.status_code, 302)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.PAID)

    def test_paid_order_cancellation_requires_full_refund_and_restores_unshipped_stock(self):
        from product.models import Category, Product, ProductVariant
        category = Category.objects.create(name="Accessoires", slug="accessoires-test")
        product = Product.objects.create(category=category, name="Sac test", slug="sac-test-stock")
        variant = ProductVariant.objects.create(
            product=product, sku="SAC-TEST-STOCK", color_name="Noir",
            color_slug="noir", color_code="#111111", stock_quantity=4,
        )
        self.order.stock_committed = True
        self.order.stock_requirements_snapshot = {str(variant.pk): 1}
        self.order.stripe_payment_intent_id = "pi_test_cancel"
        self.order.save(update_fields=["stock_committed", "stock_requirements_snapshot", "stripe_payment_intent_id"])
        Refund.objects.create(
            order=self.order, amount=self.order.total, currency="eur",
            reason="Remboursement total confirmé", status=Refund.SUCCEEDED,
        )
        response = self.client.post(
            reverse("dashboard:order_cancel", args=[self.order.pk]),
            {"reason": "Commande annulée avant expédition"},
        )
        self.assertEqual(response.status_code, 302)
        self.order.refresh_from_db()
        variant.refresh_from_db()
        self.assertEqual(self.order.status, Order.PAID)
        self.assertEqual(self.order.commercial_status, Order.COMMERCIAL_CANCELLED)
        self.assertFalse(self.order.stock_committed)
        self.assertEqual(variant.stock_quantity, 5)
