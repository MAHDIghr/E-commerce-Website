# Catalogue et raccordements — corrections sans refonte

Date : 6 novembre 2026. Branche : `fix/commercial-information`.
Base examinée : `6a306c1cc4eedf205e2e582c070c8414802683ee`.
Ce rapport accompagne le commit qui contient ce fichier. Aucun déploiement.

## Contrat et constats avant correction

- `published_products()` sélectionne les produits publiables. `product_card_data()`
  choisit la variante affichée et l'offre existantes, image, prix de référence,
  couleurs, stock de la variante et avis approuvés. Ces règles restent inchangées.
- La vue ne filtrait que la recherche `q`. Tout le catalogue correspondant était
  transmis au navigateur ; JS filtrait/triait puis affichait huit cartes.
- La grille initiale ne contenait aucune carte ni lien produit sans JS.
- `replaceState` supprimait les paramètres inconnus, `page` n'était pas mémorisé,
  et aucun gestionnaire `popstate` ne restaurait les contrôles.
- Les favoris conservaient un instantané en mémoire : une autre page/onglet
  pouvait modifier le stockage, puis une action locale écraser ces modifications.
- Le passage desktop vers mobile ne rétablissait pas toujours `inert` sur les
  filtres fermés. L'ouverture ne synchronisait pas tous les déclencheurs.

## Diff fonctionnel

| Fichier | Changement |
| --- | --- |
| `shop/catalog.py` | Transposition des filtres et tris existants ; présentation monétaire FR ; sélection cumulative par tranches de huit. |
| `shop/views.py` | HTML initial et réponse partielle GET avec le même contexte ; `Vary: X-Catalog-Update`. |
| `shop/templates/shop/_cards.html` | Balisage des cartes reproduit depuis l'ancien constructeur JS ; liens Django et échappement automatique. |
| `shop/templates/catalog.html` | Remplissage des emplacements existants ; association des contrôles aux formulaires GET invisibles, sans enveloppe modifiant la disposition. |
| `shop/static/js/shop.js` | Attachement aux cartes initiales, requêtes annulables, historique, maintien du focus catégorie, événements uniques, reprise d'ajout après échec, synchronisation des favoris et du tiroir. |
| `home/static/js/home.js` | Rafraîchissement des favoris sur retour navigateur, changement de stockage et avant modification. |
| `shop/test_catalog_rendering.py` | Huit tests serveur : rendu, GET, bornage initial, pagination, échappement, publication, paramètres et noms de catégories inchangés. |
| `tests/catalog.test.cjs` | Simulations DOM : initialisation, double clic, réponses tardives, historique, favoris, focus, redimensionnement ; comparaison optionnelle avec le JS de base. |
| `README.md` | Contrat actuel et limites sans JS. |
| `docs/catalog-functional-review.md` | Présent rapport. |

Les cartes utilisent désormais un seul partial. Le navigateur reçoit huit produits
initialement ; « Voir plus » conserve le comportement cumulatif (16, 24, etc.) et
le paramètre `page` permet de le retrouver. Une page excessive est ramenée à la
dernière tranche disponible. Les paramètres inconnus, la recherche et le fragment
URL sont conservés lors des changements JS. En échec réseau, navigation GET vers
l'état demandé plutôt qu'affichage d'un résultat erroné comme réussi.

Le parcours serveur parcourt encore les produits correspondant à la recherche
pour préserver exactement les choix d'offres/variantes, les tris et les couleurs.
L'optimisation du travail SQL à très grand volume reste à effectuer ; ce lot
limite la transmission initiale, pas le coût serveur à un nombre fixe de lignes.

## Raccordements examinés et volontairement inchangés

- Les liens de catégories d'accueil et du header emploient les slugs administrés.
  Les liens de cartes utilisent la bonne fiche ; les identifiants variante et
  l'URL des offres sont conservés. Les tests existants panier/offres passent.
- « En savoir plus » mène déjà à la page À propos : aucune correction nécessaire.
- Le CTA hero « Découvrir la collection » mène à `#selection` : intention ambiguë,
  aucune redirection ni réécriture éditoriale effectuée.
- Les cartes affichent les traductions historiques de quatre slugs connus ; le
  libellé reste vide pour les catégories personnalisées. Correction visible donc
  non appliquée. Les filtres conservent leurs noms administrés existants.
- SignatureSelection exige une image dédiée mais affiche l'image de variante/
  produit : divergence confirmée, image/alt/texte/rendu volontairement inchangés.
- Aucune liste de favoris n'existe : les boutons et leur persistance sont conservés,
  aucune liste créée, aucun bouton retiré.
- Les sections vides de la fiche et l'ordre des actions restent inchangés.

## Sans JavaScript

