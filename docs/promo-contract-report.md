# Lot 2 — contrat des promotions

Base confirmée : `fix/commercial-information`, commit `49d13d1ae256b09559cae339de6a505f43388ddf`. Les changements de ce lot constituent un seul commit supplémentaire sur cette même branche. Aucun déploiement, fusion ou paiement réel.

## Constat et contrat

Le constat est encore présent sur la branche de départ : `checkout/views.py` expose l’objet `PromoCode` sous la clé de contexte `promo_code`, alors que le template utilise `promo`. Le calcul serveur est correct mais le champ n’est pas prérempli, le code manque au récapitulatif et le contrôle Retirer n’est pas rendu. Un test de rendu ajouté pendant la préparation a reproduit l’échec sur `value="CONTRAT20"`. Le même décalage a été confirmé par lecture du code au commit de départ finalement demandé.

Les instructions des README et les fichiers concernés, leurs routes, formulaire, CSS/JavaScript, modèle PromoCode, services et tests existants ont été consultés. Pas de fichier AGENTS.md dans le dépôt.

Contrat conservé : le POST `promo_code` et la session `checkout_promo_code` transportent uniquement la chaîne du code. `apply_promo_code` lit les règles en base et retourne `(objet PromoCode, remise Decimal)` ; les prix viennent des offres en base, le panier de la session serveur. Le nom de contexte pour l’objet est désormais **`promo`** dans la vue et le template. `promo_discount`, `discounted_subtotal`, `estimated_shipping` et `estimated_total` sont des montants calculés côté serveur. Le POST et la session ne contiennent aucun montant de remise faisant foi.

Le retrait supprime le code et la clé de tentative de paiement ; la redirection relit le panier, recalcule la remise, les modes de livraison et le total. Un code devenu invalide lors de la revalidation est également retiré et invalide cette clé. Une tentative de remplacement invalide conserve le code valide précédemment appliqué et affiche une erreur, sans réafficher la saisie brute.

## Avant / après

| État | Résultat après correction |
| --- | --- |
| Promotion valide | Code prérempli et affiché, contrôle Retirer rendu, accordéon promo ouvert même après rafraîchissement, remise et sous-total remisé affichés. |
| Réponse sur mobile | Le script conserve le récapitulatif ouvert si le panneau promo est ouvert (code actif ou résultat), pour ne pas masquer le contrôle. Rendu navigateur restant à vérifier. |
| Succès / retrait | Message de succès dans un statut `role="status"`, `aria-live="polite"`, `aria-atomic="true"`. |
| Code inconnu ou mal formé | Message « Ce code promo n’est pas valide. » dans ce même statut, avec classe d’erreur. |
| Code expiré | Message distinct « Ce code promo a expiré. ». |
| Promotion non applicable | Message distinct pour promotion inactive/future ; les messages existants de minimum, plafond nul ou utilisation par e-mail sont préservés. |
| Saisie vide | Erreur explicite ; plus d’accès à `.code` sur `None`. |
| Mode express sur un formulaire invalide | Estimation HTML calculée avec le mode express soumis s’il fait partie des choix serveur, et non avec le standard par défaut. Aucun montant navigateur utilisé. |

Les formules, arrondis, minimums, plafonds et restrictions par e-mail de `apply_promo_code` sont conservés. Sa validation sépare les causes de refus ; le verrou `select_for_update` reste appliqué lorsque demandé.

## Critère monétaire vérifié

Le code **CONTRAT20 n’existe que dans les tests** ; aucun enregistrement de promotion publique n’a été ajouté.

| Étape | Montant vérifié |
| --- | ---: |
| Sous-total | 89,90 € |
| Remise 20 % affichée dans le HTML | −17,98 € |
| Sous-total après remise affiché | 71,92 € |
| Livraison standard configurée | 4,90 € |
| Total standard affiché dans le HTML et reçu du devis serveur | 76,82 € |
| Livraison express configurée | 9,90 € |
| Total express affiché dans le HTML et reçu du devis serveur | 81,82 € |
| Après retrait | 89,90 €, livraison offerte |

## Fichiers modifiés

| Fichier | Raison |
| --- | --- |
| `checkout/views.py` | Clé de contexte cohérente, succès/erreur séparés, saisie vide traitée, revalidation et invalidation de tentative, estimation selon le mode serveur sélectionné. |
| `checkout/templates/checkout.html` | Statut accessible, code/Retirer correctement rendus grâce au contrat, sous-total remisé et frais chiffrés. |
| `checkout/services.py` | Messages distincts invalide/expiré/non applicable, sans changer le calcul ni les règles d’éligibilité. |
| `checkout/tests.py` | Sept nouveaux tests d’intégration : rendu exact et devis, retrait et gratuité, causes d’erreurs, remplacement invalide et rafraîchissement, expiration après application, express et prix client falsifié, CSRF du retrait et absence de réservation. |
| `checkout/static/checkout/checkout-summary.js` | Ne pas refermer le récapitulatif mobile lorsqu’une promotion ou son résultat doit être visible. Aucun calcul de prix ajouté au navigateur. |
| `checkout/static/checkout/checkout.css` | Contrôle Retirer de 44 px minimum, retour à la ligne des codes longs. |
| `README.md` | Documentation du contrat et de la recette locale. |
| `docs/promo-contract-report.md` | Présent compte rendu. |

