# Lot 5 — Lisibilité sur petits écrans

Branche : `fix/commercial-information`, départ `ed2862f`. Correction CSS uniquement ; aucune logique commerciale, aucun modèle ni migration modifiés.

## Constat vérifié dans le code

Les anciennes règles `.hero-trust__item` imposaient quatre colonnes et des tailles entre .37 et .59 rem (environ 6–9 px avec une racine à 16 px). Le template actuel utilise toutefois le composant commercial partagé, et non ces quatre anciens éléments : aucune reproduction visuelle du défaut historique n’est revendiquée. Les offres étaient sur trois colonnes, certains prix ne revenaient pas à la ligne, et les barres produit/catalogue étaient fixes au bas de l’écran.

Instructions de contribution et état Git vérifiés avant modification. Lecture des cinq feuilles CSS, de leurs composants concernés (en-tête, accueil, offres, panier, checkout) et des tests de conservation du checkout/pages. Aucun travail local préexistant modifié.

## Diff ciblé et fichiers

- `home/static/css/home.css` : suppression des deux séries de règles miniaturisées ; ancien composant en deux colonnes, une sous 360 px, texte .875 rem. Le bloc réel utilise le style commercial partagé. La sélection signature n’a pas été retouchée.
- `static/css/base.css` : texte commercial à 1 rem, liens de 44 px de haut, champs mobiles à 1 rem ; en-tête sur deux rangées sous 600 px sans supprimer d’accès ; cellules panier rétractables ; menu défilant limité en hauteur. En-tête dans le flux sur téléphone pour éviter de masquer le focus au zoom.
- `product/static/css/product.css` : offres sur deux colonnes avec prix sur sa propre rangée, retours à la ligne, variantes sur plusieurs lignes, informations à .875 rem. Barre d’achat dans le flux sous 600 px, avec safe-area conservée.
- `shop/static/css/shop.css` : noms/prix longs non bloqués, informations utiles à .875 rem, une carte par rangée sous 360 px. Barre panier et outils dans le flux sous 600 px pour éviter les superpositions.
- `checkout/static/checkout/checkout.css` : prix sur une rangée distincte, informations utiles à .875 rem, champs à 1 rem, résumé/promo/CGV et totaux pouvant se répartir ; minimums de largeur corrigés sur les cellules.
- `README.md` : comportement mobile documenté.
- `docs/mobile-readability-report.md` : compte rendu et limites.

Couleurs, polices et composants de marque conservés. Aucun nouveau `overflow-x:hidden` ajouté. Celui déjà présent dans la base ne constitue pas une preuve d’absence de débordement. Les changements corrigent des contraintes intrinsèques identifiées dans le code ; l’inventaire des éléments débordants dans un rendu réel reste à faire.

## Commandes et résultats réellement exécutés

```bash
DJANGO_SECRET_KEY=local-tests-only ../venv/bin/python manage.py check --settings=config.settings.development
DJANGO_SECRET_KEY=local-tests-only ../venv/bin/python manage.py test checkout.test_preservation pages --settings=config.settings.development
git diff --check
```

- Django check : aucun problème.
- Tests ciblés : **20 tests réussis**, 1,024 s. Ces tests vérifient le rendu serveur et la conservation du checkout, pas la disposition CSS.
- Diff : aucune erreur d’espacement.
- Aucun test artificiel ajouté pour les retouches CSS. Aucun modèle modifié, aucune migration nécessaire.
- Tentative de lancement Chromium headless via Playwright : échec, exécutable `chromium_headless_shell-1234` absent.

## Recette restante — lot non entièrement validé

**Aucune capture et aucune largeur n’ont été validées visuellement dans cet environnement.** Vérifier sur préproduction 320, 360, 390, 430, 768 et 1366 px, puis zoom texte 200 %, noms très longs et montants longs. Contrôler l’absence de coupure, le contraste, les cibles 44 × 44 px, le focus clavier et les retours à la ligne. Tester iPhone Safari et Android Chrome réels, en portrait/paysage, clavier virtuel ouvert, safe-area et retour arrière inclus. Une émulation Chromium ne suffirait pas à valider ces deux appareils.

Contrôler les rectangles des éléments visibles par rapport au viewport, en distinguant les pistes de carrousels volontairement défilantes et les panneaux fermés des débordements involontaires. Désactiver temporairement le masquage horizontal global pendant ce diagnostic. Vérifier spécialement les montants, la barre promotionnelle, le tiroir panier, le menu ouvert, les modalités de livraison et les erreurs du checkout. Mesurer aussi l’espace pris par les barres aux largeurs 600–959 px, où leur comportement fixe existant est conservé.

Les barres d’achat ne sont plus flottantes sous 600 px : ce compromis privilégie l’accès au contenu et aux champs, tout en conservant les actions d’achat. Leur position et le menu ouvert doivent être relus dans la recette visuelle avant validation.

## Protections

Contrôle du diff : aucun changement des prix, remises, stock, CSRF, données personnelles, paiement hébergé, webhook ou idempotence. Aucun nouveau stockage ni journal de coordonnées. Ventes toujours bloquées tant que le dossier commercial manque. Aucun déploiement, fusion ou paiement réel.
