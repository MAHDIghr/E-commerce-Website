import json
import os
from pathlib import Path
from django.test import TestCase
from django.urls import reverse
from product.models import Category, Product, ProductVariant, ProductMedia, ProductOffer, ProductOfferItem, Review


class CatalogRenderingTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Sacs à main', slug='handbags')
        for index in range(11):
            product = Product.objects.create(category=self.category, is_active=True, name=f'Sac {index:02} <long>', slug=f'sac-{index}', is_new=index == 0)
            ProductVariant.objects.create(product=product, sku=f'SKU-{index}', stock_quantity=index,
                                          color_slug='camel', color_code='#B07A4A', color_name='Camel')
            ProductMedia.objects.create(product=product, source_url='https://example.test/image.webp')
            offer = ProductOffer.objects.create(product=product, title='Essentiel', badge='essential', price=10 + index,
                                                reference_price=30 if index == 1 else None)
            ProductOfferItem.objects.create(offer=offer, product=product, use_selected_variant=True)
            if index == 1:
                Review.objects.create(product=product, author_name='Test', rating=4, is_approved=True)
        self.url = reverse('shop:catalog')

    def test_initial_html_contains_eight_cards_and_bounded_json(self):
        response = self.client.get(self.url)
        self.assertContains(response, '<article class="pcard"', count=8)
        self.assertEqual(len(response.context['catalog_data']['products']), 8)
        for card in response.context['cards']:
            self.assertContains(response, reverse('product:detail', args=[card['id']]))
            self.assertContains(response, card['price_text'])
        self.assertContains(response, '&lt;long&gt;')
        self.assertContains(response, 'form="catalog-form" name="page" value="2"')

    def test_get_filters_and_order_use_same_card_contract(self):
        response = self.client.get(self.url, {'min': '12', 'max': '15', 'color': 'camel', 'sort': 'desc'})
        self.assertEqual([p['price'] for p in response.context['cards']], [15, 14, 13, 12])
        self.assertContains(response, '<article class="pcard"', count=4)
        self.assertEqual(self.client.get(self.url, {'sale': '1'}).context['total'], 1)
        self.assertEqual(self.client.get(self.url, {'low': '1'}).context['total'], 5)
        self.assertEqual(self.client.get(self.url, {'q': 'Sac 01'}).context['total'], 1)

    def test_fragment_matches_initial_cards_and_varies_cache(self):
        response = self.client.get(self.url, {'sort': 'asc', 'page': 2})
        fragment = self.client.get(self.url, {'sort': 'asc', 'page': 2}, HTTP_X_CATALOG_UPDATE='1')
        payload = fragment.json()
        self.assertEqual(payload['visible'], 11)
        self.assertFalse(payload['has_more'])
        self.assertIn(payload['html'], response.content.decode())
        self.assertIn('X-Catalog-Update', response.headers['Vary'])
        self.assertIn('X-Catalog-Update', fragment.headers['Vary'])

    def test_invalid_parameters_and_repeated_categories(self):
        response = self.client.get(self.url, {'page': '-4', 'min': 'NaN', 'max': 'Infinity', 'sort': 'unknown', 'cat': ['unknown', 'handbags']})
        self.assertEqual(response.context['total'], 11)
        self.assertEqual(response.context['page'], 1)
        self.assertEqual(response.context['sort'], 'pop')
        self.assertContains(self.client.get(self.url, {'page': 'bad'}), '<article class="pcard"', count=8)
        self.assertEqual(self.client.get(self.url, {'page': 9999}).context['page'], 2)

    def test_hidden_and_non_public_products_are_excluded(self):
        Product.objects.filter(slug='sac-0').update(is_active=False)
        response = self.client.get(self.url, {'sort': 'asc'})
        self.assertNotContains(response, 'data-product-slug="sac-0"')
        self.assertEqual(response.context['total'], 10)

    def test_get_forms_preserve_unknown_parameters(self):
        response = self.client.get(self.url, {'q': 'Sac', 'campaign': 'test', 'sort': 'asc'})
        self.assertContains(response, 'name="campaign" value="test"')
        self.assertContains(response, 'name="q" value="Sac"')
        # Optional local fixture export for DOM simulations, never production data.
        if os.environ.get('CATALOG_DOM_FIXTURE'):
            Path(os.environ['CATALOG_DOM_FIXTURE']).write_text(json.dumps({
                'html': response.content.decode(),
                'second': self.client.get(self.url, {'sort': 'asc', 'page': 2}, HTTP_X_CATALOG_UPDATE='1').json(),
            }))

    def test_decimal_values_and_existing_nojs_buttons(self):
        response = self.client.get(self.url, {'min': '12.5', 'campaign': 'test'})
        self.assertContains(response, 'value="12.5"')
        self.assertContains(response, 'form="catalog-price-1" data-price="0-50"')
        self.assertContains(response, 'form="catalog-reset-form"')

    def test_custom_category_text_is_not_renamed(self):
        self.category.slug = 'custom-category'
        self.category.save()
        response = self.client.get(self.url)
        self.assertContains(response, '<p class="pcard__cat"></p>', count=8)
