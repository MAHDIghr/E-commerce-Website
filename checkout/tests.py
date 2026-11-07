import json
import re
import uuid
from types import SimpleNamespace
from decimal import Decimal
from unittest.mock import patch

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from product.models import Category, Product, ProductMedia, ProductOffer, ProductOfferItem, ProductVariant
from .models import Order, OrderLine, PaymentAttempt, PromoCode, StripeWebhookEvent, Refund, OrderEvent
from shop.views import CART_SESSION_KEY
from .forms import CheckoutForm
from .services import CheckoutProblem, RetryableWebhookError, apply_promo_code, create_order_and_reserve, create_stripe_session, process_stripe_event, release_reserved_stock, shipping_price


from pages.test_commercial_information import approved_information


@override_settings(COMMERCIAL_INFORMATION=approved_information())
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

    def test_applied_promo_is_rendered_with_remove_control_and_server_totals(self):
        self.add_to_cart()
        PromoCode.objects.create(code="CONTRAT20", discount_type=PromoCode.PERCENT,
                                 value=Decimal("20.00"), is_active=True)
        response = self.client.post(reverse("checkout:checkout"),
                                    {"promo_action": "apply", "promo_code": "contrat20"}, follow=True)
        self.assertContains(response, 'value="CONTRAT20"')
        self.assertContains(response, '<strong>CONTRAT20</strong>', html=True)
        self.assertContains(response, 'name="promo_action" value="remove"')
        self.assertContains(response, 'Retirer</button>')
        self.assertContains(response, 'Remise (CONTRAT20)')
        self.assertContains(response, '−17,98 €')
        self.assertContains(response, '71,92 €')
        self.assertContains(response, '76,82 €')
        self.assertContains(response, 'role="status" aria-live="polite" aria-atomic="true"')
        quote = self.client.get(reverse("checkout:shipping_quote"),
                                {"country": "FR", "postal_code": "75001", "subtotal": "0.01"})
        self.assertEqual(quote.json()["discounted_subtotal"], "71.92")
        self.assertEqual([option["total"] for option in quote.json()["options"]], ["76.82", "81.82"])

    def make_contract_promo(self, **overrides):
        values = {"code": "CONTRAT20", "discount_type": PromoCode.PERCENT,
                  "value": Decimal("20.00"), "is_active": True}
        values.update(overrides)
        return PromoCode.objects.create(**values)

    def test_removing_promo_renders_free_shipping_and_invalidates_payment_attempt(self):
        self.add_to_cart()
        promo = self.make_contract_promo()
        self.client.post(reverse("checkout:checkout"), {"promo_action": "apply", "promo_code": promo.code})
        session = self.client.session
        session["checkout_attempt_key"] = str(uuid.uuid4())
        session.save()
        response = self.client.post(reverse("checkout:checkout"), {"promo_action": "remove"}, follow=True)
        self.assertContains(response, "Code promo retiré.")
        self.assertContains(response, '<dd id="shipping-preview">Offerte</dd>', html=True)
        self.assertContains(response, '<dd id="checkout-total-preview">89,90 €</dd>', html=True)
        self.assertNotContains(response, 'name="promo_action" value="remove"')
        self.assertNotContains(response, "Remise (CONTRAT20)")
        self.assertNotContains(response, "Sous-total après remise")
        self.assertNotIn("checkout_promo_code", self.client.session)
        self.assertNotIn("checkout_attempt_key", self.client.session)
        quote = self.client.get(reverse("checkout:shipping_quote"), {"country": "FR", "postal_code": "75001"})
        self.assertEqual(quote.json()["options"], [{"method": "free", "label": "Standard offert — 0,00 €", "amount": "0.00", "total": "89.90"}, {"method": "express", "label": "Express — 9,90 €", "amount": "9.90", "total": "99.80"}])
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_quantity, 4)
        self.assertEqual(Order.objects.count(), 0)

    def test_promo_rejections_render_distinct_accessible_errors(self):
        from datetime import timedelta
        from django.utils import timezone
        self.add_to_cart()
        self.make_contract_promo(code="EXPIRE", ends_at=timezone.now() - timedelta(seconds=1))
        self.make_contract_promo(code="FUTUR", starts_at=timezone.now() + timedelta(days=1))
        self.make_contract_promo(code="INACTIF", is_active=False)
        self.make_contract_promo(code="MINIMUM", minimum_subtotal=Decimal("100.00"))
        self.make_contract_promo(code="ZERO", maximum_discount=Decimal("0.00"))
        cases = [
            ("INCONNU", "Ce code promo n’est pas valide."),
            ("EXPIRE", "Ce code promo a expiré."),
            ("FUTUR", "Cette promotion n’est pas applicable actuellement."),
            ("INACTIF", "Cette promotion n’est pas applicable actuellement."),
            ("MINIMUM", "Ce code nécessite un sous-total d’au moins 100.00 €."),
            ("ZERO", "Ce code ne peut pas être appliqué à cette commande."),
            ("", "Saisissez un code promo."),
        ]
        for code, message in cases:
            with self.subTest(code=code):
                response = self.client.post(reverse("checkout:checkout"), {"promo_action": "apply", "promo_code": code}, follow=True)
                self.assertContains(response, '<div id="checkout-promo-status" role="status" aria-live="polite" aria-atomic="true">')
                self.assertContains(response, f'<p class="checkout-promo__notice checkout-promo__notice--error">{message}</p>', html=True)
                self.assertNotContains(response, 'name="promo_action" value="remove"')
                self.assertNotContains(response, "Code appliqué")
                self.assertNotIn("checkout_promo_code", self.client.session)

    def test_invalid_replacement_keeps_valid_promo_visible_without_echoing_raw_input(self):
        self.add_to_cart()
        promo = self.make_contract_promo()
        self.client.post(reverse("checkout:checkout"), {"promo_action": "apply", "promo_code": promo.code})
        response = self.client.post(reverse("checkout:checkout"), {"promo_action": "apply", "promo_code": '<script>alert("x")</script>'}, follow=True)
        self.assertContains(response, 'value="CONTRAT20"')
        self.assertContains(response, 'name="promo_action" value="remove"')
        self.assertContains(response, "−17,98 €")
        self.assertContains(response, "Ce code promo n’est pas valide.")
        self.assertNotContains(response, 'alert("x")')
        self.assertEqual(self.client.session["checkout_promo_code"], promo.code)
        refreshed = self.client.get(reverse("checkout:checkout"))
        self.assertContains(refreshed, '<details class="checkout-promo" open>')
        self.assertContains(refreshed, 'value="CONTRAT20"')
        self.assertContains(refreshed, 'name="promo_action" value="remove"')

    def test_expired_applied_code_is_removed_on_revalidation_with_shipping_recalculated(self):
        from datetime import timedelta
        from django.utils import timezone
        self.add_to_cart()
        promo = self.make_contract_promo()
        self.client.post(reverse("checkout:checkout"), {"promo_action": "apply", "promo_code": promo.code})
        promo.ends_at = timezone.now() - timedelta(seconds=1)
        promo.save(update_fields=["ends_at"])
        session = self.client.session
        session["checkout_attempt_key"] = str(uuid.uuid4())
        session.save()
        response = self.client.get(reverse("checkout:checkout"))
        self.assertContains(response, "Ce code promo a expiré.")
        self.assertNotContains(response, "appliqué. La remise")
        self.assertNotContains(response, 'name="promo_action" value="remove"')
        self.assertContains(response, '<dd id="shipping-preview">Offerte</dd>', html=True)
        self.assertContains(response, '<dd id="checkout-total-preview">89,90 €</dd>', html=True)
        self.assertNotIn("checkout_promo_code", self.client.session)
        self.assertNotIn("checkout_attempt_key", self.client.session)

    def test_bound_express_choice_renders_server_total_without_browser_price(self):
        self.add_to_cart()
        promo = self.make_contract_promo()
        self.client.post(reverse("checkout:checkout"), {"promo_action": "apply", "promo_code": promo.code})
        response = self.client.post(reverse("checkout:checkout"), {"shipping_method": "express", "total": "0.01", "discount": "89.90"})
        self.assertContains(response, '<dd id="shipping-preview">9,90 €</dd>', html=True)
        self.assertContains(response, '<dd id="checkout-total-preview">81,82 €</dd>', html=True)
        self.assertContains(response, "−17,98 €")
        self.assertContains(response, "71,92 €")
        self.assertEqual(Order.objects.count(), 0)

    def test_remove_promo_requires_csrf_and_does_not_reserve_stock(self):
        self.add_to_cart()
        promo = self.make_contract_promo()
        self.client.post(reverse("checkout:checkout"), {"promo_action": "apply", "promo_code": promo.code})
        strict = Client(enforce_csrf_checks=True)
        strict.cookies = self.client.cookies
        page = strict.get(reverse("checkout:checkout"))
        self.assertEqual(strict.post(reverse("checkout:checkout"), {"promo_action": "remove"}).status_code, 403)
        self.assertEqual(strict.session["checkout_promo_code"], promo.code)
        token = re.search(rb'name="csrfmiddlewaretoken" value="([^\"]+)"', page.content).group(1).decode()
        response = strict.post(reverse("checkout:checkout"), {"promo_action": "remove", "csrfmiddlewaretoken": token}, follow=True)
        self.assertContains(response, "Code promo retiré.")
        self.assertNotIn("checkout_promo_code", strict.session)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_quantity, 4)
        self.assertEqual(Order.objects.count(), 0)

    def test_empty_cart_redirects_to_catalog_with_message(self):
        response = self.client.get(reverse("checkout:checkout"), follow=True)
        self.assertRedirects(response, reverse("shop:catalog"))
        self.assertContains(response, "Votre panier est vide")

    def test_shipping_quote_uses_server_cart_and_recalculates_after_promo(self):
        self.add_to_cart()
        url = reverse("checkout:shipping_quote")
        response = self.client.get(url, {"country": "FR", "postal_code": "75001", "subtotal": "0.01"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["options"][0]["method"], "free")
        self.assertEqual(response.json()["options"][0]["total"], "89.90")
        promo = PromoCode.objects.get(code="BIENVENUE")
        promo.is_active = True
        promo.save(update_fields=["is_active"])
        self.client.post(reverse("checkout:checkout"), {"promo_action": "apply", "promo_code": promo.code})
        response = self.client.get(url, {"country": "BE", "postal_code": "1000"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([option["method"] for option in response.json()["options"]], ["standard", "express"])
        self.assertEqual(response.json()["discounted_subtotal"], "76.41")
        self.assertEqual(response.json()["options"][0]["total"], "81.31")
        self.assertEqual(self.client.get(url, {"country": "ZZ", "postal_code": "1000"}).status_code, 400)

    def test_identity_billing_and_terms_are_validated_and_stored(self):
        self.add_to_cart()
        data = {
            "first_name": "Camille", "last_name": "Martin", "email": "camille@example.test",
            "address_line1": "1 rue du Test", "postal_code": "75001", "city": "Paris",
            "country": "FR", "shipping_method": "free", "billing_address_line1": "2 rue de la Paix",
            "billing_postal_code": "69001", "billing_city": "Lyon", "billing_country": "FR",
        }
        form = CheckoutForm(data, subtotal=Decimal("89.90"))
        self.assertFalse(form.is_valid())
        self.assertIn("accept_terms", form.errors)
        data["accept_terms"] = "on"
        form = CheckoutForm(data, subtotal=Decimal("89.90"))
        self.assertTrue(form.is_valid(), form.errors)
        request = SimpleNamespace(session=self.client.session, user=SimpleNamespace(is_authenticated=False))
        order, reused = create_order_and_reserve(request, form, uuid.uuid4())
        self.assertFalse(reused)
        self.assertEqual(order.full_name, "Camille Martin")
        self.assertFalse(order.billing_same_as_shipping)
        self.assertEqual(order.billing_address_line1, "2 rue de la Paix")
        self.assertEqual(order.billing_city, "Lyon")

    def test_commercial_message_and_shipping_config_match_across_pages(self):
        from config.commercial import FREE_SHIPPING_THRESHOLD, SHIPPING_PRICES
        welcome, _ = PromoCode.objects.update_or_create(code="BIENVENUE", defaults={
            "discount_type": PromoCode.PERCENT, "value": Decimal("12.00"),
            "minimum_subtotal": Decimal("25.00"), "once_per_email": True,
            "is_active": True,
        })
        home = self.client.get(reverse("home:home"))
        catalog = self.client.get(reverse("shop:catalog"))
        detail = self.client.get(reverse("product:detail", kwargs={"slug": self.product.slug}))
        self.add_to_cart()
        checkout = self.client.get(reverse("checkout:checkout"))
        message = "−12 % avec le code BIENVENUE dès 25 €"
        for page in (home, catalog, detail, checkout):
            self.assertEqual(page.status_code, 200)
            self.assertContains(page, message)
            self.assertEqual(page.context["commercial"]["free_shipping_threshold"], str(FREE_SHIPPING_THRESHOLD))
        config = json.loads(re.search(r'<script id="commercial-config" type="application/json">(.*?)</script>', checkout.content.decode()).group(1))
        self.assertEqual(config["standard_shipping"], str(SHIPPING_PRICES["standard"]))
        self.assertEqual(config["express_shipping"], str(SHIPPING_PRICES["express"]))
        self.client.post(reverse("checkout:checkout"), {"promo_action": "apply", "promo_code": welcome.code})
        discounted_checkout = self.client.get(reverse("checkout:checkout"))
        self.assertFalse(discounted_checkout.context["free_shipping"])
        self.assertEqual(discounted_checkout.context["discounted_subtotal"], Decimal("79.11"))
        self.assertEqual([choice[0] for choice in discounted_checkout.context["form"].fields["shipping_method"].choices], ["standard", "express"])
        self.assertNotContains(home, "Vente flash")
        self.assertNotContains(detail, "Livraison payante")
        welcome.is_active = False
        welcome.save(update_fields=["is_active"])
        home = self.client.get(reverse("home:home"))
        self.assertNotContains(home, "−12 % avec le code")
        self.assertNotContains(home, 'id="welcome-modal-backdrop"')

    def test_cart_page_renders_current_server_validated_cart(self):
        self.add_to_cart()
        response = self.client.get(reverse("shop:cart_page"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cabas camel")
        self.assertContains(response, "Passer à la commande")
        self.assertContains(response, reverse("checkout:checkout"))

    def test_cart_mutation_invalidates_previous_checkout_attempt_key(self):
        session = self.client.session
        session["checkout_attempt_key"] = str(uuid.uuid4())
        session.save()
        self.add_to_cart()
        self.assertNotIn("checkout_attempt_key", self.client.session)

    def test_checkout_promo_and_payment_forms_accept_valid_csrf_tokens(self):
        client = Client(enforce_csrf_checks=True)
        session = client.session
        session[CART_SESSION_KEY] = {f"{self.variant.pk}:{self.offer.pk}": 1}
        session.save()

        page = client.get(reverse("checkout:checkout"), secure=True)
        self.assertEqual(page.status_code, 200)
        self.assertIn("csrftoken", client.cookies)
        self.assertContains(page, 'name="referrer" content="same-origin"')
        self.assertNotContains(page, 'name="referrer" content="no-referrer"')
        match = re.search(
            rb'name="csrfmiddlewaretoken" value="([^"]+)"',
            page.content,
        )
        self.assertIsNotNone(match)
        csrf_token = match.group(1).decode()

        promo_response = client.post(
            reverse("checkout:checkout"),
            {"promo_action": "apply", "promo_code": "CODE-INCONNU", "csrfmiddlewaretoken": csrf_token},
            secure=True,
            HTTP_ORIGIN="https://testserver",
        )
        self.assertEqual(promo_response.status_code, 302)

        payment_response = client.post(
            reverse("checkout:checkout"),
            {"csrfmiddlewaretoken": csrf_token},
            secure=True,
            HTTP_ORIGIN="https://testserver",
        )
        self.assertEqual(payment_response.status_code, 200)
        self.assertNotEqual(payment_response.status_code, 403)

    def test_checkout_forms_reject_opaque_null_origin(self):
        client = Client(enforce_csrf_checks=True)
        session = client.session
        session[CART_SESSION_KEY] = {f"{self.variant.pk}:{self.offer.pk}": 1}
        session.save()

        page = client.get(reverse("checkout:checkout"))
        self.assertEqual(page.status_code, 200)
        match = re.search(
            rb'name="csrfmiddlewaretoken" value="([^"]+)"',
            page.content,
        )
        self.assertIsNotNone(match)
        token = match.group(1).decode()

        promo_response = client.post(
            reverse("checkout:checkout"),
            {
                "promo_action": "apply",
                "promo_code": "CODE-INCONNU",
                "csrfmiddlewaretoken": token,
            },
            HTTP_ORIGIN="null",
        )
        self.assertEqual(promo_response.status_code, 403)

        payment_response = client.post(
            reverse("checkout:checkout"),
            {
                "full_name": "Camille Martin",
                "email": "camille@example.test",
                "address_line1": "1 rue du Test",
                "postal_code": "75001",
                "city": "Paris",
                "country": "FR",
                "shipping_method": "free",
                "csrfmiddlewaretoken": token,
            },
            HTTP_ORIGIN="null",
        )
        self.assertEqual(payment_response.status_code, 403)

    def test_checkout_and_result_reject_unsupported_http_methods(self):
        self.assertEqual(self.client.put(reverse("checkout:checkout")).status_code, 405)
        self.assertEqual(
            self.client.post(
                reverse("checkout:result", kwargs={"public_id": uuid.uuid4()})
            ).status_code,
            405,
        )

    def test_unknown_checkout_session_webhook_is_retryable_and_not_deduplicated(self):
        event = {"id": "evt_unknown_session", "type": "checkout.session.completed", "data": {"object": {
            "object": "checkout.session", "id": "cs_session_not_yet_associated",
            "currency": "eur", "amount_total": 100, "payment_status": "paid",
        }}}
        with self.assertRaises(RetryableWebhookError):
            process_stripe_event(event)
        self.assertFalse(StripeWebhookEvent.objects.filter(event_id="evt_unknown_session").exists())

    def test_free_shipping_is_automatic_at_threshold_and_paid_delivery_has_two_choices(self):
        free_form = CheckoutForm(subtotal=Decimal("80.00"))
        self.assertEqual(list(free_form.fields["shipping_method"].choices), [("free", "Standard offert — 0,00 €"), ("express", "Express — 9,90 €")])
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
        self.assertContains(response, "Paiement temporairement indisponible")

    def test_paid_return_clears_matching_cart_but_preserves_a_new_cart(self):
        from shop.views import CART_SESSION_KEY
        order = Order.objects.create(
            checkout_key=uuid.uuid4(), email="client@example.test", full_name="Client Test",
            address_line1="1 rue Test", postal_code="75001", city="Paris", country="FR",
            shipping_method="standard", subtotal=Decimal("89.90"), shipping_amount=Decimal("4.90"),
            total=Decimal("94.80"), status=Order.PAID,
            stripe_session_id="cs_test_paid_return",
            cart_snapshot={f"{self.variant.pk}:{self.offer.pk}": 1},
        )
        session = self.client.session
        session[CART_SESSION_KEY] = dict(order.cart_snapshot)
        session.save()
        response = self.client.get(reverse("checkout:result", kwargs={"public_id": order.public_id}), {"session_id": order.stripe_session_id})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(CART_SESSION_KEY, self.client.session)

        new_cart = {f"{self.variant.pk}:{self.offer.pk}": 2}
        session = self.client.session
        session[CART_SESSION_KEY] = new_cart
        session.save()
        # Après le premier retour, la clé de session est invalidée : sans
        # session Stripe ni preuve de propriété, l'URL seule ne doit plus suffire.
        response = self.client.get(reverse("checkout:result", kwargs={"public_id": order.public_id}))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.client.session.get(CART_SESSION_KEY), new_cart)

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
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(response["Referrer-Policy"], "no-referrer")
        self.assertContains(response, 'name="robots" content="noindex, nofollow"')
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
        self.assertEqual(order.commercial_status, Order.COMMERCIAL_CONFIRMED)
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


class PromoCodeTests(TestCase):
    def setUp(self):
        self.promo = PromoCode.objects.create(code="TESTPROMO", discount_type=PromoCode.PERCENT, value=Decimal("15.00"), minimum_subtotal=Decimal("20.00"), maximum_discount=Decimal("25.00"), is_active=True)

    def test_code_is_normalized_and_discount_is_server_calculated(self):
        promo, discount = apply_promo_code(" testpromo ", Decimal("100.00"))
        self.assertEqual(promo.code, "TESTPROMO")
        self.assertEqual(discount, Decimal("15.00"))

    def test_discount_cap_and_minimum_are_enforced(self):
        _promo, discount = apply_promo_code("TESTPROMO", Decimal("300.00"))
        self.assertEqual(discount, Decimal("25.00"))
        with self.assertRaises(CheckoutProblem):
            apply_promo_code("TESTPROMO", Decimal("19.99"))

    def test_inactive_and_expired_codes_are_rejected(self):
        from django.utils import timezone
        self.promo.ends_at = timezone.now()
        self.promo.save()
        with self.assertRaises(CheckoutProblem):
            apply_promo_code("TESTPROMO", Decimal("100.00"))
        self.promo.ends_at = None
        self.promo.is_active = False
        self.promo.save()
        with self.assertRaises(CheckoutProblem):
            apply_promo_code("TESTPROMO", Decimal("100.00"))

    def test_welcome_code_cannot_be_reused_after_paid_order_for_same_email(self):
        Order.objects.create(checkout_key=uuid.uuid4(), email="client@example.test", full_name="Client Test", address_line1="1 rue Test", postal_code="75001", city="Paris", country="FR", shipping_method="standard", subtotal=Decimal("100.00"), promo_code_snapshot="TESTPROMO", discount_amount=Decimal("15.00"), shipping_amount=Decimal("4.90"), total=Decimal("89.90"), status=Order.PAID)
        with self.assertRaises(CheckoutProblem):
            apply_promo_code("TESTPROMO", Decimal("100.00"), "CLIENT@example.test")


    def test_code_is_reserved_while_an_order_for_the_same_email_is_pending(self):
        Order.objects.create(checkout_key=uuid.uuid4(), email="client@example.test", full_name="Client Test", address_line1="1 rue Test", postal_code="75001", city="Paris", country="FR", shipping_method="standard", subtotal=Decimal("100.00"), promo_code_snapshot="TESTPROMO", discount_amount=Decimal("15.00"), shipping_amount=Decimal("4.90"), total=Decimal("89.90"), status=Order.PENDING)
        with self.assertRaises(CheckoutProblem):
            apply_promo_code("TESTPROMO", Decimal("100.00"), "client@example.test")

    def test_checkout_apply_stores_only_code_not_a_client_discount(self):
        category = Category.objects.create(name="Promo", slug="promo")
        product = Product.objects.create(category=category, name="Sac promo", slug="sac-promo", is_active=True)
        ProductMedia.objects.create(product=product, media_type=ProductMedia.IMAGE, source_url="https://cdn.example.test/promo.webp", alt_text="Sac promo", is_primary=True)
        variant = ProductVariant.objects.create(product=product, sku="PROMO-TEST", stock_quantity=3)
        offer = ProductOffer.objects.create(product=product, title="Essentiel", price=Decimal("100.00"), is_active=True)
        ProductOfferItem.objects.create(offer=offer, product=product, use_selected_variant=True, quantity=1)
        self.client.post(reverse("shop:cart_mutation"), data=json.dumps({"action":"add","variant_id":variant.pk,"offer_id":offer.pk,"quantity":1}), content_type="application/json")
        response = self.client.post(reverse("checkout:checkout"), {"promo_action":"apply","promo_code":"testpromo"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session.get("checkout_promo_code"), "TESTPROMO")
        self.assertNotIn("checkout_discount_amount", self.client.session)


    def test_refund_webhook_reconciles_early_event_and_never_downgrades_success(self):
        order = Order.objects.create(
            checkout_key=uuid.uuid4(), email="client@example.test", full_name="Client Test",
            address_line1="1 rue Test", postal_code="75001", city="Paris", country="FR",
            shipping_method="standard", subtotal=Decimal("40.00"), shipping_amount=Decimal("4.90"),
            total=Decimal("44.90"), status=Order.PAID, stripe_payment_intent_id="pi_refund_test",
        )
        refund = Refund.objects.create(
            order=order, amount=Decimal("10.00"), currency="eur", reason="Test refund",
            status=Refund.PROCESSING, external_payment_reference="pi_refund_test",
        )
        succeeded = {"id": "evt_refund_succeeded", "type": "refund.updated", "data": {"object": {
            "object": "refund", "id": "re_test_123", "status": "succeeded",
            "amount": 1000, "currency": "eur", "metadata": {"local_refund_id": str(refund.pk)},
        }}}
        self.assertEqual(process_stripe_event(succeeded), "processed")
        refund.refresh_from_db()
        self.assertEqual(refund.status, Refund.SUCCEEDED)
        self.assertEqual(refund.stripe_refund_id, "re_test_123")
        self.assertTrue(OrderEvent.objects.filter(order=order, event_type="refund_confirmed").exists())

        delayed_pending = {"id": "evt_refund_pending_late", "type": "refund.updated", "data": {"object": {
            "object": "refund", "id": "re_test_123", "status": "pending",
            "amount": 1000, "currency": "eur", "metadata": {"local_refund_id": str(refund.pk)},
        }}}
        self.assertEqual(process_stripe_event(delayed_pending), "processed")
        refund.refresh_from_db()
        self.assertEqual(refund.status, Refund.SUCCEEDED)

    def test_distinct_success_events_do_not_turn_an_already_paid_order_into_review(self):
        order = Order.objects.create(
            checkout_key=uuid.uuid4(), email="client@example.test", full_name="Client Test",
            address_line1="1 rue Test", postal_code="75001", city="Paris", country="FR",
            shipping_method="standard", subtotal=Decimal("89.90"), shipping_amount=Decimal("4.90"),
            total=Decimal("94.80"), status=Order.PAID, stock_reserved=False,
            stripe_session_id="cs_paid_already", stripe_payment_intent_id="pi_paid_already",
        )
        event = {"id": "evt_distinct_success", "type": "checkout.session.async_payment_succeeded", "data": {"object": {
            "object": "checkout.session", "id": "cs_paid_already", "currency": "eur",
            "amount_total": 9480, "payment_status": "paid", "payment_intent": "pi_paid_already",
        }}}
        self.assertEqual(process_stripe_event(event), "already_paid")
        order.refresh_from_db()
        self.assertEqual(order.status, Order.PAID)
