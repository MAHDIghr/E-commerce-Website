from django.test import TestCase
from django.urls import reverse
from product.models import Product, ProductOffer, ProductOfferItem, ProductMedia, ProductVariant
from . import tests as fixtures


class MerchandisingTests(TestCase):
    setUp = fixtures.CartAndSearchTests.setUp

    def test_favorites_page_is_linked_and_does_not_store_customer_data(self):
        response = self.client.get(reverse('shop:favorites'))
        self.assertContains(response, 'favorites-grid')
        self.assertContains(response, 'Activez JavaScript')
        self.assertContains(self.client.get(reverse('home:home')), reverse('shop:favorites'))
        self.assertNotIn('wishlist_v1', self.client.session)

    def test_favorites_resolve_only_published_cards_and_are_bounded(self):
        for n in range(9):
            p = Product.objects.create(category=self.category, name=f'Favori {n}', slug=f'favori-{n}', is_active=True)
            ProductMedia.objects.create(product=p, source_url='https://cdn.example.test/image.webp')
            ProductVariant.objects.create(product=p, sku=f'FAV-{n}', stock_quantity=2)
            o = ProductOffer.objects.create(product=p, price=10)
            ProductOfferItem.objects.create(offer=o, product=p, use_selected_variant=True)
        response = self.client.get(reverse('shop:favorites'), {'format':'cards', 'slug':[f'favori-{n}' for n in range(9)]})
        self.assertEqual(len(response.json()['found']), 8)
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.product.is_active = False; self.product.save()
        response = self.client.get(reverse('shop:favorites'), {'format':'cards', 'slug':[self.product.slug, '<script>']})
        self.assertEqual(response.json(), {'html':'','found':[]})

    def test_admin_category_and_empty_product_sections(self):
        self.category.name = 'Pièces personnalisées'; self.category.save()
        self.assertContains(self.client.get(reverse('shop:catalog')), 'Pièces personnalisées')
        response = self.client.get(reverse('product:detail', kwargs={'slug':self.product.slug}))
        for heading in ('Pourquoi choisir ce produit', 'Contenu et dimensions', 'Les détails de fabrication', 'Usages du produit', 'Questions fréquentes'):
            self.assertNotContains(response, heading + '</h2>')
        self.assertContains(response, '>Acheter maintenant</button>')
        self.assertContains(response, '<span>Ajouter au panier</span>', html=True)

    def test_only_supplied_product_facts_are_shown_and_escaped(self):
        self.product.material = '<script>test</script>'; self.product.width_cm = 12; self.product.description = 'Description factuelle de test'
        self.product.save()
        response = self.client.get(reverse('product:detail', kwargs={'slug':self.product.slug}))
        self.assertContains(response, 'Contenu et dimensions')
        self.assertContains(response, 'Matière : &lt;script&gt;test&lt;/script&gt;')
        self.assertContains(response, 'Description factuelle de test')
        self.assertNotContains(response, '<dt>Poids</dt>')
