# Lot 4 — Livraison et disponibilité du paiement

Branche : `fix/commercial-information`. Départ : `95fb8bb6f6fd54c4595aab8b97a1565bc00244ad`. Audit de référence : `a9c854edc764ceb65867b9a156c0f8d13b1b5fab`. Un nouveau commit pour ce lot ; aucun déploiement, fusion ou paiement réel.

## Constat et contrat avant modification

Lecture des instructions de contribution, des formulaires, vues, services, templates, scripts, modèles d’offres, construction des lignes panier et tests existants. Contrôle du code : `display_delivery_label` était explicitement descriptif ; ni le devis ni la commande ne l’utilisaient. Le formulaire et `shipping_price` dupliquaient la règle : sous-total après remise inférieur à 80 € → standard 4,90 € ou express 9,90 € ; sinon uniquement le mode `free`. Les pays incluaient CH/GB sans validation distincte. L’absence de configuration Stripe était annoncée après les champs, en termes techniques, et ne désactivait pas à elle seule le bouton HTML.

Aucune reproduction visuelle dans un navigateur n’est revendiquée.

## Décisions reçues et comportement après correction

- L’utilisateur a confirmé qu’une seule offre gratuite rend le standard gratuit pour **tout le panier**, y compris un panier mixte, sous le seuil et après remise.
- L’utilisateur a confirmé que l’express reste achetable au tarif configuré lorsque le standard est gratuit.
- L’utilisateur a indiqué que la matrice de livraison **n’est pas encore validée**. Les ventes restent bloquées ; aucune destination de livraison n’est proposée sans validation commerciale complète. Aucune configuration de production n’a été approuvée ou modifiée.

`shipping_choices` centralise les méthodes, libellés et montants ; le mode interne `free` désigne explicitement le standard offert. Les deux endpoints de devis, le formulaire et le service de création utilisent cette grille. Le service relit l’offre depuis les lignes validées et recalcule la remise et les frais avant réservation. Un indicateur de gratuité envoyé par le navigateur n’a aucun effet. Le panier expose une progression calculée après remise et tenant compte des offres gratuites. Le catalogue mobile ne déduit plus une promesse de gratuité du seul total avant remise.

La liste candidate par défaut est FR/BE/LU/DE/ES/IT/NL/PT, retirant CH/GB de la livraison par défaut. Elle n’est pas une validation de desserte : elle reste invisible dans le choix de livraison tant que l’approbation manque. CH/GB restent possibles comme **pays de facturation**, ce qui ne les autorise pas à la livraison. Une activation de destination exige une configuration explicite et une nouvelle approbation de son empreinte. Les codes postaux exclus sont refusés par le formulaire, les devis et le service de commande.

Les délais ne sont affichés qu’avec une approbation correspondante et leurs conditions. Aucun délai n’a été inventé. Aucun libellé « Traitement prioritaire » n’a été trouvé dans les templates/scripts du lot. La promesse résiduelle « SSL & 3D Secure » du catalogue FR/EN a été remplacée par « Stripe Checkout », sans promettre un moyen de paiement ou une authentification systématique.

Une configuration absente, un mode de clé incohérent ou une URL canonique invalide rend le paiement indisponible. L’avis « Paiement temporairement indisponible » apparaît avant les coordonnées ; le bouton porte ce libellé et est désactivé même sans JavaScript. Aucun détail de variable technique n’est affiché au client. Une configuration syntaxiquement cohérente ne garantit pas la disponibilité distante de Stripe.

## Fichiers modifiés et raison

