# Ajustements visuels et ouverture locale du paiement test

Branche existante `fix/commercial-information` (orthographe du dépôt, la mention `fix/comercial-information` étant interprétée comme une coquille). Départ `8f037db`. Instructions du dépôt et règles concernées relues ; aucune modification locale préexistante.

## Avant / après

- `.card__details` utilisait un fond blanc `--color-surface`. Il devient transparent et laisse apparaître le fond de page ; texte sombre conservé. L’image Signature dédiée n’est pas modifiée.
- Les offres mobiles avaient un prix sur une rangée séparée et un badge dans le flux. Sous 600 px elles retrouvent trois colonnes : sélection, texte, prix ; badge superposé et espacement réduit. Les tailles utiles restent lisibles et les montants longs peuvent revenir à la ligne ; aucun masquage horizontal ajouté. Les réglages desktop ne changent pas.
- Le bandeau promo de l’accueil garde les textes réels et leurs conditions, mais adopte un dégradé champagne/cuivre, des détails dorés et un encart arrondi pour le code. Hauteur 38 px, texte .875 rem. Le défilement est plus lent sur téléphone ; en mouvement réduit, la piste est consultable horizontalement sans animation ni double contenu accessible. Aucun tarif/code/avis/urgence ajouté.
- Le tunnel local bloquait sur l’absence de validation commerciale. Une autorisation **distincte de l’approbation juridique** permet maintenant les tests sous conditions strictes : profil de développement avec DEBUG=True et LOCAL_TEST_CHECKOUT=True, clé sk_test_, mode live désactivé, SITE_BASE_URL sur localhost/127.0.0.1/::1. Le checkout exige toujours sa configuration Stripe complète, dont le secret webhook. Le serveur, le devis et le bouton utilisent la même autorisation ; les pays candidats sont proposés uniquement pour cet essai local.

Un avertissement « Mode test Stripe local » est affiché ; aucune page commerciale ou coordonnée fictive n’est publiée comme validée. Les informations publiques restent non approuvées. En production DEBUG=False rend ce contournement impossible ; le verrou commercial existant reste requis. Stripe Checkout reste hébergé. Une clé live avec mode live est refusée en DEBUG, même avec un dossier commercial approuvé.

## Fichiers

- `home/static/css/home.css` : fond Signature et bandeau promo d’accueil.
- `product/static/css/product.css` : présentation compacte des offres sur téléphone.
- `config/settings/development.py` : option locale, activée par défaut suivant la demande utilisateur.
- `config/commercial.py` : autorisation locale contrôlée, pays de test et avertissement sans approbation légale fictive.
- `checkout/views.py` : autorisation cohérente du formulaire et du devis.
- `checkout/services.py` : mêmes contrôles au moment de créer la commande/session ; refus de paiement live en DEBUG.
- `checkout/templates/checkout.html` : avertissement local explicite.
- `checkout/test_local_checkout.py` : trois tests du chemin local simulé et de ses garde-fous.
- `.env.example` : option locale documentée, aucun secret.
- `README.md` et ce rapport : instructions et limites.

## Validation exécutée

```bash
DJANGO_SECRET_KEY=local-tests-only ../venv/bin/python manage.py test checkout.test_local_checkout --settings=config.settings.development
DJANGO_SECRET_KEY=local-tests-only ../venv/bin/python manage.py test --settings=config.settings.development
DJANGO_SECRET_KEY=local-tests-only ../venv/bin/python manage.py check --settings=config.settings.development
git diff --check
```

Trois tests ciblés réussis (0,175 s), puis **231 tests Django réussis** (20,143 s). La première passe complète, avant ajout des trois tests, comptait 228 réussites ; ce n’est pas la validation finale. Django check et diff sans erreur. Aucun modèle modifié, aucune migration nécessaire.

Le test local vérifie la réservation et la redirection vers une session hébergée simulée, sans publier le dossier légal ; les appels Stripe sont mockés. Les deux autres refusent le mode live/la clé live/l’hôte public et DEBUG=False. Aucun appel à une vraie session Stripe ni paiement exécuté.

Tentative réelle de lancement Chromium via Playwright : exécutable chromium_headless_shell-1234 absent. **Aucune capture, aucune largeur 320/360/390/430/768/1366 px validée visuellement.** Restent à vérifier les retours à la ligne des offres, prix longs, le badge, le contraste sur le fond réel des cartes et le bandeau en mouvement réduit sur téléphone. Le rendu n’est pas annoncé comme entièrement validé.

## Reprise locale Windows

Récupérer la branche sans écraser de travail local, puis redémarrer le serveur avec `python manage.py runserver --settings=config.settings.development`. Dans la configuration locale déjà existante, conserver les clés Stripe de test hors du dépôt et vérifier :

```dotenv
LOCAL_TEST_CHECKOUT=true
STRIPE_LIVE_MODE=False
SITE_BASE_URL=http://127.0.0.1:8000
```

La clé secrète existante doit commencer par sk_test_ et le secret webhook doit être configuré. Aucune valeur de secret n’est fournie ni demandée dans le chat. Utiliser uniquement des coordonnées et moyens de paiement fictifs de test. `LOCAL_TEST_CHECKOUT=false` rétablit le verrou commercial même en développement.

Prix/remises serveur, CSRF, contrôle et réservation de stock, webhook signé et idempotence conservés. Aucune coordonnée ni secret ajouté au stockage du navigateur ou aux journaux. Aucun changement de configuration de production, déploiement, fusion ou paiement réel. Le NO-GO de lancement reste valable : le déblocage concerne les essais locaux seulement.
