# Stripe Checkout — My Line Collection

## État
Le checkout est raccordé au panier serveur et au SDK Python officiel Stripe. Aucune clé réelle n'est incluse. Tant que `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` et `SITE_BASE_URL` ne sont pas configurés, le paiement est refusé sans simulation. Cette branche reste en développement local et n'est pas déclarée prête pour la production.

## Architecture
- `shop.views` reste la source de vérité du panier invité : identifiants de variante/offre, quantités et sélection obligatoire des accessoires inclus.
- `checkout.services.validated_cart` recharge les lignes depuis la base, revalide publication, offre, variante, disponibilité et recalcule les prix en `Decimal`.
- `Order` et `OrderLine` conservent un instantané des lignes, des accessoires offerts à 0 €, de la livraison et du total.
- Le stock est réservé par mises à jour conditionnelles dans la transaction de création. L'expiration et l'échec asynchrone libèrent une réservation au plus une fois. Un paiement tardif après libération passe en `payment_review` et nécessite une intervention humaine.
- `PaymentAttempt` suit la session ; `StripeWebhookEvent.event_id` est unique.
- La page de retour ne modifie jamais le statut. Seul un webhook à signature valide peut confirmer le paiement.

## Variables d'environnement
- `STRIPE_SECRET_KEY` : clé secrète Stripe test puis live, stockée uniquement dans l'environnement.
- `STRIPE_PUBLISHABLE_KEY` : clé publique réservée à un usage futur ; Checkout hébergé n'en a pas besoin côté navigateur.
- `STRIPE_WEBHOOK_SECRET` : secret de signature de l'endpoint correspondant à l'environnement.
- `STRIPE_CURRENCY=eur`.
- `STRIPE_LIVE_MODE=False` en test. La clé est contrôlée côté serveur : une clé `sk_test_` est exigée en mode test et `sk_live_` en mode live.
- `SITE_BASE_URL` : domaine canonique. Exemple local `http://127.0.0.1:8000`, HTTPS obligatoire en production.
- `CHECKOUT_STANDARD_SHIPPING`, `CHECKOUT_EXPRESS_SHIPPING`, `CHECKOUT_FREE_SHIPPING_THRESHOLD` : valeurs de la maquette actuelle (4,90 €, 9,90 €, seuil 80 €), à confirmer avant toute vente.

Ne placez jamais de secrets dans Git, JavaScript, templates, captures ou logs. Le fichier `.env` est ignoré par Git.

## Installation et migrations
```bash
python -m pip install -r requirements.txt
python manage.py check --settings=config.settings.development
python manage.py makemigrations --check --dry-run --settings=config.settings.development
python manage.py migrate --settings=config.settings.development
python manage.py test checkout shop product --settings=config.settings.development
```

La migration `checkout.0001_initial` dépend de `product.0005_offer_only_pricing`. Vérifiez la liste des migrations du catalogue avant application.

## Tester avec Stripe
1. Dans le Dashboard Stripe, sélectionner le mode test et copier la clé secrète de test dans l'environnement local.
2. Lancer Django.
3. Avec Stripe CLI, transférer les événements vers `http://127.0.0.1:8000/checkout/stripe/webhook/` et définir le secret de signature communiqué par la CLI dans `STRIPE_WEBHOOK_SECRET`.
4. Vérifier les événements `checkout.session.completed`, `checkout.session.async_payment_succeeded`, `checkout.session.async_payment_failed` et `checkout.session.expired`.
5. Utiliser les moyens de paiement de test documentés par Stripe, jamais une carte réelle en mode test.

## Sécurité et exploitation
- Le navigateur ne décide jamais du montant. Les lignes Stripe sont créées depuis l'instantané serveur.
- Le stock est décrémenté via une mise à jour conditionnelle. Vérifier les garanties de concurrence du moteur de base de données choisi : SQLite est moins adapté aux écritures concurrentes qu'un serveur de base de données dédié.
- Les événements dupliqués ne déclenchent pas de deuxième effet métier. Les incohérences de montant/devise passent en revue manuelle.
- Aucun numéro de carte ou CVC n'est traité ou stocké par Django.
- Les paiements reçus après libération du stock sont signalés pour intervention ; aucun remboursement automatique n'est envoyé.

## Avant production
Confirmer les frais et conditions de livraison ; sélectionner et tester le moteur de base ; configurer HTTPS, cookies, hôtes autorisés, CSRF, sauvegardes et permissions ; définir les variables via cPanel/Passenger ; créer le webhook live et son secret ; tester succès, refus, expiration, événements dupliqués, erreurs réseau et paiements tardifs ; valider les remboursements, e-mails, factures, mentions légales, CGV, confidentialité et exigences fiscales. Exécuter les tests, `python manage.py check --deploy --settings=config.settings.production` et une recette bout en bout avant activation.

## Limites connues à valider
Les tarifs de livraison sont issus de la maquette et ne sont pas encore confirmés commercialement. Les e-mails de commande, factures et remboursements automatiques ne sont pas inclus. La validation réelle exige les clés, le webhook, HTTPS et des tests end-to-end sur l'environnement cible.
