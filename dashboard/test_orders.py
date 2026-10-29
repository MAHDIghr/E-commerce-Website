import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from checkout.models import Order, OrderLine, PaymentAttempt
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

    def test_paid_order_can_be_prepared_shipped_and_delivered(self):
        url = reverse("dashboard:order_update_fulfillment", args=[self.order.pk])
        response = self.client.post(url, {
            "fulfillment_status": Order.FULFILLMENT_PREPARING,
            "shipping_carrier": "Colissimo", "tracking_number": "TEST-123",
            "internal_note": "Emballage contrôlé",
        })
        self.assertRedirects(response, reverse("dashboard:order_detail", args=[self.order.pk]), fetch_redirect_response=False)
        self.order.refresh_from_db()
        self.assertEqual(self.order.fulfillment_status, Order.FULFILLMENT_PREPARING)
        self.assertEqual(self.order.internal_note, "Emballage contrôlé")
        response = self.client.post(url, {
            "fulfillment_status": Order.FULFILLMENT_SHIPPED,
            "shipping_carrier": "Colissimo", "tracking_number": "TEST-123",
        })
        self.assertEqual(response.status_code, 302)
        self.order.refresh_from_db()
        self.assertEqual(self.order.fulfillment_status, Order.FULFILLMENT_SHIPPED)
        self.assertIsNotNone(self.order.shipped_at)
        response = self.client.post(url, {
            "fulfillment_status": Order.FULFILLMENT_DELIVERED,
            "shipping_carrier": "Colissimo", "tracking_number": "TEST-123",
        })
        self.assertEqual(response.status_code, 302)
        self.order.refresh_from_db()
        self.assertEqual(self.order.fulfillment_status, Order.FULFILLMENT_DELIVERED)
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
