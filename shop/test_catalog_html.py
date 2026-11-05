from django.test import TestCase
from django.urls import reverse
from product.models import Product, ProductMedia, ProductVariant, ProductOffer, ProductOfferItem
from . import tests as fixtures


class CatalogHtmlTests(TestCase):
    setUp = fixtures.CartAndSearchTests.setUp

    def test_cards_are_html_links_without_javascript(self):
        response = self.client.get(reverse('shop:catalog'))
        self.assertContains(response, '<article class="pcard"')
        self.assertContains(response, 'href="' + reverse('product:detail', kwargs={'slug': self.product.slug}) + '"')
        self.assertContains(response, '89,90 €')
        self.assertContains(response, 'https://cdn.example.test/cabas.webp')
        self.assertContains(response, 'method="get"')
        self.assertNotContains(response, 'aria-busy="true"')

    def test_filters_use_card_offer_price_and_do_not_leak_reference_price(self):
        url = reverse('shop:catalog')
        self.assertContains(self.client.get(url, {'min': '90'}), 'Aucun produit ne correspond')
        self.assertContains(self.client.get(url, {'max': '90', 'cat': self.category.slug, 'color': 'camel'}), '<article class="pcard"')
        for params in [{'cat': 'unknown'}, {'color': 'unknown'}, {'q': 'inexistant'}]:
            self.assertContains(self.client.get(url, params), 'Aucun produit ne correspond')
        self.assertEqual(self.client.get(url, {'min': 'NaN', 'max': 'not-a-price', 'page': 'bad'}).status_code, 200)

    def test_pagination_is_bounded_and_preserves_query_parameters(self):
        for number in range(10):
            p = Product.objects.create(category=self.category, name=f'Sac {number}', slug=f'sac-{number}', is_active=True)
            ProductMedia.objects.create(product=p, source_url='https://cdn.example.test/test.webp')
            ProductVariant.objects.create(product=p, sku=f'PAGE-{number}', stock_quantity=1)
            offer = ProductOffer.objects.create(product=p, price=10 + number)
            ProductOfferItem.objects.create(offer=offer, product=p, use_selected_variant=True)
        response = self.client.get(reverse('shop:catalog'), {'q': 'Sac', 'sort': 'asc', 'campaign': 'kept'})
        self.assertEqual(len(response.context['cards']), 8)
        self.assertEqual(len(response.context['catalog_data']['products']), 8)
        self.assertContains(response, 'Page suivante')
        self.assertIn('campaign=kept', response.context['next_url'])
        self.assertIn('sort=asc', response.context['next_url'])
        second = self.client.get(reverse('shop:catalog') + response.context['next_url'])
        self.assertEqual(len(second.context['cards']), 3)
        self.assertTrue(set(c['id'] for c in response.context['cards']).isdisjoint(c['id'] for c in second.context['cards']))

    def test_card_text_and_query_are_escaped(self):
        self.product.name = '<script>alert(1)</script>'; self.product.save()
        response = self.client.get(reverse('shop:catalog'))
        self.assertContains(response, '&lt;script&gt;')
        self.assertNotContains(response, '<script>alert(1)</script>')

    def test_featured_offer_cannot_change_essential_price_filter(self):
        offer = ProductOffer.objects.create(product=self.product, badge=ProductOffer.BADGE_MEDIUM, price=5, is_featured=True)
        ProductOfferItem.objects.create(offer=offer, product=self.product, use_selected_variant=True)
        response = self.client.get(reverse('shop:catalog'), {'max': '10'})
        self.assertContains(response, 'Aucun produit ne correspond')
        self.offer.reference_price = 99; self.offer.save()
        response = self.client.get(reverse('shop:catalog'), {'sale': '1'})
        self.assertEqual(response.context['cards'][0]['price'], 89.9)
        self.assertContains(response, '99,00')

    def test_unillustrated_color_is_not_offered_when_an_illustrated_variant_exists(self):
        self.variant.image_url = 'https://cdn.example.test/camel.webp'; self.variant.save()
        ProductVariant.objects.create(product=self.product, sku='NO-PHOTO', color_slug='noir', color_name='Noir', color_code='#000000', stock_quantity=3)
        response = self.client.get(reverse('shop:catalog'), {'color': 'noir'})
        self.assertContains(response, 'Aucun produit ne correspond')
        self.assertNotContains(response, 'value="noir"')
