# Compte rendu — informations avant vente

Branche : `fix/commercial-information`, issue de `developpement-backend` au commit `a9c854edc764ceb65867b9a156c0f8d13b1b5fab`. Aucun déploiement, fusion ou paiement réel.

## Constat reproduit avant modification

L’accès GitHub a confirmé que la branche de départ correspondait encore au commit audité. Aucune instruction AGENTS.md n’a été trouvée dans le dépôt ; les règles de contribution des deux README, les templates/CSS/JS associés, les routes, les vues/services, le formulaire et les tests concernés ont été lus.

Recensement dans les sources de départ (nombre d’occurrences textuelles, y compris traductions et métadonnées ; les données d’une éventuelle base de production ne sont pas accessibles) :

| Fichier | Constat | Occurrences |
| --- | --- | --- |
| `pages/views.py` | Champs à compléter | 25 |
| `templates/partials/_footer.html` | Champs à compléter | 3 |
| `home/templates/home.html` | Promesse 30 jours | 1 |
| `home/templates/home.html` | Sans condition / équivalent | 1 |
| `home/templates/home.html` | Disponibilité 7j/7 | 1 |
| `home/templates/home.html` | Cuir généralisé | 1 |
| `home/templates/home.html` | Faux compte social | 2 |
| `shop/templates/catalog.html` | Promesse 30 jours | 3 |
| `shop/templates/catalog.html` | Sans condition / équivalent | 1 |
| `shop/templates/catalog.html` | Cuir généralisé | 1 |
| `product/templates/product.html` | Promesse 30 jours | 1 |
| `static/js/base.js` | Promesse 30 jours | 4 |
| `static/js/base.js` | Disponibilité 7j/7 | 4 |
| `static/js/base.js` | Cuir généralisé | 2 |
| `static/js/base.js` | Faux compte social | 2 |
| `shop/static/js/shop.js` | Promesse 30 jours | 4 |
| `shop/static/js/shop.js` | Sans condition / équivalent | 2 |
| `shop/static/js/shop.js` | Cuir généralisé | 2 |

Liens : le footer possédait trois coordonnées factices et un vrai lien `pages:contact`, mais la page contact n’avait aucune coordonnée validée. Les pages légales avaient des routes réelles mais servaient leurs trames. Le CTA communautaire utilisait `href="#"`. Le bouton « En savoir plus » pointait sur des témoignages via `#about`, corrigé vers `pages:about`. Les liens des stories/reels restent les déclencheurs du lecteur vidéo existant, hors de ce lot ; ce ne sont pas des liens de contact. Le libellé administratif de livraison des offres n’était pas le tarif calculé, et pouvait contredire le checkout.

## Contrat de données avant/après

Avant : prix des offres et stocks en base, panier en session ; prix/remise/frais recalculés par les services Django. `config/commercial.py` fournit devise EUR, seuil, frais, délais configurés et promotion BIENVENUE issue de la base. Pays autorisés définis par `checkout.forms.COUNTRIES`. Le HTML et plusieurs dictionnaires JavaScript ajoutaient des engagements sans source validée. Les pages d’information avaient un dictionnaire de trames dans la vue.

Après : ce contrat de prix/panier/promotion reste inchangé. Une configuration Django `COMMERCIAL_INFORMATION` contient l’approbation humaine, sa référence, l’e-mail de contact, les paragraphes approuvés et une copie des règles de livraison approuvées. Elle est vide par défaut. Le code refuse de publier un dossier partiel/non approuvé, un e-mail invalide, un marqueur « À COMPLÉTER » ou une configuration de livraison différente. Le code ne peut pas vérifier le sens juridique des textes : aucune certification automatique n’est annoncée.

Un composant unique présente les mêmes liens et le même état commercial sur l’accueil, le catalogue, la fiche, le panier et le checkout. Les promesses non confirmées sont retirées du HTML, des métadonnées et des traductions. Les libellés de livraison des offres utilisent le même message serveur. Les trames demeurent uniquement dans le dossier interne de validation.

Sans dossier complet : les routes d’information restent consultables mais affichent une indisponibilité factuelle et `noindex`. Le bouton de paiement est désactivé. Un POST direct et les services de création/réservation et de session Stripe refusent la prise de commande. Les CGV et retours restent accessibles, sans prétendre que leur contenu est finalisé. Aucun mailto vide ni contact inventé.

