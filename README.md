# E-commerce Website — My Line Collection

> Application e-commerce Django orientée mode, sacs à main et accessoires, avec une interface éditoriale premium, responsive et pensée en priorité pour le mobile.

**Dépôt :** [MAHDIghr/E-commerce-Website](https://github.com/MAHDIghr/E-commerce-Website)  
**Branches de référence :** `main` et `developpement`  
**Langue actuelle de l'interface :** français  
**État fonctionnel :** prototype front-end servi par Django ; les données commerciales et le paiement restent à connecter à un véritable back-end.

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
- Données de démonstration pour la fiche produit et le checkout.
- Dans `developpement`, améliorations récentes de la zone communautaire avec stories/reels et une visionneuse média.

### Ce qui n'est pas encore un véritable système e-commerce

Les vues de catalogue, produit et checkout décrivent explicitement une phase **front-end only**. Le checkout utilise des données fictives ; le code de la page précise qu'aucune commande, aucun paiement ni calcul métier réel n'est exécuté côté serveur. Les données de produit sont construites dans le code et sont prévues pour être remplacées par des modèles métier.

Ne pas supposer que les fonctionnalités visuelles suivantes sont connectées à un service réel sans vérifier le code concerné :

- base de données de produits, variantes, inventaire ou prix ;
- comptes clients et authentification de boutique ;
- persistance serveur du panier ;
- application effective de codes promotionnels ;
- calcul serveur des taxes, frais de port et totaux ;
- création, suivi ou confirmation de commande ;
- paiement par carte, Stripe, PayPal ou autre prestataire ;
- envoi réel de newsletter ;
- avis clients vérifiés, preuve sociale ou statistiques commerciales.

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