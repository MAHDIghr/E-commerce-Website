import re
import uuid
from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from checkout.models import Order, OrderLine, ReturnRequest


class PublicOrderTrackingTests(TestCase):
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

    def test_valid_public_reference_displays_only_its_order(self):
        response = self.client.get(reverse("checkout:tracking", args=[self.order.public_id]))
        self.assertEqual(response.status_code, 200)
        # Le suivi public ne doit pas exposer les données personnelles du client.
        self.assertNotContains(response, "Client Privé")
        self.assertNotContains(response, "private-client@example.test")
        self.assertContains(response, "Sac test")
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(response["Referrer-Policy"], "same-origin")
        self.assertContains(response, 'name="referrer" content="same-origin"')

    def test_unknown_public_reference_returns_404(self):
        response = self.client.get(reverse("checkout:tracking", args=[uuid.uuid4()]))
        self.assertEqual(response.status_code, 404)

    def test_public_reference_cannot_display_another_order(self):
        another_order = Order.objects.create(
            checkout_key=uuid.uuid4(), email="another@example.test",
            full_name="Autre client", address_line1="2 rue de Test",
            postal_code="75002", city="Paris", country="FR",
            shipping_method="standard", subtotal=Decimal("10.00"),
            shipping_amount=Decimal("4.90"), total=Decimal("14.90"),
            status=Order.PAID,
        )
        response = self.client.get(reverse("checkout:tracking", args=[another_order.public_id]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Autre client")
        self.assertNotContains(response, "another@example.test")
        self.assertNotContains(response, "Client Privé")
        self.assertNotContains(response, "Sac test")

    def test_customer_can_submit_partial_return_request(self):
        response = self.client.post(
            reverse("checkout:return_request", args=[self.order.public_id]),
            {
                "reason_category": "defective",
                "reason": "Le produit présente un défaut.",
                f"line_{self.line.pk}": "1",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ReturnRequest.objects.filter(order=self.order).count(), 1)

    def test_tracking_lookup_form_accepts_same_origin_csrf_submission(self):
        from django.test import Client

        client = Client(enforce_csrf_checks=True)
        page = client.get(reverse("checkout:tracking_lookup"))
        self.assertEqual(page.status_code, 200)
        self.assertIn("csrftoken", client.cookies)
        match = re.search(
            rb'name="csrfmiddlewaretoken" value="([^"]+)"',
            page.content,
        )
        self.assertIsNotNone(match)

        response = client.post(
            reverse("checkout:tracking_lookup"),
            {
                "reference": str(self.order.public_id),
                "csrfmiddlewaretoken": match.group(1).decode(),
            },
            HTTP_ORIGIN="http://testserver",
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response, reverse("checkout:tracking", args=[self.order.public_id]),
            fetch_redirect_response=False,
        )

    def test_tracking_lookup_rejects_opaque_null_origin(self):
        from django.test import Client

        client = Client(enforce_csrf_checks=True)
        page = client.get(reverse("checkout:tracking_lookup"))
        match = re.search(
            rb'name="csrfmiddlewaretoken" value="([^"]+)"',
            page.content,
        )
        self.assertIsNotNone(match)
        response = client.post(
            reverse("checkout:tracking_lookup"),
            {
                "reference": str(self.order.public_id),
                "csrfmiddlewaretoken": match.group(1).decode(),
            },
            HTTP_ORIGIN="null",
        )
        self.assertEqual(response.status_code, 403)

    def test_tracking_lookup_redirects_when_reference_exists(self):
        response = self.client.post(reverse("checkout:tracking_lookup"), {
            "reference": str(self.order.public_id),
        })
        self.assertRedirects(
            response, reverse("checkout:tracking", args=[self.order.public_id]),
            fetch_redirect_response=False,
        )

    def test_tracking_lookup_does_not_disclose_unknown_references(self):
        response = self.client.post(reverse("checkout:tracking_lookup"), {
            "reference": str(uuid.uuid4()),
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Référence introuvable")
        self.assertNotContains(response, "Client Privé")

    def test_withdrawal_requires_no_justification_and_duplicate_quantities_are_rejected(self):
        url = reverse('checkout:return_request', args=[self.order.public_id])
        data = {'reason_category':'withdrawal', f'line_{self.line.pk}':'1'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code,302)
        declaration = ReturnRequest.objects.get(order=self.order)
        self.assertIn('rétractation',declaration.reason)
        response = self.client.post(url,data)
        self.assertEqual(response.status_code,400)
        self.assertEqual(ReturnRequest.objects.filter(order=self.order).count(),1)
