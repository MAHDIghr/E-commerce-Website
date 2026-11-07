from types import SimpleNamespace
from django.test import TestCase, RequestFactory, override_settings
from django.core.cache import cache
from django.http import HttpResponse
from config.security import EntryProtectionMiddleware

class EntryTests(TestCase):
    @override_settings(ENTRY_LIMITS_ENABLED=True)
    def test_limit_and_retry_without_storing_credentials(self):
        cache.clear()
        request=RequestFactory().post('/checkout/', {'promo_action':'apply','promo_code':'TEST'})
        request.resolver_match=SimpleNamespace(view_name='checkout:checkout')
        middleware=EntryProtectionMiddleware(lambda r:HttpResponse())
        for _ in range(30): self.assertIsNone(middleware.process_view(request,None,(),{}))
        response=middleware.process_view(request,None,(),{})
        self.assertEqual(response.status_code,429)
        self.assertEqual(response['Retry-After'],'300')
        cache.clear()
        self.assertIsNone(middleware.process_view(request,None,(),{}))

    def test_private_headers_and_report_only(self):
        request=RequestFactory().get('/checkout/')
        request.resolver_match=SimpleNamespace(view_name='checkout:checkout')
        response=EntryProtectionMiddleware(lambda r:HttpResponse()).process_response(request,HttpResponse())
        self.assertIn('no-store',response['Cache-Control'])
        self.assertIn('Content-Security-Policy-Report-Only',response)
        self.assertNotIn('Content-Security-Policy',response)
