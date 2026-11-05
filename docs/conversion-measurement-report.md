# Lot 14 — Mesure de conversion après stabilisation

Branche `fix/commercial-information`, départ `2cbb9b0`. Le NO-GO du lot 13 reste actif ; aucune expérimentation publique ou collecte visiteur n'est activée avant stabilisation.

## Constat et solution retenue

Lecture des gabarits/base, scripts de découverte/achat, vues checkout et publication des pages de confidentialité : aucun SDK analytics, pixel, gtag ou dataLayer actif trouvé dans les fichiers concernés. Le panier et les favoris utilisent déjà leurs mécanismes nécessaires/locaux ; aucun nouveau bandeau n'est ajouté pour ces usages dans ce lot.

Choix pour l'étape actuelle : **rapport interne de première partie**, calculé en lecture seule depuis les commandes, preuves de paiement, tentatives et demandes existantes. Aucun prestataire analytics, script tiers, cookie, identifiant visiteur, empreinte d'appareil ou émission marketing ajouté. Ce rapport est une commande de gestion réservée aux personnes ayant accès à l'environnement serveur, pas une page publique.

Le rapport opérationnel ne mesure pas encore le taux de conversion visiteur ou les abandons : il expose ces indicateurs comme indisponibles (`null`), jamais comme zéro. Il ne constitue pas un instrument complet de mesure du tunnel. La collecte de découverte/étapes est définie ci-dessous mais reste non instrumentée.

## Contrat des événements à instrumenter seulement après décision

| Événement | Déclencheur admissible | Données minimales envisageables | État actuel |
|---|---|---|---|
| `view_item` | Fiche effectivement affichée | Produit, langue, catégorie d'appareil grossière si autorisée | Non collecté |
| `select_variant` | Changement explicite de variante | Identifiant produit/variante | Non collecté |
| `select_offer` | Changement explicite d'offre | Identifiant produit/offre | Non collecté |
| `add_to_cart` | Mutation serveur réussie, pas le clic | Identifiants et quantité validée | Non collecté |
| `begin_checkout` | Checkout effectivement ouvert avec panier valide | Étape, devise | Non collecté |
| `select_shipping` | Mode sélectionné dans un devis serveur valide | Code de mode, sans pays/code postal/adresse | Non collecté |
| `payment_attempt` | Tentative créée côté serveur | Résultat technique codifié, sans message brut | Agrégat de lignes PaymentAttempt existantes seulement |
| `purchase` | Paiement confirmé côté serveur, événement de cycle de vie `payment_confirmed` source Stripe | Agrégats par devise ; aucune référence exportée | Comptage interne dédupliqué, aucun événement marketing émis |
| `blocking_error` | Action refusée empêchant l'étape | Code contrôlé stock/devis/réseau/paiement, jamais texte libre | Non collecté |

Ne jamais envoyer nom, e-mail, téléphone, adresse, code postal, IP, jeton invité/UUID public de capacité, URL complète avec query string, contenu de formulaire ou message d'erreur brut. La future classification d'appareil ne doit pas devenir du fingerprinting. Une future déduplication externe devrait utiliser une clé serveur dédiée non réversible, jamais le secret de suivi invité ; sa définition et sa conservation ne sont pas implémentées ici.

## Purchase : preuve et déduplication

`checkout/conversion.py` sélectionne chaque commande sur **sa première preuve de paiement** `payment_confirmed` d'origine Stripe dans `[start, end[`. Ces événements existants proviennent du traitement serveur du paiement et de ses contrôles de signature/montant. Deux événements de confirmation sur la même commande ne produisent qu'un achat dans les agrégats. Un statut PAID sans preuve ou un clic Acheter n'est pas compté.

La période porte sur la confirmation, pas la création de commande ; aucune nouvelle date de paiement n'est inventée. Un remboursement ultérieur ne supprime pas l'achat historique : il est indiqué séparément. Les montants proviennent du snapshot serveur, regroupés par devise sans addition inter-devises. Le rapport n'exporte aucun identifiant de commande, de paiement, de client ou de produit.

## Indicateurs, périodes et dénominateurs