## Commandes et résultats réellement exécutés

Environnement isolé déjà installé depuis `requirements.txt`, utilisé avec `DJANGO_SECRET_KEY=local-tests-only`. Aucun ajout de dépendance. Les commandes Python ci-dessous ont été exécutées avec `../venv/bin/python`.

| Commande | Résultat |
| --- | --- |
| `python manage.py test checkout.tests.CheckoutIntegrationTests.test_applied_promo_is_rendered_with_remove_control_and_server_totals --settings=config.settings.development --verbosity=1` avant correction pendant la préparation | 1 test exécuté, échec attendu : code absent de la valeur du champ HTML. |
| `python manage.py test checkout --settings=config.settings.development --verbosity=1` pendant la préparation isolée | 66 tests puis 72 tests exécutés, tous réussis aux étapes correspondantes. |
| `python manage.py test --settings=config.settings.development --verbosity=1` sur la préparation initiale issue de developpement-backend | 179 tests, OK, 10,769 s. Ce résultat ne remplace pas celui sur la base finale ci-dessous. |
| `python manage.py test checkout home.test_frontend_assets --settings=config.settings.development --verbosity=1` sur cette préparation après retouches CSS/JS | 74 tests, OK, 4,550 s. |
| `python manage.py test --settings=config.settings.development --verbosity=1` **après report sur fix/commercial-information** | **187 tests, OK, 10,741 s**. Validation nouvelle du lot et des protections précédentes ; aucun ancien résultat repris comme validation actuelle. |
| `python manage.py check --settings=config.settings.development` sur la base finale | Aucun problème signalé. |
| `python manage.py makemigrations --check --dry-run --settings=config.settings.development` sur la base finale | Aucune modification détectée ; aucun modèle ni migration changé. |
| `node --check checkout/static/checkout/checkout-summary.js` | Succès. |
| `git diff --check` | Succès. |
| Tentative `chromium.launch({headless:true})` via Playwright installé dans l’environnement | Échec : exécutable Chromium absent. Aucun essai de page dans un navigateur effectué. |

Les scénarios de montants/signatures/idempotence, stock, CSRF, publication et blocage commercial sont inclus dans la suite finale. Les messages de notification en échec et de webhook en reprise font partie de scénarios attendus ; résultat global `OK`.

## Revue et protections

Diff limité au contrat promo, à son rendu et à ses tests/documentation. Les calculs restent en Decimal côté serveur. Le test express soumet notamment un faux `total=0.01` et un faux `discount=89.90` : ils ne modifient pas les montants rendus. Le devis est aussi testé avec un faux sous-total.

Les actions promo ne créent ni commande, ni session Stripe, ni réservation de stock. Le retrait est soumis à CSRF, avec vérification de rejet sans jeton et de succès avec jeton valide. Le code normalisé est stocké dans la session ; aucune donnée personnelle ni secret n’est ajouté au localStorage ou aux journaux. Les variables du template restent échappées ; les messages de refus n’injectent pas la saisie brute. Aucune modification des webhooks signés, de l’idempotence, de Stripe Checkout hébergé ou du verrou commercial du lot 1.

## Vérifications restantes et recette locale

**Aucune capture et aucune largeur vérifiée dans un navigateur.** Contrôler à **320, 360, 390, 430, 768 et 1366 px** : bloc ouvert avec promotion, code long, contrôle Retirer, retour à la gratuité, absence de débordement et de focus masqué ; vérifier les annonces avec un lecteur d’écran réel. La lecture du CSS et les tests HTML ne prouvent pas ces critères visuels.

La conservation des coordonnées lors d’application/retrait reste pour le **Prompt 3** : la redirection POST/GET existante est conservée. Aucune décision métier nouvelle n’a été prise et aucune offre 20 % publiée. Le dossier commercial/juridique du lot 1 reste manquant : les ventes demeurent fermées sur la configuration livrée.

Depuis PowerShell, dans le dépôt local (conserver d’abord tout travail local non commité) :

```powershell
git fetch origin
git switch fix/commercial-information
git pull --ff-only origin fix/commercial-information
.\venv\Scripts\Activate.ps1
$env:DJANGO_SECRET_KEY = "local-development-only"
python manage.py migrate --settings=config.settings.development
python manage.py runserver --settings=config.settings.development
```

Si nécessaire, créer l’environnement avec `py -m venv venv` avant activation, puis `python -m pip install -r requirements.txt`. Si la branche n’existe pas encore localement, `git switch --track origin/fix/commercial-information` remplace `git switch`.

Ouvrir http://127.0.0.1:8000/, ajouter un produit réellement publié au panier et consulter le checkout. Le scénario exact à 20 % se reproduit sans créer d’offre publique avec :

```powershell
python manage.py test checkout.tests.CheckoutIntegrationTests.test_applied_promo_is_rendered_with_remove_control_and_server_totals --settings=config.settings.development --verbosity=2
```

Ce test utilise une base temporaire détruite à la fin ; il n’ajoute rien à la base locale. Ne pas désactiver le verrou commercial pour effectuer cette recette automatique.
