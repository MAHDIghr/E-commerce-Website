# Lot 3 — préserver le checkout et invalider les devis

Base : `fix/commercial-information`, commit `c8e86d017b96d5df9093c84f184c1e5a622b6df6`. Un seul nouveau commit sur cette branche. Aucun déploiement, fusion ou paiement réel.

## Constat et contrat avant/après

Les instructions des README, les fichiers demandés, leurs templates, styles, scripts, routes, services et tests ont été lus. La branche distante a été vérifiée avant les modifications ; aucun AGENTS.md dans le dépôt.

La perte de saisie a été reproduite par un test HTTP sur le commit de départ dans une copie isolée : la soumission promo redirigeait vers GET, le code restait appliqué mais l’adresse « 15 rue PRIVEE » disparaissait du formulaire. Après modification de quantité, un nouveau GET ne contenait pas davantage cette adresse. Ce test de reproduction a exécuté un scénario avec succès, en vérifiant volontairement l’ancien défaut. La lecture du JavaScript a confirmé le rechargement aveugle sur `cart:updated` et l’absence d’effacement des anciens totaux en cas de destination effacée ou d’erreur réseau.

Avant : POST promo puis redirection ; GET de devis avec destination dans l’URL ; rechargement de tout le checkout après mutation du panier. Les champs du formulaire n’étaient pas conservés. Les prix et remises provenaient déjà du serveur.

Après : le formulaire de coordonnées reste en place. Les mises à jour asynchrones font un POST vers la même vue checkout avec `X-Checkout-Update: 1`, CSRF, pays/code postal et mode de livraison ; une action promo ajoute seulement son action et son code. Le serveur revalide panier, lignes, disponibilité, promotion et livraison, puis renvoie un fragment de résumé échappé et les options avec leurs montants calculés. Le navigateur formate les montants renvoyés sans calculer prix ou remises.

Contrat JSON : `summary_html`, `options` (method/label/amount/total), `quote_valid`, `can_pay`, `errors`, `cart_error`, `promo_error`. Aucun nom, adresse complète ou e-mail n’est renvoyé par cette réponse partielle. `ShippingQuoteForm` valide exclusivement pays/code postal ; le devis ne dépend pas du nom.

Sans JavaScript, les contrôles promo sont associés au formulaire principal grâce à l’attribut HTML `form`. Leur soumission contient les champs nécessaires, marqués `checkout_fields_present=1`. Le serveur les réaffiche dans la même réponse, sans valider prématurément les champs de paiement et sans les copier en session. Les anciens POST promo autonomes restent compatibles avec leur redirection existante.

## Comportement obtenu

- Application/retrait promo et changements du panier actualisent le résumé sans remplacer les champs de coordonnées. La facturation distincte et les cases cochées sont conservées. Le brouillon de code promo et son curseur survivent aussi à un rafraîchissement indépendant.
- Dès qu’une destination, une remise ou le panier change : anciennes options retirées, frais et total affichés « À recalculer », paiement désactivé. Les mutations panier annoncent leur début et leur fin, y compris sur échec.
- Les lectures obsolètes sont annulées via AbortController et leurs réponses ignorées par numéro de révision. Les actions promo sont sérialisées et ne sont pas interrompues en vol : une annulation réseau ne prouverait pas l’annulation de la mutation serveur.
- En erreur réseau : aucun ancien tarif confirmé, coordonnées conservées, message accessible et bouton Réessayer. Une réponse valide rétablit les options et les estimations serveur.
- Les erreurs serveur conservent les valeurs et sont reliées aux champs et à un résumé accessible. Le focus va au résumé après refus, ou au statut promo après son action. Les champs corrigés retirent leur ancienne erreur. Les liens et champs ciblés ont une marge de défilement pour le header fixe ; rendu réel à vérifier.
- L’état d’envoi bloque les doubles soumissions. `pageshow` remet les contrôles en état et demande une nouvelle validation ; les scénarios de retour arrière simulé conservent les nœuds et valeurs. La restauration effective d’une page par le navigateur dépend de son comportement de cache : elle reste à vérifier dans les navigateurs cibles.
- Entrée dans le champ promo applique le code, sans déclencher le paiement.

## Fichiers modifiés et raisons

| Fichier | Raison |
| --- | --- |
| `checkout/views.py` | Réponses partielles CSRF, revalidation serveur, fallback conservant les champs sans persistance, cache privé/no-store. Le chemin de paiement et son verrou commercial restent actifs. |
| `checkout/forms.py` | Formulaire de destination indépendant de l’identité. Aucun changement de modèle. |
| `checkout/templates/checkout.html` | Formulaire principal unique pour coordonnées et actions promo, résumé d’erreurs, associations ARIA, identifiants des champs, statut et reprise. |
| `checkout/templates/checkout/_summary.html` | Résumé partagé entre réponse complète et partielle, valeurs de devis invalides explicitement indisponibles. |
| `checkout/static/checkout/checkout-summary.js` | Actualisations en place, gestion des courses et annulations, états invalide/envoi/reprise, focus et retour arrière. |
| `checkout/static/checkout/checkout.css` | Sélecteurs adaptés au fragment, erreurs, contrôles de 44 px et marge de focus. |
| `static/js/base.js` | Événements `cart:changing` et `cart:settled` autour de la file de mutations existante ; aucune modification des prix ou du contenu des requêtes panier. |
| `checkout/test_preservation.py` | Neuf tests serveur sur conservation, confidentialité, calcul indépendant du nom, panier/stock, CSRF, erreurs, formulaire unique et blocage des ventes. |
| `tests/checkout-summary.test.cjs` | Dix simulations DOM/réseau : promo, devis périmé, courses, erreur/reprise, panier, doubles soumissions, retour arrière, blocage commercial, brouillon et clavier. |
| `README.md` | Nouveau contrat et commandes de recette. |
| `docs/checkout-preservation-report.md` | Présent relevé de preuves et limites. |

