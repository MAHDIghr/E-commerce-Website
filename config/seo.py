"""Métadonnées publiques et protections d'indexation ; aucune donnée client exposée."""
from django.templatetags.static import static
from django.urls import reverse
from django.shortcuts import render


def metadata(request):
    name = getattr(request.resolver_match, 'view_name', '')
    titles = {'home:home':'My Line Collection — Sacs et accessoires', 'shop:catalog':'Boutique | My Line Collection',
              'shop:favorites':'Mes favoris | My Line Collection'}
    if name.startswith('pages:'):
        from pages.views import PAGE_TITLES
        titles[name] = PAGE_TITLES.get(name.split(':')[-1], 'Informations') + ' | My Line Collection'
    title = titles.get(name, 'My Line Collection')
    if name == 'shop:catalog':
        query = ' '.join(request.GET.get('q', '').split())[:100]
        if query:
            title = f'Recherche : {query} | My Line Collection'
        if request.GET.get('page', '').isdigit():
            title += f" — Page {request.GET['page']}"
    canonical = request.build_absolute_uri(request.path)
    if name == 'shop:catalog' and request.GET:
        canonical += '?' + request.GET.urlencode()
    return {'seo': {'title': title, 'description':title + ' — Consultez les informations et caractéristiques publiées par My Line Collection.',
                    'url':canonical, 'image':request.build_absolute_uri(static('images/mainLogo.svg'))}}


def not_found(request, exception):
    response = render(request, '404.html', status=404)
    response['X-Robots-Tag'] = 'noindex, nofollow'
    return response


def server_error(request):
    # Template autonome : aucune requête catalogue ou contexte commercial en erreur 500.
    from django.template.loader import get_template
    from django.http import HttpResponse
    response = HttpResponse(get_template('500.html').render({'catalog_url':reverse('shop:catalog'), 'contact_url':reverse('pages:contact')}), status=500)
    response['X-Robots-Tag'] = 'noindex, nofollow'
    return response


class PublicIndexingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Réservation de l'URL anglaise : pas de faux contenu bilingue tant que la traduction manque.
        if request.path == '/en' or request.path.startswith('/en/'):
            from django.http import HttpResponse
            response = HttpResponse('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="robots" content="noindex"><title>English version unavailable | My Line Collection</title><main><h1>The English version is not available yet.</h1><p>The complete shopping journey is being prepared.</p><a href="/">Continue in French</a></main></html>', status=503)
            response['X-Robots-Tag'] = 'noindex, nofollow'
            response['Cache-Control'] = 'no-store'
            return response
        response = self.get_response(request)
        private = ('checkout:', 'dashboard:', 'admin:')
        name = getattr(getattr(request, 'resolver_match', None), 'view_name', '')
        if name.startswith(private) or name in {'shop:cart_page','shop:cart_api','shop:cart_mutation','shop:search_suggestions','shop:favorites'} or name.startswith('home:newsletter_') or response.status_code >= 400:
            response['X-Robots-Tag'] = 'noindex, nofollow'
        return response