## Fichiers modifiés et raison

| Fichier | Changement |
| --- | --- |
| `config/commercial.py` | Contrat de publication, vérification du dossier et de la configuration de livraison, message commercial commun. |
| `config/settings/base.py` | Configuration fermée par défaut, sans données ni approbation fictives. |
| `pages/views.py` | Retrait des trames publiques, lecture exclusive du contenu approuvé. |
| `pages/templates/pages/information_page.html` | État indisponible factuel, paragraphes échappés, suivi des commandes accessible. |
| `pages/static/pages/pages.css` | Texte des pages d’information porté à 1rem. |
| `templates/partials/_commercial_information.html` | Composant commun de liens livraison/retours/CGV/contact. |
| `templates/partials/_footer.html` | Retrait des coordonnées factices et de PayPal non confirmé ; contact e-mail seulement si validé ; composant commun. |
| `templates/partials/_promo_bar.html` | Message serveur, absence de promesse de frais non approuvés. |
| `templates/partials/_cart_drawer.html` | Informations communes et progression de livraison uniquement après validation. |
| `templates/cart_page.html` | Accès aux informations avant commande. |
| `home/templates/home.html` | Retrait des promesses non validées, du compte fictif et de son CTA ; vrai lien À propos. |
| `home/static/css/home.css` | Couleur du composant commun sur fond sombre. |
| `shop/templates/catalog.html` | Métadonnées et accroche sans promesses ; informations communes. |
| `shop/static/js/shop.js` | Suppression des affirmations FR/EN et état du rappel panier cohérent. |
| `product/templates/product.html` | Informations communes et vrai lien retours à la place de la promesse 30 jours. |
| `product/views.py` | Libellé de livraison issu de la source commune. |
| `shop/views.py` | Même libellé pour l’API de choix d’offres, aucun changement de prix. |
| `static/js/base.js` | Traductions nettoyées ; aucun rétablissement des anciennes promesses à la bascule de langue. |
| `static/css/base.css` | Composant partagé : texte 1rem, liens de 44px, retour à la ligne et focus visible ; espacement du tiroir. |
| `checkout/templates/checkout.html` | Liens avant paiement, état fermé explicite, bouton désactivé, suppression du traitement prioritaire non confirmé. |
| `checkout/views.py` | Refus du paiement tant que le dossier est absent/non approuvé. |
| `checkout/services.py` | Verrou avant réservation et avant création Stripe, y compris appels directs. |
| `pages/tests.py` | Mise à jour des assertions de l’ancien comportement de brouillons publics. |
| `home/test_public_pages.py` | Même mise à jour pour les pages légales indisponibles. |
| `pages/test_commercial_information.py` | Huit tests du contrat de publication, de l’échappement, du verrou et des liens. |
| `checkout/tests.py` | Configuration approuvée fictive limitée à la classe d’intégration pour conserver les tests du parcours ouvert. |
| `docs/commercial-information-review.md` | Anciennes trames conservées hors routes, liste regroupée des décisions et procédure de configuration. |
| `README.md` | Documentation du nouveau comportement et lien vers le dossier. |
| `docs/commercial-lot-report.md` | Présent relevé de modifications, de preuves et de limites. |

## Tests et commandes réellement exécutés

Python 3.12, dépendances installées dans un environnement isolé avec `python -m venv ../venv` puis `../venv/bin/pip install -r requirements.txt`. Aucun ajout à `requirements.txt`. Les commandes Django ont utilisé `DJANGO_SECRET_KEY=local-tests-only` et `--settings=config.settings.development` ; cette valeur est uniquement un paramètre local de test.

