"""Trames publiques à compléter avec les informations vérifiées de l'exploitant."""
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.http import require_GET


PAGES = {
    "legal": {
        "title": "Mentions légales",
        "sections": [
            ("Éditeur", ["[À COMPLÉTER : raison sociale ou identité de l’exploitant, forme juridique, capital social si applicable, siège et adresse postale.]", "[À COMPLÉTER : SIRET, immatriculation RCS/RNE et ville si applicable, numéro de TVA intracommunautaire si applicable.]", "[À COMPLÉTER : téléphone et adresse e-mail de contact.] "]),
            ("Publication et hébergement", ["[À COMPLÉTER : directeur ou responsable de la publication.]", "[À COMPLÉTER : nom ou raison sociale, adresse et téléphone de l’hébergeur.] "]),
        ],
    },
    "terms": {
        "title": "Conditions générales de vente",
        "sections": [
            ("Vendeur et champ d’application", ["[À COMPLÉTER : identité et coordonnées du vendeur, clients concernés, date d’entrée en vigueur et modalités d’acceptation des CGV.] "]),
            ("Produits, prix et paiement", ["[À COMPLÉTER : caractéristiques, disponibilité, prix TTC, frais additionnels, moyens et conditions de paiement, promotions.] "]),
            ("Livraison et rétractation", ["[À COMPLÉTER : zones, modes, frais, délais, transfert des risques, modalités de rétractation et exceptions éventuelles.] "]),
            ("Garanties, litiges et médiation", ["[À COMPLÉTER : garanties légales, service après-vente, réclamations, médiateur de la consommation et ses coordonnées, droit applicable.] "]),
        ],
    },
    "privacy": {
        "title": "Politique de confidentialité",
        "sections": [
            ("Responsable et traitements", ["[À COMPLÉTER : identité et coordonnées du responsable du traitement, données collectées, finalités et bases légales.] "]),
            ("Destinataires et conservation", ["[À COMPLÉTER : destinataires et prestataires, durées de conservation, éventuels transferts hors EEE et garanties.] "]),
            ("Vos droits", ["[À COMPLÉTER : modalités d’accès, rectification, effacement, opposition, limitation, portabilité et coordonnées de contact ; réclamation auprès de la CNIL.] "]),
            ("Cookies et traceurs", ["[À COMPLÉTER : inventaire des cookies et traceurs effectivement utilisés, finalités, durées et modalités de gestion du consentement si nécessaire.] "]),
        ],
    },
    "returns": {
        "title": "Retours et rétractation",
        "sections": [
            ("Droit de rétractation", ["[À COMPLÉTER : délai légal applicable, point de départ, modalités de notification, exceptions éventuelles et formulaire type de rétractation.] "]),
            ("Retour des articles", ["[À COMPLÉTER : adresse de retour, délai de renvoi, état des produits, frais de retour et procédure de suivi.] "]),
            ("Remboursement et garanties", ["[À COMPLÉTER : modalités et délai de remboursement, distinction entre rétractation, retour commercial et garanties légales.] "]),
        ],
    },
    "delivery": {
        "title": "Livraison",
        "sections": [
            ("Zones et transporteurs", ["[À COMPLÉTER : pays et zones desservis, transporteurs et modes de livraison.] "]),
            ("Frais et délais", ["[À COMPLÉTER : tarifs TTC, seuil éventuel de livraison offerte, délais de préparation et d’acheminement, point de départ des délais.] "]),
            ("Suivi et incidents", ["[À COMPLÉTER : suivi, procédure en cas de retard, colis perdu ou endommagé, coordonnées du service client.] "]),
        ],
    },
    "contact": {
        "title": "Contact",
        "sections": [
            ("Nous joindre", ["[À COMPLÉTER : adresse e-mail, numéro de téléphone, adresse postale et horaires réels du service client.] "]),
            ("Commandes et réclamations", ["Pour une commande existante, préparez votre référence et consultez la page de suivi.", "[À COMPLÉTER : procédure et délai de traitement des réclamations.] "]),
        ],
    },
    "faq": {
        "title": "Questions fréquentes",
        "sections": [
            ("Comment suivre une commande ?", ["Utilisez le lien « Suivre ma commande » et la référence communiquée par e-mail."]),
            ("Quels sont les frais de livraison ?", ["[À COMPLÉTER : frais et zones en cohérence avec le checkout et la politique de livraison.] "]),
            ("Comment exercer mon droit de rétractation ?", ["[À COMPLÉTER : procédure de notification, adresse et formulaire type en cohérence avec la page Retours et rétractation.] "]),
        ],
    },
    "about": {
        "title": "À propos",
        "sections": [
            ("My Line Collection", ["[À COMPLÉTER : présentation factuelle de la marque, de l’équipe et de son activité.] "]),
            ("Savoir-faire", ["[À COMPLÉTER : origine des produits et engagements vérifiables, si applicables.] "]),
        ],
    },
}


@require_GET
def information_page(request, page):
    content = PAGES.get(page)
    if content is None:
        raise Http404
    return render(request, "pages/information_page.html", {"page": content})
