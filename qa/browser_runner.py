"""Recette locale isolée : jamais de connexion à Stripe, données fictives uniquement."""
import os
import subprocess
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from pages.test_commercial_information import approved_information
from checkout import tests as fixtures
from checkout.models import PromoCode

@override_settings(COMMERCIAL_INFORMATION=approved_information())
class CheckoutBrowserTests(StaticLiveServerTestCase):
    def setUp(self):
        fixtures.CheckoutIntegrationTests.setUp(self)
        self.product.name = 'Produit de recette au nom volontairement très long pour contrôler le retour à la ligne sur petit écran'
        self.product.is_new = True
        self.product.save()
        self.product.media_items.update(source_url=self.live_server_url + '/static/images/mainLogo.svg')
        PromoCode.objects.create(code='QA20', discount_type=PromoCode.PERCENT, value=20, once_per_email=False)

    def test_browser_journeys(self):
        result = subprocess.run(['node', 'qa/journeys.cjs', self.live_server_url, self.product.slug], env=os.environ.copy(), timeout=180, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