Chaque sortie précise début inclus, fin exclue et date d'observation, avec fuseaux obligatoires. La période est exigée en argument : aucune période d'activité fictive n'est choisie pour la boutique.

| Indicateur | Numérateur | Dénominateur / période | Disponible |
|---|---|---|---|
| Achats confirmés | Commandes distinctes dont première preuve Stripe est dans la période | Nombre absolu, même devise | Oui |
| Montant brut des commandes | Somme des totaux serveur des commandes de cette cohorte | Même cohorte/devise ; inclut livraison, après remises, avant remboursements | Oui |
| Panier moyen | Montant brut de la cohorte | Nombre d'achats confirmés de cette cohorte ; arrondi monétaire 2 décimales | Oui |
| Demandes de retour | Commandes de la cohorte ayant au moins une demande, tout type/statut | Commandes payées de la cohorte ; état observé au moment du rapport | Oui, intentions seulement |
| Montant remboursé | Remboursements SUCCEEDED de la cohorte, confirmés avant la fin de période | Même devise ; distinct du montant d'achat | Oui |
| Échecs de tentative | Lignes PaymentAttempt actuellement FAILED, créées dans la période | Toutes les lignes PaymentAttempt créées dans la période | Comptages oui ; pas de taux de refus bancaire déduit |
| Conversion par appareil | Visiteurs/visites admissibles ayant acheté | Visiteurs/visites de même définition, période et appareil ; attribution à définir | Non, dénominateur absent |
| Ajout au panier | Visites/visiteurs avec mutation réussie | Visites/visiteurs avec fiche vue, même cohorte | Non collecté |
| Passage au checkout | Visites/visiteurs ayant ouvert un checkout valide | Visites/visiteurs avec ajout réussi | Non collecté |
| Abandon par étape | Visites éligibles sans étape suivante à échéance | Visites ayant atteint cette étape ; fenêtre et visites encore ouvertes à exclure | Non collecté |
| Retours physiques | Commandes/unités réellement revenues | Commandes/unités livrées d'une cohorte mature, fenêtre définie | Non calculé : une demande n'est pas un retour physique |

Le taux de demandes est un indicateur de cohorte observé maintenant, pas un historique figé à la fin de période. Il peut évoluer avec les demandes tardives, y compris refusées. Les tentatives peuvent changer d'état après la période ; l'horodatage d'observation est donc nécessaire. Les requêtes ne constituent pas un snapshot transactionnel multi-requêtes garanti sous toutes les bases : préférer une période close et vérifier l'isolation avant usage décisionnel. Les montants remboursés ne sont pas présentés comme un chiffre d'affaires comptable net.

## Consentement et confidentialité : décision avant toute collecte supplémentaire

Références officielles CNIL consultées :
- https://www.cnil.fr/fr/cookies-solutions-pour-les-outils-de-mesure-daudience
- https://www.cnil.fr/fr/cookies-et-autres-traceurs/regles/cookies/FAQ

L'exemption d'un traceur de mesure d'audience dépend de la finalité et de la configuration démontrée ; elle n'est pas présumée pour un tunnel commercial. La suppression de contacts ne garantit pas à elle seule l'anonymat. Ce lot n'affirme pas qu'un futur outil sera exempté ni que les traitements de données de commandes sont hors RGPD.

Avant installation d'un outil visiteur : choisir le prestataire/configuration, finalité et base légale, modalités de consentement le cas échéant, destinataires et transferts, durées, identifiants/attribution, droits et dispositif de retrait. Quand le consentement est requis, bloquer le chargement ET les événements avant accord, offrir refuser aussi simplement qu'accepter, et un retrait aussi accessible ; arrêter alors les envois et traiter les identifiants selon la politique validée. Aucun tel mécanisme n'est simulé comme déjà opérationnel ici : **aucun nouveau suivi visiteur n'est activé**.

Le rapport CLI ne crée pas de table de conservation ni de fichier automatiquement : sortie standard uniquement. Il lit les données transactionnelles déjà conservées ; aucune durée légale de commande n'est modifiée. Les exports éventuels restent sensibles, surtout pour les petits effectifs : limiter leurs accès et définir leur durée avant utilisation réelle. Ne pas publier de petits groupes permettant de déduire l'activité d'une personne.

