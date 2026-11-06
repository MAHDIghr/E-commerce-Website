from types import SimpleNamespace
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.urls import reverse
from config.commercial import public_information, local_test_checkout
from . import tests as fixtures
from .models import Order

@override_settings(DEBUG=True, LOCAL_TEST_CHECKOUT=True, COMMERCIAL_INFORMATION={})
@patch.dict('os.environ', {'STRIPE_SECRET_KEY':'sk_test_fixture', 'STRIPE_WEBHOOK_SECRET':'whsec_fixture', 'STRIPE_LIVE_MODE':'False', 'SITE_BASE_URL':'http://127.0.0.1:8000'})
class LocalCheckoutTests(TestCase):
    setUp = fixtures.CheckoutIntegrationTests.setUp
    add_to_cart = fixtures.CheckoutIntegrationTests.add_to_cart

    def test_local_checkout_can_reach_hosted_test_session_without_publishing_legal_text(self):
        self.add_to_cart()
        self.assertTrue(local_test_checkout())
        self.assertFalse(public_information()['sales_ready'])
        self.assertEqual(public_information()['pages'],{})
        response=self.client.get(reverse('checkout:checkout'))
        self.assertContains(response, 'Mode test Stripe local')
        with patch('checkout.services.stripe.checkout.Session.create', return_value=SimpleNamespace(id='cs_test_fixture',url='https://checkout.stripe.test/session')) as stripe:
            response=self.client.post(reverse('checkout:checkout'), {'first_name':'Test','last_name':'Local','email':'test@example.test','address_line1':'Adresse fictive','postal_code':'75001','city':'Paris','country':'FR','shipping_method':'free','billing_same_as_shipping':'on','accept_terms':'on'})
        self.assertEqual(response.status_code,302)
        self.assertEqual(response.url,'https://checkout.stripe.test/session')
        self.assertEqual(Order.objects.count(),1)
        self.assertEqual(stripe.call_count,1)

    def test_live_key_live_mode_and_public_url_do_not_enable_bypass(self):
        for values in [{'STRIPE_SECRET_KEY':'sk_live_fixture'}, {'STRIPE_LIVE_MODE':'True'}, {'SITE_BASE_URL':'https://example.test'}]:
            with patch.dict('os.environ',values):
                self.assertFalse(local_test_checkout())

    @override_settings(DEBUG=False)
    def test_production_never_enables_bypass(self):
        self.assertFalse(local_test_checkout())
