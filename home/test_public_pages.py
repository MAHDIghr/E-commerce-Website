from django.test import TestCase
from django.urls import reverse


class PublicInformationPagesTests(TestCase):
    def test_homepage_renders_newsletter_signup(self):
        response = self.client.get(reverse("home:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "newsletter_subscribe")
        self.assertContains(response, "footer-news-email")
        self.assertContains(response, 'name="consent"')

    def test_help_pages_are_available(self):
        for name in ("delivery", "returns", "faq", "contact"):
            with self.subTest(page=name):
                response = self.client.get(reverse(f"home:{name}"))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "My Line Collection")

    def test_legal_pages_are_marked_as_drafts_and_not_indexable(self):
        for name in ("legal", "privacy", "terms"):
            with self.subTest(page=name):
                response = self.client.get(reverse(f"home:{name}"))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'name="robots" content="noindex, nofollow"')
                self.assertContains(response, "Page à finaliser")

    def test_sitemap_is_xml_and_contains_catalog(self):
        response = self.client.get(reverse("sitemap"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/xml; charset=utf-8")
        self.assertContains(response, "/boutique/")

    def test_robots_txt_is_plain_text_and_declares_sitemap(self):
        response = self.client.get(reverse("robots"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/plain; charset=utf-8")
        self.assertContains(response, "Sitemap: ")
