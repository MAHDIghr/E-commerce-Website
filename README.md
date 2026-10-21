# E-commerce Website — My Line Collection

> Application e-commerce Django orientée mode, sacs à main et accessoires, avec une interface éditoriale premium, responsive et pensée en priorité pour le mobile.

**Dépôt :** [MAHDIghr/E-commerce-Website](https://github.com/MAHDIghr/E-commerce-Website)  
**Branches de référence :** `main`, `developpement` et `developpement-backend`  
**Langue actuelle de l'interface :** français  
**État fonctionnel :** sur `developpement-backend`, les catégories, produits, variantes et contenus de fiche sont chargés depuis les modèles Django. Le panier reste côté navigateur et le checkout/paiement ne sont pas encore des fonctionnalités métier réelles.

---

## Sommaire

- [1. Objectif du projet](#1-objectif-du-projet)
- [2. État fonctionnel et limites importantes](#2-état-fonctionnel-et-limites-importantes)
- [3. Organisation générale](#3-organisation-générale)
- [4. Parcours et pages](#4-parcours-et-pages)
- [5. Architecture technique](#5-architecture-technique)
- [6. Différences entre les branches](#6-différences-entre-les-branches)
- [7. Installation locale](#7-installation-locale)
- [8. Commandes de développement](#8-commandes-de-développement)
- [9. Configuration et déploiement](#9-configuration-et-déploiement)
- [10. Sécurité, accessibilité et qualité](#10-sécurité-accessibilité-et-qualité)
- [11. Feuille de route technique](#11-feuille-de-route-technique)
- [12. Guide de travail pour une IA ou un nouveau contributeur](#12-guide-de-travail-pour-une-ia-ou-un-nouveau-contributeur)
- [13. Règles de contribution Git](#13-règles-de-contribution-git)

---

## 1. Objectif du projet

Le projet est une boutique en ligne de démonstration pour une marque de sacs et d'accessoires féminins. L'objectif est de construire une expérience d'achat moderne et crédible, avec une identité visuelle éditoriale, des médias produits riches, des offres groupées, un panier latéral et un tunnel de commande conçu pour évoluer vers une implémentation métier complète.

Les priorités de conception sont :

- **Mobile-first :** navigation, carrousels, offres et actions principales doivent rester utilisables sur de petits écrans.
- **Présentation produit convaincante :** galerie d'images et de vidéos, variantes de contenu, offres groupées, avis et produits associés.
- **Parcours d'achat cohérent :** catalogue → fiche produit → panier → checkout.
- **Interface soignée :** typographies Playfair Display et Inter, composants partagés, hiérarchie visuelle claire et micro-interactions.
- **Base technique compréhensible :** Django gère le routage et le rendu des templates ; CSS et JavaScript assurent l'essentiel des interactions côté navigateur.

Les libellés commerciaux, prix, notes, avis, réductions, compteurs et articles visibles dans cette version peuvent être des **données fictives de démonstration**. Ils ne doivent pas être présentés comme des données réelles en production.

## 2. État fonctionnel et limites importantes

### Ce qui est en place

- Projet Django avec configuration centrale et applications séparées.
- Templates Django héritant d'un layout partagé.
- Pages d'accueil, de catalogue, de produit et de checkout.
- Feuilles de style et scripts JavaScript organisés par fonctionnalité.
- Panier et éléments de navigation côté client, selon les scripts partagés.
- Modèles métier et administration du catalogue dans `developpement-backend` : catégories, produits, variantes, médias, offres, contenus de fiche et avis modérés.
- Page d'accueil : catégories actives et section « Nos nouveautés » chargées depuis la base.
- Catalogue et fiche produit alimentés par les données Django.
- Le checkout conserve ses données de démonstration et le panier reste géré côté navigateur.
- Dans `developpement`, améliorations récentes de la zone communautaire avec stories/reels et une visionneuse média.

### Ce qui n'est pas encore un véritable système e-commerce

Dans `developpement-backend`, le catalogue, les catégories et les fiches produit utilisent les modèles Django. Le checkout utilise encore des données fictives ; aucune commande, aucun paiement ni calcul métier de checkout n'est exécuté côté serveur. Le panier est toujours conservé dans le navigateur et ne constitue pas une source fiable pour les prix ou les stocks.

Ne pas supposer que les fonctionnalités visuelles suivantes sont connectées à un service réel sans vérifier le code concerné :

- comptes clients et authentification de boutique ;
- persistance serveur du panier ;
- application effective de codes promotionnels ;
- calcul serveur des taxes, frais de port et totaux ;
- création, suivi ou confirmation de commande ;
- paiement par carte, Stripe, PayPal ou autre prestataire ;
- envoi réel de newsletter ;
- vérification réelle des avis clients, preuve sociale ou statistiques commerciales.

**Règle de sécurité :** aucun montant affiché par le navigateur ne doit être considéré comme fiable. Avant toute mise en production, le serveur devra recalculer les prix et totaux, valider les promotions et les quantités, vérifier les stocks, créer les commandes et confirmer les paiements à partir de notifications vérifiées du prestataire.

## 3. Organisation générale

La structure fonctionnelle connue du dépôt est organisée autour de ces éléments :

```text
.
├── manage.py
├── requirements.txt
├── config/
│   ├── urls.py
│   └── settings/                 # paramètres Django organisés en package
├── home/
│   ├── views.py
│   ├── urls.py
│   ├── templates/
│   │   └── home.html
│   └── static/
│       ├── css/
│       │   └── home.css
│       └── js/
│           ├── home.js
│           └── community-media.js  # présent sur developpement
├── shop/
│   ├── views.py
│   └── urls.py
├── product/
│   ├── views.py
│   └── urls.py
├── checkout/
│   ├── views.py
│   └── urls.py
├── templates/
│   ├── base.html
│   └── partials/                # en-tête, pied de page, recherche, panier…
└── static/                      # ressources partagées (CSS/JS et médias)
```

Cette arborescence est un guide de navigation, pas un inventaire exhaustif de chaque fichier. Consultez la branche cible pour confirmer les chemins exacts et les ressources qui y sont présentes.

### Responsabilités des dossiers

| Élément | Responsabilité |
|---|---|
| `config/` | Configuration du projet Django et routage global. |
| `home/` | Page d'accueil, sections éditoriales et fonctionnalités de la page d'accueil. |
| `shop/` | Vue de catalogue ; les produits sont actuellement préparés côté client à partir de données statiques. |
| `product/` | Construction des données de démonstration et rendu de la fiche produit. |
| `checkout/` | Construction des données de démonstration et rendu du formulaire de commande. |
| `templates/base.html` | Structure HTML partagée : métadonnées, styles communs, barre promotionnelle, en-tête, recherche, panier, contenu, pied de page et scripts communs. |
| `static/` et `<app>/static/` | Styles, scripts, images et médias utilisés par les templates. |
| `requirements.txt` | Dépendances Python épinglées. |

## 4. Parcours et pages

Les routes sont définies dans `config/urls.py`.

| URL | Application | Fonction |
|---|---|---|
| `/` | `home` | Accueil et présentation de la boutique. |
| `/boutique/` | `shop` | Catalogue. |
| `/produit/` | `product` | Fiche du produit de démonstration par défaut. |
| `/produit/<slug>/` | `product` | Fiche produit résolue à partir d'un slug. |
| `/checkout/` | `checkout` | Formulaire et récapitulatif de commande de démonstration. |
| `/admin/` | Django Admin | Administration Django standard, sous réserve de la configuration locale. |

### Accueil

La page d'accueil est un template Django qui s'appuie sur des styles et scripts dédiés. Elle contient notamment des sections marketing et éditoriales, des contenus de collection, des éléments promotionnels, une newsletter de présentation et des composants d'engagement. Leur présence visuelle ne garantit pas qu'un service métier soit raccordé.

### Catalogue

La vue `shop.views.catalog` rend `catalog.html`. Les commentaires du code précisent que les produits sont actuellement rendus côté client à partir de `static/js/shop.js`. Une future intégration doit remplacer cette source de démonstration par des données provenant du back-end.

### Fiche produit

La vue `product.views.detail` appelle `build_product()` et transmet un dictionnaire `product` au template `product.html`. Les données incluent notamment :

- nom, slug, accroche et ligne de marque ;
- médias de type image ou vidéo, vignettes et textes alternatifs ;
- offres groupées, prix indicatifs, anciens prix, économies affichées et informations de livraison ;
- éléments de réassurance, avis/FAQ et suggestions de produits associés.

Le code de la vue indique explicitement que les données sont fictives. Le template est conçu pour dépendre de la forme du dictionnaire plutôt que de la façon dont les données sont obtenues. C'est un point d'extension prévu pour brancher ultérieurement des modèles tels que produit, variante, média, offre, avis et produit associé.

### Checkout

La vue `checkout.views.checkout` transmet `build_checkout_data()` au template `checkout.html`. Le dictionnaire contient actuellement des articles, des modes de livraison, une devise/locale, un seuil de livraison offerte et une liste de pays de démonstration. Le champ `isMock` signale cet état fictif.

Le checkout actuel sert à construire et évaluer l'interface. Il ne constitue pas une implémentation de paiement ou de traitement des commandes.

### Stories et reels — branche `developpement`

La branche `developpement` contient `home/static/js/community-media.js`, qui gère les interactions de la zone communautaire, les aperçus différés des reels et l'ouverture d'une visionneuse média. Les stories conservent une vignette statique plutôt que de lancer automatiquement leur vidéo. Une règle CSS masque également l'icône de lecture superposée sur les reels. Cette fonctionnalité n'est pas présente dans `main` à l'état comparé pour la rédaction de ce document.

## 5. Architecture technique

### Back-end

- **Python / Django :** routage, vues et rendu des templates.
- **Templates Django :** héritage via `base.html`, inclusion de composants partagés, chargement des ressources statiques et transmission de données au navigateur.
- **Données de démonstration :** construites dans les vues produit et checkout ; le catalogue dépend de données côté client.
- **Dépendances :** la version de Django déclarée dans `requirements.txt` est `6.1.1`. Le fichier est la référence pour installer les dépendances du dépôt.

### Front-end

- **HTML et templates Django** pour la structure.
- **CSS** pour les styles globaux et spécifiques aux pages.
- **JavaScript natif** pour les interactions : navigation, panier côté client, page d'accueil, galerie/achat produit, checkout et, dans `developpement`, médias communautaires.
- **Google Fonts** : Playfair Display et Inter sont chargées par le template de base.
- **Images de démonstration** : plusieurs visuels utilisent des URL Unsplash. Une vidéo de démonstration locale est référencée dans les données produit ; vérifiez la présence du fichier média correspondant avant de tester cette partie.

### Routage et noms d'URL

Les applications déclarent des espaces de noms (`app_name`) tels que `home`, `shop`, `product` et `checkout`. Préférez les noms d'URL Django et les balises `{% url %}` aux chemins codés en dur lorsque cela est compatible avec le contexte.

## 6. Différences entre les branches

Les deux branches partagent le socle Django et les pages principales. La comparaison des références au moment de la rédaction montre que `developpement` est en avance sur `main` et contient des changements concentrés sur l'interface d'accueil et la zone communautaire. Le contenu exact peut évoluer : vérifiez toujours les références actuelles avant de modifier le code.

### `main` — branche de référence stable

Utilisez `main` pour comprendre le socle commun et l'état de référence du projet :

- routage Django vers l'accueil, le catalogue, la fiche produit et le checkout ;
- layout partagé et composants globaux ;
- interface de la boutique, catalogue, page produit et checkout en mode démonstration ;
- styles et scripts présents dans cette branche.

Dans l'état comparé, `main` ne contient pas `home/static/js/community-media.js) ; les interactions stories/reels récemment ajoutées à `developpement` ne doivent donc pas être supposées disponibles sur cette branche.

### `developpement` — branche de travail UI/UX

Cette branche part du même socle que `main` et comprend les changements UI/UX plus récents de la page d'accueil :

- ajustements de `home/templates/home.html` ;
- refonte/ajustements responsive et styles communautaires dans `home/static/css/home.css` ;
- nouveau script `home/static/js/community-media.js` ;
- stories et reels avec logique de prévisualisation et visionneuse ;
- vignette des stories conservée sans lecture automatique ;
- icône de lecture superposée des reels masquée par CSS.

### Tableau synthétique

| Sujet | `main` | `developpement` |
|---|---|---|
| Socle Django et routes principales | Présent | Présent |
| Accueil, catalogue, produit et checkout | Présents | Présents |
| Données produit et checkout réelles | Non, démonstration | Non, démonstration |
| Ajustements récents de la zone communautaire | Non dans la comparaison actuelle | Oui |
| Script `community-media.js` | Absent dans la comparaison actuelle | Présent |
| Usage recommandé | Référence stable | Développement et validation UI/UX |

**Ne fusionnez pas automatiquement les branches.** Examinez le diff et testez les pages touchées avant toute intégration. Les différences entre branches doivent être déduites du code et de Git, pas uniquement de ce résumé.

## 7. Installation locale

### Prérequis

- Git ;
- Python compatible avec la version de Django déclarée dans `requirements.txt` ;
- pip.

Vérifiez la version Python disponible :

```bash
python --version
python -m pip --version
```

### Cloner le dépôt et choisir une branche

```bash
git clone https://github.com/MAHDIghr/E-commerce-Website.git
cd E-commerce-Website

# Branche de référence
git switch main

# Ou branche de développement
git switch developpement
```

### Installer les dépendances

Sous Linux/macOS :

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Sous Windows PowerShell :

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Le dépôt épingle ses dépendances dans `requirements.txt`. Si l'installation échoue, vérifier d'abord la version de Python prise en charge par la version de Django installée et le contenu actuel du fichier de dépendances ; ne pas remplacer arbitrairement les versions.

### Lancer le serveur de développement

```bash
python manage.py check
python manage.py runserver
```

Puis ouvrir [http://127.0.0.1:8000/](http://127.0.0.1:8000/).

Le projet configure `manage.py` pour utiliser `config.settings.development` par défaut. Si Django indique que ce module ou une configuration nécessaire est introuvable, inspecter le package `config/settings/` de la branche sélectionnée et suivre sa configuration réelle. Ne pas inventer de variables d'environnement ou de fichiers de configuration absents.

Si une migration est nécessaire, consulter d'abord les applications et migrations existantes. Les fonctionnalités de démonstration décrites dans ce README ne signifient pas qu'un modèle métier ou une migration produit/commande existe déjà.

## 8. Commandes de développement

```bash
# Vérifier la configuration Django
python manage.py check

# Démarrer le serveur local
python manage.py runserver

# Lister les routes/configurations disponibles selon le projet
python manage.py help
```

Aucune suite de tests automatisés complète n'a été confirmée pendant la rédaction de ce document. Avant de déclarer une modification validée, exécuter les contrôles disponibles dans la branche et effectuer des vérifications manuelles des pages concernées. Ajouter des tests Django/JavaScript à mesure que la logique métier est implémentée.

## 9. Configuration et déploiement

Le projet utilise les mécanismes standards de Django et un fichier `requirements.txt`. La configuration réelle de déploiement doit être vérifiée dans `config/settings/` et dans l'environnement cible.

Avant une mise en production :

1. utiliser des paramètres de production distincts de ceux du développement ;
2. définir une `SECRET_KEY` forte via une variable d'environnement ou un gestionnaire de secrets ;
3. désactiver `DEBUG` ;
4. configurer précisément `ALLOWED_HOSTS), HTTPS, cookies sécurisés et protections CSRF ;
5. configurer la base de données, les migrations, les fichiers statiques et les médias ;
6. définir une politique de logs, sauvegardes, surveillance et gestion des erreurs ;
7. ne jamais committer de secrets, tokens, clés de paiement ou données personnelles ;
8. tester le parcours complet dans un environnement de préproduction avant d'ouvrir la boutique.

Ne pas considérer le serveur `runserver` comme un serveur de production. La configuration d'hébergement ne peut pas être déduite uniquement des vues front-end.

## 10. Sécurité, accessibilité et qualité

### Sécurité

- Conserver l'échappement automatique des templates Django et ne pas injecter de HTML non fiable.
- Garder la protection CSRF pour les formulaires qui effectuent des actions côté serveur.
- Valider les données côté serveur dès que les formulaires sont reliés à une logique métier.
- Calculer les prix, remises, frais et taxes sur le serveur.
- Ne jamais stocker de données de carte bancaire dans l'application ; déléguer les données sensibles à un prestataire de paiement conforme.
- Vérifier les signatures des webhooks de paiement avant de marquer une commande comme payée.
- Ne pas exposer les secrets dans les fichiers statiques ou dans le JavaScript client.

### Accessibilité et UX

- Préserver les libellés accessibles, textes alternatifs, attributs ARIA utiles et états de focus.
- Garder une navigation utilisable au clavier, y compris dans les modales et visionneuses.
- Respecter `prefers-reduced-motion` pour les animations lorsque c'est pertinent.
- Vérifier les contrastes, les tailles tactiles et le comportement responsive sur de vrais formats mobiles.
- Éviter le lancement automatique de médias qui perturbe la navigation ou consomme inutilement des données.
- Tester les erreurs, états vides, chargements et interactions, pas seulement le parcours idéal.

## 11. Feuille de route technique

Cette liste décrit les évolutions nécessaires pour passer d'un prototype UI à une boutique opérationnelle ; elle ne signifie pas que ces fonctions sont déjà implémentées.

1. **Modèle de données :** produits, variantes, médias, prix, promotions, inventaire, avis et catégories.
2. **Catalogue serveur :** remplacer les listes de démonstration par des requêtes Django et une pagination adaptée.
3. **Panier fiable :** définir la stratégie de persistance et recalculer toutes les valeurs côté serveur.
4. **Checkout :** validation des coordonnées, adresse, pays, modes de livraison, taxes et totaux côté serveur.
5. **Commandes :** cycle de vie, identifiants, statuts, confirmations, emails et journal d'audit.
6. **Paiement :** intégrer un prestataire, gérer l'authentification forte si nécessaire et confirmer le paiement via webhook.
7. **Comptes et données personnelles :** définir les besoins d'authentification, de conservation, d'accès et de suppression.
8. **Newsletter et promotions :** relier les formulaires à des services réels avec consentement et validation.
9. **Qualité :** tests unitaires, tests de vues, tests de parcours et contrôles de régression visuelle.
10. **Production :** configuration sécurisée, observabilité, sauvegardes, performance et accessibilité.

## 12. Guide de travail pour une IA ou un nouveau contributeur

Cette section est destinée à tout agent de programmation qui reçoit le dépôt comme contexte.

### Avant de modifier le code

1. Identifier la branche réellement checkoutée et examiner `git status`.
2. Lire ce README, puis ouvrir les fichiers source concernés dans **la branche actuelle**.
3. Comparer `main` et `developpement` si la demande touche une fonctionnalité présente dans une seule branche.
4. Lire le template, le CSS et le JavaScript associés ensemble : beaucoup de composants dépendent de classes CSS, d'identifiants HTML et d'attributs `data-*`.
5. Rechercher les points d'entrée, les inclusions de templates, les noms d'URL et les scripts chargés avant de créer un doublon.
6. Vérifier si une donnée est réelle, statique, simulée ou fournie par le navigateur.

### Règles de modification

- Faire des changements ciblés et cohérents avec l'architecture existante ; éviter les réécritures globales non demandées.
- Ne pas supprimer des fonctionnalités existantes simplement pour simplifier une implémentation.
- Ne pas modifier les contrats entre HTML, CSS et JavaScript sans mettre à jour toutes les parties concernées.
- Conserver la compatibilité mobile et les comportements clavier/lecteur d'écran.
- Préserver les noms de routes et les espaces de noms Django sauf nécessité clairement justifiée.
- Ne pas ajouter de dépendance sans raison technique et sans mettre à jour les fichiers de dépendances.
- Ne jamais prétendre qu'un paiement, une commande, une newsletter ou une persistance est opérationnel si le code ne le démontre pas.
- Ne pas inventer de variables d'environnement, de modèles, d'API ou de fichiers qui n'existent pas ; inspecter d'abord le dépôt.
- Pour les stories/reels, consulter `home/static/js/community-media.js` et les règles de `home/static/css/home.css` sur `developpement` avant de modifier les interactions.
- Après modification, contrôler le diff, lancer `python manage.py check` si possible, puis tester les pages et tailles d'écran affectées.
- Dans le compte rendu final, lister les fichiers modifiés, le comportement obtenu, les vérifications effectuées et les limites restantes. Distinguer clairement les tests réellement exécutés des tests seulement recommandés.

### Comment comprendre une fonctionnalité

Pour suivre une page, partir de `config/urls.py`, puis suivre l'URL vers `<app>/urls.py`, la vue Python, le template rendu, les feuilles CSS et les scripts JavaScript associés. Pour les composants globaux, commencer par `templates/base.html`, `static/css/base.css` et `static/js/base.js`.

## 13. Règles de contribution Git

La convention de travail recommandée est :

- `main` : branche de référence stable ;
- `developpement` : intégration et validation des évolutions en cours.

Avant de commencer :

```bash
git status
git branch --show-current
git log --oneline -8
```

Pour examiner les différences :

```bash
git diff main...developpement
```

Après une modification :

```bash
python manage.py check
git diff --check
git diff
```

Créer des commits petits et descriptifs. Ne pas pousser de secrets, fichiers de base de données locaux, environnements virtuels ou fichiers générés. Avant de fusionner vers `main`, revoir les différences, tester les pages affectées et confirmer que le comportement de démonstration est bien identifié comme tel.

---

## État du document

Ce README documente le code inspecté dans les branches `main` et `developpement` au moment de sa rédaction. Le code du dépôt reste la source de vérité : si ce document et l'implémentation divergent, inspecter la branche concernée, confirmer les différences et mettre à jour cette documentation.

---

# Backend catalogue — branche `developpement-backend`

Cette section documente la première phase de connexion du catalogue à la base de données. Elle complète le README existant sans remplacer l'historique ni les consignes générales du dépôt.

## 1. Périmètre de cette phase

Le code a été développé dans la branche `developpement-backend`, créée à partir de `developpement`. La branche `developpement` n'est pas modifiée par ce travail.

### Inclus
- Modèles Django pour les catégories, produits, variantes, médias, contenus de fiche produit, offres groupées et avis.
- Enregistrement des modèles dans l'administration Django.
- Chargement serveur des catégories et des nouveautés de la page d'accueil.
- Alimentation du catalogue par des données issues de la base, transmises au JavaScript avec le filtre Django `json_script`.
- Chargement de la fiche produit depuis le produit publié demandé par son slug.
- Tests automatisés de base sur les modèles et les vues publiques.
- Migration initiale `product/migrations/0001_initial.py`.

### Explicitement non inclus
- La section **« Notre sélection signature »** de l'accueil : elle a été laissée telle quelle et reste statique dans cette phase.
- La section de produits associés « Vous aimerez aussi » de la fiche produit : elle reste hors périmètre ; aucune liste de produits fictifs n'est injectée.
- Les commandes, le panier serveur, le paiement, les promotions globales, les frais de livraison réels et la réservation de stock au moment de la commande.
- L'envoi de fichiers médias vers le serveur : les modèles stockent actuellement des URL HTTPS. Les fichiers doivent être hébergés sur un CDN ou un stockage adapté.
- Des données commerciales de démonstration : aucune fiche produit ou catégorie réelle n'est créée automatiquement.

## 2. Modèle de données

Les modèles sont définis dans `product/models.py`.

| Modèle | Rôle |
|---|---|
| `Category` | Catégorie visible ou masquée, slug, description, image et ordre d'affichage. |
| `Product` | Identité, descriptions, catégorie, dimensions, matière, indicateurs éditoriaux, publication et SEO. |
| `ProductVariant` | SKU, couleur, prix, prix de référence éventuel, stock et activation. |
| `ProductMedia` | Image ou vidéo commune au produit ou rattachée à une variante, texte alternatif, vignette et ordre. |
| `ProductReason` | Arguments de vente de la fiche produit. |
| `ProductContentItem` | Éléments qui peuvent ou non rentrer dans le sac. |
| `ProductCraftDetail` | Détails de fabrication avec description et image facultative. |
| `ProductUsage` | Situations d'utilisation avec image et texte alternatif. |
| `ProductFAQ` | Questions fréquentes et réponses. |
| `Review` | Avis avec note de 1 à 5, modération et adresse e-mail privée facultative. |
| `ProductOffer` | Offre groupée affichée sur la fiche principale et son prix final configuré. |
| `ProductOfferItem` | Produit, variante fixe ou variante choisie sur la fiche, et quantité dans l'offre. |

### Prix et stock

- Le prix et le stock appartiennent à `ProductVariant`, pas à `Product`.
- Chaque SKU doit être unique.
- Le prix est un `DecimalField`, pas un flottant.
- Le prix de référence est facultatif et, s'il est renseigné, doit être supérieur au prix de vente.
- Les variantes avec stock nul ne doivent pas être considérées comme disponibles pour une future commande. La validation finale du stock devra être réalisée côté serveur lors de l'implémentation des commandes.
- Les contraintes de base de données protègent les quantités et les montants non négatifs ainsi que certaines unicités.

### Publication publique

Une fiche n'est visible par les vues publiques que si :
1. le produit est actif ;
2. sa catégorie est active ;
3. sa date de publication est vide ou n'est pas dans le futur ;
4. il existe au moins une variante active ;
5. il existe au moins une image commune au produit (média de type `image`, sans variante).

Ce dernier point évite de publier un produit sans image de catalogue. Un produit sans variante active ou sans image commune ne sera pas rendu comme fiche publique, même si son indicateur `is_active` est activé.

### Médias

- Les URL de médias publics doivent utiliser HTTPS.
- Une image exige un texte alternatif ; une vidéo exige une URL de vignette.
- Une variante associée à un média doit appartenir au même produit.
- Les contraintes permettent au plus un média principal commun par produit et un média principal par variante.
- Les médias sont ordonnés avec le média principal en premier.
- Cette phase utilise des URL et ne gère pas le téléversement de fichiers. Le stockage et l'analyse de fichiers envoyés par des utilisateurs nécessiteront une conception distincte.

### Offres groupées

Pour chaque ligne de `ProductOfferItem` :
- le produit principal peut utiliser la variante choisie par le client sur la fiche ; dans ce cas, `use_selected_variant=True` et la variante fixe reste vide ;
- les produits complémentaires doivent avoir une variante fixe appartenant au produit indiqué ;
- la quantité doit être au moins égale à 1.

Chaque offre publique doit inclure au moins une ligne utilisant la variante choisie sur la fiche. Les formulaires d'administration valident ces relations, et la vue de fiche filtre également les offres incomplètes, incohérentes ou dont un composant ne dispose pas du stock nécessaire avant de les exposer. Le prix final du lot est celui configuré dans `ProductOffer.price`. La comparaison et le pourcentage d'économie sont calculés à partir des prix de vente actuels des composants, et non de prix barrés qui pourraient déjà intégrer une remise. La référence tient compte de la variante sélectionnée lorsque le lot contient le produit principal.

Le champ `display_delivery_label` est uniquement une mention éditoriale. Il ne calcule ni ne garantit des frais de port.

### Avis

Seuls les avis dont `is_approved=True` alimentent la note, la répartition des étoiles et les commentaires publics. L'adresse e-mail de l'auteur n'est pas transmise au template.

## Téléversement des images (développement et production)

Les images du catalogue peuvent être téléversées directement depuis Django Admin. Les fichiers sont enregistrés automatiquement sous `MEDIA_ROOT`, avec des sous-dossiers dédiés :
- catégories : `media/categories/AAAA/MM/` ;
- images produit et variantes : `media/products/AAAA/MM/` ;
- détails de fabrication : `media/products/craft/AAAA/MM/` ;
- images d'usage : `media/products/usage/AAAA/MM/`.

En développement, `MEDIA_ROOT` pointe par défaut vers le dossier `media/` à la racine du projet. Quand `DEBUG=True`, `config/urls.py` expose les fichiers médias via `/media/` pour faciliter les tests locaux.

En production, `DEBUG=False` : Django ne sert volontairement pas les fichiers médias lui-même. Le serveur web doit rendre le dossier `MEDIA_ROOT` accessible sous le préfixe `MEDIA_URL=/media/`. Le chemin peut être configuré avec la variable d'environnement `DJANGO_MEDIA_ROOT`. Sur cPanel/o2switch, définis-la vers un dossier réellement servi publiquement par le domaine, ou configure un lien/routage web vers ce dossier. Vérifie les permissions et ne rends jamais accessibles les fichiers privés ou les fichiers de configuration. Ne suppose pas qu'un dossier situé dans la racine Python est automatiquement public. Teste une URL d'image après déploiement.

Les champs d'URL externe sont conservés comme solution de repli pour les médias déjà hébergés ailleurs. Pour une image locale, utiliser le champ de téléversement plutôt que saisir une URL. Les fichiers du dossier `media/` sont exclus de Git et doivent être sauvegardés séparément de la base de données.

Pour activer les téléversements d'images, installer les dépendances puis appliquer les migrations :

```bash
python -m pip install -r requirements.txt
python manage.py migrate --settings=config.settings.development
```

## 3. Administration et ajout des premiers produits

Les modèles sont disponibles dans l'administration Django :
- catégories et produits ;
- variantes et médias en ligne sur la fiche produit ;
- arguments, éléments de capacité, détails de fabrication, usages, FAQ et offres en ligne ;
- lignes d'offres groupées et avis dans leurs écrans d'administration dédiés.

Pour préparer une fiche :
1. Créer et activer une catégorie.
2. Créer le produit avec son slug et sa catégorie. Laisser le produit inactif pendant la préparation.
3. Créer au moins une variante active avec un SKU unique, un prix et un stock.
4. Dans la ligne « Médias », téléverser une image depuis l'ordinateur (le fichier sera stocké dans `media/products/`). Renseigner un texte alternatif et définir le média principal si nécessaire. Les URL externes restent facultatives.
5. Compléter les contenus de la fiche et, si besoin, les offres et leurs lignes.
6. Renseigner le titre et la description SEO, puis activer le produit et définir sa date de publication si nécessaire.
7. Vérifier la fiche, le catalogue et la page d'accueil avant de préparer toute mise en production.

Un produit est une nouveauté de la page d'accueil uniquement si `is_new=True`. La section « Nos nouveautés » affiche au maximum quatre produits publiables portant cet indicateur. Les catégories de l'accueil et les catégories de filtres du catalogue proviennent des catégories actives.

## 4. Transmission des données au frontend

### Page d'accueil

`home/views.py` transmet :
- les catégories actives, triées par position puis nom ;
- les produits publiables avec `is_new=True`, limités aux quatre plus récents, avec variantes actives et médias communs préchargés.

Les boucles Django utilisent les valeurs du modèle : titre, catégorie, prix, prix de référence, stock et image. Les cartes ne sont plus alimentées par les anciennes valeurs de démonstration de la section « Nouveautés ».

La section « Notre sélection signature » n'a pas été reliée à ces données et n'a pas été modifiée.

### Catalogue

`shop/views.py` charge les produits publiables, leur catégorie, leurs variantes actives, leurs médias et leurs avis approuvés. Les catégories et les métadonnées de couleurs sont aussi chargées depuis la base.

Le contexte `catalog_data` est transmis dans `shop/templates/catalog.html` via `json_script`. `shop/static/js/shop.js` lit cet objet au lieu de contenir sa propre liste de produits fictifs. Le JavaScript conserve les filtres, le tri, la pagination d'affichage, les favoris et les interactions visuelles déjà présents. Les filtres par catégorie utilisent désormais les slugs réellement configurés dans l'administration.

### Fiche produit

`product/views.py` retrouve le produit par son slug et charge les variantes, les médias, les arguments, les éléments de capacité, les dimensions, les détails de fabrication, les usages, les FAQ, les offres et les avis approuvés. Un produit inactif, non encore publiable ou introuvable renvoie une réponse 404.

Le template existant `product/templates/product.html` a été conservé comme structure de présentation. Les données fictives de `product/views.py` ont été remplacées par les données de la base. Les prix des variantes sont synchronisés avec le choix de couleur et la galerie filtre les médias selon la variante sélectionnée. Le prix final d'une offre reste configuré dans l'offre ; son prix de référence affiché suit la variante choisie et la quantité de produit principal incluse. Les images de la section d'usage utilisent les URL configurées dans les données. Les éléments sans données ne sont pas inventés.

Les données structurées de la fiche sont insérées avec `json_script`, puis lues par `product/static/js/product.js`. Les templates Django conservent leur échappement automatique.

## 5. Sécurité et limites actuelles

Mesures mises en place dans cette phase :
- accès public limité aux produits publiables ;
- ORM Django et filtres côté serveur ;
- modèles et contraintes de base de données pour les identifiants, montants, stocks et relations pertinentes ;
- validation des variantes et médias dans les formulaires d'administration ;
- contrôle défensif des lignes d'offre avant leur affichage ;
- URL HTTPS pour les médias externes ;
- avis en attente exclus des données publiques ;
- transfert de données vers JavaScript avec `json_script`, sans construire un bloc JavaScript à partir de chaînes interpolées dans le HTML.

**Limite importante :** le panier reste celui du prototype frontend et utilise toujours le stockage local du navigateur. Le prix affiché ou conservé par le navigateur n'est pas une preuve de prix ni de stock. Lors de la prochaine phase panier/commande, le serveur devra recalculer les montants depuis les variantes en base, revalider les quantités et les offres, vérifier le stock et traiter les mises à jour de stock de manière atomique. Aucun paiement ni commande réelle n'est implémenté ici.

## 6. Migration, contrôles et tests

Après avoir récupéré la branche, installer les dépendances :

```bash
python -m pip install -r requirements.txt
```

Les paramètres de développement utilisent `DJANGO_SECRET_KEY`. Définir cette variable dans l'environnement local ou dans le fichier `.env` non versionné, puis exécuter :

```bash
python manage.py check --settings=config.settings.development
python manage.py makemigrations --check --dry-run --settings=config.settings.development
python manage.py migrate --settings=config.settings.development
python manage.py test product --settings=config.settings.development
```

Pour administrer le catalogue localement :

```bash
python manage.py createsuperuser --settings=config.settings.development
python manage.py runserver --settings=config.settings.development
```

Ces commandes doivent être exécutées dans l'environnement local du projet. La migration initiale a été ajoutée au dépôt, mais elle n'a pas été appliquée à une base de production dans le cadre de cette modification. Les tests ont été ajoutés au dépôt ; ils doivent être exécutés dans un environnement disposant des dépendances du projet avant de considérer la phase comme validée.

## 7. Fichiers principaux de cette phase

- `product/models.py` — modèles, téléversements d'images et règles de validation.
- `product/admin.py` — administration du catalogue.
- `product/migrations/0001_initial.py` — schéma initial de la base.
- `product/selectors.py` — règles partagées de publication et sérialisation des cartes catalogue.
- `product/views.py` — données de fiche et exposition des données publiées.
- `product/tests.py` — tests de modèle et de vues.
- `home/views.py` et `home/templates/home.html` — catégories et nouveautés dynamiques, sans changement de la sélection signature.
- `shop/views.py`, `shop/templates/catalog.html` et `shop/static/js/shop.js` — catalogue dynamique et filtres fondés sur les catégories configurées.
- `product/templates/product.html` et `product/static/js/product.js` — liaison de la fiche produit aux variantes et offres réelles.
- `requirements.txt` — dépendances, dont `python-dotenv` et Pillow pour les téléversements d'images.
