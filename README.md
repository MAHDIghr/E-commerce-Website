# My Line Collection — Site e-commerce Django

> Boutique en ligne de sacs à main et d'accessoires féminins. Cette branche connecte le catalogue à la base de données Django et permet de téléverser les images depuis l'administration. Le checkout, les commandes et les paiements réels restent hors périmètre.

- **Dépôt :** https://github.com/MAHDIghr/E-commerce-Website
- **Branche documentée :** `developpement-backend`
- **Langue de l'interface :** français
- **Framework :** Django `6.1.1` (voir `requirements.txt`)
- **Base locale par défaut :** SQLite
- **Fichiers statiques :** CSS, JavaScript et ressources du site
- **Fichiers médias téléversés :** dossier `media/` en local par défaut ; chemin configurable avec `DJANGO_MEDIA_ROOT`

---

## Sommaire

1. [Objectif et état du projet](#1-objectif-et-état-du-projet)
2. [Fonctionnalités et limites](#2-fonctionnalités-et-limites)
3. [Architecture du dépôt](#3-architecture-du-dépôt)
4. [Routes du site](#4-routes-du-site)
5. [Architecture Django et données](#5-architecture-django-et-données)
6. [Modèle de données du catalogue](#6-modèle-de-données-du-catalogue)
7. [Installation locale](#7-installation-locale)
8. [Commandes de développement et de test](#8-commandes-de-développement-et-de-test)
9. [Gérer le catalogue dans Django Admin](#9-gérer-le-catalogue-dans-django-admin)
10. [Téléverser et stocker les images](#10-téléverser-et-stocker-les-images)
11. [Configuration des fichiers statiques et médias](#11-configuration-des-fichiers-statiques-et-médias)
12. [Déploiement en production sur cPanel / o2switch](#12-déploiement-en-production-sur-cpanel--o2switch)
13. [Sécurité et bonnes pratiques](#13-sécurité-et-bonnes-pratiques)
14. [État des tests et checklist de recette](#14-état-des-tests-et-checklist-de-recette)
15. [Périmètre restant et feuille de route](#15-périmètre-restant-et-feuille-de-route)
16. [Règles de travail et de contribution](#16-règles-de-travail-et-de-contribution)

---

## 1. Objectif et état du projet

My Line Collection est une boutique en ligne orientée sacs à main et accessoires féminins, avec une interface éditoriale premium et une conception mobile-first. Django rend les pages et expose les données du catalogue aux templates ; CSS et JavaScript gèrent l'affichage et les interactions côté navigateur.

La branche `developpement-backend` introduit une source de données persistante pour les catégories, produits, variantes, médias, offres et contenus éditoriaux des fiches produits. Elle permet également de téléverser des images depuis Django Admin, au lieu d'imposer la saisie d'une URL pour chaque image.

### Principes de conception

- **Mobile-first :** les pages et interactions doivent rester utilisables sur téléphone.
- **Catalogue administrable :** les données éditoriales du catalogue sont gérées via les modèles Django et Django Admin.
- **Médias organisés :** les fichiers envoyés par l'administration sont rangés automatiquement dans des sous-dossiers de `MEDIA_ROOT`.
- **Prix explicites :** le prix est porté exclusivement par une offre commerciale ; les variantes décrivent la couleur et le stock.
- **Publication contrôlée :** seuls les produits actifs et associés à une catégorie active sont éligibles à l'affichage public, selon les sélecteurs utilisés.
- **Pas de fausse promesse métier :** une interface de panier ou de checkout ne signifie pas qu'une commande ou un paiement réel est implémenté.

Les contenus, avis, prix, promotions, compteurs ou éléments de preuve sociale présents à des fins de démonstration doivent être vérifiés et remplacés par des données réelles avant toute ouverture commerciale.

## 2. Fonctionnalités et limites

### Fonctionnalités raccordées aux modèles Django

- Catégories actives chargées depuis la base.
- Produits, catégories et variantes gérés dans Django Admin.
- Page d'accueil alimentée par les catégories actives et les nouveautés.
- Catalogue alimenté par les données du catalogue.
- Fiche produit résolue par slug.
- Médias associés à un produit et, si nécessaire, à une variante.
- Offres groupées et éléments qui composent ces offres.
- Contenus éditoriaux : arguments, éléments de capacité, détails de fabrication, situations d'usage et FAQ.
- Avis stockés dans la base ; seuls les avis approuvés sont récupérés par la vue de fiche produit.
- Téléversement local d'images via `ImageField`, avec une organisation automatique des fichiers.
- Compatibilité conservée avec certaines URL externes de médias.
- Migration de base de données ajoutant les champs d'images téléversées.

### Fonctionnalités qui ne doivent pas être considérées comme un système métier terminé

Dans cette branche, les éléments suivants ne sont pas un système e-commerce complet tant qu'une implémentation serveur dédiée n'a pas été développée et vérifiée :

- réservation ou décrémentation transactionnelle du stock au moment de la commande ;
- création et gestion des commandes ;
- calcul serveur des taxes, frais de livraison, réductions et totaux ;
- application sécurisée de codes promotionnels ;
- intégration et confirmation de paiement ;
- remboursements, annulations et notifications de commande ;
- authentification et espace client complets ;
- traitement réel des abonnements newsletter ;
- collecte et vérification des avis par de vrais clients.

**Règle essentielle :** le navigateur est contrôlé par l'utilisateur. Les prix, quantités, remises et totaux envoyés par JavaScript ne doivent jamais être considérés comme fiables. Lorsqu'un vrai checkout sera développé, le serveur devra recharger les produits et variantes depuis la base, recalculer les montants, vérifier les stocks, créer les commandes et vérifier les notifications du prestataire de paiement.

## 3. Architecture du dépôt

L'arborescence ci-dessous présente les principaux éléments utiles pour travailler sur cette branche. Elle n'est pas exhaustive ; le dépôt GitHub reste la référence pour les fichiers effectivement présents.

```text
.
├── manage.py
├── requirements.txt
├── .gitignore
├── .env.example                 # si présent dans la branche
├── config/
│   ├── urls.py                  # routes principales
│   ├── wsgi.py
│   ├── asgi.py
│   └── settings/
│       ├── base.py              # paramètres partagés, DB, static et media
│       ├── development.py       # paramètres locaux
│       └── production.py        # paramètres de production
├── home/
│   ├── views.py
│   ├── urls.py
│   ├── templates/home.html
│   └── static/
├── shop/
│   ├── views.py
│   ├── urls.py
│   ├── templates/catalog.html
│   └── static/
├── product/
│   ├── models.py                # modèles du catalogue
│   ├── admin.py                 # formulaires d'administration
│   ├── selectors.py             # sélection et préparation des produits publiés
│   ├── views.py                 # fiche produit
│   ├── urls.py
│   ├── migrations/
│   ├── tests.py
│   ├── templates/product.html
│   ├── static/
│   └── ...
├── checkout/
│   ├── views.py
│   ├── urls.py
│   └── ...
├── templates/
│   ├── base.html
│   └── partials/
├── static/                      # ressources statiques partagées
├── staticfiles/                 # destination de collectstatic, générée
├── media/                       # fichiers téléversés en local, ignorés par Git
└── db.sqlite3                   # base locale, ignorée par Git
```

### Responsabilités principales

| Élément | Responsabilité |
|---|---|
| `config/settings/base.py` | Paramètres communs, SQLite, fichiers statiques et médias. |
| `config/settings/development.py` | Paramètres locaux, chargement du fichier `.env`, hôtes autorisés. |
| `config/settings/production.py` | Paramètres de production, secrets requis, HTTPS, cookies sécurisés et SMTP. |
| `home/` | Page d'accueil et sections éditoriales. |
| `shop/` | Vue de catalogue et préparation des catégories/produits à afficher. |
| `product/` | Modèles du catalogue, administration, sélection des produits et fiche produit. |
| `checkout/` | Interface de checkout de démonstration ; ne pas la confondre avec un système de commande opérationnel. |
| `templates/` | Layout partagé et composants communs. |
| `static/` et `<app>/static/` | Ressources statiques versionnées : CSS, JavaScript, icônes et images intégrées au code. |
| `media/` | Fichiers téléversés par les utilisateurs autorisés ; ils ne sont pas versionnés dans Git. |
| `staticfiles/` | Fichiers rassemblés par `collectstatic` pour le déploiement. |

## 4. Routes du site

Les routes principales sont déclarées dans `config/urls.py` et dans les URLconf des applications.

| URL | Fonction |
|---|---|
| `/` | Accueil. |
| `/boutique/` | Catalogue. |
| `/produit/` | Fiche par défaut, associée au slug `sac-cabas-camel`. |
| `/produit/<slug>/` | Fiche produit identifiée par son slug. |
| `/checkout/` | Interface de checkout de démonstration. |
| `/admin/` | Administration Django. |
| `/media/...` | URL publique des fichiers médias, sous réserve de la configuration du serveur et du mode d'exécution. |

Les routes d'images ne sont pas des vues de catalogue : elles servent des fichiers depuis le stockage média. En développement, Django ajoute une route de service des médias lorsque `DEBUG=True`. En production, le serveur web doit servir les fichiers de `MEDIA_ROOT` sous le préfixe `MEDIA_URL`.

## 5. Architecture Django et données

### Paramètres Django

Les paramètres sont séparés par environnement :

- `config.settings.base` : paramètres partagés, applications installées, middleware, templates, base de données, static et media.
- `config.settings.development` : charge les variables depuis `.env`, active le mode développement et utilise la console pour les e-mails.
- `config.settings.production` : exige les variables de configuration de production, désactive le mode debug, configure les cookies sécurisés et le backend SMTP.

Il faut toujours préciser le module de paramètres dans les commandes de gestion :

```powershell
python manage.py check --settings=config.settings.development
```

Ne mélange pas les variables locales et les secrets de production. La base configurée dans `base.py` est SQLite par défaut. Vérifie la stratégie de base de données avant de mettre le site en production, particulièrement si plusieurs requêtes concurrentes sont attendues.

### Catalogue piloté par la base

- `product/selectors.py` fournit le sélecteur commun des produits publiés et prépare les données des cartes.
- `home/views.py` récupère les catégories actives et les nouveautés depuis les modèles.
- `shop/views.py` récupère les catégories et les données produit pour le catalogue.
- `product/views.py` récupère une fiche publiée à partir de son slug, prépare les variantes, les médias, les offres, les contenus et les avis approuvés.
- Les templates utilisent les données préparées par les vues. Lorsqu'un fichier image est téléversé, l'URL est obtenue depuis le champ Django `ImageField`; l'image n'est pas codée en dur dans le template.

### Publication d'un produit

Le modèle `Product` comprend notamment `is_active`, `is_new`, `is_best_seller` et `published_at`. Le sélecteur public filtre les produits actifs et ceux dont la catégorie est active, avec des variantes actives et des médias image répondant aux conditions du sélecteur. La propriété `is_published` tient compte de `published_at`, mais il faut se référer au sélecteur utilisé par chaque page pour connaître exactement ses conditions d'affichage.

Pour qu'un produit soit visible, renseigne correctement sa catégorie, ses variantes et son média principal, puis active sa publication. Un produit incomplet peut être enregistré dans l'administration mais ne pas apparaître dans les listes publiques.

## 6. Modèle de données du catalogue

Les modèles sont définis dans `product/models.py`. Les champs exacts du code constituent la référence en cas de divergence avec ce résumé.

| Modèle | Rôle |
|---|---|
| `Category` | Nom, slug, description, image téléversée ou URL externe, texte alternatif, activation et ordre. |
| `Product` | Identité, catégorie, descriptions, matière, dimensions, attributs de publication et métadonnées SEO. |
| `ProductVariant` | Référence interne unique, couleur, stock, activation et ordre d'affichage. Aucun prix n'est enregistré sur une variante. |
| `ProductMedia` | Image ou vidéo associée au produit, éventuellement à une variante, texte alternatif, ordre et média principal. |
| `ProductReason` | Arguments éditoriaux en faveur du produit. |
| `ProductContentItem` | Éléments de capacité et indication qu'ils rentrent dans le produit. |
| `ProductCraftDetail` | Détails de fabrication, description et image. |
| `ProductUsage` | Situations d'usage illustrées par une image. |
| `ProductFAQ` | Questions et réponses propres au produit. |
| `ProductOffer` | Offre commerciale configurée pour le produit. |
| `ProductOfferItem` | Produit/variante et quantité composant une offre. |
| `Review` | Avis rattaché à un produit, note, commentaire, état d’approbation et sélection facultative pour l’accueil. |

### Prix et variantes

- Le prix et le stock sont portés par `ProductVariant`, pas par `Product`.
- Le SKU doit être unique.
- Le prix de vente doit être positif ou nul.
- Le prix de vente est défini par `ProductOffer.price` ; les couleurs n'ont pas de prix individuel.
- Le stock est un entier positif ou nul.
- Les variantes ont un ordre d'affichage et peuvent être désactivées.
- La couleur peut être décrite par un nom, un slug et un code hexadécimal.

Les contraintes et validations Django sont des protections utiles, mais il faut conserver une validation serveur stricte dans toute future logique de panier et de commande. `Model.clean()` n'est pas automatiquement exécuté par chaque appel à `save()` ; les services métier devront appeler explicitement la validation nécessaire et s'appuyer sur les contraintes de base de données.

### Médias

- `Category.image` : image téléversée de catégorie.
- `ProductMedia.image` : image téléversée du produit ou d'une variante.
- `ProductCraftDetail.image` : image téléversée d'un détail de fabrication.
- `ProductUsage.image` : image téléversée d'une situation d'usage.
- Les champs URL associés restent disponibles pour des médias externes. Les URL renseignées dans les modèles concernés sont soumises à une validation HTTPS via `clean()`.
- Pour les vidéos, `ProductMedia.source_url` représente l'URL du média et `poster_url` l'URL de la vignette.
- Un texte alternatif descriptif doit être renseigné pour les images du produit.
- Le champ `upload_to` détermine le sous-dossier et le classement par année/mois. Django crée le chemin nécessaire lors de l'enregistrement.

### Offres groupées

Une offre possède un prix affiché et des éléments associés. Le produit principal peut utiliser la variante choisie sur la fiche ; les autres éléments utilisent une variante fixe. Les validations du modèle contrôlent la cohérence de ces références.

Le libellé de livraison d'une offre est éditorial : il ne calcule pas les frais de livraison réels. Le checkout et les paiements ne doivent pas être considérés comme fonctionnels simplement parce que les offres sont configurables.

### Avis

Les avis sont toujours rattachés à un produit via `Review.product`. Les visiteurs peuvent déposer un avis depuis la fiche du produit ; les champs publics sont le nom affiché, la note et le commentaire. L’avis est créé avec `is_approved=False` et `is_featured=False` : il n’apparaît nulle part publiquement avant modération. L’administration permet de modifier ou supprimer les avis, de les approuver et de choisir lesquels apparaissent sur l’accueil. La contrainte `featured_review_must_be_approved` empêche de mettre en avant un avis non approuvé. L’e-mail éventuel de l’auteur reste privé et n’est pas collecté par le formulaire public.

## 7. Installation locale

Les commandes suivantes sont prévues pour Windows PowerShell. Depuis macOS/Linux, adapte l'activation de l'environnement virtuel.

### Prérequis

- Git.
- Python compatible avec la version de Django déclarée dans `requirements.txt`. Python 3.12 est un choix pratique si cette version est installée localement.
- Accès au dépôt GitHub.

Vérifie les outils :

```powershell
git --version
py --version
```

### Cloner le dépôt (première installation)

```powershell
git clone https://github.com/MAHDIghr/E-commerce-Website.git
cd E-commerce-Website
git fetch origin
git switch --track -c developpement-backend origin/developpement-backend
```

Si le dépôt existe déjà sur l'ordinateur, ne le clone pas une seconde fois : ouvre le dossier existant puis récupère la branche :

```powershell
git status
git fetch origin
git switch developpement-backend
git pull origin developpement-backend
```

Si Git indique que la branche locale n'existe pas, utilise la commande `git switch --track -c developpement-backend origin/developpement-backend`. Si `git status` montre des modifications locales, examine-les avant de changer de branche ; ne les écrase pas avec une commande forcée.

### Créer et activer un environnement virtuel

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Si PowerShell bloque l'activation, l'autorisation temporaire pour le terminal courant peut être utilisée :

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Installe les dépendances :

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m django --version
```

La version Django attendue selon le fichier de dépendances est `6.1.1`. Pillow est requis pour traiter les champs d'images.

### Configurer les variables locales

La configuration de développement charge le fichier `.env` à la racine du dépôt et exige `DJANGO_SECRET_KEY`. Génère une clé :

```powershell
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Crée un fichier `.env` à la racine :

```dotenv
DJANGO_SECRET_KEY=REMPLACER_PAR_LA_CLE_GENEREE
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
```

Remplace la valeur par la clé générée. Ne committe jamais le fichier `.env` ni les secrets. Le fichier `.gitignore` exclut `.env`, la base SQLite, `media/` et `staticfiles/`.

### Vérifier, migrer et lancer

```powershell
python manage.py check --settings=config.settings.development
python manage.py makemigrations --check --dry-run --settings=config.settings.development
python manage.py migrate --settings=config.settings.development
python manage.py createsuperuser --settings=config.settings.development
python manage.py runserver --settings=config.settings.development
```

Ouvre ensuite :

- Accueil : http://127.0.0.1:8000/
- Catalogue : http://127.0.0.1:8000/boutique/
- Fiche par défaut : http://127.0.0.1:8000/produit/
- Administration : http://127.0.0.1:8000/admin/

La base de données et les médias locaux sont créés dans l'environnement local. Ne copie pas la base de production sur un environnement de test sans avoir vérifié qu'elle ne contient pas de données sensibles.

## 8. Commandes de développement et de test

Toutes les commandes ci-dessous doivent être lancées depuis le dossier contenant `manage.py`, avec l'environnement virtuel activé et les paramètres adaptés.

### Vérifications Django

```powershell
python manage.py check --settings=config.settings.development
python manage.py makemigrations --check --dry-run --settings=config.settings.development
python manage.py showmigrations --settings=config.settings.development
```

- `check` repère des problèmes de configuration Django.
- `makemigrations --check --dry-run` indique si les modèles divergent des migrations existantes sans générer de fichier.
- `showmigrations` affiche l'état des migrations.

### Base de données

```powershell
python manage.py migrate --settings=config.settings.development
```

Ne supprime pas `db.sqlite3` pour résoudre une erreur de migration. Sauvegarde les données locales utiles et examine d'abord le message d'erreur.

### Tests

```powershell
python manage.py test product --settings=config.settings.development
python manage.py test --settings=config.settings.development
```

La suite `product` contient des tests de modèles, de vues et de stockage d'images. Exécute-la avant d'intégrer de nouvelles modifications. La commande globale peut également lancer des tests d'autres applications si elles en possèdent.

**État des tests :** la présence de tests dans le dépôt ne signifie pas qu'ils ont été exécutés avec succès sur chaque commit. En cas d'échec, conserve la sortie complète et corrige la cause avant de considérer le changement validé.

### Fichiers statiques

```powershell
python manage.py collectstatic --noinput --settings=config.settings.development
```

Cette commande collecte les fichiers statiques vers `STATIC_ROOT` (par défaut `staticfiles/`). Elle ne collecte pas les médias téléversés dans `media/`.

### Diagnostic de configuration

```powershell
python manage.py diffsettings --settings=config.settings.development
```

Ne publie pas la sortie complète si elle contient des valeurs confidentielles.

## 9. Gérer le catalogue dans Django Admin

### Accéder à l'administration

1. Lancer le serveur avec les paramètres de développement.
2. Ouvrir http://127.0.0.1:8000/admin/.
3. Se connecter avec un compte créé par `createsuperuser`.

### Ordre conseillé pour créer un produit

1. **Créer une catégorie** et choisir son nom, son slug, son ordre, son état actif et son image si nécessaire.
2. **Créer un produit** et renseigner sa catégorie, son nom, son slug, ses descriptions, sa matière et ses dimensions facultatives.
3. **Ajouter au moins une variante active** avec une référence interne unique, une couleur et un stock. Le prix se définit dans une offre commerciale.
4. **Ajouter un média image** dans la section des médias du produit. Pour un média partagé entre toutes les variantes, laisser la variante vide ; pour une photo propre à une variante, sélectionner celle-ci.
5. **Choisir le média principal** et renseigner un texte alternatif descriptif.
6. **Configurer les contenus facultatifs** : arguments, éléments de capacité, détails de fabrication, situations d'usage, FAQ et offres.
7. **Configurer les champs de publication** : activer le produit, vérifier que sa catégorie est active, choisir `is_new` si le produit doit apparaître parmi les nouveautés et renseigner `published_at` si une date est nécessaire.
8. **Enregistrer puis tester la page publique** et la présence du produit dans le catalogue.

### Champs à connaître

- `is_active` sur la catégorie : rend la catégorie éligible à l'affichage.
- `is_active` sur le produit : le produit est éligible à l'affichage public.
- `is_new` : marque le produit comme nouveauté pour la section concernée.
- `is_best_seller` : indicateur de meilleure vente.
- `published_at` : date de publication facultative.
- `position` : contrôle l'ordre dans les sections qui utilisent cet ordre.
- `is_primary` sur un média : indique le média principal ; des contraintes limitent le nombre de médias principaux selon le produit/variante.

### Dépannage : le produit n'apparaît pas

Vérifie, dans cet ordre :

- la catégorie existe et est active ;
- le produit est actif ;
- le produit a au moins une variante active ;
- le produit dispose d'un média image compatible avec les critères du sélecteur public ;
- le média principal et la variante sont correctement associés ;
- le produit est marqué comme nouveauté si tu le recherches dans cette section ;
- les migrations ont été appliquées ;
- les erreurs du terminal et de la console du navigateur.

## 10. Téléverser et stocker les images

### Principe

Les champs `ImageField` enregistrent le chemin du fichier dans la base de données et le fichier lui-même dans le stockage configuré par Django. Le paramètre `upload_to` définit le sous-dossier à utiliser.

Pour les champs locaux, tu n'as pas à copier l'URL de l'image ni à créer manuellement son nom dans le HTML. Dans les templates et vues, Django fournit l'URL à travers `.url`, par exemple `category.image.url` ou `media.image.url`, si un fichier est présent.

### Dossiers de destination

Les dossiers sont relatifs à `MEDIA_ROOT`. Le chemin inclut automatiquement l'année et le mois :

| Type de fichier | Valeur `upload_to` | Exemple de chemin relatif |
|---|---|---|
| Image de catégorie | `categories/%Y/%m/` | `categories/2026/10/nom-image.webp` |
| Image de produit/variante | `products/%Y/%m/` | `products/2026/10/nom-image.webp` |
| Détail de fabrication | `products/craft/%Y/%m/` | `products/craft/2026/10/nom-image.webp` |
| Situation d'usage | `products/usage/%Y/%m/` | `products/usage/2026/10/nom-image.webp` |

Ces exemples illustrent la forme du chemin ; l'année et le mois réels sont ceux de la date du téléversement.

### En développement

Par défaut, `MEDIA_ROOT` vaut `BASE_DIR / "media"`, donc le dossier `media/` à la racine du projet. Tu peux personnaliser cet emplacement avec la variable d'environnement `DJANGO_MEDIA_ROOT`.

Exemple PowerShell pour la session courante :

```powershell
$env:DJANGO_MEDIA_ROOT = "C:\chemin\vers\E-commerce-Website\media"
python manage.py runserver --settings=config.settings.development
```

Si la variable n'est pas définie, Django utilise automatiquement le dossier local par défaut. En mode développement, `config/urls.py` expose les médias avec `static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)` lorsque `DEBUG=True`.

**Important :** la route de service des médias ajoutée par Django est prévue pour le développement. Elle ne doit pas être utilisée comme stratégie de diffusion en production.

### Formats et bonnes pratiques de fichiers

- Utilise des noms de fichiers simples, sans informations personnelles.
- Préfère des images optimisées en WebP ou AVIF lorsque ton flux de travail et les navigateurs cibles le permettent ; garde une qualité suffisante pour la fiche produit.
- Redimensionne les fichiers à une taille adaptée à leur usage plutôt que d'envoyer des images originales inutilement lourdes.
- Fournis un texte alternatif descriptif et utile.
- N'utilise pas le texte alternatif pour empiler des mots-clés SEO.
- Ne téléverse pas d'archives, de scripts, de fichiers exécutables ou de documents confidentiels dans les champs d'images.
- Vérifie la taille maximale de requête du serveur et la taille des images avant un téléversement volumineux.
- Pillow est déclaré dans `requirements.txt` pour la prise en charge des images par Django.

### URL externe ou fichier téléversé ?

Utilise le champ de téléversement lorsque le fichier doit être géré par ton site. Les champs d'URL externe restent disponibles lorsqu'une ressource est réellement hébergée sur un CDN ou une autre origine HTTPS. Une URL externe doit être stable et accessible publiquement si elle est utilisée pour une image affichée sur le site.

Pour une vidéo, le modèle actuel utilise une URL externe pour la source et une URL externe pour sa vignette. Le téléversement de vidéos n'est pas mis en place par ces champs.

### Sauvegardes et Git

Le dossier `media/` est exclu de Git par `.gitignore`. C'est intentionnel : les photos produits sont des fichiers de données, pas du code source.

Il faut donc sauvegarder séparément :
1. la base de données ;
2. le dossier média complet ;
3. les variables de configuration et procédures de déploiement, sans versionner les secrets.

Restaurer uniquement la base de données ne restaure pas les fichiers images. Restaurer uniquement `media/` ne restaure pas les relations de la base. Les deux doivent correspondre.

## 11. Configuration des fichiers statiques et médias

### Fichiers statiques

Les fichiers statiques sont les ressources versionnées du front-end : CSS, JavaScript, icônes et images incluses dans le code. La configuration partagée utilise :

- `STATIC_URL = "static/"`
- `STATIC_ROOT = BASE_DIR / "staticfiles"`
- `STATICFILES_DIRS = [BASE_DIR / "static"]`

En production, exécute `collectstatic` et configure le serveur web pour servir les fichiers de `STATIC_ROOT`.

### Fichiers médias

Les médias sont les fichiers téléversés par l'administration et ne sont pas versionnés avec le code. La configuration utilise :

- `MEDIA_URL = "/media/"`
- `MEDIA_ROOT = Path(os.environ.get("DJANGO_MEDIA_ROOT", str(BASE_DIR / "media"))).resolve()`

`MEDIA_ROOT` est un chemin sur le système de fichiers ; `MEDIA_URL` est le préfixe d'URL public. Ils remplissent des rôles différents et ne doivent pas être confondus.

### Exigence de production

Avec `DEBUG=False`, la configuration actuelle n'ajoute pas de route Django pour servir les fichiers médias. Le serveur web doit être configuré pour exposer le répertoire indiqué par `DJANGO_MEDIA_ROOT` sous `/media/`, ou un mécanisme équivalent doit être configuré.

Le fait de définir `DJANGO_MEDIA_ROOT` ne rend pas automatiquement le dossier public. Le routage du domaine et les permissions du système de fichiers doivent être configurés explicitement. Teste une URL d'image dans le navigateur après déploiement et vérifie qu'elle renvoie le fichier attendu, sans exposer le reste de l'application.

**Ne place jamais les secrets, le fichier `.env`, la base de données ou d'autres fichiers privés dans un répertoire public.** Si le serveur web ne peut pas exposer un dossier situé hors de la racine publique, configure un dossier média dédié et renseigne son chemin absolu via `DJANGO_MEDIA_ROOT`.

## 12. Déploiement en production sur cPanel / o2switch

Cette section décrit les points à préparer ; elle ne signifie pas que l'application a été déployée ou que le routage média est déjà configuré sur l'hébergement.

### Paramètres et secrets requis

La configuration `config.settings.production` exige les variables suivantes :

| Variable | Utilisation |
|---|---|
| `DJANGO_SECRET_KEY` | Clé secrète Django. |
| `DJANGO_ALLOWED_HOSTS` | Liste séparée par des virgules des noms d'hôtes autorisés. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Liste séparée par des virgules des origines HTTPS de confiance pour CSRF. |
| `EMAIL_HOST` | Serveur SMTP. |
| `EMAIL_PORT` | Port SMTP, par défaut 587 si non défini. |
| `EMAIL_USE_TLS` | Active STARTTLS lorsque vrai. |
| `EMAIL_USE_SSL` | Active SSL implicite lorsque vrai. |
| `EMAIL_HOST_USER` | Compte SMTP. |
| `EMAIL_HOST_PASSWORD` | Mot de passe SMTP. |
| `DEFAULT_FROM_EMAIL` | Adresse expéditeur par défaut. |
| `SERVER_EMAIL` | Adresse expéditeur des messages techniques. |
| `DJANGO_MEDIA_ROOT` | Chemin absolu du stockage média à utiliser ; le serveur web doit aussi l'exposer sous `/media/`. |

Les secrets doivent être définis dans l'environnement de l'application cPanel ou un gestionnaire de secrets approprié. Ne les écris pas dans les fichiers suivis par Git, les tickets, les captures d'écran ou ce README.

### Étapes de préparation

1. Vérifier la version de Python sélectionnée par l'application cPanel.
2. Déployer le code de la branche voulue et installer `requirements.txt` dans l'environnement Python de l'application.
3. Configurer `DJANGO_SETTINGS_MODULE=config.settings.production` selon la configuration Passenger/cPanel.
4. Définir toutes les variables requises, notamment les hôtes, origines CSRF, SMTP et la clé secrète.
5. Définir `DJANGO_MEDIA_ROOT` sur un dossier persistant adapté au stockage des images téléversées.
6. Configurer le serveur web pour servir les fichiers de `STATIC_ROOT` et les médias sous `MEDIA_URL`. Vérifier le chemin public réel sur l'hébergement avant d'autoriser les téléversements en production.
7. Vérifier les permissions du dossier média : l'application doit pouvoir y écrire et le serveur web doit pouvoir lire les images publiques.
8. Exécuter les vérifications Django, les migrations et `collectstatic`.
9. Redémarrer l'application Python/Passenger si l'environnement cPanel le requiert.
10. Tester la page d'accueil, le catalogue, les fiches produit, l'administration, les téléversements et les URLs des fichiers.
11. Mettre en place des sauvegardes régulières de la base et des médias, puis tester une restauration.

### Commandes de déploiement

À exécuter dans l'environnement de production avec les variables déjà configurées :

```bash
python -m pip install -r requirements.txt
python manage.py check --settings=config.settings.production
python manage.py check --deploy --settings=config.settings.production
python manage.py migrate --settings=config.settings.production
python manage.py collectstatic --noinput --settings=config.settings.production
```

La configuration de production force `DEBUG=False`, redirige vers HTTPS et active les cookies sécurisés. Vérifie que HTTPS fonctionne réellement avant d'utiliser ces paramètres. Les vérifications de déploiement peuvent signaler des points de configuration supplémentaires à traiter.

### Point particulier : SQLite

Le dépôt configure SQLite par défaut. Avant de mettre le site en production, évalue si SQLite correspond à la charge attendue et au fonctionnement du plan d'hébergement. Si tu conserves SQLite, vérifie les permissions du fichier, l'accès concurrent, les sauvegardes et la restauration. Ne stocke pas la base dans un emplacement temporaire ou public.

### Point particulier : médias publics

Les photos de produits sont destinées à être publiques, mais le dossier média ne doit pas devenir une zone d'exécution de scripts. Configure le serveur pour servir les fichiers comme des fichiers statiques, désactive l'exécution de code dans ce répertoire et limite les types de fichiers acceptés par le formulaire. Si des documents privés sont ajoutés ultérieurement, ne les stocke pas dans le même emplacement public.

## 13. Sécurité et bonnes pratiques

### Secrets et configuration

- Ne jamais committer `.env`, clés secrètes, mots de passe SMTP ou identifiants.
- Utiliser `config.settings.development` en local et `config.settings.production` en production.
- Ne jamais activer `DEBUG=True` sur le site public.
- Restreindre `DJANGO_ALLOWED_HOSTS` aux hôtes réellement utilisés.
- Définir `DJANGO_CSRF_TRUSTED_ORIGINS` avec les origines exactes nécessaires.

### Données et validation

- Utiliser les contraintes de base de données et les validations Django.
- Ne jamais faire confiance aux prix et stocks fournis par le navigateur.
- Garder les avis non approuvés invisibles publiquement.
- Vérifier que les variantes appartiennent au produit attendu et que les éléments d'offres sont cohérents.
- Ne pas publier de prix de référence, réductions, avis ou statistiques qui ne sont pas justifiés.
- Ne pas exposer les e-mails privés des auteurs d'avis.

### Téléversement de fichiers

- Réserver les formulaires de téléversement à des utilisateurs autorisés.
- Limiter la taille des fichiers au niveau de l'application et du serveur web.
- Contrôler les formats réellement autorisés ; ne pas se fier uniquement à l'extension du nom de fichier ou au type MIME envoyé par le navigateur.
- Utiliser le traitement d'image approprié et envisager une normalisation des images.
- Ne pas rendre le dossier média exécutable.
- Garder les fichiers téléversés hors du dépôt Git.
- Sauvegarder les fichiers média et contrôler les permissions de lecture/écriture.

### Front-end

- Échapper les données dans les templates et utiliser les mécanismes de rendu Django.
- Ne pas insérer du contenu utilisateur dans le DOM comme du HTML non fiable.
- Garder les scripts et styles partagés cohérents avec les templates.
- Tester les interactions au clavier, les libellés accessibles, les textes alternatifs et les vues mobiles.

### Dépendances et mises à jour

- Installer les versions définies dans `requirements.txt`.
- Vérifier la compatibilité avant de mettre à jour Django, Python ou Pillow.
- Tester les migrations sur une copie de données avant un déploiement sensible.
- Lire les erreurs de test avant de modifier les contraintes ou de supprimer des données.

## 14. État des tests et checklist de recette

### Tests automatisés disponibles

Le fichier `product/tests.py` contient des tests sur les modèles, les vues du catalogue et le stockage local d'images, notamment :

- validation des prix d'offres commerciales ;
- cohérence d'une variante dans un élément d'offre ;
- cohérence du produit et de la variante d'un média ;
- affichage des données de catalogue ;
- filtre de nouveautés sur la page d'accueil ;
- accès à une fiche publiée et rejet d'un produit inactif ;
- invisibilité des avis non approuvés ;
- stockage des images téléversées dans les chemins prévus.

L'existence de ces tests n'est pas une preuve de réussite. Lance les commandes de test et conserve leur résultat pour chaque modification significative.

### Recette manuelle

- [ ] Les migrations sont appliquées sans erreur.
- [ ] L'administration est accessible uniquement aux utilisateurs autorisés.
- [ ] Une catégorie peut être créée et son image téléversée.
- [ ] Un produit peut être créé avec une variante active (couleur et stock) et au moins une offre tarifée.
- [ ] Les médias se retrouvent dans le sous-dossier attendu de `MEDIA_ROOT`.
- [ ] L'image de catégorie s'affiche sur la page qui l'utilise.
- [ ] La fiche produit affiche ses médias et ses variantes.
- [ ] Une URL externe HTTPS existante continue de fonctionner si elle est utilisée.
- [ ] Un produit inactif ne peut pas être consulté publiquement.
- [ ] Les avis non approuvés ne sont pas affichés.
- [ ] La sélection signature est administrable, chaque carte possède une image dédiée et mène à sa fiche produit.
- [ ] Les nouveautés sont filtrées avec `is_new`.
- [ ] Les images s'affichent sur téléphone et sur grand écran.
- [ ] En production, les fichiers média sont accessibles par leur URL publique, sans rendre les fichiers privés accessibles.
- [ ] La base de données et le dossier média sont inclus dans la procédure de sauvegarde.

## 15. Périmètre restant et feuille de route

Les sujets suivants doivent être traités comme des chantiers séparés, avec leur propre analyse, tests et critères d'acceptation.

### Priorité 1 — valider le catalogue et les médias

- Exécuter l'ensemble des tests sur la branche.
- Tester les téléversements en local avec plusieurs images et variantes.
- Vérifier les tailles maximales, formats, dimensions et erreurs d'upload.
- Configurer et tester le service du dossier média sur l'hébergement cible.
- Définir une stratégie d'optimisation et de sauvegarde des images.
- Vérifier la cohérence des données d'administration et des contenus publics.

### Priorité 2 — rendre le parcours d'achat réellement opérationnel

- Transformer le panier en commande avec des lignes et des prix figés au moment de l'achat.
- Calculer côté serveur les taxes, frais de livraison et réductions réellement applicables.
- Réserver/décrémenter le stock de façon transactionnelle et prévenir les commandes concurrentes sur les dernières unités.
- Créer des modèles de commande et de lignes de commande avec un état explicite.
- Intégrer un prestataire de paiement en mode test, vérifier ses webhooks et traiter les paiements de manière idempotente.
- Mettre en place les e-mails de commande, les erreurs, les remboursements et la journalisation.

### Priorité 3 — exploitation

- Mettre en place une stratégie de sauvegarde et de restauration testée.
- Ajouter des journaux exploitables et une surveillance des erreurs.
- Examiner le besoin d'une base de données de production adaptée à la charge.
- Évaluer un CDN si le catalogue et le trafic le justifient.
- Mettre en place une procédure de mise à jour et de retour arrière.

Ces éléments sont des pistes de travail, pas des fonctionnalités déjà livrées.

## 16. Règles de travail et de contribution

### Avant de modifier le code

1. Confirmer la branche courante avec `git branch --show-current`.
2. Vérifier `git status` et préserver les modifications locales.
3. Lire le code et les tests concernés avant de choisir une implémentation.
4. Respecter les conventions et la structure déjà utilisées.
5. Ne pas modifier les sections visuelles hors périmètre, notamment « Notre sélection signature », sans demande explicite.
6. Ne pas inventer de règles métier ou de données produit : demander les précisions manquantes.

### Après une modification

1. Lancer `python manage.py check --settings=config.settings.development`.
2. Vérifier les migrations avec `makemigrations --check --dry-run`.
3. Exécuter les tests pertinents.
4. Vérifier les pages concernées dans le navigateur et dans la console.
5. Mettre à jour ce README si l'architecture, les commandes, les variables ou le comportement ont changé.
6. Décrire le périmètre réel dans le message de commit ; ne pas annoncer des tests qui n'ont pas été exécutés.

### Commandes Git utiles

```powershell
git status
git branch --show-current
git fetch origin
git pull origin developpement-backend
git diff
git diff --check
```

Ne force pas un push, ne supprime pas de branche et ne réinitialise pas la base de données pour contourner un problème sans comprendre ses conséquences.

---

## Référence finale

Pour cette branche, les sources de vérité sont, dans l'ordre :

1. le code actuellement présent dans `developpement-backend` ;
2. les modèles et migrations pour le schéma des données ;
3. les tests pour les comportements explicitement couverts ;
4. ce README pour l'installation, les procédures et les limites connues.

Si le code change, ce document doit être mis à jour pour rester fidèle au comportement réel. Les procédures de production doivent toujours être validées sur l'hébergement cible : en particulier, définir `DJANGO_MEDIA_ROOT` ne suffit pas à rendre les images publiques tant que le serveur web n'est pas configuré pour servir ce répertoire.


---

## 17. Audit du raccordement Accueil ↔ Boutique ↔ Fiche produit

Cette section documente les contrôles et corrections effectués lors de l'audit du parcours de navigation de la branche.

### 17.1 Parcours nominal

Le parcours du catalogue est le suivant :

1. **Accueil — `/`** : `home.views.home` charge les catégories actives et les produits marqués comme nouveautés. Les données commerciales proviennent des modèles Django, pas d'un tableau de produits de démonstration ajouté dans la vue.
2. **Catégorie — lien vers `/boutique/?cat=<slug>`** : les cartes de catégories de l'accueil transmettent le slug réel enregistré en base.
3. **Boutique — `/boutique/`** : `shop.views.catalog` charge les catégories et les produits publiables, puis sérialise les champs strictement nécessaires à l'interface dans `catalog_data`.
4. **Cartes du catalogue — `/produit/<slug>/`** : le JavaScript du catalogue construit les liens à partir du préfixe généré par Django (`data-product-url`) et du slug de produit reçu du serveur.
5. **Fiche produit** : `product.views.detail` recherche le produit par slug via le sélecteur des produits publiés. Un produit absent, inactif ou non publiable ne doit pas être rendu comme une fiche publique.

Les noms d'URL Django (`home:home`, `shop:catalog`, `product:detail`) sont préférables aux chemins codés en dur, car ils gardent les liens cohérents si les routes évoluent.

### 17.2 Catégories dans la navigation commune

Les liens de catégories ne doivent pas supposer que les slugs en base sont toujours `handbags`, `shoulder`, `wallets` ou `accessories`. Les slugs sont des données administrables : un lien basé sur un slug fictif peut ouvrir le catalogue sans appliquer le filtre attendu.

Pour éviter cette divergence :

- les liens principaux « Sacs » et « Accessoires » ouvrent maintenant la boutique sans filtre de catégorie prédéfini ;
- le pied de page reçoit les catégories actives via `product.context_processors.active_catalog_categories` ;
- les liens du pied de page utilisent le `slug` réel de chaque catégorie active ;
- lorsqu'aucune catégorie active n'existe, le pied de page conserve un lien de repli vers la boutique ;
- l'accueil continue d'utiliser sa liste de catégories issue de sa propre vue. Le contexte partagé est nommé `catalog_categories` afin de ne pas remplacer la variable `categories` propre à l'accueil.

Pour ajouter ou renommer une catégorie, il faut donc mettre à jour ses données dans Django Admin ; il n'est pas nécessaire de modifier les liens du pied de page.

### 17.3 Images des nouveautés de l'accueil

La vue d'accueil précharge désormais uniquement les médias qui sont des images communes au produit (`variant__isnull=True` et `media_type=ProductMedia.IMAGE`). Cela évite qu'une vidéo marquée comme média principal soit utilisée par erreur comme source d'une balise HTML `<img>` dans les cartes de nouveautés.

La sélection publique des produits reste centralisée dans `product.selectors.published_products()`. Elle exige actuellement un produit actif, une catégorie active, une variante active, une date de publication atteinte (ou absente) et au moins une image commune au produit. Si un produit ne s'affiche pas, vérifier ces conditions dans Django Admin avant de modifier le code.

### 17.4 Données dynamiques et frontière de confiance

- Le catalogue reçoit ses données depuis Django via `json_script`, mécanisme qui échappe le contenu JSON pour son insertion dans le HTML.
- Le JavaScript crée les cartes à partir des données fournies par le serveur ; les filtres de catégorie utilisent les slugs réellement reçus.
- Le panier est conservé dans la session Django ; les prix et stocks sont recalculés côté serveur. Le panier ne réserve pas le stock et ne constitue pas une commande.
- Les templates Django doivent continuer à utiliser l'échappement automatique ; ne pas injecter les noms, descriptions ou avis en HTML brut.
- Les catégories inactives et les produits non publiables ne doivent pas être exposés dans les listes publiques.
- Les médias externes doivent rester limités à des sources de confiance en HTTPS. En production, la configuration du serveur web doit également empêcher l'exécution de fichiers téléversés.

### 17.5 Tests de non-régression ajoutés

Le fichier `product/tests.py` couvre maintenant notamment :

- le chargement du catalogue depuis la base ;
- la présence de liens entre l'accueil, la boutique et la fiche produit ;
- la génération des liens de catégories avec les slugs réels, sans dépendance au slug fictif `handbags` ;
- le chargement des nouveautés filtrées par `is_new` ;
- l'accès aux fiches publiées et le refus des produits inactifs ;
- l'absence d'exposition des avis non approuvés ;
- le stockage des images téléversées dans les dossiers prévus.

Exécuter les contrôles depuis la racine du dépôt avec l'environnement de développement configuré :

```powershell
python manage.py check --settings=config.settings.development
python manage.py makemigrations --check --dry-run --settings=config.settings.development
python manage.py test product --settings=config.settings.development
```

**État de vérification :** les modifications ont été poussées sur la branche GitHub, mais ces commandes n'ont pas été exécutées dans un environnement Python/Django pendant cet audit à distance. Il faut donc les lancer localement et corriger toute erreur éventuelle avant de considérer la recette comme validée.

### 17.6 Construction des URL de fiches depuis le catalogue

Le conteneur du catalogue reçoit un modèle d'URL produit généré par Django avec `reverse` via `{% url 'product:detail' slug='__product_slug__' %}`. Le JavaScript remplace ensuite uniquement le marqueur `__product_slug__` par le slug du produit encodé avec `encodeURIComponent`. Les deux liens de chaque carte (image et nom) utilisent cette même fonction. Ainsi, le préfixe ne dépend pas d'un chemin écrit en dur ni de la route `product:index`, et le test Django vérifie le modèle d'URL et les données JSON. Les liens sont rendus dans le navigateur ; un test de réponse HTTP Django ne doit pas prétendre qu'ils existent déjà comme éléments HTML dans la réponse initiale.

### 17.6 Périmètre préservé

La section **« Notre sélection signature »** est désormais alimentée par le modèle `home.SignatureSelection`. Le checkout, les commandes et les paiements réels restent hors périmètre : aucun lien ou comportement de navigation ne doit être interprété comme la preuve qu'un parcours de commande complet est opérationnel.


## 18. Diagnostic de publication et vérification de l'administration

### Conditions actuelles pour qu'un produit soit visible

Le sélecteur commun `product.selectors.published_products()` filtre les produits publics. Pour apparaître dans le catalogue et dans les sélections dynamiques qui utilisent ce sélecteur, un produit doit remplir toutes ces conditions :

1. le produit est actif (`is_active = True`) ;
2. sa catégorie est active ;
3. sa date `published_at` est vide ou n'est pas dans le futur ;
4. il possède au moins une variante active ;
5. il possède un média commun de type **Image**, avec le champ **Variante laissé vide**, et une image téléversée ou une URL de source renseignée.

Le champ `Product.is_active` a par défaut la valeur `False`. Créer un produit dans l'administration ne le publie donc pas automatiquement. De plus, une image uniquement rattachée à une variante ne remplit pas la condition d'image commune utilisée par le sélecteur actuel.

### Diagnostic dans Django Admin

La liste des produits affiche désormais un état **Prêt** ou **À compléter**. La fiche d'administration du produit fournit un diagnostic expliquant les conditions manquantes : activation du produit, catégorie inactive, date future, absence de variante active ou absence d'image commune valide. Le diagnostic est informatif : il ne publie pas automatiquement un produit et ne remplace pas la validation des formulaires.

### Contrôles réalisés dans le code

Le sélecteur public écarte maintenant aussi les médias communs de type Image dont ni le champ de fichier ni l'URL source ne sont renseignés. Des tests couvrent les cas d'un produit sans image commune, sans variante active, et le diagnostic administratif. Ces tests ont été ajoutés au dépôt ; ils ne sont considérés comme validés qu'après exécution dans l'environnement Python/Django du projet.

### Procédure de diagnostic sur un produit existant

Dans **Django Admin → Produits → ouvrir le produit** :

- lire le diagnostic « État catalogue » ;
- si le produit doit apparaître dans les nouveautés de l'accueil, cocher aussi « Nouveauté » (is_new) ; la page d'accueil n'affiche que les quatre nouveautés les plus récentes ;
- vérifier que le produit et sa catégorie sont actifs ;
- vérifier la date de publication ;
- ouvrir la section des variantes et confirmer qu'au moins une variante est active, avec sa couleur et son stock renseignés ;
- dans les médias du produit, ajouter une ligne de type **Image**, téléverser le fichier ou renseigner une URL HTTPS, renseigner le texte alternatif, puis laisser **Variante** vide pour une image commune ;
- enregistrer, puis recharger le catalogue sans cache.

En production, il faut aussi confirmer que l'administration et le site utilisent la même base de données, que les migrations sont appliquées et que le stockage média est accessible. Le dépôt seul ne permet pas de vérifier les valeurs réelles du produit créé dans l'instance en ligne.


## 19. Offres commerciales : règles, administration et publication

### Règles métier

- Une offre est toujours rattachée à un produit principal.
- Chaque produit doit disposer d'au moins une offre active contenant une ligne qui référence le produit principal avec **« Utiliser la variante choisie sur la fiche »** activé et sans variante fixe.
- Trois badges au maximum sont proposés : **Essentiel**, **Medium**, **Premium**.
- Le titre affiché et l'ordre sont dérivés du badge ; l'ordre est fixe : Essentiel, Medium, Premium. Il n'est pas saisi manuellement. Le prix appartient uniquement à l'offre, jamais à la variante de couleur.
- Le type de livraison est une liste fermée : **Livraison payante** ou **Livraison gratuite**. Cette mention décrit l'offre ; elle ne calcule pas encore les frais réels de livraison au checkout.
- Une offre peut inclure d'autres produits. Chaque ligne doit sélectionner le produit et, pour un produit complémentaire, une variante appartenant à ce produit.
- Un produit sans offre active valide est exclu du catalogue public. La fiche produit ne doit pas remplacer une offre invalide par un prix de variante présenté comme une offre commerciale.

### Créer de une à trois offres dans Django Admin

1. Ouvrir la fiche du produit dans **Produits** et enregistrer le produit, ses variantes actives et son image commune.
2. Dans la section **Offres** au bas de la fiche produit, ajouter une ligne pour chaque niveau souhaité : Essentiel, Medium et/ou Premium. Il est possible d'en créer une seule, deux ou les trois.
3. Pour chaque ligne, choisir le badge, le type de livraison, le prix et l'état actif. Le titre et l'ordre sont automatiques. Un même badge ne peut pas être utilisé deux fois pour ce produit.
4. Enregistrer la fiche produit. Utiliser le lien **Modifier** d'une offre pour ouvrir sa fiche détaillée et configurer les produits qui la composent.
5. Dans la section des articles de l'offre, ajouter une ligne pour le produit principal. Sélectionner ce même produit et cocher **Utiliser la variante choisie sur la fiche** ; laisser **Variante fixe** vide.
6. Pour chaque produit complémentaire, ajouter une ligne distincte, sélectionner ce produit, choisir sa variante fixe et définir la quantité.
7. Enregistrer l'offre, puis revenir sur la fiche du produit et lire le diagnostic de publication. N'activer le produit que lorsque les autres conditions de publication sont satisfaites.

Le badge détermine le titre et la position automatiquement. Un produit peut avoir une, deux ou trois offres actives, mais pas deux offres actives portant le même badge.

### Migration et vérifications

La migration `0003_offer_choices_and_order` normalise les anciennes valeurs de badge et de livraison. Les offres historiques au-delà des trois niveaux pris en charge sont conservées mais désactivées ; vérifier ces enregistrements après migration avant de les réactiver.

Après récupération de la branche :

```powershell
python manage.py check --settings=config.settings.development
python manage.py makemigrations --check --dry-run --settings=config.settings.development
python manage.py migrate --settings=config.settings.development
python manage.py test product --settings=config.settings.development
```

Ces commandes doivent être exécutées avant déploiement. Le code poussé sur GitHub ne signifie pas que la migration est déjà appliquée sur l'hébergement de production.


## 20. Avis produits et témoignages de l’accueil

### Fonctionnement actuel

- Chaque avis est obligatoirement rattaché à un produit via Review.product.
- La création et la modification des avis sont réservées à l’administration Django pendant la phase de développement. Aucun formulaire public ne permet actuellement d’envoyer un avis.
- La fiche produit affiche uniquement les avis approuvés, associés à ce produit et échappés automatiquement par les templates Django.
- L’accueil affiche au maximum trois avis approuvés et mis en avant dont le produit est toujours publiable. Chaque témoignage renvoie vers la fiche du produit.
- Un avis non approuvé ne peut pas être mis en avant. Cette règle est appliquée par le modèle et par une contrainte de base de données.
- L’adresse e-mail reste facultative, privée et n’est jamais rendue dans le site public.

### Ajouter un avis de test

Dans Administration → Avis → Ajouter un avis :

1. Sélectionner le produit exact auquel l’avis doit être rattaché.
2. Renseigner le nom affiché, la note entre 1 et 5 et le commentaire.
3. Cocher Approuvé pour rendre l’avis visible sur la fiche produit.
4. Cocher Mis en avant sur l’accueil uniquement si l’avis est approuvé et doit figurer parmi les témoignages de la page d’accueil.
5. Enregistrer, puis vérifier la fiche du produit et l’accueil.

Le formulaire d’administration présente des champs organisés, un aperçu après enregistrement et une liste avec filtres de modération. Le formulaire public sera étudié après la mise en place du checkout et des règles permettant de vérifier une commande réelle. Aucune preuve d’achat n’est simulée à ce stade.

### Recette des avis

```powershell
python manage.py check --settings=config.settings.development
python manage.py test product --settings=config.settings.development
```

La migration 0004_review_featured ajoute le champ de mise en avant des avis. La migration `home.0001_initial` ajoute la sélection signature. Exécutez `python manage.py migrate --settings=config.settings.development` pour appliquer les migrations en attente. La publication sur GitHub ne signifie pas que les migrations ont été appliquées sur l’hébergement de production.

## Panier invité

Le panier utilise la session Django côté serveur. Le navigateur ne peut envoyer que l’identifiant de variante, l’identifiant obligatoire d’offre et la quantité ; les prix, les produits publiés, les variantes actives et les stocks sont recalculés et contrôlés par le serveur. Les prix fournis par le client sont ignorés.

- GET /boutique/panier/ renvoie le contenu et les totaux calculés côté serveur.
- POST /boutique/panier/modifier/ accepte les actions add, update, remove et clear, avec protection CSRF Django.
- `STATIC_URL` doit commencer par `/` (`/static/`) : les chemins relatifs cassaient le chargement de `base.js`, de la fiche produit et des styles depuis les URL imbriquées comme `/produit/<slug>/`.
- La fiche produit émet le cookie CSRF dès son affichage, nécessaire au POST sécurisé du panier depuis cette page.
- Les quantités sont limitées à 10 par ligne, les lignes à 30 par panier, et les quantités doivent être des entiers stricts. Une addition qui ferait dépasser la limite d'une ligne est rejetée sans effacer la quantité déjà enregistrée.
- Les offres sont contrôlées avec leurs composants et le stock de chaque variante ; le champ `ProductOffer.price` est le prix appliqué côté serveur à l'offre sélectionnée. Les nouvelles lignes de panier exigent un identifiant d'offre valide.
- Les mutations reçues depuis l'interface sont sérialisées côté JavaScript pour éviter que des clics rapprochés se remplacent. Le serveur reste la source de vérité ; aucune mutation ne réserve le stock.
- Les lignes devenues invalides (produit non publié, variante inactive ou offre supprimée) sont retirées lors de la relecture.
- Le tiroir du panier et les badges sont alimentés par la réponse serveur. Le prix affiché n’est pas une preuve de prix définitif pour une commande.
- Les ajouts rapides accueil/catalogue récupèrent les offres actives via `GET /boutique/offres/<slug>/` ; une offre est ajoutée automatiquement si elle est unique, sinon un dialogue accessible présente les prix, le contenu, la livraison indiquée et l’économie calculée côté serveur. La route émet aussi le cookie CSRF avant la mutation POST.
- Les boutons de la fiche produit sont gérés par délégation dans `static/js/base.js` pour éviter qu’une erreur d’initialisation secondaire de `product.js` les laisse sans action. L’offre et la variante cochées sont envoyées au serveur ; le serveur recalcule disponibilité et prix.
- Le panier affiche les composants configurés de chaque offre. La composition interactive d’une offre (choix libre du deuxième article) nécessite toutefois une modélisation dédiée des options autorisées et de leur sélection dans la session ; elle n’est pas activée par cette première étape.
- La route publique `GET /boutique/offres/<slug>/?variant_id=<id>` renvoie uniquement les offres actives validées pour le produit et la variante demandés. Les prix, composants et disponibilités sont recalculés côté serveur.
- Depuis l'accueil et le catalogue, une offre disponible est ajoutée directement ; plusieurs offres ouvrent le sélecteur commun. L'offre choisie est envoyée au panier avec son identifiant, puis validée à nouveau côté serveur.
- La fiche produit synchronise les cartes d'offres avec `querySelectorAll` ; un appel à `querySelector(...).forEach(...)` interrompait l'initialisation JavaScript.
- Les lignes de panier exposent les composants de l'offre pour rendre la composition lisible. La sélection interactive d'articles alternatifs dans une offre multi-articles nécessite encore de définir les choix autorisés pour chaque offre avant d'ajouter le modèle métier correspondant.
- Les trois boutons d’ajout de la fiche produit (CTA principal, CTA de fin de page et barre d’achat collante) sont initialisés via `querySelectorAll`. Un sélecteur simple `querySelector` suivi de `forEach` interrompait le script avant l’attachement des événements.
- L’ajout depuis la fiche produit transmet explicitement la variante et l’offre sélectionnées. Les erreurs serveur sont remontées à l’interface au lieu d’être silencieusement transformées en échec sans diagnostic.
- Les boutons rapides de l’accueil et du catalogue interrogent `/boutique/offres/<slug>/`. Une seule offre disponible est ajoutée directement ; plusieurs offres ouvrent une boîte de dialogue accessible avec prix serveur, composition connue et badge. Les économies ne sont affichées que lorsqu'une référence tarifaire explicite existe.
- Les tests Django couvrent la récupération des offres, plusieurs offres actives, le rejet d’une variante qui ne correspond pas au produit, ainsi que la présence des trois CTA de la fiche produit. Ils doivent encore être exécutés localement.
- Le tiroir distingue explicitement l’état vide de l’état avec articles : la liste, la progression de livraison et le récapitulatif sont masqués ou affichés selon la réponse serveur. Le nombre d’articles, les images, les quantités et les totaux sont synchronisés depuis cette réponse.
- Le tiroir a une mise en page mobile-first, des liens vers les fiches produits, une progression accessible vers le seuil de livraison offerte, une navigation clavier et un retour du focus à l’élément déclencheur.
- Le checkout reste une maquette front-end : aucun paiement, aucune commande et aucun frais de livraison ne sont calculés ou confirmés par cette fonctionnalité.

## Sélection signature

La section « Notre sélection signature » est gérée depuis **Django Admin → Sélection signature → Ajouter une carte de la sélection signature**.

- Choisir le produit à ouvrir au clic.
- Téléverser une image dédiée à cette carte : elle est stockée sous `MEDIA_ROOT/home/signature/` et reste indépendante des médias de la fiche produit.
- Renseigner le texte alternatif, l'ordre d'affichage et l'état « Afficher sur l'accueil ».
- Un produit ne peut apparaître qu'une fois dans cette sélection.
- Seules les cartes actives dont le produit satisfait les conditions de publication sont affichées.
- Le carrousel conserve ses classes et son comportement visuel existants ; les cartes deviennent des liens vers la fiche produit associée.

La migration `home.0001_initial` crée le modèle `SignatureSelection`. Appliquez-la avec `python manage.py migrate --settings=config.settings.development` après avoir récupéré la branche. Les images téléversées sont des fichiers médias : elles doivent être incluses dans la stratégie de sauvegarde et servies par la configuration média de l'environnement.

## Recherche catalogue

La recherche est disponible depuis l’overlay global et la page boutique. Elle propose des suggestions après deux caractères, limite les requêtes et ne renvoie que des produits satisfaisant les conditions de publication. La recherche du catalogue combine les termes saisis sur le nom, le slug, la description courte/complète, la ligne de marque, l’accroche et la catégorie. Les filtres du catalogue peuvent ensuite être combinés aux résultats de recherche.

### Recette panier, sélection signature et recherche

```powershell
python manage.py check --settings=config.settings.development
python manage.py makemigrations --check --dry-run --settings=config.settings.development
python manage.py migrate --settings=config.settings.development
python manage.py test home shop product --settings=config.settings.development
```

Ces commandes doivent être exécutées dans l’environnement local du projet. Aucun test ni déploiement n’est réputé réussi sans résultat effectivement observé.


### Sélection d'offre depuis l'accueil et le catalogue

- Les boutons d'ajout rapide interrogent `shop:offer_options` avec le slug du produit et l'identifiant de la variante active.
- Le serveur ne renvoie que les offres actives, cohérentes et disponibles, avec leurs prix recalculés côté serveur, leur composition, les économies indicatives et le badge configuré.
- Une seule offre disponible : ajout direct. Plusieurs offres disponibles : dialogue natif accessible avec choix explicite, prix, contenu et économie éventuelle.
- Le choix final est envoyé au point d'entrée du panier avec les seuls identifiants de variante et d'offre ; la mutation du panier revalide l'offre et le stock.
- La fiche produit conserve l'offre et la variante sélectionnées à l'écran. Les erreurs d'initialisation ou de validation sont rendues visibles plutôt que de laisser le bouton sembler inactif.
- La composition déjà configurée dans une offre est affichée dans le panier. La sélection dynamique d'un article parmi plusieurs choix possibles au sein d'une offre reste une évolution distincte : elle nécessite de définir les choix autorisés dans l'administration et de persister cette composition dans l'identité de ligne du panier.


## 21. Dashboard privé My Line Collection

### Objectif et accès

L'application dashboard/ fournit un espace de gestion distinct de l'interface publique, accessible sous /gestion/. La connexion se fait sous /gestion/connexion/. L'accès est limité aux comptes Django actifs et superutilisateurs (is_active=True et is_superuser=True) ; le statut is_staff seul ne suffit pas. Les vues vérifient cette règle côté serveur.

La connexion réutilise le mécanisme d'authentification Django et ses validateurs de mot de passe. Les formulaires utilisent le jeton CSRF, la déconnexion se fait par POST, et la session du dashboard expire après 30 minutes d'inactivité. La page est exclue de l'indexation via noindex,nofollow ; cette directive n'est pas une mesure de contrôle d'accès.

### Fonctionnalités de cette première version

- Vue d'ensemble : compteurs calculés à partir de la base (produits, produits activés, catégories, offres actives, avis à modérer) et derniers produits modifiés.
- Produits : recherche, création, modification et suppression protégée depuis un formulaire regroupant l'identité, les variantes (couleur/stock), une à trois offres tarifées et plusieurs images/vidéos.
- Catégories : création, liste, modification et suppression uniquement lorsqu'aucun produit n'est rattaché ; aperçu des images téléversées ou distantes.
- Offres : liste filtrable par produit, niveau Essentiel/Medium/Premium et état ; accès à l'administration avancée des compositions.
- Gestion avancée : accès direct à Django Admin pour les compositions d'offres et les contenus détaillés des fiches produits. Cette première version ne remplace pas encore tous les formulaires spécialisés de Django Admin ; elle rassemble les opérations courantes et conserve les outils avancés existants.

### Automatisation de l'offre initiale

Dans le dashboard, chaque création ou modification de produit comprend directement la création ou la modification de une à trois offres commerciales et de plusieurs médias. Chaque offre possède son prix propre et est automatiquement reliée au produit principal. Les variantes ne contiennent plus de prix : elles décrivent les couleurs et les stocks.

Les offres Essentiel, Medium et Premium sont limitées à trois niveaux par produit. Les compositions multi-articles avancées restent configurables dans Django Admin. Une offre doit être créée avant qu'un produit puisse être publié. Un produit ne devient pas automatiquement publiable : les règles existantes concernant la catégorie active, la variante, l'image commune et la cohérence de l'offre continuent de s'appliquer. Vérifiez le diagnostic de publication avant d'activer un produit.

### Sécurité et déploiement

- Garder /admin/ et /gestion/ accessibles uniquement via HTTPS en production.
- Conserver DEBUG=False, les cookies sécurisés, les hôtes autorisés et les origines CSRF strictement configurés.
- Utiliser un mot de passe unique et robuste pour le superutilisateur, ne pas partager ce compte et activer une protection supplémentaire au niveau de l'hébergement / reverse proxy contre les tentatives de connexion répétées.
- Ne pas exposer les fichiers média ou les sauvegardes de base de données autrement que prévu ; sauvegarder la base et les médias avant toute mise en production.
- La migration `product.0005_offer_only_pricing` transfère les prix historiques des variantes vers l'offre Essentiel lorsque nécessaire, puis retire les champs de prix des variantes. Appliquer les migrations et vérifier les offres après la mise à jour.
- Les fichiers CSS et JavaScript sont des ressources statiques versionnées. Exécuter collectstatic lors du déploiement de production.

### Recette locale

Après avoir récupéré la branche :

```powershell
python manage.py check --settings=config.settings.development
python manage.py test dashboard product --settings=config.settings.development
python manage.py runserver --settings=config.settings.development
```

Ouvrir http://127.0.0.1:8000/gestion/connexion/, puis se connecter avec le compte superutilisateur créé pour le projet. Les tests doivent être exécutés dans l'environnement Django du dépôt ; la présence des fichiers sur GitHub ne prouve pas que les tests ont passé ni que le déploiement de production est effectué.

### Évolutions prévues, hors périmètre de cette version

Les graphiques, les statistiques de ventes, les marges, les exports, les journaux d'activité et un éditeur visuel complet de composition des offres sont des évolutions distinctes. Aucun chiffre de vente fictif n'est affiché dans cette première version.
