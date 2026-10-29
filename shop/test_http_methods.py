from django.test import TestCase
from django.urls import reverse


class ReadOnlyShopEndpointTests(TestCase):
    def test_catalog_rejects_mutating_http_methods(self):
        response = self.client.post(reverse("shop:catalog"), data={})
        self.assertEqual(response.status_code, 405)

    def test_search_suggestions_rejects_post(self):
        response = self.client.post(reverse("shop:search_suggestions"), data={"q": "sac"})
        self.assertEqual(response.status_code, 405)

    def test_cart_page_is_read_only(self):
        response = self.client.post(reverse("shop:cart_page"), data={})
        self.assertEqual(response.status_code, 405)
