import json
from django.test import TestCase, override_settings, RequestFactory
from django.urls import reverse
from config.seo import server_error
from shop import tests as fixtures

class SeoTests(TestCase):
    setUp = fixtures.CartAndSearchTests.setUp

    def test_french_default_ignores_browser_language(self):
        response = self.client.get('/', HTTP_ACCEPT_LANGUAGE='en-US')
        self.assertContains(response, '<html lang="fr"')
        self.assertNotContains(response, 'hreflang="en"')
        response = self.client.get('/en/')
        self.assertEqual(response.status_code, 503)
        self.assertIn('noindex', response['X-Robots-Tag'])
        self.assertContains(response, 'lang="en"', status_code=503)

    def test_product_sharing_matches_real_image_price_and_no_fake_rating(self):
        response = self.client.get(reverse('product:detail', kwargs={'slug':self.product.slug}))
        self.assertContains(response, 'property="og:image" content="https://cdn.example.test/cabas.webp"')
        self.assertContains(response, 'property="product:price:amount" content="89.90"')
        self.assertContains(response, 'property="og:url" content="http://testserver/produit/sac-cabas-camel/"')
        data = json.loads(response.context['product']['structured_data_json'])
        self.assertNotIn('aggregateRating', data)
        self.assertEqual(data['offers']['lowPrice'],89.9)

    @override_settings(DEBUG=False, ALLOWED_HOSTS=['testserver'])
    def test_error_pages_have_real_exits_and_no_diagnostics(self):
        response = self.client.get('/missing-page/')
        self.assertEqual(response.status_code,404)
        self.assertContains(response, reverse('shop:catalog'),status_code=404)
        self.assertNotContains(response,'Traceback',status_code=404)
        response = server_error(RequestFactory().get('/'))
        self.assertEqual(response.status_code,500)
        self.assertIn(reverse('pages:contact').encode(),response.content)
        self.assertIn('noindex',response['X-Robots-Tag'])

    def test_private_pages_noindex_are_not_blocked_before_crawl(self):
        response=self.client.get(reverse('shop:cart_page'))
        self.assertIn('noindex',response['X-Robots-Tag'])
        robots=self.client.get('/robots.txt').content.decode()
        self.assertNotIn('Disallow: /boutique/',robots)
        sitemap=self.client.get('/sitemap.xml').content.decode()
        self.assertNotIn('/favoris/',sitemap)
        self.assertNotIn('/checkout/',sitemap)
        self.assertNotIn('/en/',sitemap)

    def test_catalog_page_canonical_and_title_preserve_navigation(self):
        response=self.client.get(reverse('shop:catalog'),{'q':'Sac','page':'2'})
        self.assertIn('page=2',response.context['seo']['url'])
        self.assertIn('Recherche : Sac',response.context['seo']['title'])
