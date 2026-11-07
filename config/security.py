"""Limites par fenêtre : le backend production doit garantir add/incr atomiques."""
from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from django.utils.crypto import salted_hmac
from django.utils.deprecation import MiddlewareMixin

class EntryProtectionMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.method != 'POST' or not getattr(settings, 'ENTRY_LIMITS_ENABLED', False):
            return None
        name = request.resolver_match.view_name
        scope, limit = '', 0
        if name in ('dashboard:login','admin:login'):
            scope, limit = 'login', 20
        elif name == 'checkout:checkout':
            if request.POST.get('promo_action') == 'apply': scope, limit = 'promo', 30
            elif not request.headers.get('X-Checkout-Update') and not request.POST.get('promo_action'): scope, limit = 'payment', 10
        if not scope: return None
        key = 'entry:' + salted_hmac(scope, request.META.get('REMOTE_ADDR','unknown')).hexdigest()
        try:
            if cache.add(key, 1, timeout=300): count = 1
            else: count = cache.incr(key)
        except Exception:
            return HttpResponse('Service temporairement indisponible. Réessayez plus tard.', status=503)
        if count > limit:
            response = HttpResponse('Trop de tentatives. Réessayez dans quelques minutes.', status=429)
            response['Retry-After'] = '300'
            return response

    def process_response(self, request, response):
        name = getattr(getattr(request, 'resolver_match', None), 'view_name', '')
        if name.startswith(('checkout:', 'dashboard:', 'admin:')) or name.startswith('shop:cart') or name == 'shop:favorites':
            response['Cache-Control'] = 'private, no-store'
        response['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        response['Content-Security-Policy-Report-Only'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' https: data:; media-src 'self' https:; connect-src 'self'; frame-src https://checkout.stripe.com; form-action 'self' https://checkout.stripe.com; object-src 'none'; base-uri 'self'"
        return response
