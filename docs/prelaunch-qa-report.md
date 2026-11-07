# Lot 13 — Recette avant lancement

Date du compte rendu : 5 novembre 2026. Branche existante `fix/commercial-information` (la mention `fix/comercial-information` du prompt est traitée comme une coquille). Version de départ : `97a5ec653a5ec3f5a371338aa058f9d4ce78a8d2` ; le diff de ce rapport identifie la version du harnais de recette.

## Décision : NO-GO

La recette de lancement n'est pas validée. Les tests serveur passent, mais il n'existe pas ici de preuve de parcours navigateur ni Stripe réel en mode test. Plusieurs points prioritaires demeurent ouverts. Aucun déploiement, fusion ou paiement réel effectué ; le blocage commercial existant reste actif.

## Contrat avant / après et fichiers

La CI exécutait déjà check, migrations et suite Django. Ces étapes sont conservées. Elle accepte désormais un déclenchement manuel avec `browser_qa=true`, ainsi que les pushes de la branche de correction pour le job serveur. Le job navigateur installe Playwright 1.62.1 (version constatée dans le runtime local) et Chromium dans un environnement de test, démarre un serveur Django de test et conserve les preuves produites en artifact. Aucun workflow n'a été déclenché manuellement ici ; son succès distant n'est pas revendiqué.

- `.github/workflows/django-checks.yml` : conservation des vérifications existantes et job navigateur manuel isolé, limité à 15 minutes, sans déploiement.
- `qa/__init__.py` : package de recette.
- `qa/browser_runner.py` : StaticLiveServerTestCase avec catalogue, nom long et promotion fictifs dans une base de test ; aucune donnée réelle modifiée. Le fichier est lancé explicitement et ne se confond pas avec la suite serveur par défaut.
- `qa/journeys.cjs` : parcours Chromium à 320/390/1366 px, captures et résultats UTC si le navigateur démarre. Refus d'une cible autre que localhost/127.0.0.1 ; aucun clic de paiement ni création de session Stripe.
- `.gitignore` : exclusion de qa-output, qui peut contenir des champs fictifs de checkout et des captures volumineuses.
- `README.md` et ce rapport : fonctionnement, verdict, preuves et contrôles restants.

Les fichiers de tests existants checkout/tests.py, shop/tests.py, product/tests.py et home/test_frontend_assets.py ont été relus ; ils restent conservés. Aucun changement de modèles, prix, promotions publiques, stock, paiement ou webhook.

## Exécution locale réelle

```bash
DJANGO_SECRET_KEY=local-tests-only ../venv/bin/python manage.py test --settings=config.settings.development
DJANGO_SECRET_KEY=local-tests-only ../venv/bin/python manage.py check --settings=config.settings.development
DJANGO_SECRET_KEY=local-tests-only ../venv/bin/python manage.py makemigrations --check --dry-run --settings=config.settings.development
NODE_PATH="$CODEX_PRIMARY_RUNTIME_NODE_MODULES" DJANGO_SECRET_KEY=local-tests-only ../venv/bin/python manage.py test qa.browser_runner --settings=config.settings.development
node --check qa/journeys.cjs
git diff --check
```

- Suite serveur : **225 tests exécutés et réussis**, 16,063 s. Les 172 tests de l'audit ne sont pas repris comme un résultat courant.
- Check Django : aucun problème. Migrations : aucune modification détectée. Syntaxe du script navigateur et diff : réussis.
- Recette navigateur : **1 test lancé, 1 échec**, avant toute navigation : Playwright ne trouve pas `/root/.cache/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell`. Aucun scénario navigateur n'est considéré réussi.
- Playwright local identifié : 1.62.1. Chromium : absent. Appareil réel : aucun.
- **Aucune capture réelle disponible pour ce lot**, aucune des six largeurs validée. Aucune mesure Lighthouse/CWV, aucun scan automatique d'accessibilité, aucun essai lecteur d'écran ni appareil réel exécuté.

La preuve de panne est l'échec reproductible de la commande navigateur, pas une capture fabriquée. Un fichier capture présent ne doit jamais être considéré comme une recette réussie sans résultat associé.

## Matrice de recette et preuve

| Scénario | Attendu | Résultat / preuve actuelle | Responsable attendu |
|---|---|---|---|
| Suite Django et migrations | Pas de régression serveur | PASS : 225 tests et check/migrations | Développement |
| Accueil → fiche, catalogue → fiche | Liens réels et produit accessible | HTTP couvert dans la suite ; parcours navigateur BLOQUÉ | QA / développement |
| Fiche → panier → checkout | Offre ajoutée, panier conservé | Script navigateur préparé, non exécuté | QA |
| Promo QA20 visible/retrait | Remise 17,98 € sur fixture 89,90 €, code/Retirer visibles | Serveur couvert ; assertions navigateur non exécutées | QA |
| Conservation adresse | Même saisie après apply/remove | Serveur couvert ; navigateur non exécuté | QA |
| Destination effacée | Devis invalide, paiement désactivé | Script préparé, pas de preuve navigateur | QA |
| Catalogue sans JS | Cartes et formulaire GET fonctionnels | HTTP couvert ; contextes navigateur sans JS non exécutés | QA |
| Nom long / débordement | Pas de coupure ni scroll horizontal involontaire | Fixture + diagnostic scrollWidth préparés ; BLOQUÉ | QA / front |
| Offres avec accessoires / quantités / sections vides | Contenus utiles et quantités cohérentes | Cas serveur existants ; parcours navigateur dédié restant à compléter | Développement / QA |
| Confirmation commande + notification | État payé uniquement après preuve serveur, notification durable | Simulations serveur existantes ; pas de vraie session Stripe test | Développement / QA paiement |
| 360/430/768, clavier, zoom 200 %, lecteur d'écran | Focus, lisibilité, compréhension | NON TESTÉ | QA accessibilité |
| Safari iPhone / Chrome Android | Tunnel utilisable sur appareils | NON TESTÉ | QA mobile |
| Images cassées / liens inactifs / cibles tactiles / contraste | Inventaire sans défaut critique | Diagnostic intégré incomplet, recette manuelle nécessaire | QA / front |
| Lighthouse et CWV | Mesures comparables documentées | NON MESURÉ, aucune valeur inventée | Performance / exploitant |