| Fichier | Changement |
|---|---|
| `config/commercial.py` | Grille serveur unique, gratuité par offre, express payant, destinations approuvées, empreinte des exclusions/conditions/douanes et messages partagés. |
| `checkout/forms.py` | Choix de livraison issus de la grille ; mêmes refus de destination et d’exclusions pour formulaire et devis. |
| `checkout/services.py` | Calcul depuis l’offre relue en base, revalidation de destination à la création, disponibilité de configuration et erreurs de paiement non techniques. |
| `checkout/views.py` | Propagation de l’éligibilité serveur au formulaire, aux deux devis et au récapitulatif ; message de refus de paiement. |
| `checkout/templates/checkout.html` | Avis avant saisie, bouton désactivé et libellé adapté sans JavaScript. |
| `shop/views.py` | Indicateur d’offre issu de la base, API d’offres cohérente et progression panier après remise. |
| `product/views.py` | Mention de livraison de chaque offre alignée avec son effet réel. |
| `product/models.py` | Aide administrateur expliquant la portée financière du champ existant. |
| `product/migrations/0009_alter_productoffer_display_delivery_label.py` | Migration de l’aide du champ uniquement ; aucune transformation des données. |
| `static/js/base.js` | Progression utilisant les données serveur, standard/express explicités dans les messages FR/EN. |
| `shop/static/js/shop.js` | Retrait de la promesse 3D Secure et de la déduction de gratuité avant remise dans la barre mobile. |
| `templates/partials/_cart_drawer.html` | Message initial partagé au lieu d’une promesse partielle. |
| `checkout/test_shipping.py` | 11 tests de contrat, seuils, offres mixtes, refus de destination, disponibilité et payload Stripe simulé. |
| `checkout/tests.py` | Attentes adaptées à l’express maintenu et au message d’indisponibilité. |
| `checkout/test_preservation.py` | Attentes adaptées aux deux options et à l’absence de devis sans matrice approuvée. |
| `pages/test_commercial_information.py` | Construction du formulaire de test sous approbation fictive, puis vérification du verrou réel hors de cette approbation. |
| `tests/checkout-summary.test.cjs` | Régression standard offert / express payant, conservation du choix express et de l’adresse après actualisation. |
| `README.md` | Contrat et configuration actualisés ; ancienne description purement éditoriale supprimée. |
| `docs/shipping-payment-report.md` | Compte rendu du lot et recette restante. |

`checkout/static/checkout/checkout-summary.js` a été relu et testé, sans modification : il consomme déjà les options et totaux du serveur, préserve la sélection encore valide et garde les champs de coordonnées en place.

## Tests et commandes réellement exécutés

Dans le checkout local, avec un secret exclusivement local de test et les dépendances existantes :

```bash
DJANGO_SECRET_KEY=local-tests-only ../venv/bin/python manage.py test --settings=config.settings.development
DJANGO_SECRET_KEY=local-tests-only ../venv/bin/python manage.py test checkout.test_shipping --settings=config.settings.development
NODE_PATH=../checkout-test-runtime/node_modules node --test tests/checkout-summary.test.cjs
DJANGO_SECRET_KEY=local-tests-only ../venv/bin/python manage.py check --settings=config.settings.development
DJANGO_SECRET_KEY=local-tests-only ../venv/bin/python manage.py makemigrations --check --dry-run --settings=config.settings.development
node --check checkout/static/checkout/checkout-summary.js
node --check static/js/base.js
node --check shop/static/js/shop.js
git diff --check
```

- **207 tests Django : OK**, 14,087 s, suite complète. Ce nombre inclut les 11 nouveaux tests ; ce n’est pas le nombre historique de l’audit.
- **11 tests Django ciblés : OK**, 1,106 s après les derniers ajustements de conversion du sous-total et de refus d’URL de paiement malformée.
- **19 tests Django de revue : OK**, 1,436 s, après harmonisation des délais et conditions dans le composant partagé (`manage.py test checkout.test_shipping pages.test_commercial_information --settings=config.settings.development`).
- **11 tests JavaScript : OK**, 1,970 s. Simulations DOM avec réseau contrôlé, pas des essais dans un navigateur réel. `jsdom` est installé dans un répertoire temporaire de test extérieur au dépôt ; aucune dépendance de production ajoutée.
- `manage.py check` : aucun problème. `makemigrations --check --dry-run` : aucune migration oubliée. La migration d’aide `product.0009` a été générée avec `manage.py makemigrations product --settings=config.settings.development`, puis appliquée dans les bases de test éphémères par le test runner. La base de boutique n’a pas été migrée dans ce lot.
- Les trois vérifications de syntaxe JavaScript et `git diff --check` réussissent.
- Première passe avant adaptation des tests : 196 tests, 9 échecs liés au nouveau contrat attendu. Passe intermédiaire ciblée : 28 tests, 6 erreurs de sous-cas, car les promotions fictives étaient limitées par défaut à un usage par e-mail. Les fixtures ont été rendues réutilisables explicitement ; le contrôle métier d’usage unique n’a pas été modifié.

Le test des limites parcourt 79,99/80,00/80,01 € **et** seuil courant −0,01 / seuil / seuil +0,01 ; le seuil courant est 80 €, donc ces séries coïncident aujourd’hui. Chaque montant est testé avec/sans remise et en standard/express, en comparant le montant du devis à celui de la commande réellement créée dans la base de test. Les valeurs de test ne remplacent aucun tarif de la boutique.

Autres cas exécutés : offre gratuite à 49,90 € avec remise 20 % → net 39,92 €, standard 0 €, express 9,90 € ; panier mixte et retrait de l’offre gratuite ; falsification d’un indicateur client ; offre désactivée ; CH/GB/pays inconnu refusés ; exclusions postales fictives ; empreinte commerciale périmée ; conditions de délai fictives affichées uniquement après approbation de test ; paiement indisponible sans commande ni mouvement de stock ; montant envoyé à Stripe égal au total serveur avec coupon et express.