## Commandes et résultats réellement exécutés

Django utilise l’environnement isolé installé depuis `requirements.txt`, Python 3.12 et `DJANGO_SECRET_KEY=local-tests-only`. Aucun ajout de dépendance de production. Node utilisé : v24.22.1. Pour exercer le vrai DOM et ses associations de formulaire en l’absence de Chromium, jsdom 30.1.3 a été installé uniquement dans un répertoire de tests temporaire extérieur au dépôt.

| Commande / contrôle | Résultat |
| --- | --- |
| Test HTTP de reproduction sur c8e86d0 | 1 scénario exécuté, confirme la perte d’adresse avant correction. |
| `python manage.py test checkout pages --settings=config.settings.development --verbosity=1` première passe | 83 tests ; une assertion dépendait de l’ordre exact des attributs du bouton désactivé. Ordre HTML ajusté ; blocage conservé. |
| `python manage.py test checkout.test_preservation --settings=config.settings.development --verbosity=1` après ajustements | 9 tests, OK, 0,438 s. |
| `python manage.py test --settings=config.settings.development --verbosity=1` | **196 tests Django, OK, 10,837 s.** Exécution nouvelle ; les 172 tests de l’audit ne sont pas repris comme validation actuelle. |
| `python manage.py test checkout.test_preservation checkout.tests.CheckoutIntegrationTests.test_applied_promo_is_rendered_with_remove_control_and_server_totals --settings=config.settings.development --verbosity=1` après dernières retouches de rendu/confidentialité | **10 tests, OK, 0,556 s.** |
| `NODE_PATH=../checkout-test-runtime/node_modules node --test tests/checkout-summary.test.cjs` après dernier ajout clavier | **10 tests JavaScript, OK, 1,379 s.** |
| `python manage.py check --settings=config.settings.development` | Aucun problème. |
| `python manage.py makemigrations --check --dry-run --settings=config.settings.development` | Aucune modification détectée ; aucun modèle ni migration modifié. |
| `node --check checkout/static/checkout/checkout-summary.js` et `node --check static/js/base.js` | Succès. |
| `git diff --check` | Succès. |
| Lancement Playwright Chromium | Impossible : exécutable chromium_headless_shell absent. Aucun essai visuel réalisé. |

Les messages de scénarios de notification en échec et de webhook en reprise sont attendus ; la suite se termine par OK. Les simulations DOM vérifient la conservation du même nœud d’adresse, les champs envoyés par POST, les montants retirés immédiatement, une réponse tardive ignorée, une réponse récente acceptée, le réseau en panne et la reprise, les doubles soumissions, la touche Entrée et `pageshow` avec `persisted=true`. Elles ne mesurent ni mise en page ni support réel d’un lecteur d’écran.

## Protections contrôlées

Les prix, remises, stock et frais restent revalidés par les services existants. Aucun prix du navigateur ne fait foi. Aucun changement de `checkout/services.py`, des clés d’idempotence, de la signature du webhook ou de Stripe Checkout hébergé. Les tests des lots précédents font partie de la suite complète. Les mises à jour ne créent ni commande, ni réservation, ni paiement. Le verrou commercial est testé : même avec un devis valide, `can_pay` reste faux sans dossier approuvé et un POST de paiement ne crée rien.

Les nouveaux appels sont des POST avec CSRF ; ils n’inscrivent pas le code postal dans une URL. Aucun localStorage/sessionStorage de coordonnées, aucune nouvelle journalisation de formulaire, aucun brouillon de coordonnées en session. Les fragments passent par l’échappement Django et les messages DOM par `textContent`. Les réponses contenant du formulaire ou du résumé portent `Cache-Control: private, no-store`.

L’ancienne route GET `/checkout/livraison/devis/` reste disponible pour compatibilité ; le checkout n’y envoie plus la destination. Les clients externes éventuels et leur journalisation restent à examiner séparément.

## Recette restante

**Aucune capture ; aucune largeur vérifiée dans un vrai navigateur.** Recette requise à **320, 360, 390, 430, 768 et 1366 px** : coordonnées après promo/retrait et quantités, facturation distincte, résumé ouvert/fermé, absence de débordement et focus non masqué. Vérifier réseau lent/hors ligne, retour arrière réel avec et sans restauration de page, paiement de test uniquement, annonces du lecteur d’écran et reprise après un refus serveur. Ne pas déduire ces résultats de jsdom, du CSS ou de `overflow-x:hidden`.

Le dossier commercial/juridique précédent demeure absent : les ventes restent fermées. Aucune décision métier nouvelle ni promotion publique créée. Le lot est vérifié automatiquement et reste en attente de recette navigateur ; il n’est pas déclaré entièrement validé.

## Rejouer les tests

```bash
python manage.py test checkout.test_preservation --settings=config.settings.development
python manage.py test --settings=config.settings.development
npm install --prefix ../checkout-test-runtime --no-save --package-lock=false jsdom@30.1.3
NODE_PATH=../checkout-test-runtime/node_modules node --test tests/checkout-summary.test.cjs
```

Pour la dernière commande dans PowerShell :

```powershell
$env:NODE_PATH = (Resolve-Path ../checkout-test-runtime/node_modules).Path
node --test tests/checkout-summary.test.cjs
```

jsdom 30.1.3 demande une version de Node compatible ; ici les tests ont été exécutés avec Node 24.22.1. Cette dépendance sert uniquement à la recette DOM et n’est pas nécessaire au fonctionnement Django.