À faire valider pour la politique de confidentialité : finalité exacte du rapport interne, base du traitement secondaire des données de commande, responsables autorisés, durée des exports, information/droits et prestataires éventuels. La politique publique n'est pas modifiée avec du texte juridique inventé ; elle reste soumise au dossier commercial approuvé existant. Les choix de prestataire, durée et collecte du tunnel restent attendus de l'exploitant.

## Expérimentation après base de référence

Aucune amélioration chiffrée promise. Après stabilisation et période de référence définie, tester une hypothèse à la fois (par exemple compréhension de l'information livraison). Documenter avant test : cohorte, métrique principale/dénominateur, période, taille minimale selon trafic réel, critère d'arrêt et garde-fous (erreurs, remboursements, retours). Garder prix/règles comparables et ne pas conclure sur des données insuffisantes. Pas de fausse rareté, faux avis ou urgence artificielle. Aucun A/B test déployé dans ce lot.

## Fichiers modifiés

- `checkout/conversion.py` : agrégats internes, preuve de paiement et absence d'export de contacts/identifiants.
- `checkout/management/commands/conversion_report.py` : commande à période ISO explicite et validation des dates.
- `checkout/test_conversion.py` : déduplication, exclusion du statut sans preuve, absence de contacts et validation de période.
- `README.md` et ce rapport : événements, indicateurs, limites et décisions attendues.

Les fichiers front demandés ont été vérifiés mais restent inchangés : aucune collecte client n'est introduite. Aucun modèle ni migration, dépendance ou fournisseur ajouté.

## Commandes réellement exécutées et résultats

```bash
DJANGO_SECRET_KEY=local-tests-only ../venv/bin/python manage.py test checkout.test_conversion --settings=config.settings.development
DJANGO_SECRET_KEY=local-tests-only ../venv/bin/python manage.py test --settings=config.settings.development
DJANGO_SECRET_KEY=local-tests-only ../venv/bin/python manage.py check --settings=config.settings.development
DJANGO_SECRET_KEY=local-tests-only ../venv/bin/python manage.py makemigrations --check --dry-run --settings=config.settings.development
git diff --check
```

Trois tests ciblés réussis, puis **228 tests Django réussis**, 16,979 s, suite complète. Django check sans problème, aucune migration détectée, diff sans erreur. Une première passe ciblée avait révélé le nom de relation ORM incorrect ; il a été corrigé vers `lifecycle_events`, puis les tests ciblés et la suite complète ont été exécutés avec succès. Les tests utilisent des commandes fictives, pas les résultats commerciaux réels.

La commande est aussi exécutée par le test via call_command, avec stdout capturée et période fictive ; aucun rapport sur la base réelle n'est présenté comme une observation de conversion.

Exemple de reprise locale, **à adapter à une période close réelle**, environnement déjà configuré :

```bash
python manage.py conversion_report --start 2026-11-01T00:00:00+01:00 --end 2026-11-02T00:00:00+01:00 --settings=config.settings.development
```

Ces dates illustrent le format ; aucune donnée de boutique n'est inventée pour cette journée. Ne pas copier le secret local de tests en production.

## Limites et protections

Aucune recette navigateur, capture ou largeur 320/360/390/430/768/1366 px validée pour ce lot : aucun front n'est modifié. Aucun événement tiers observé ou test de bandeau prétendu. Le critère de mesure complète des abandons n'est pas satisfait tant que la collecte et ses règles ne sont pas décidées/instrumentées. Les agrégats doivent être profilés sur le volume réel avant planification.

Les contrôles prix, stock, CSRF, accès, webhook signé, idempotence et paiement hébergé sont préservés : seul un outil de lecture interne est ajouté. Aucun événement marketing envoyé, aucune coordonnée ajoutée à l'analytics, aucun secret ou contact écrit aux journaux/stockage navigateur. Aucun déploiement, fusion ni paiement réel ; aucun gain de conversion annoncé. Le NO-GO de lancement reste inchangé.
