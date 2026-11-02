from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse
from product.models import Category, Product, ProductVariant, ProductMedia, ProductOffer, ProductOfferItem
from shop.views import CART_SESSION_KEY


class FrontendAssetTests(TestCase):
    def test_checkout_assets_have_one_source(self):
        for name in ('checkout/checkout.css', 'checkout/checkout-summary.js'):
            self.assertEqual(len(finders.find(name, find_all=True)), 1, name)
        category = Category.objects.create(name="Sacs", slug="sacs")
        product = Product.objects.create(category=category, name="Sac test", slug="sac-test")
        variant = ProductVariant.objects.create(product=product, sku="SAC-TEST", stock_quantity=2)
        ProductMedia.objects.create(product=product, source_url="https://cdn.example.test/sac.webp", alt_text="Sac test")
        offer = ProductOffer.objects.create(product=product, title="Essentiel", price="49.90")
        ProductOfferItem.objects.create(offer=offer, product=product, use_selected_variant=True)
        session = self.client.session
        session[CART_SESSION_KEY] = {f"{variant.pk}:{offer.pk}": 1}
        session.save()
        response = self.client.get(reverse('checkout:checkout'))
        self.assertContains(response, '/static/checkout/checkout.css')
        self.assertContains(response, '/static/checkout/checkout-summary.js')
        self.assertNotContains(response, '/static/js/checkout.js')

    def test_newsletter_keeps_email_and_explicit_consent_without_footer_coupon(self):
        response = self.client.get(reverse('home:home'))
        self.assertContains(response, 'id="newsletter-email"')
        self.assertContains(response, 'id="newsletter-consent"')
        self.assertContains(response, 'name="consent" value="yes" required')
        footer = response.content.decode().split('<footer class="site-footer">', 1)[1].split('</footer>', 1)[0]
        self.assertNotIn('data-copy-promo', footer)
        self.assertNotIn('Copier le code', footer)
