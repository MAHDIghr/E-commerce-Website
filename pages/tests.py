from django.test import TestCase
from django.urls import reverse


class InformationPagesTests(TestCase):
    NAMES = ("legal", "terms", "privacy", "returns", "delivery", "contact", "faq", "about")

    def test_all_pages_render_without_working_text_and_with_named_links(self):
        for name in self.NAMES:
            with self.subTest(page=name):
                response = self.client.get(reverse(f"pages:{name}"))
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, "[À COMPLÉTER")
                self.assertContains(response, "La prise de commande est momentanément indisponible.")
                self.assertContains(response, 'name="robots" content="noindex, nofollow"')
                self.assertContains(response, reverse("pages:legal"))
                self.assertContains(response, reverse("pages:terms"))
                self.assertContains(response, reverse("pages:privacy"))

    def test_old_home_paths_redirect_to_new_named_pages(self):
        for name in self.NAMES[:-1]:
            with self.subTest(page=name):
                response = self.client.get(reverse(f"home:{name}"))
                self.assertRedirects(response, reverse(f"pages:{name}"), status_code=301)

    def test_navigation_links_to_about(self):
        response = self.client.get(reverse("pages:about"))
        self.assertContains(response, reverse("pages:about"))
        self.assertNotContains(response, 'href="#"')
