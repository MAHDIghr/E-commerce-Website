# Lot 7 — Catalogue sans JavaScript

Branche `fix/commercial-information`, départ `a67dd16`. Lecture préalable des instructions de contribution, sélecteurs et modèles de publication/offres/variantes, vues, templates, scripts, styles et tests pertinents. Aucun modèle modifié, aucune migration.

## Avant / après

Le constat a été vérifié dans le code : grille HTML vide, catalogue complet sérialisé en JSON, filtres/tri et pagination uniquement en JavaScript. La règle `.reveal` masquait l’accueil avant initialisation de son observateur.

Django filtre et trie maintenant les produits en base avant pagination par huit. Les cartes proviennent de `product_card_data`, conservé comme source de présentation, et du partial `shop/_product_card.html`. Les annotations SQL reflètent la sélection de l’offre Essentiel, sinon de l’offre mise en avant, puis de la première offre valide ; les couleurs et la variante de stock suivent les règles publiques existantes. Les prix du filtre ne sont pas ceux d’une offre secondaire moins chère. Les offres sans ligne principale valide sont exclues.

Le formulaire GET conserve la recherche, les sélections et les paramètres supplémentaires. Les liens de page préservent la query string et la soumission des filtres repart de la première page. Le navigateur assure naturellement historique et retour arrière : aucun replaceState ni rerendu client n’écrase l’URL. Les contrôles sont standards et restent accessibles si les scripts ne démarrent pas.

Le JSON de compatibilité se limite aux huit cartes de la page ; il n’alimente plus un second moteur de filtrage/rendu. Il n’y a pas d’hydratation ni de double catalogue. Les favoris et l’ajout rapide restent des améliorations progressives des cartes existantes, sans remplacer leurs nœuds ni leurs liens. Les boutons sont initialement masqués et révélés après installation de leur gestionnaire ; si les helpers de base manquent, les liens restent disponibles.

L’achat sans JavaScript n’est pas présenté comme opérationnel : les cartes mènent à la fiche avec « Choisir une offre ». La fiche affiche un message noscript expliquant l’activation nécessaire pour le panier et le paiement, et masque alors les boutons dépendants du script. Les protections de vente fermée restent actives. Les pages restent consultables sans promesse de commande silencieuse.

L’accueil est visible par défaut. La classe optionnelle `reveal-ready` n’ajoute aucun masquage ; une erreur de script ou d’observateur ne fait donc pas disparaître le contenu. La section sélection signature n’a pas été retouchée.

## Fichiers et raisons

| Fichier | Raison |
|---|---|
| `shop/views.py` | Filtres GET, tri SQL, pagination bornée, valeurs du formulaire et conservation des paramètres. |
| `product/selectors.py` | Sélections SQL cohérentes avec les cartes pour prix d’offre, variante/stock, couleurs et notes approuvées. |
| `shop/templates/catalog.html` | Cartes initiales, formulaire standard, pagination réelle et chemin explicite vers l’achat. |
| `shop/templates/shop/_product_card.html` | Partial unique des cartes : image, nom, prix, lien réel et contrôles progressifs. |
| `shop/static/js/shop.js` | Retrait du moteur de catalogue client concurrent ; conservation des favoris, ajout rapide et barre panier. |
| `shop/static/css/shop.css` | Mise en page et contrôles tactiles du formulaire GET et de la pagination. |
| `home/static/css/home.css` | `.reveal` visible par défaut. |
| `home/static/js/home.js` | Marqueur de préparation de l’animation sans masquer les produits. |
| `product/templates/product.html` | Explication noscript et masquage des boutons d’achat inopérants sans script. |
| `product/tests.py` | Test du lien Django réel dans le HTML au lieu de l’ancien modèle de lien client. |
| `shop/test_catalog_html.py` | Six tests de rendu, filtrage, pagination, prix d’offre, couleurs publiques et échappement. |
| `tests/catalog-progressive.test.cjs` | Deux tests DOM des améliorations et du maintien des cartes quand les helpers manquent. |
| `README.md` et ce rapport | Contrat, commandes, limites et recette restante. |

## Commandes réellement exécutées et résultats

