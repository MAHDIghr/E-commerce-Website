# Lot 6 — Clavier et surcouches

Branche `fix/commercial-information`, départ `424a462`. Un commit pour ce lot. Instructions de contribution, composants et protections existantes relus avant modification.

## Inventaire et contrat

| Composant | Avant | Après |
|---|---|---|
| Menu mobile | Navigation avec aria-expanded, sans Échap ni reset au changement de largeur | Navigation non modale conservée ; Échap dans le menu ou sur son bouton, reset au changement de breakpoint |
| Recherche | Focus initial seulement, arrière-plan actif | Dialog nommé, focus initial, confinement, Échap, déclencheur restauré, arrière-plan inert |
| Panier | Confinement Tab, inert fermé, restitution ; Échap fermait aussi la recherche | Protections existantes conservées, fermeture isolée et arrière-plan inert via gestion commune |
| Choix d’offre | Dialog natif avec showModal et annulation | Conservé, priorité du dialog natif sur les gestionnaires personnalisés |
| Filtres | Focus initial, Échap, verrou de défilement indépendant | Modale uniquement sur mobile, confinement et isolation communs ; redevient une section interactive sur desktop |
| Bienvenue | Ouverture après 4 secondes, sans gestion clavier dédiée ; lien ancre absent | Bouton explicite, aucune ouverture automatique, mêmes protections clavier ; catalogue Django réel |
| Communauté | Focus initial, Tab, Échap, restitution, arrêt vidéo | Isolation commune ; arrêt/nettoyage vidéo conservés ; refus d’ouverture concurrente |
| Lightbox produit | Dialog natif showModal, Échap natif, fermeture et commandes de navigation | Conservé |

Le gestionnaire refuse une seconde modale personnalisée lorsque l’une est active ou qu’un dialog natif est ouvert. Les états inert antérieurs et le défilement sont restaurés à la fermeture. Les backdrops panier/filtres restent cliquables. Fermer une surcouche inactive ne déplace pas le focus. La bienvenue ne revient plus spontanément ; les préférences de fermeture restent écrites sans données personnelles. Le bouton explicite permet de consulter de nouveau l’offre volontairement.

Les erreurs du checkout conservent leur résumé accessible et leur focus utile. Les changements de mode de livraison annoncent désormais le total estimé dans le statut live existant ; aucun montant n’est recalculé à partir de prix client.

## Fichiers et raisons

- `static/js/overlays.js` : gestion commune des modales personnalisées.
- `templates/base.html` : chargement avant les scripts utilisateurs du gestionnaire.
- `static/js/base.js` : intégration recherche/panier, fermeture isolée, menu non modal et reset au breakpoint.
- `templates/partials/_search_overlay.html` : nom et sémantique de dialog recherche.
- `home/static/js/home.js` : bienvenue volontaire, gestion commune et préférence de fermeture conservée.
- `home/templates/home.html` : déclencheur bienvenue, attributs du dialog et lien réel au catalogue.
- `shop/static/js/shop.js` : filtres modaux uniquement sur mobile, restitution et défilement communs.
- `home/static/js/community-media.js` : intégration commune, suppression du gestionnaire concurrent Tab/Échap.
- `checkout/static/checkout/checkout-summary.js` : annonce du total estimé lors d’un changement de mode.
- `static/css/base.css` : texte secondaire légèrement assombri pour le contraste sur le fond crème.
- `tests/overlays.test.cjs` : tests DOM du confinement, fermeture/restauration, concurrence et priorité native.
- `README.md` et ce rapport : contrat et limites documentés.

## Validation exécutée

```bash
NODE_PATH=../checkout-test-runtime/node_modules node --test tests/overlays.test.cjs
NODE_PATH=../checkout-test-runtime/node_modules node --test tests/checkout-summary.test.cjs
DJANGO_SECRET_KEY=local-tests-only ../venv/bin/python manage.py test pages checkout.test_preservation --settings=config.settings.development
DJANGO_SECRET_KEY=local-tests-only ../venv/bin/python manage.py check --settings=config.settings.development
node --check static/js/overlays.js
node --check static/js/base.js
node --check home/static/js/home.js
node --check shop/static/js/shop.js
node --check home/static/js/community-media.js
node --check checkout/static/checkout/checkout-summary.js
git diff --check
```

Résultats : 4 tests de modales, 11 tests du checkout et 20 tests Django réussis. Django check et syntaxe JavaScript sans erreur. Ces simulations utilisent jsdom installé hors dépôt ; aucune dépendance de production ajoutée. Aucun changement de modèle ni migration.

Contraste calculé par luminance relative sRGB sur les couleurs CSS opaques : texte principal #1c1613 / fond #faf7f4 = 16,77:1 ; blanc / accent sombre #8a5a32 = 5,85:1. Le texte secondaire #7d7166 donnait 4,45:1 sur ce fond : sa variable partagée passe à #786c61, soit 4.78:1 sur ce fond. Les styles calculés, opacités, images, états hover/focus et tous les composants n’ont pas été mesurés dans un navigateur ; aucune conformité globale n’est annoncée.

## Vérifications restantes

Chromium était indisponible lors du lot précédent et aucun nouveau navigateur ni préproduction n’a été fourni : aucune capture ni largeur réellement testée ici. Vérifier 320/360/390/430/768/1366 px, zoom texte 200 %, visibilité du focus, menu et filtres après redimensionnement, enchaînements recherche/panier/offres et communauté, fermeture vidéo, ainsi que le contraste calculé réel. Les tests DOM du gestionnaire ne constituent pas une recette de chaque page intégrée.

Un parcours lecteur d’écran représentatif reste obligatoire, notamment titre de la modale, contenu inert, erreurs et annonces de total. Vérifier iPhone Safari et Android Chrome et les dialogs natifs dans un vrai navigateur. Le lot reste partiellement validé tant que cette recette n’est pas faite.

## Protections

Diff limité aux interactions, sémantique, contraste et annonces. Aucun changement des prix/remises serveur, du stock, de CSRF, du webhook signé, de l’idempotence ou de Stripe Checkout hébergé. Aucune coordonnée ni secret ajouté au stockage ou aux journaux. Aucun déploiement, fusion ou paiement réel.
