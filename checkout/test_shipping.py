"""Contrat de livraison : données fictives, aucune requête réseau Stripe."""
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch
import json
import uuid

from django.test import TestCase, override_settings
from django.urls import reverse

from config.commercial import FREE_SHIPPING_THRESHOLD, SHIPPING_PRICES, public_information
from pages.test_commercial_information import approved_information
from product.models import ProductOffer, ProductOfferItem
from . import tests as fixtures
from .forms import CheckoutForm, ShippingQuoteForm
from .models import Order, PromoCode
from .services import (CheckoutProblem, create_order_and_reserve, create_stripe_session,
                       shipping_price, stripe_configured)


@override_settings(COMMERCIAL_INFORMATION=approved_information())
class ShippingContractTests(TestCase):
    setUp = fixtures.CheckoutIntegrationTests.setUp
    add_to_cart = fixtures.CheckoutIntegrationTests.add_to_cart

    def address(self, method, **changes):
        return dict({"first_name": "Test", "last_name": "Livraison", "email": "shipping@example.test",
                     "address_line1": "Adresse de test", "postal_code": "75001", "city": "Paris",
                     "country": "FR", "shipping_method": method, "billing_same_as_shipping": "on",
                     "accept_terms": "on"}, **changes)

    def quote(self, **changes):
        return self.client.post(reverse("checkout:checkout"),
                                dict({"country": "FR", "postal_code": "75001"}, **changes),
                                HTTP_X_CHECKOUT_UPDATE="1")

    def order(self, method, subtotal, offer_free=False):
        form = CheckoutForm(self.address(method), subtotal=subtotal, offer_free=offer_free)
        self.assertTrue(form.is_valid(), form.errors)
        request = SimpleNamespace(session=self.client.session, user=SimpleNamespace(is_authenticated=False))
        return create_order_and_reserve(request, form, uuid.uuid4())[0]

    def test_boundaries_quote_order_before_and_after_discount(self):
        promo = PromoCode.objects.create(code="SHIPTEST", discount_type=PromoCode.FIXED,
                                         value=Decimal("10.00"), is_active=True, once_per_email=False)
        values = {Decimal("79.99"), Decimal("80.00"), Decimal("80.01"),
                  FREE_SHIPPING_THRESHOLD - Decimal("0.01"), FREE_SHIPPING_THRESHOLD,
                  FREE_SHIPPING_THRESHOLD + Decimal("0.01")}
        for discounted in (False, True):
            for net in sorted(values):
                for mode in ("standard", "express"):
                    with self.subTest(net=net, discounted=discounted, mode=mode):
                        self.offer.price = net + (promo.value if discounted else Decimal("0.00"))
                        self.offer.save(update_fields=["price"])
                        self.variant.stock_quantity = 100; self.variant.save(update_fields=["stock_quantity"])
                        # Exactement une unité, sans accumulation entre sous-cas.
                        from shop.views import CART_SESSION_KEY
                        session = self.client.session
                        session[CART_SESSION_KEY] = {f"{self.variant.pk}:{self.offer.pk}": 1}
                        if discounted:
                            session["checkout_promo_code"] = promo.code
                        else:
                            session.pop("checkout_promo_code", None)
                        session.save()
                        method = "free" if mode == "standard" and net >= FREE_SHIPPING_THRESHOLD else mode
                        options = self.quote().json()["options"]
                        option = next(o for o in options if o["method"] == method)
                        expected = Decimal("0.00") if method == "free" else SHIPPING_PRICES[method]
                        self.assertEqual(Decimal(option["amount"]), expected)
                        order = self.order(method, net)
                        self.assertEqual(order.shipping_amount, expected)
                        self.assertEqual(order.total, Decimal(option["total"]))
                        self.assertEqual(order.total, net + expected)

    def test_offer_free_applies_below_threshold_after_promo_and_express_stays_paid(self):
        self.offer.price = Decimal("49.90")
        self.offer.display_delivery_label = ProductOffer.DELIVERY_FREE
        self.offer.save(); self.add_to_cart()
        PromoCode.objects.create(code="SHIP20", discount_type=PromoCode.PERCENT, value=20, is_active=True, once_per_email=False)
        data = self.quote(promo_action="apply", promo_code="SHIP20").json()
        self.assertEqual([o["total"] for o in data["options"]], ["39.92", "49.82"])
        order = self.order("free", Decimal("39.92"), offer_free=True)
        self.assertEqual(order.shipping_amount, Decimal("0.00"))
        self.assertEqual(order.total, Decimal("39.92"))
        express = self.order("express", Decimal("39.92"), offer_free=True)
        self.assertEqual(express.total, Decimal("49.82"))
        cart = self.client.get(reverse("shop:cart_api")).json()
        self.assertTrue(cart["free_shipping_reached"])
        self.assertEqual(cart["amount_to_free_shipping"], "0.00")
        offers = self.client.get(reverse("shop:offer_options", kwargs={"slug": self.product.slug}), {"variant_id": self.variant.pk}).json()
        self.assertIn("standard gratuite pour tout le panier", offers["offers"][0]["delivery_label"])

    def test_mixed_cart_free_offer_and_removal_recompute_fees(self):
        self.offer.price = Decimal("20.00"); self.offer.save(); self.add_to_cart()
        free = ProductOffer.objects.create(product=self.product, badge=ProductOffer.BADGE_MEDIUM,
                                          price=Decimal("10.00"), display_delivery_label=ProductOffer.DELIVERY_FREE)
        ProductOfferItem.objects.create(offer=free, product=self.product, use_selected_variant=True)
        self.client.post(reverse("shop:cart_mutation"), json.dumps({"action": "add", "variant_id": self.variant.pk,
                         "offer_id": free.pk, "quantity": 1}), content_type="application/json")
        self.assertEqual(self.quote().json()["options"][0]["amount"], "0.00")
        self.assertEqual(self.order("free", Decimal("30.00"), offer_free=True).total, Decimal("30.00"))
        self.client.post(reverse("shop:cart_mutation"), json.dumps({"action": "remove", "variant_id": self.variant.pk,
                         "offer_id": free.pk}), content_type="application/json")
        self.assertEqual(self.quote().json()["options"][0]["amount"], "4.90")

    def test_browser_cannot_grant_free_shipping_or_reuse_changed_offer(self):
        self.offer.price = Decimal("20.00"); self.offer.save(); self.add_to_cart()
        self.assertEqual(self.quote(offer_free_shipping="true", shipping_amount="0", shipping_method="free").json()["options"][0]["amount"], "4.90")
        with self.assertRaises(CheckoutProblem):
            self.order("free", Decimal("20.00"), offer_free=True)
        self.offer.display_delivery_label = ProductOffer.DELIVERY_FREE; self.offer.save()
        self.assertEqual(self.quote().json()["options"][0]["amount"], "0.00")
        self.offer.is_active = False; self.offer.save()
        self.assertFalse(self.quote().json()["quote_valid"])
        self.assertFalse(Order.objects.exists())

    def test_excluded_countries_refused_in_both_endpoints_and_order(self):
        self.add_to_cart()
        for country in ("CH", "GB", "ZZ"):
            with self.subTest(country=country):
                data = self.quote(country=country).json()
                self.assertFalse(data["quote_valid"]); self.assertFalse(data["can_pay"])
                self.assertIn("pas prise en charge", data["errors"]["country"][0]["message"])
                self.assertEqual(self.client.get(reverse("checkout:shipping_quote"), {"country": country, "postal_code": "12345"}).status_code, 400)
                form = CheckoutForm(self.address("free", country=country), subtotal=Decimal("89.90"))
                self.assertFalse(form.is_valid())
        self.assertFalse(Order.objects.exists())

    @override_settings(CHECKOUT_EXCLUDED_POSTAL_PREFIXES={"FR": ["97", "98"]})
    def test_configured_postal_exclusions_and_policy_changes_fail_closed(self):
        self.assertFalse(public_information()["sales_ready"])
        with override_settings(COMMERCIAL_INFORMATION=approved_information()):
            self.add_to_cart()
            self.assertFalse(self.quote(postal_code="97100").json()["quote_valid"])
            self.assertTrue(self.quote(postal_code="75001").json()["quote_valid"])
            form = CheckoutForm(self.address("free", postal_code="97100"), subtotal=Decimal("89.90"))
            self.assertFalse(form.is_valid()); self.assertIn("postal_code", form.errors)
            # Défense du service même si un appelant lui remet un formulaire prévalidé altéré.
            form = CheckoutForm(self.address("free"), subtotal=Decimal("89.90"))
            self.assertTrue(form.is_valid()); form.cleaned_data["postal_code"] = "97100"
            request = SimpleNamespace(session=self.client.session, user=SimpleNamespace(is_authenticated=False))
            with self.assertRaises(CheckoutProblem):
                create_order_and_reserve(request, form, uuid.uuid4())
            self.assertFalse(Order.objects.exists())

    @override_settings(COMMERCIAL_INFORMATION={})
    def test_unapproved_matrix_offers_no_shipping_country(self):
        self.assertEqual(list(ShippingQuoteForm().fields["country"].choices), [])
        self.assertEqual(list(CheckoutForm().fields["country"].choices), [])
        self.assertFalse(ShippingQuoteForm({"country": "FR", "postal_code": "75001"}).is_valid())

    def test_only_approved_delivery_days_with_conditions_are_rendered(self):
        with patch.dict("config.commercial.DELIVERY_DAYS", {"standard": "Délai fictif test", "express": ""}):
            with override_settings(COMMERCIAL_INFORMATION=approved_information()):
                self.assertNotContains(self.client.get(reverse("home:home")), "Délai fictif test")
            with override_settings(CHECKOUT_DELIVERY_CONDITIONS={"standard": "Condition fictive test"},
                                   COMMERCIAL_INFORMATION=approved_information()):
                # L'empreinte doit être prise après la configuration des conditions.
                self.assertFalse(public_information()["sales_ready"])
                with override_settings(COMMERCIAL_INFORMATION=approved_information()):
                    self.add_to_cart()
                    label = self.quote().json()["options"][0]["label"]
                    self.assertIn("Délai fictif test (Condition fictive test)", label)
                    self.assertNotIn("Traitement prioritaire", label)
                    self.assertContains(self.client.get(reverse("home:home")),
                                        "Délai fictif test (Condition fictive test)")

    @patch.dict("os.environ", {"STRIPE_SECRET_KEY": "", "STRIPE_WEBHOOK_SECRET": "", "SITE_BASE_URL": ""})
    def test_unavailable_payment_announced_before_fields_no_order_or_stock_change(self):
        self.add_to_cart()
        response = self.client.get(reverse("checkout:checkout"))
        html = response.content.decode()
        self.assertLess(html.index('id="payment-unavailable"'), html.index('id="checkout-form"'))
        self.assertContains(response, 'id="checkout-submit" disabled')
        self.assertNotContains(response, "variables Stripe")
        with patch("checkout.views.create_order_and_reserve") as create:
            response = self.client.post(reverse("checkout:checkout"), self.address("free"))
            self.assertContains(response, "Paiement temporairement indisponible")
            create.assert_not_called()
        self.assertFalse(self.quote().json()["can_pay"])
        self.assertFalse(Order.objects.exists())
        self.variant.refresh_from_db(); self.assertEqual(self.variant.stock_quantity, 4)

    def test_misconfigured_provider_is_unavailable_without_technical_client_message(self):
        for key, base in [("sk_live_fake", "https://example.test"), ("sk_test_fake", "invalid"), ("sk_test_fake", "http://[invalid")]:
            with patch.dict("os.environ", {"STRIPE_SECRET_KEY": key, "STRIPE_WEBHOOK_SECRET": "whsec_fake",
                                           "STRIPE_LIVE_MODE": "False", "SITE_BASE_URL": base}):
                self.assertFalse(stripe_configured())
                with self.assertRaisesMessage(CheckoutProblem, "Paiement temporairement indisponible"):
                    create_stripe_session(SimpleNamespace())

    def test_mocked_stripe_receives_server_amount_with_free_offer_and_discount(self):
        self.offer.price = Decimal("49.90"); self.offer.display_delivery_label = ProductOffer.DELIVERY_FREE
        self.offer.save(); self.add_to_cart()
        PromoCode.objects.create(code="SHIP20", discount_type=PromoCode.PERCENT, value=20, is_active=True, once_per_email=False)
        self.quote(promo_action="apply", promo_code="SHIP20")
        order = self.order("express", Decimal("39.92"), offer_free=True)
        with patch.dict("os.environ", {"STRIPE_SECRET_KEY": "sk_test_fake", "STRIPE_WEBHOOK_SECRET": "whsec_fake",
                                       "STRIPE_LIVE_MODE": "False", "SITE_BASE_URL": "https://example.test"}), \
             patch("checkout.services.stripe.Coupon.create", return_value=SimpleNamespace(id="coupon_test")) as coupon, \
             patch("checkout.services.stripe.checkout.Session.create", return_value=SimpleNamespace(id="cs_test", url="https://checkout.stripe.test")) as create:
            create_stripe_session(order)
        payload = create.call_args.kwargs
        total = sum(item["price_data"]["unit_amount"] * item["quantity"] for item in payload["line_items"])
        self.assertEqual(total - coupon.call_args.kwargs["amount_off"], int(order.total * 100))
        self.assertEqual(order.total, Decimal("49.82"))
        self.assertEqual(payload["idempotency_key"], f"mlc-checkout-{order.checkout_key}")
        self.assertEqual(payload["mode"], "payment")
        self.assertNotIn("payment_method_types", payload)  # Moyens réels à vérifier dans Stripe test.