```bash
DJANGO_SECRET_KEY=local-tests-only ../venv/bin/python manage.py test shop product --settings=config.settings.development
DJANGO_SECRET_KEY=local-tests-only ../venv/bin/python manage.py test --settings=config.settings.development
DJANGO_SECRET_KEY=local-tests-only ../venv/bin/python manage.py test shop.test_catalog_html --settings=config.settings.development
NODE_PATH=../checkout-test-runtime/node_modules node --test tests/catalog-progressive.test.cjs
DJANGO_SECRET_KEY=local-tests-only ../venv/bin/python manage.py check --settings=config.settings.development
DJANGO_SECRET_KEY=local-tests-only ../venv/bin/python manage.py makemigrations --check --dry-run --settings=config.settings.development
node --check shop/static/js/shop.js
node --check home/static/js/home.js
git diff --check
```

- Suite complète finale : **213 tests Django réussis**, 12,405 s, dont six nouveaux tests du catalogue. Ce nombre n’est pas celui de l’audit.
- Passe ciblée shop/product : 68 tests réussis avant les deux derniers cas ajoutés. Passe ciblée après harmonisation des couleurs : quatre tests réussis, puis les six cas sont inclus dans la suite finale.
- Deux tests DOM JavaScript réussis, 0,608 s : mêmes nœuds/liens conservés, aucun doublon, favoris/ajout rapide opérationnels avec helpers simulés, contrôles masqués sans helpers. Il ne s’agit pas d’une recette navigateur.
- Django check : aucun problème. Migrations : aucune modification détectée. Syntaxe JS et diff : réussis.
- Première passe : 64 tests, un échec dû au test qui attendait encore le modèle de lien client ; il a été remplacé par l’attente du vrai lien de fiche, maintenant rendu côté serveur.

Les tests HTTP contrôlent les cartes, noms/prix/images/liens dans la réponse initiale, le formulaire GET, l’état vide, les critères invalides, les limites de pagination, la query string conservée, l’absence de produits communs entre pages, le prix de l’offre Essentiel malgré une offre secondaire moins chère, la promotion réelle et l’exclusion d’une couleur sans photo lorsqu’une variante illustrée existe. Le nom produit contenant des balises reste échappé.

## Contrôles du code et protections

Les cartes reprennent les prix de base existants à titre informatif ; aucun montant client ne fait foi. La consultation ne crée pas de commande. L’ajout rapide réutilise `addProductFromCard` et la route d’offres existants ; validations du panier, stock, prix serveur et CSRF conservées. Aucun changement du checkout, webhook signé, idempotence ou Stripe Checkout hébergé. Aucun nouveau stockage de coordonnées ou secrets. Les favoris stockent seulement les identifiants produit, comme auparavant.

Les cartes et paramètres sont échappés par Django ; le JSON borné utilise json_script. Les paramètres de tri sont soumis à une liste autorisée. Aucun prix de boutique, stock ou offre commerciale n’est inventé.

## Vérifications restantes

Tentative réelle de lancement Playwright/Chromium : exécutable `chromium_headless_shell-1234` absent. **Aucune capture, aucune largeur 320/360/390/430/768/1366 px n’a été contrôlée dans un navigateur.** Aucun paiement ni déploiement.

Il reste à relire les nouvelles cartes et le formulaire sur préproduction, JavaScript désactivé puis en erreur, ainsi qu’après activation : aucun doublon, ajout rapide, favoris, historique/retour arrière, navigation de page et recherche. Vérifier zoom texte 200 %, noms/prix longs, focus, lecture d’écran, iPhone Safari et Android Chrome. Les contrôles HTTP et simulations DOM ne valident pas le rendu visuel ni le comportement de cache d’un vrai navigateur.

La requête catalogue est bornée avant sérialisation des produits, mais ses annotations et filtres doivent être profilés sur le volume réel de production avant optimisation d’index. Les options de couleurs sont une projection SQL distincte, pas un préchargement des fiches complètes. Les pages françaises sont rendues par Django ; les libellés fixes de navigation, formulaire et actions conservent une traduction progressive FR/EN sans recréer les cartes ni les champs. La traduction du chrome partagé reste gérée par le script existant. Le catalogue ne dispose plus d’un second moteur de tri en mémoire.

Le lot n’est pas entièrement validé visuellement ; les ventes demeurent soumises au dossier commercial approuvé. Aucune fusion automatique, aucun déploiement, aucun paiement réel.