| Commande | Résultat |
| --- | --- |
| `python manage.py test --settings=config.settings.development --verbosity=1` avant modification | **172 tests, OK, 10,099 s**. Exécution nouvelle, distincte de l’audit. |
| `python manage.py test pages checkout home.test_public_pages home.test_frontend_assets --settings=config.settings.development --verbosity=1` première passe | 84 tests ; 5 échecs d’assertion liés à un produit de test resté inactif par défaut. Fixture corrigée en déclarant explicitement `is_active=True`. Aucun comportement de publication du produit n’a été assoupli. |
| `python manage.py test pages --settings=config.settings.development --verbosity=1` après correction de fixture | **11 tests, OK, 0,428 s**. |
| `python manage.py test --settings=config.settings.development --verbosity=1` après implémentation | **180 tests, OK, 9,987 s**. |
| `python manage.py test pages product home checkout --settings=config.settings.development --verbosity=1` après dernières retouches CSS/markup et garde de type d’e-mail | **130 tests, OK, 4,705 s** sur le diff final fonctionnel. |
| `python manage.py check --settings=config.settings.development` | Aucun problème signalé, y compris après les dernières retouches. |
| `python manage.py makemigrations --check --dry-run --settings=config.settings.development` | Aucune modification détectée. Aucun modèle ni migration modifiés. |
| `node --check static/js/base.js` et `node --check shop/static/js/shop.js` | Succès, sur les scripts modifiés. |
| `git diff --check` | Succès. |

Les messages de scénarios de notifications en échec et de webhook en reprise sont des cas de test attendus ; la suite se termine par `OK`. Stripe est simulé dans les tests, sans appel de paiement réel.

Les tests Django parcourent les liens internes réellement rendus depuis le checkout (réponse finale 200 après redirection), CGV et retours inclus, et vérifient que le panier est conservé. Ce sont des essais HTTP serveur, pas des clics dans un navigateur. Les nouveaux tests portent sur le verrou métier, le contrat et la sécurité de rendu ; aucun test ajouté uniquement pour figer une phrase décorative.

## Contrôle du code et protections

Le diff ne change ni les prix/remises, ni les validations de stock, ni les mises à jour atomiques, ni les clés d’idempotence, ni la vérification de signature des webhooks. Il ajoute seulement des refus avant création lorsque le dossier manque. CSRF conservé sur les formulaires et POST ; l’exemption du webhook reste associée à sa vérification de signature existante. Stripe Checkout reste hébergé. Les tests existants de montants, remises, stock/réservation, CSRF, événements répétés et signatures ont été exécutés.

Les nouvelles données publiques passent par les variables échappées de Django ; les messages JavaScript utilisent `textContent`/le JSON déjà sérialisé avec `json_script`. Aucun nouveau stockage de coordonnées/secrets ni nouvelle journalisation de formulaires. La référence interne d’approbation et les textes non approuvés ne sont pas ajoutés au JSON public. Les liens de contact réels dépendent du dossier approuvé ; l’e-mail n’est pas inventé.

## Navigateur et vérifications restantes

**Aucune largeur réellement vérifiée, aucune capture.** Chromium n’est pas présent dans l’environnement. La commande `node "$CODEX_PRIMARY_RUNTIME_NODE_MODULES/playwright/cli.js" install chromium` a échoué : téléchargement renvoyant une archive vide/invalide (`End of central directory record signature not found`). Aucun résultat visuel n’est déduit de la lecture du CSS ou de `overflow-x:hidden` préexistant.

Recette encore requise aux **320, 360, 390, 430, 768 et 1366 px** : accueil, catalogue, fiche, panier/tiroir, checkout, pages d’information ; bascule FR/EN ; focus clavier, absence de focus recouvert par les barres fixes, lisibilité, liens tactiles, débordements réels et navigation depuis le checkout. Vérifier également la console et les liens externes après fourniture des coordonnées officielles.

Le dossier métier/juridique et les médias ne sont pas disponibles. **Le lot n’est pas intégralement validé et les ventes doivent rester fermées.** Les CGV/retours à URL réelle sont encore indisponibles dans l’état livré. La liste regroupée des informations à transmettre est dans `docs/commercial-information-review.md` ; la politique commerciale de retour doit y être traitée séparément du droit de rétractation et des garanties.

Relire également les données éditoriales administrées (matières, origines, textes libres, FAQ) sur la vraie base, absente de cet environnement. Ce lot ne valide ni la conformité du traitement newsletter ni les médias communautaires déjà présents. Les sessions Stripe créées avant une fermeture ne sont pas expirées automatiquement : contrôle d’exploitation séparé si nécessaire. Aucun déploiement ni fusion n’a été réalisé.
