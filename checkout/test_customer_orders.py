import uuid
from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from .models import Order, OrderLine, ReturnRequest


class PublicOrderTrackingTests(TestCase):
    def setUp(self):
        cache.clear()
        self.order = Order.objects.create(
            checkout_key=uuid.uuid4(),
            customer=None,
            email="guest@example.test",
            full_name="Client invité",
            address_line1="1 rue du Test",
            postal_code="75001",
            city="Paris",
            shipping_method="standard",
            subtotal=Decimal("30.00"),
            total=Decimal("30.00"),
            status=Order.PAID,
        )

    def test_tracking_page_is_accessible_by_reference_without_login(self):
        response = self.client.get(
            reverse("checkout:tracking", kwargs={"public_id": self.order.public_id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(self.order.public_id))
        self.assertContains(response, "Suivi de commande")
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(response["Referrer-Policy"], "no-referrer")
        self.assertNotContains(response, self.order.email)
        self.assertNotContains(response, self.order.address_line1)

    def test_direct_tracking_route_rate_limits_invalid_references(self):
        from uuid import uuid4

        url = reverse("checkout:tracking", kwargs={"public_id": uuid4()})
        for _ in range(30):
            self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get(url).status_code, 429)

    def test_successful_tracking_views_do_not_consume_failure_limit(self):
        url = reverse("checkout:tracking", kwargs={"public_id": self.order.public_id})
        for _ in range(35):
            self.assertEqual(self.client.get(url).status_code, 200)

    def test_reference_form_redirects_to_matching_order_tracking(self):
        response = self.client.post(
            reverse("checkout:tracking_lookup"),
            {"reference": str(self.order.public_id)},
        )
        self.assertRedirects(
            response,
            reverse("checkout:tracking", kwargs={"public_id": self.order.public_id}),
        )

    def test_reference_lookup_accepts_optional_hash_prefix(self):
        response = self.client.post(
            reverse("checkout:tracking_lookup"),
            {"reference": f"#{self.order.public_id}"},
        )
        self.assertRedirects(
            response,
            reverse("checkout:tracking", kwargs={"public_id": self.order.public_id}),
        )

    def test_unknown_reference_shows_generic_error_without_leaking_order_data(self):
        response = self.client.post(
            reverse("checkout:tracking_lookup"),
            {"reference": str(uuid.uuid4())},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Référence introuvable")
        self.assertNotContains(response, self.order.email)

    def test_invalid_reference_does_not_raise_an_exception(self):
        response = self.client.post(
            reverse("checkout:tracking_lookup"),
            {"reference": "not-a-valid-reference"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Référence introuvable")

    def test_paid_guest_can_submit_return_request_using_reference_without_login(self):
        line = OrderLine.objects.create(
            order=self.order,
            offer_id_snapshot=1,
            product_name="Sac test",
            quantity=1,
            unit_price=Decimal("30.00"),
            line_total=Decimal("30.00"),
        )
        response = self.client.post(
            reverse("checkout:return_request", kwargs={"public_id": self.order.public_id}),
            {
                f"line_{line.pk}": "1",
                "reason_category": "defective",
                "reason": "Produit endommagé",
                "customer_note": "",
            },
        )
        self.assertRedirects(
            response,
            reverse("checkout:tracking", kwargs={"public_id": self.order.public_id}),
        )
        self.assertEqual(ReturnRequest.objects.filter(order=self.order).count(), 1)

    def test_public_return_request_endpoint_is_rate_limited(self):
        url = reverse("checkout:return_request", kwargs={"public_id": self.order.public_id})
        payload = {"reason_category": "defective", "reason": "Produit endommagé"}
        for _ in range(5):
            self.assertEqual(self.client.post(url, payload).status_code, 400)
        self.assertEqual(self.client.post(url, payload).status_code, 429)

    def test_unpaid_order_cannot_accept_public_return_request(self):
        self.order.status = Order.PENDING
        self.order.save(update_fields=["status"])
        response = self.client.post(
            reverse("checkout:return_request", kwargs={"public_id": self.order.public_id}),
            {"reason_category": "defective", "reason": "Produit endommagé"},
        )
        self.assertEqual(response.status_code, 404)

    def test_lookup_is_rate_limited(self):
        url = reverse("checkout:tracking_lookup")
        for _ in range(10):
            response = self.client.post(url, {"reference": "invalid"})
            self.assertEqual(response.status_code, 200)
        response = self.client.post(url, {"reference": "invalid"})
        self.assertEqual(response.status_code, 429)