Le script contrôle les erreurs JavaScript et console, conserve les nœuds du formulaire et vérifie un débordement global après retrait temporaire du masquage horizontal. Il ne remplace pas un inventaire de chaque élément débordant, un audit images/liens exhaustif ou une mesure des cibles tactiles. Aucune conformité globale ne découle des assertions.

## Stripe : frontière entre simulations et vraie recette

Les tests existants vérifient notamment les montants serveur, réservation/libération de stock, signatures invalides, événements dupliqués, événements arrivant avant association de session, montant/devise incohérents, échec asynchrone, retour navigateur non probant et snapshots de paiement. Ils inspectent états de commande et tentatives ; certains contrôlent les notifications durables. **Ils emploient des objets/SDK simulés : ce ne sont pas des paiements Stripe test réels.**

Reste à exécuter en préproduction autorisée avec clés de test injectées hors du dépôt : succès, refus, annulation, reprise, double clic, événement dupliqué/retardé, montant incohérent et stock insuffisant. Pour chaque cas enregistrer référence de commande, événement Stripe test, état et quantité de stock avant/après, statut de tentative et notification. Ne jamais déduire un paiement de la seule URL de retour. Aucun secret ou donnée de carte ne doit figurer dans le rapport/captures.

Il manque une URL de préproduction et son commit exact, la configuration test Stripe/webhook, les moyens d'observer commandes/notifications, la base réelle et les appareils autorisés. Aucun accès ni clé réel n'a été utilisé. Le harnais ajouté ne tente pas de substituer une simulation au checkout Stripe réel.

## Performance et accessibilité

Objectifs de travail fournis : LCP ≤ 2,5 s ; INP ≤ 200 ms ; CLS ≤ 0,1. Ils ne constituent pas un résultat mesuré. Avant/après doivent cibler le même appareil, navigateur/version, URL, contenu, réseau, CPU et état de cache, avec plusieurs passes et médiane conservée. Définir une version avant et après sur la même infrastructure.

Lighthouse est une mesure de laboratoire ; son TBT n'est pas une mesure réelle d'INP. Les CWV de terrain exigent des données réelles suffisamment représentatives ; aucun historique n'est disponible ici. Ne pas assimiler une passe locale à une preuve de CWV en production. Un scan automatique d'accessibilité reste à installer/exécuter, puis à compléter par clavier, zoom, lecteur d'écran et appareils réels.

## Défauts ouverts interdisant une conclusion de lancement

| Blocage | Statut | Responsable attendu |
|---|---|---|
| Dossier commercial/juridique et matrice livraison non validés | Ouvert ; ventes fermées | Exploitant + validation juridique |
| Réservations : expiration autonome et concurrence base réelle | Non implémenté/vérifié au lot 11 | Développement + exploitation |
| Suivi invité : jeton distinct révocable et transition des anciens liens | Non implémenté au lot 12 | Développement sécurité |
| FR/EN complet, URL et hreflang | Anglais non livré au lot 10 | Développement + éditorial |
| Cache partagé, quotas multi-processus, proxy/CDN et CSP | Validation infrastructure absente | Exploitation + développement |
| Recette navigateur / Stripe test / notifications | Bloquée ou non exécutée | QA + exploitation |

Ces responsables sont des rôles à affecter par l'exploitant, pas des personnes auxquelles un message aurait été envoyé. Aucun P0 n'est déclaré clos par ce rapport.

## Reprise reproductible

En CI : lancer manuellement « Django checks and tests » sur la branche voulue avec browser_qa=true ; consulter l'artifact local-browser-evidence et le log du job. Le job peut révéler des défauts du script lui-même, qui n'a pas pu parcourir les pages ici. Les tests non exécutés restent à valider.

En local Linux, avec les dépendances applicatives installées : installer Playwright 1.62.1 dans un préfixe temporaire, installer son Chromium, définir NODE_PATH vers ses node_modules, puis lancer explicitement qa.browser_runner comme ci-dessus. Le répertoire QA_OUTPUT_DIR optionnel reçoit captures et results.json horodatés en UTC. Utiliser uniquement les fixtures fournies ; aucune approbation commerciale fictive ne doit être copiée en configuration réelle.

Les protections prix/stock, CSRF, idempotence, webhook signé et paiement hébergé sont préservées. Aucun secret, coordonnée client réelle ou engagement commercial ajouté. Le code de recette modifie seulement la base de test éphémère. Aucun déploiement automatique ni paiement réel.
