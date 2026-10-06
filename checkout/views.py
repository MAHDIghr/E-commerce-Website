"""Page checkout — FRONT-END ONLY. Toutes les données ci-dessous sont FICTIVES.

Aucune commande, aucun paiement, aucun calcul métier n'est effectué ici.
Remplacer build_checkout_data() par les données réelles (panier serveur,
modes de livraison, totaux calculés côté serveur) : le template et checkout.js
ne dépendent que de la forme du dict retourné.
"""
from django.shortcuts import render


def img(photo_id, w=240):
    return f"https://images.unsplash.com/photo-{photo_id}?auto=format&fit=crop&w={w}&q=80"


def build_checkout_data():
    return {
        # True tant que les données sont fictives. Le JS affiche alors une note
        # de démonstration et préfère le panier localStorage s'il n'est pas vide.
        "isMock": True,
        "currency": "EUR",
        "locale": "fr-FR",
        # Même seuil que le tiroir panier (base.js). À fournir par le serveur.
        "freeShippingThreshold": 80,
        # MOCK : articles de démonstration (utilisés si le panier est vide).
        "items": [
            {"id": "sac-cuir-camel", "name": "Sac cabas cuir camel", "variant": "Camel",
             "image": img("1590874103328-eac38a683ce7"), "quantity": 1, "unitPrice": 129.90},
            {"id": "portefeuille-beige", "name": "Portefeuille compact beige", "variant": "",
             "image": img("1591344395067-98c9a56b1a1a"), "quantity": 2, "unitPrice": 45.00},
        ],
        # MOCK : modes de livraison (prix définis plus tard par le backend).
        "shippingMethods": [
            {"id": "standard", "label": "Livraison standard", "eta": "3–5 jours ouvrés", "price": 4.90},
            {"id": "express", "label": "Livraison express", "eta": "1–2 jours ouvrés", "price": 9.90},
        ],
        "countries": [
            {"code": "FR", "name": "France"},
            {"code": "BE", "name": "Belgique"},
            {"code": "LU", "name": "Luxembourg"},
            {"code": "CH", "name": "Suisse"},
            {"code": "DE", "name": "Allemagne"},
            {"code": "ES", "name": "Espagne"},
            {"code": "IT", "name": "Italie"},
            {"code": "NL", "name": "Pays-Bas"},
            {"code": "PT", "name": "Portugal"},
            {"code": "GB", "name": "Royaume-Uni"},
        ],
        "defaultCountry": "FR",
    }


def checkout(request):
    """Display the checkout page (front-end only for now)."""
    return render(request, "checkout.html", {"checkout_data": build_checkout_data()})