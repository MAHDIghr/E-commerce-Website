# Audit du parcours d'achat — My Line Collection

Date : 25 octobre 2026  
Branche : `developpement-backend`

## Périmètre

Audit statique du parcours panier → checkout Django → Stripe Checkout → retour de commande, incluant les actions depuis les fiches produit et les cartes catalogue. Cet audit de code ne constitue pas une certification de sécurité ni un test réel de paiement.

## Parcours cible implémenté

| Point de départ | Action | Destination |
|---|---|---|
| Fiche produit | **Ajouter au panier** | Page dédiée `/boutique/mon-panier/` |
| Fiche produit | **Acheter** | Checkout Django `/checkout/` ; le formulaire doit être validé avant la redirection vers Stripe |
| Carte catalogue / ajout rapide | **Ajouter au panier** | Page dédiée du panier |
| Panneau latéral du panier | **Commander** | Checkout Django |
| Page dédiée du panier | **Passer à la commande** | Checkout Django |
| Checkout Django | Validation du formulaire | Page de paiement hébergée par Stripe |
| Retour Stripe | Succès / annulation | Page de résultat associée à la commande ; le navigateur ne confirme jamais le paiement |

Le checkout est volontairement une étape distincte de la confirmation : le client doit renseigner et valider les informations de livraison avant d'être envoyé chez Stripe.

## Corrections effectuées

### 1. Page de panier dédiée

- Ajout d'une route nommée `shop:cart_page` et d'un template dédié.
- Les articles et montants sont rendus à partir des données recalculées par le serveur.
- Quantités et suppressions utilisent l'API de mutation existante ; les erreurs serveur sont affichées.
- Le bouton de commande est désactivé si le panier est vide ou contient un article indisponible.
- Les noms et détails produits sont insérés dans le DOM via `textContent`, pas comme HTML arbitraire.

### 2. Redirections cohérentes

- Les boutons de la fiche produit distinguent maintenant `.js-add` et `.js-buy`.
- Les ajouts rapides du catalogue rejoignent aussi la page de panier.
- Le panier latéral et la page dédiée mènent au checkout, jamais directement à une URL de succès.
- Les URL sont obtenues depuis les routes Django injectées dans le template, avec des chemins de repli internes uniquement.

### 3. Cohérence de livraison

Le seuil de livraison gratuite du panier était codé en dur à 80 €, alors que le checkout lit `CHECKOUT_FREE_SHIPPING_THRESHOLD`. Le panier lit désormais la même variable d'environnement, afin d'éviter d'afficher une promesse de livraison gratuite qui ne correspondrait pas à la règle de calcul du checkout.

### 4. Tentative de paiement obsolète après modification du panier

La clé de tentative `checkout_attempt_key` est désormais invalidée quand le client modifie ou vide son panier. Cela empêche de réutiliser silencieusement une session Checkout créée pour une ancienne sélection après une modification du panier.

### 5. Panier résiduel après confirmation du paiement

La page de retour vide désormais le panier uniquement lorsqu'il correspond à l'instantané de la commande payée. Si le client a commencé une nouvelle sélection pendant le paiement, cette nouvelle sélection est préservée.

### 6. Webhook reçu avant l'association de la session à la commande

Le traitement enregistrait auparavant un événement de session inconnue comme traité et répondait ensuite avec succès. Si Stripe livrait le webhook avant que l'identifiant de session soit enregistré sur la commande, cet événement pouvait ne jamais être retraité. Le traitement lève désormais une erreur réessayable, ce qui annule l'enregistrement de déduplication dans la transaction et renvoie une réponse 5xx à Stripe pour déclencher une nouvelle livraison.

## Contrôles automatiques ajoutés

- Rendu de la page panier avec les données validées côté serveur.
- Invalidation de la clé de tentative après une mutation du panier.
- Réessayabilité d'un webhook lié à une session Checkout encore inconnue.

## Points de vigilance restants

Ces éléments doivent être vérifiés ou traités avant toute mise en production :

1. **Tests locaux et intégration Stripe :** exécuter toute la suite Django, puis tester un vrai parcours en mode test depuis la boutique. Un `stripe trigger` seul ne prouve pas qu'une commande réelle de test est liée à l'événement.
2. **Réservation de stock :** la réservation commence avant la création de la session Stripe. Vérifier le comportement lors d'une interruption réseau, d'une erreur de base de données ou d'une session abandonnée ; prévoir une surveillance et une procédure de réconciliation des commandes bloquées.
3. **Événements webhook :** confirmer dans le Dashboard Stripe que les événements configurés sont livrés, que les réponses 2xx correspondent aux événements traités et que les erreurs 5xx sont réessayées.
4. **Sélection d'offre et accessoires :** tester chaque combinaison réelle d'offre, variante, accessoires obligatoires et stock partagé. Le serveur reste la source de vérité ; les données envoyées par le navigateur ne doivent jamais déterminer les prix.
5. **Retour d'annulation :** vérifier manuellement qu'un panier restauré peut être modifié, puis repassé en commande sans réutiliser l'ancienne session pour une sélection différente.
6. **Configuration :** confirmer que les clés API, le secret webhook et `SITE_BASE_URL` appartiennent au même environnement Stripe. Les secrets restent uniquement dans `.env` en local et dans un gestionnaire de secrets en production.
7. **Production :** HTTPS obligatoire, endpoint webhook public configuré dans Stripe, mode live activé uniquement avec les clés live correspondantes, et paramètres Django de production contrôlés.
8. **Contrôle métier :** valider les frais de livraison, les pays desservis, les délais annoncés, les textes de retour et les conditions commerciales avant le lancement.

## Procédure de validation locale

Depuis la racine du dépôt, avec l'environnement virtuel activé :

```powershell
python manage.py check --settings=config.settings.development
python manage.py makemigrations --check --dry-run --settings=config.settings.development
python manage.py migrate --settings=config.settings.development
python manage.py test --settings=config.settings.development
```

Ensuite, avec Django et Stripe CLI actifs, tester successivement :

- Ajout depuis une fiche produit → page panier.
- Achat depuis une fiche produit → checkout.
- Ajout rapide depuis le catalogue → page panier.
- Modification et suppression d'articles → total et disponibilité mis à jour.
- Panier vide ou article indisponible → commande bloquée.
- Livraison standard, express et gratuite selon le seuil configuré.
- Paiement test réussi, refusé, authentification 3-D Secure et annulation.
- Webhook livré deux fois, signature invalide et événement d'une session inconnue.
- Confirmation uniquement après événement Stripe signé et cohérence du montant/devise.

## Limites de cet audit

Les modifications ont été effectuées dans le dépôt GitHub. Les commandes de test locales et les parcours navigateur n'ont pas été exécutés sur ton ordinateur dans le cadre de cet audit. Ne considère donc pas le parcours comme validé de bout en bout tant que la suite Django et les scénarios Stripe ci-dessus n'ont pas été exécutés avec succès.