## Contrôles du code et protections

- Aucun prix ou frais reçu du navigateur n’est accepté comme autorité. `apply_promo_code` et sa limitation d’usage sont conservés. Gratuité issue exclusivement des offres valides en base.
- Réservation de stock conditionnelle et transactionnelle, CSRF, snapshot de commande et clés d’idempotence conservés. Les tests existants correspondants passent dans la suite complète.
- Aucun changement du traitement des webhooks signés, de leurs contrôles de montant/devise ou de l’idempotence des événements. Stripe Checkout reste hébergé.
- Aucune nouvelle conservation de coordonnées ou secrets en session, localStorage, sessionStorage ou journaux. Les messages de configuration côté client ne révèlent aucun secret. Textes affichés par les templates Django échappés ; libellés des modes insérés avec `textContent` par le JS existant.
- Les anciennes tentatives et commandes conservent leur snapshot ; le lot ne recalcule pas rétroactivement les commandes existantes.

## Navigateur et Stripe : vérifications restantes

Tentative réellement exécutée : lancement headless de Chromium avec Playwright. Échec : exécutable `chromium_headless_shell-1234` absent. **Aucune capture, aucune des largeurs 320, 360, 390, 430, 768 ou 1366 px n’a été vérifiée dans un navigateur.** La lisibilité, les retours à la ligne des nouveaux textes, le focus, les contrôles tactiles et l’absence de débordement restent à contrôler ; aucun `overflow-x:hidden` n’a été ajouté comme palliatif.

Aucun appel au vrai service Stripe, aucun paiement réel ni Stripe test effectué. Les appels Stripe des tests sont simulés : cela vérifie le payload et le montant, pas les moyens réellement proposés. Il reste à disposer d’une préproduction autorisée, de clés **de test uniquement**, d’une URL et d’un webhook test, puis vérifier les moyens affichés, le montant final, l’annulation/reprise, les erreurs et le retour signé. Apple Pay/PayPal et 3D Secure systématique ne sont pas annoncés.

## Informations attendues avant réouverture

Fournir une matrice datée et approuvée : pays/zones réellement desservis, territoires et codes postaux exclus, frais TTC par mode et zone, seuil applicable, délais et leur point de départ/conditions, éventuelles formalités et charges douanières. Confirmer les moyens de paiement par une recette Stripe test. Les autres informations essentielles du lot 1 restent également nécessaires.

La configuration actuelle représente une **grille commune candidate**, conservant 4,90 € / 9,90 € et le seuil de 80 €, sans affirmer que des frais identiques entre pays seraient erronés. Si la future décision exige des tarifs distincts par zone, des suppléments, des transporteurs ou des exclusions autres que des préfixes postaux, il faudra compléter le moteur et ses tests avant activation ; aucune valeur n’est inventée ici.

Points de configuration destinés au développeur/exploitant, non affichés comme texte public : `CHECKOUT_SHIPPING_COUNTRIES`, `CHECKOUT_EXCLUDED_POSTAL_PREFIXES` (codes pays → listes de préfixes), `CHECKOUT_DELIVERY_CONDITIONS` (standard/express), `CHECKOUT_CUSTOMS_INFORMATION`, les tarifs/seuil/délais existants et `COMMERCIAL_INFORMATION`. Une nouvelle empreinte `shipping_configuration()` doit être explicitement approuvée avec les pages commerciales, pas simplement copiée pour ouvrir les ventes.

Revoir les offres existantes marquées gratuites avant réouverture : elles accordent désormais la gratuité standard de tout le panier. La migration ne change aucune valeur d’offre. Les décisions de gratuité par offre et d’express payant sont validées ; **le lot n’est pas entièrement validé pour la vente**, faute de matrice, de recette navigateur et de recette Stripe test.

## Reprise locale

```bash
git fetch origin
git switch fix/commercial-information
git pull --ff-only origin fix/commercial-information
python manage.py migrate --settings=config.settings.development
python manage.py check --settings=config.settings.development
python manage.py test checkout.test_shipping checkout.test_preservation --settings=config.settings.development
python manage.py runserver --settings=config.settings.development
```

Activer l’environnement virtuel et la configuration locale habituels avant ces commandes. Les commandes de reprise ci-dessus sont proposées à l’exploitant ; elles ne sont pas présentées comme un déploiement exécuté. Garder les ventes fermées et les clés Stripe en mode test pour la recette.
