import re

from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import NewsletterSubscription


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class NewsletterDoubleOptInTests(TestCase):
    def setUp(self):
        cache.clear()

    def subscribe(self, email="client@example.com", consent="yes"):
        return self.client.post(reverse("home:newsletter_subscribe"), {"email": email, "consent": consent})

    def confirmation_token(self):
        match = re.search(r"/newsletter/confirmer/([^/\s]+)/", mail.outbox[-1].body)
        self.assertIsNotNone(match)
        return match.group(1)

    def test_consent_is_required(self):
        response = self.subscribe(consent="")
        self.assertEqual(response.status_code, 302)
        self.assertFalse(NewsletterSubscription.objects.exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_double_opt_in_activates_only_after_confirmation(self):
        self.subscribe()
        sub = NewsletterSubscription.objects.get(email="client@example.com")
        self.assertFalse(sub.is_confirmed)
        self.assertFalse(sub.is_active)
        token = self.confirmation_token()
        response = self.client.get(reverse("home:newsletter_confirm", kwargs={"token": token}))
        self.assertEqual(response.status_code, 200)
        sub.refresh_from_db()
        self.assertTrue(sub.is_confirmed)
        self.assertTrue(sub.is_active)
        self.assertEqual(sub.confirmation_token_hash, "")

    def test_confirmation_token_is_single_use_and_hashed_in_database(self):
        self.subscribe()
        token = self.confirmation_token()
        sub = NewsletterSubscription.objects.get(email="client@example.com")
        self.assertNotEqual(sub.confirmation_token_hash, token)
        self.assertEqual(len(sub.confirmation_token_hash), 64)
        url = reverse("home:newsletter_confirm", kwargs={"token": token})
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.get(url).status_code, 400)

    def test_unsubscribe_requires_post(self):
        self.subscribe()
        sub = NewsletterSubscription.objects.get(email="client@example.com")
        self.client.get(reverse("home:newsletter_confirm", kwargs={"token": self.confirmation_token()}))
        url = reverse("home:newsletter_unsubscribe", kwargs={"token": sub.unsubscribe_token})
        self.assertEqual(self.client.get(url).status_code, 200)
        sub.refresh_from_db()
        self.assertTrue(sub.is_active)
        self.assertEqual(self.client.post(url).status_code, 200)
        sub.refresh_from_db()
        self.assertFalse(sub.is_active)
        self.assertIsNotNone(sub.unsubscribed_at)

    def test_resubscription_after_unsubscribe_requires_new_confirmation(self):
        self.subscribe()
        sub = NewsletterSubscription.objects.get(email="client@example.com")
        self.client.get(reverse("home:newsletter_confirm", kwargs={"token": self.confirmation_token()}))
        self.client.post(reverse("home:newsletter_unsubscribe", kwargs={"token": sub.unsubscribe_token}))
        mail.outbox.clear()
        self.subscribe()
        sub.refresh_from_db()
        self.assertFalse(sub.is_confirmed)
        self.assertFalse(sub.is_active)
        self.assertEqual(len(mail.outbox), 1)
        token = self.confirmation_token()
        self.assertEqual(self.client.get(reverse("home:newsletter_confirm", kwargs={"token": token})).status_code, 200)
        sub.refresh_from_db()
        self.assertTrue(sub.is_confirmed)
        self.assertTrue(sub.is_active)
