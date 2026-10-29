import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Order, OrderLine, ReturnRequest


class CustomerOrderAccessTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(username="order-owner", password="test-password-123")
        self.other = user_model.objects.create_user(username="other-customer", password="test-password-123")
        self.order = Order.objects.create(
            checkout_key=uuid.uuid4(),
            customer=self.owner,
            email="owner@example.test",
            full_name="Client Test",
            address_line1="1 rue du Test",
            postal_code="75001",
            city="Paris",
            shipping_method="standard",
            subtotal=Decimal("30.00"),
            total=Decimal("30.00"),
            status=Order.PAID,
        )

    def test_customer_order_list_contains_only_the_authenticated_customers_orders(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("checkout:customer_orders"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(self.order.public_id)[:8])

        self.client.force_login(self.other)
        response = self.client.get(reverse("checkout:customer_orders"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, str(self.order.public_id)[:8])

    def test_customer_cannot_open_another_customers_order(self):
        self.client.force_login(self.other)
        response = self.client.get(
            reverse("checkout:customer_order_detail", kwargs={"public_id": self.order.public_id})
        )
        self.assertEqual(response.status_code, 404)

    def test_customer_can_submit_a_return_for_an_owned_paid_order(self):
        self.order.fulfillment_status = Order.FULFILLMENT_DELIVERED
        self.order.save(update_fields=["fulfillment_status"])
        line = OrderLine.objects.create(
            order=self.order,
            offer_id_snapshot=1,
            product_name="Sac de test",
            quantity=2,
            unit_price=Decimal("15.00"),
            line_total=Decimal("30.00"),
        )
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("checkout:customer_return_request", kwargs={"public_id": self.order.public_id}),
            {
                "reason_category": "defective",
                "reason": "Article endommagé",
                f"line_{line.pk}": "1",
            },
        )
        self.assertRedirects(
            response,
            reverse("checkout:customer_order_detail", kwargs={"public_id": self.order.public_id}),
        )
        return_request = ReturnRequest.objects.get(order=self.order)
        self.assertEqual(return_request.customer, self.owner)
        self.assertEqual(return_request.lines.get(order_line=line).quantity, 1)
