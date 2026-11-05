# Lot 12 — Suivi et rétractation : livraison partielle

Travail sur la branche existante `fix/commercial-information` ; `fix/comercial-information` dans le prompt est interprété comme une coquille. Départ f6ee2fb. Instructions du dépôt, modèles, vues de suivi/lookup/retour, service transactionnel, gabarits et tests relus.

## Modèle actuel et manque critique

L'UUID public de commande est un secret de capacité à forte entropie, pas une référence facilement devinable. Le lien permet de lire articles, montants, expéditions et demandes de retour, et de soumettre une demande avec CSRF. Les vues masquent le nom et l'e-mail ; no-store et politique de referrer existants conservés.

**La séparation référence commerciale / jeton invité révocable n'est pas implémentée dans ce lot.** Les anciens liens continuent de fonctionner ; aucune migration destructive d'accès n'est réalisée. Le critère « jeton erroné/révoqué » n'est donc pas satisfait. Il reste à définir et implémenter le jeton aléatoire stocké haché, sa rotation/révocation, une procédure sûre d'envoi à l'adresse enregistrée, une période de transition des liens envoyés et la fin explicite de leur accès de capacité. Ne pas simplement rediriger automatiquement un ancien lien vers un nouveau secret : cela empêcherait sa révocation réelle. L'accès propriétaire authentifié doit aussi être conservé. Aucun jeton nouvellement introduit n'est présenté comme sécurisé.

## Corrections indépendantes

La catégorie Rétractation constitue désormais une déclaration explicite pour les articles sélectionnés ; aucune justification détaillée n'est exigée côté service ni par l'attribut required du textarea. Les autres types gardent leur validation métier côté serveur. Le texte du formulaire distingue cette déclaration d'une demande commerciale ou de non-conformité. L'envoi ne signifie pas qu'un remboursement est effectué.

L'accusé est persisté dans les notifications existantes avec référence commande/demande, horodatage ISO, type, déclaration, produits/quantités et commentaire. Il inclut le lien de suivi lorsque SITE_BASE_URL fournit une URL HTTPS. La consultation des demandes affiche maintenant la date et l'heure. Les séquences littérales antislash-n présentes dans les messages de cycle de vie ont été remplacées par de vrais sauts de ligne. La file durable et son mécanisme existant de reprise sont conservés ; aucun envoi réel n'est revendiqué.

Fichiers : checkout/lifecycle.py (validation, notifications et sauts de ligne), checkout/templates/order_tracking.html (déclaration/justification/statut/date), checkout/test_order_tracking.py (rétractation sans motif et double quantité refusée), README et ce rapport. Aucun modèle/migration modifié. Aucun nouveau délai juridique ou engagement de remboursement ajouté.

## Vérifications exécutées

- `DJANGO_SECRET_KEY=local-tests-only ../venv/bin/python manage.py test checkout --settings=config.settings.development` : 93 tests réussis, avant l'ajout final du lien HTTPS dans l'accusé.
- `DJANGO_SECRET_KEY=local-tests-only ../venv/bin/python manage.py test checkout.test_order_tracking --settings=config.settings.development` : 9 tests réussis après cet ajout. Ils couvrent suivi anonyme légitime, UUID inconnu, périmètre d'une commande, CSRF existant et nouvelle déclaration sans justification avec double quantité rejetée.
- `manage.py check --settings=config.settings.development` : aucun problème ; `git diff --check` sans erreur.

Les quantités sont toujours contrôlées sous transaction et verrous existants, en déduisant les demandes actives/résolues déjà prises en compte. Le test ajouté vérifie qu'une seconde demande sur la même unité ne crée pas de doublon. Prix/stock, CSRF, webhook signé, idempotence et Stripe hébergé ne sont pas modifiés. Aucune coordonnée/secrets dans le stockage navigateur ou les journaux. Les données de l'accusé sont destinées au client via la file existante, pas aux logs.

## Restant à faire

Séparation/révocation/rotation et transition sécurisée des liens ; tests invalides/révoqués ; recette de livraison réelle des accusés et de leurs liens ; tests de concurrence sur la base hébergée. Aucun navigateur disponible, aucune capture ni largeur 320/360/390/430/768/1366 px vérifiée pour ce lot. Valider focus, erreurs et compréhension de la déclaration sur mobile et lecteur d'écran.

Les règles juridiques applicables à la date de mise en service, notamment novembre 2026, **n'ont pas été validées** : faire confirmer modalités, accès au mécanisme de rétractation, délais, exceptions et accusé durable. Ce correctif technique ne constitue pas un texte juridique validé. Le blocage commercial des ventes reste actif. Aucun déploiement, fusion ou paiement réel. Le lot n'est pas entièrement terminé.
