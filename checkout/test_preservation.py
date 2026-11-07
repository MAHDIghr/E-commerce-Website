"""Régression du formulaire, des devis et des mises à jour sans coordonnées persistées."""
from decimal import Decimal
from unittest.mock import patch
import uuid

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from pages.test_commercial_information import approved_information
from . import tests as checkout_tests
from .models import Order, PromoCode


@override_settings(COMMERCIAL_INFORMATION=approved_information())
class CheckoutPreservationTests(TestCase):
    setUp = checkout_tests.CheckoutIntegrationTests.setUp
    add_to_cart = checkout_tests.CheckoutIntegrationTests.add_to_cart

    def address(self):
        return {"checkout_fields_present": "1", "first_name": "Camille-PRIVE",
                "last_name": "Martin-PRIVE", "email": "prive@example.test",
                "address_line1": "15 rue PRIVEE", "postal_code": "75001", "city": "Paris",
                "country": "FR", "shipping_method": "free", "accept_terms": "on",
                "billing_address_line1": "20 rue FACTURATION", "billing_postal_code": "69001",
                "billing_city": "Lyon", "billing_country": "FR"}

    def promo(self):
        return PromoCode.objects.create(code="PRESERVE20", discount_type=PromoCode.PERCENT,
                                        value=Decimal("20.00"), is_active=True)

    def update(self, data=None):
        return self.client.post(reverse("checkout:checkout"), data or {"country": "FR", "postal_code": "75001"}, HTTP_X_CHECKOUT_UPDATE="1")

    def test_no_js_promo_actions_preserve_address_and_billing_without_storing_them(self):
        self.add_to_cart(); self.promo()
        for action, code in [("apply", "PRESERVE20"), ("remove", ""), ("apply", "INCONNU")]:
            with self.subTest(action=action, code=code):
                response = self.client.post(reverse("checkout:checkout"), {**self.address(), "promo_action": action, "promo_code": code})
                self.assertEqual(response.status_code, 200)
                for value in ("Camille-PRIVE", "Martin-PRIVE", "15 rue PRIVEE", "prive@example.test", "20 rue FACTURATION", "69001"):
                    self.assertContains(response, f'value="{value}"')
                    self.assertNotIn(value, str(dict(self.client.session)))
                self.assertContains(response, 'name="billing_same_as_shipping" id="id_billing_same_as_shipping" >')
                self.assertContains(response, 'id="billing-fields">')
                self.assertFalse(response.context["form"].is_bound)
                self.assertFalse(response.context["form"].errors)
                self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(Order.objects.count(), 0)

    def test_async_promo_updates_summary_without_returning_or_persisting_coordinates(self):
        self.add_to_cart(); self.promo()
        response = self.update({**self.address(), "promo_action": "apply", "promo_code": "PRESERVE20"})
        data = response.json()
        self.assertTrue(data["quote_valid"])
        self.assertIn('value="PRESERVE20"', data["summary_html"])
        self.assertIn('value="remove"', data["summary_html"])
        self.assertIn('−17,98 €', data["summary_html"])
        self.assertEqual([option["total"] for option in data["options"]], ["76.82", "81.82"])
        for private in ["Camille-PRIVE", "Martin-PRIVE", "15 rue PRIVEE", "prive@example.test", "20 rue FACTURATION"]:
            self.assertNotIn(private, str(data))
            self.assertNotIn(private, str(dict(self.client.session)))
        data = self.update({"country": "FR", "postal_code": "75001", "promo_action": "remove"}).json()
        self.assertEqual([option["total"] for option in data["options"]], ["89.90", "99.80"])
        self.assertNotIn('value="remove"', data["summary_html"])

    def test_async_quotes_require_destination_not_identity(self):
        self.add_to_cart()
        self.assertTrue(self.update().json()["quote_valid"])
        for fields in [{"country": "", "postal_code": "75001"}, {"country": "FR", "postal_code": ""}, {"country": "ZZ", "postal_code": "75001"}]:
            with self.subTest(fields=fields):
                data = self.update(fields).json()
                self.assertFalse(data["quote_valid"])
                self.assertFalse(data["can_pay"])
                self.assertEqual(data["options"], [])
                self.assertIn("À recalculer", data["summary_html"])
                self.assertNotIn('89,90 € TTC</strong>', data["summary_html"])
                self.assertTrue(data["errors"])
                self.assertNotIn("first_name", data["errors"])

    def test_quantity_refresh_revalidates_lines_stock_totals_and_promo(self):
        self.add_to_cart(); self.promo()
        self.update({"country": "FR", "postal_code": "75001", "promo_action": "apply", "promo_code": "PRESERVE20"})
        import json
        self.client.post(reverse("shop:cart_mutation"), json.dumps({"action": "update", "variant_id": self.variant.pk, "offer_id": self.offer.pk, "quantity": 2}), content_type="application/json")
        data = self.update().json()
        self.assertTrue(data["quote_valid"])
        self.assertIn('<b>2</b>', data["summary_html"])
        self.assertIn("−35,96 €", data["summary_html"])
        self.assertEqual(data["options"][0]["total"], "143.84")
        self.variant.stock_quantity = 0; self.variant.save(update_fields=["stock_quantity"])
        data = self.update().json()
        self.assertFalse(data["quote_valid"])
        self.assertTrue(data["cart_error"])
        self.assertEqual(data["options"], [])
        self.assertFalse(Order.objects.exists())

    def test_empty_cart_async_refresh_returns_recoverable_state_not_redirect(self):
        response = self.update()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["quote_valid"])
        self.assertTrue(response.json()["cart_error"])
        self.assertEqual(response.json()["options"], [])

    def test_async_post_requires_csrf_and_read_refresh_does_not_consume_attempt(self):
        self.add_to_cart()
        session = self.client.session; session["checkout_attempt_key"] = str(uuid.uuid4()); session.save()
        before = self.client.session["checkout_attempt_key"]
        strict = Client(enforce_csrf_checks=True); strict.cookies = self.client.cookies
        strict.get(reverse("checkout:checkout"))
        self.assertEqual(strict.post(reverse("checkout:checkout"), {"country": "FR", "postal_code": "75001"}, HTTP_X_CHECKOUT_UPDATE="1").status_code, 403)
        response = strict.post(reverse("checkout:checkout"), {"country": "FR", "postal_code": "75001"}, HTTP_X_CHECKOUT_UPDATE="1", HTTP_X_CSRFTOKEN=strict.cookies["csrftoken"].value)
        self.assertTrue(response.json()["quote_valid"])
        self.assertEqual(strict.session["checkout_attempt_key"], before)

    def test_server_error_keeps_values_and_renders_linked_error_summary(self):
        self.add_to_cart()
        data = self.address(); data["email"] = "email-invalide"; data.pop("accept_terms")
        response = self.client.post(reverse("checkout:checkout"), data)
        self.assertContains(response, 'value="15 rue PRIVEE"')
        self.assertContains(response, 'value="email-invalide"')
        self.assertContains(response, 'id="checkout-errors" class="checkout-alert" role="alert" tabindex="-1">')
        self.assertContains(response, 'href="#id_email"')
        self.assertContains(response, 'id="id_email_error"')
        self.assertContains(response, 'aria-invalid="true"')
        self.assertContains(response, 'href="#id_accept_terms"')
        self.assertContains(response, 'id="id_accept_terms"')
        self.assertFalse(Order.objects.exists())

    @override_settings(COMMERCIAL_INFORMATION={})
    def test_async_updates_cannot_enable_sales_without_approved_information(self):
        self.add_to_cart()
        with patch("checkout.views.create_order_and_reserve") as create:
            data = self.update().json()
            self.assertFalse(data["quote_valid"])
            self.assertFalse(data["can_pay"])
            self.client.post(reverse("checkout:checkout"), {**self.address(), "billing_same_as_shipping": "on"})
            create.assert_not_called()

    def test_summary_controls_are_associated_with_the_single_main_form(self):
        self.add_to_cart(); self.promo()
        self.update({"country": "FR", "postal_code": "75001", "promo_action": "apply", "promo_code": "PRESERVE20"})
        response = self.client.get(reverse("checkout:checkout"))
        html = response.content.decode().split('<aside class="checkout-summary"', 1)[1].split('</aside>', 1)[0]
        self.assertNotIn('<form', html)
        self.assertIn('form="checkout-form" name="promo_action" value="apply"', html)
        self.assertIn('form="checkout-form" name="promo_action" value="remove"', html)
        self.assertContains(response, 'name="checkout_fields_present" value="1"')