Cartes, noms, prix et liens sont dans le HTML. Les boutons de catégorie, raccourcis
prix, réinitialisation et pagination utilisent GET, avec les libellés/classes
existants. Le formulaire conserve les paramètres utiles.
Le tiroir mobile reste fermé sans JS. Sur desktop, le bouton Voir du tiroir est
masqué par le CSS existant ; les champs avancés/tri n'ont donc pas toujours de
soumission autonome accessible (ils peuvent être soumis avec Voir plus lorsqu'il
est présent). Pas de nouveau bouton pour contourner cette limite. L'ajout au panier
et les favoris exigent toujours JS ; les liens vers les fiches restent accessibles.
Aucune nouvelle promesse d'achat entièrement sans JS.

## Vérifications réellement exécutées

- `python manage.py check --settings=config.settings.development` : aucun problème.
- `python manage.py makemigrations --check --dry-run --settings=config.settings.development` : aucun changement détecté ; aucun modèle modifié.
- `python manage.py test --settings=config.settings.development --noinput` : **226 tests réussis**, 12,552 s pour la dernière exécution complète.
- `node --check shop/static/js/shop.js` et `node --check home/static/js/home.js` : syntaxe valide.
- Tests jsdom catalogue + surcouches + checkout : **25 réussis**. Ce sont des simulations, pas des essais navigateur.
- `git diff --check` : sans erreur après correction d'un espace final.
- Comparaison structurelle avant/après sur les mêmes huit produits fictifs :
  classes, attributs, images, liens, textes, prix, réduction, stock, avis et styles
  inline des cartes identiques, sauf marqueur interne non visuel `data-bound`.
  La comparaison normalise l'ordre des attributs et la sérialisation CSS ; jsdom
  reçoit les propriétés réfléchies loading/decoding manquantes de son implémentation.
  **Cette preuve DOM n'est pas une validation visuelle.**

Reproduction des simulations après installation locale de jsdom dans un environnement
Node de test (aucune dépendance de production ajoutée) :

```bash
git show 6a306c1:shop/static/js/shop.js > /tmp/catalog-before.js
CATALOG_DOM_FIXTURE=/tmp/catalog-fixture.json python manage.py test shop.test_catalog_rendering --settings=config.settings.development
CATALOG_DOM_FIXTURE=/tmp/catalog-fixture.json CATALOG_BASELINE_JS=/tmp/catalog-before.js node --test tests/catalog.test.cjs tests/overlays.test.cjs tests/checkout-summary.test.cjs
```

Ici Python était `../venv/bin/python`, `DJANGO_SECRET_KEY=local-tests-only`, et
`NODE_PATH=../checkout-test-runtime/node_modules` pointait sur le jsdom de test déjà
présent hors dépôt. Les premiers essais ont détecté des fixtures inactives et des
écarts propres à jsdom ; corrigés avant les résultats finaux ci-dessus.

## Visuel et mobile : contrôles restants, aucune correction graphique

La tentative de démarrage Playwright/Chromium a échoué : exécutable absent.
Aucune capture produite. **320, 360, 390, 430, 768 et 1366 px : non validés dans
un navigateur.** Clavier réel, toucher, zoom texte 200 %, iPhone Safari, Android
Chrome, console navigateur, clavier virtuel et débordements restent à contrôler
avant/après sur les mêmes données, notamment noms et montants longs.

Risques repérés dans le code, sans les présenter comme des débordements observés :

- `home.css` contient encore des réassurances à quatre colonnes avec des valeurs
  allant jusqu'à `.37rem`–`.46rem`. Vérifier l'applicabilité aux éléments actuels ;
  proposition séparée : disposition/tailles plus lisibles après validation graphique.
- `shop.css` conserve tags `.68rem`, catégorie/avis `.72rem` et livraison `.74rem`.
  Proposition séparée : mesurer la lisibilité puis faire valider les tailles.
- La barre panier est fixe, et la compensation du footer vaut `4.5rem` : des
  textes longs/zoom/clavier peuvent nécessiter davantage d'espace. Proposition :
  mesurer la hauteur réelle et la zone couverte avant toute adaptation.
- Les boutons ajout/favori ont déjà 44×44 px déclarés ; cela ne valide ni tous les
  contrôles ni leur accessibilité au toucher réel.
- `base.css` comporte déjà `overflow-x: hidden` : laissé intact ; ne constitue
  aucune preuve d'absence de dépassement. Mesurer les rectangles des éléments
  dans un navigateur pour identifier les causes avant proposition de correction.

Aucun CSS, image, icône, breakpoint, texte commercial, template partagé ou fichier
checkout modifié. L'animation `cardIn` et ses délais sont conservés ; les cartes
serveur remplacent le besoin de fabriquer des squelettes à l'initialisation.
Les prix/stock, CSRF et paiements restent dans leurs services existants, couverts
par la suite serveur. Aucune coordonnée n'est ajoutée au stockage : seuls les slugs
favoris existants y persistent. Aucun paiement, aucune migration appliquée en
production, aucun déploiement. La conformité visuelle globale reste non validée.
