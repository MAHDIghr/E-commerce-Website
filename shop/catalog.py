"""Presentation-only filtering: preserves the existing catalogue's JS rules."""
import math
from decimal import Decimal, InvalidOperation

PAGE_SIZE = 8
SORTS = [('pop', 'Pertinence'), ('new', 'Nouveautés'), ('best', 'Meilleures notes'),
         ('asc', 'Prix croissant'), ('desc', 'Prix décroissant')]
CATEGORY_LABELS = {'handbags': 'Sacs à main', 'shoulder': 'Sacs bandoulière',
                   'wallets': 'Portefeuilles', 'accessories': 'Accessoires'}


def money(value):
    return f'{value:,.2f}'.replace(',', '\u202f').replace('.', ',') + '\u00a0€'


def selection(cards, params, categories, colors):
    def values(key, allowed):
        return {v for part in params.getlist(key) for v in part.split(',') if v in allowed}
    def number(key):
        try:
            value = Decimal(params.get(key, ''))
            return float(value) if value.is_finite() and 0 <= value <= 5000 else None
        except InvalidOperation:
            return None
    cats = values('cat', {c.slug for c in categories})
    shades = values('color', colors)
    minimum, maximum = number('min'), number('max')
    sale, low = params.get('sale') == '1', params.get('low') == '1'
    sort = params.get('sort', 'pop')
    sort = sort if sort in dict(SORTS) else 'pop'
    filtered = [p for p in cards if
                (not cats or p['cat'] in cats) and
                (not shades or shades.intersection(p['colors'])) and
                (minimum is None or p['price'] >= minimum) and
                (maximum is None or p['price'] <= maximum) and
                (not sale or p['old']) and (not low or 0 < p['stock'] <= 5)]
    keys = {'pop': lambda p: -p['pop'], 'new': lambda p: (-p['isNew'], -p['pop']),
            'best': lambda p: (-p['rating'], -p['reviews']),
            'asc': lambda p: p['price'], 'desc': lambda p: -p['price']}
    filtered.sort(key=keys[sort])
    try:
        page = max(1, int(params.get('page', 1)))
    except (ValueError, TypeError):
        page = 1
    page = min(page, max(1, math.ceil(len(filtered) / PAGE_SIZE)))
    visible = filtered[:page * PAGE_SIZE]
    for index, p in enumerate(visible):
        # Keep the currently displayed category names, including an empty custom label.
        p['swatch_colors'] = [colors[c]['hex'] for c in p['colors']]
        p['category_text'] = CATEGORY_LABELS.get(p['cat'], '')
        p['price_text'] = money(p['price'])
        p['old_text'] = money(p['old']) if p['old'] else ''
        p['discount_percent'] = math.floor((1 - p['price'] / p['old']) * 100 + .5) if p['old'] else 0
        full = math.floor(p['rating'] + .5)
        p['stars'] = '★' * full + '☆' * (5 - full)
        p['rating_text'] = f"{p['rating']:.1f}"
        p['rating_label'] = f"{p['rating']:g}"
        p['animation_index'] = min(index, 8)
    return {'cards': visible, 'total': len(filtered), 'page': page,
            'next_page': page + 1, 'has_more': len(visible) < len(filtered),
            'progress': len(visible) / len(filtered) * 100 if filtered else 0,
            'selected_cats': cats, 'selected_colors': shades, 'minimum': minimum,
            'maximum': maximum, 'sale': sale, 'low': low, 'sort': sort, 'sorts': SORTS}
