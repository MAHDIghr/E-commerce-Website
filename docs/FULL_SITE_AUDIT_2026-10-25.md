# Audit technique, sécurité et conversion — My Line Collection

- **Date de revue :** 25 octobre 2026
- **Dépôt :** `MAHDIghr/E-commerce-Website`
- **Branche revue :** `developpement-backend`
- **Révision observée :** `aecc9e36ab02744246e01f406a54a3d0056c623a`
- **Type :** revue statique du code et de la configuration, avec inspection des parcours et des contenus
- **Statut :** rapport de constats et plan d'action ; aucune certification de sécurité ni test d'intrusion

## 1. Synthèse exécutive

Le projet présente de bonnes bases : séparation des applications Django, prix recalculés côté serveur, validation des offres et variantes, contrôle des accès du dashboard par superutilisateur, vérification de signature Stripe, traitement idempotent des événements, contraintes de base de données et tests automatisés. La CI a précédemment exécuté avec succès **81 tests Django** sur la révision du parcours d'achat.

Cela ne suffit pas à autoriser une mise en production. Les principaux risques visibles dans le dépôt sont actuellement **commerciaux et opérationnels autant que techniques** : liens légaux non fonctionnels, inscription newsletter non raccordée à un service, preuve sociale simulée, promotion à vérifier, stockage et moteur de base de données de production non validés, protections de sécurité complémentaires absentes et performance des ressources graphiques à améliorer.

### Décision recommandée

**Ne pas ouvrir le site au public ni investir dans des campagnes payantes avant d'avoir traité les bloqueurs P0**, validé les obligations légales et exécuté des tests réels sur l'hébergement cible. La revue du dépôt ne permet pas de confirmer le comportement du serveur cPanel, les en-têtes HTTP réellement émis, les performances navigateur, ni un paiement Stripe complet.

## 2. Constats prioritaires

| ID | Priorité | Constat vérifiable | Risque | Action recommandée |
|---|---|---|---|---|
| A-01 | **P0 — lancement** | Les liens Mentions légales, Politique de confidentialité et CGV du footer pointent vers `#`. Les liens Livraison, Retours, FAQ, Contact et Suivi de commande sont également des placeholders. Aucune route dédiée correspondante n'apparaît dans `config/urls.py`. | Non-conformité potentielle, manque de confiance, abandon avant paiement et support impossible. | Créer les pages et routes réelles ; faire valider les mentions et CGV par une personne compétente en droit français/européen. |
| A-02 | **P0 — lancement** | Le formulaire newsletter de `templates/partials/_footer.html` utilise `action="#"` et `novalidate`. Le JavaScript indique explicitement que la validation est uniquement côté client pour le moment. | L'inscription peut sembler fonctionner sans créer d'abonnement ; promesse de remise non délivrée ; collecte d'e-mail sans parcours de consentement et de désinscription complet. | Connecter un service réel, valider côté serveur, prévoir confirmation/double opt-in selon la stratégie retenue, preuve de consentement, désinscription simple, politique de confidentialité et gestion de la remise de bienvenue. |
| A-03 | **P0 — confiance commerciale** | `home/static/js/home.js` contient des notifications de preuve sociale codées en dur avec prénoms, villes, produits et heures (« il y a X min »). Le code comporte un commentaire demandant leur remplacement par des données réelles avant production. | Impression trompeuse de commandes récentes ; risque de réputation et de pratiques commerciales trompeuses. | Désactiver ces notifications tant qu'elles ne sont pas alimentées par des événements réels et vérifiables. Ne jamais fabriquer de noms, d'achats, de stocks ou de visiteurs. |
| A-04 | **P0 — promesse promotionnelle** | L'accueil annonce « Vente flash : -20 % sur une sélection de sacs » et affiche un compte à rebours de six heures. Le compte à rebours persiste côté navigateur ; le dépôt ne prouve pas qu'une promotion réelle correspondante est automatiquement activée et expirée côté serveur. | Promotion inexistante ou prolongée artificiellement ; écart entre bannière, prix réellement facturé et prix de référence. | Relier la campagne à des produits, dates de début/fin et prix effectifs contrôlés côté serveur. À défaut, supprimer le pourcentage et le compte à rebours. Justifier le prix de référence selon les règles applicables aux annonces de réduction. |
| A-05 | **P1 — sécurité** | `config/settings/base.py` charge `.env` depuis la racine du projet. Les settings de production héritent de ce module. | Un fichier local oublié dans l'environnement de production peut devenir une source de configuration inattendue et brouiller la séparation des secrets. | Charger `.env` uniquement dans les settings de développement. En production, injecter les secrets par l'environnement ou un gestionnaire de secrets et vérifier les permissions du fichier. |
| A-06 | **P1 — disponibilité/intégrité** | La base définie dans `config/settings/base.py` est SQLite, donc aussi celle héritée par les settings de production si aucune modification n'est faite. Le checkout réserve le stock avec transactions et `select_for_update`. | SQLite est moins adaptée à des écritures concurrentes et `select_for_update` n'offre pas les mêmes garanties que PostgreSQL/MySQL. Risque de verrouillage, contention et incidents lors de ventes simultanées. | Décider explicitement du moteur de production. Préférer PostgreSQL ou une base managée adaptée ; tester les réservations concurrentes, les sauvegardes et la restauration. |
| A-07 | **P1 — sécurité HTTP** | Les settings de production activent HTTPS, HSTS et cookies sécurisés, mais aucune politique CSP n'est configurée dans les settings inspectés. Les en-têtes réels ne peuvent pas être vérifiés depuis le dépôt. | Défense en profondeur limitée contre certaines injections et chargements de ressources non autorisés. | Définir une CSP adaptée aux scripts/styles, polices, médias et Stripe, d'abord en mode report-only puis en application ; vérifier les en-têtes réels après déploiement. Ajouter les autres en-têtes utiles sans casser Stripe. |
| A-08 | **P1 — sécurité du dashboard** | Le dashboard est réservé aux superutilisateurs et la session expire après 30 minutes, ce qui est positif. Aucune limitation de tentatives de connexion ni MFA n'est visible dans les vues/settings inspectés. | Attaques par force brute ou réutilisation de mot de passe sur un compte à privilèges élevés. | Mettre en place limitation de débit/verrouillage progressif, journalisation des tentatives, MFA pour les comptes administrateurs et mots de passe uniques via un gestionnaire. |
| A-09 | **P1 — médias** | La production ne sert pas les médias par la route Django de développement ; `config/urls.py` n'ajoute la route média que lorsque `DEBUG=True`. Le dépôt documente lui-même la nécessité de configurer le serveur web/stockage média. | Images de produits manquantes en production ou configuration improvisée ; risque si le répertoire d'upload est servi avec des permissions/exécution inadaptées. | Définir et tester le chemin média public réel sur cPanel ou un stockage objet ; empêcher toute exécution dans les répertoires d'upload ; vérifier les droits et les sauvegardes. |
| A-10 | **P1 — performance mobile** | Les SVG `static/images/mainLogo.svg` et `whiteMainLogo.svg` pèsent environ 722 Ko et 1,4 Mo dans le dépôt. | Téléchargement inutilement lourd sur mobile, ralentissement de l'affichage et dégradation possible des Core Web Vitals. | Remplacer par un vrai SVG vectoriel nettoyé ou un format raster optimisé aux dimensions réellement affichées ; vérifier les poids après build. |
| A-11 | **P1 — SEO** | Les titres de l'accueil, les textes alternatifs du logo et plusieurs libellés affichent « Ma Boutique » tandis que la marque du projet est My Line Collection. Le catalogue construit une partie importante de ses cartes côté JavaScript. Aucun sitemap/robots/canonical/JSON-LD n'a été repéré dans les fichiers et routes inspectés. | Marque incohérente dans les résultats de recherche, indexation incomplète du catalogue et extraits moins maîtrisés. | Uniformiser la marque, générer sitemap XML et robots.txt, définir canonical/OG, ajouter des données structurées Product/Breadcrumb adaptées, et rendre les liens produits essentiels crawlables sans JavaScript. Vérifier dans Search Console. |
| A-12 | **P1 — emails transactionnels** | Le dépôt configure SMTP en production, mais aucun envoi d'e-mail de confirmation de commande ou d'expédition n'a été identifié dans le flux checkout inspecté. | Le client peut payer sans recevoir de récapitulatif opérationnel ; charge accrue pour le support et perte de confiance. | Ajouter des e-mails transactionnels déclenchés par des transitions d'état fiables, avec idempotence, suivi des erreurs et contenu conforme. Ne pas envoyer l'e-mail « payé » avant confirmation serveur vérifiée. |
| A-13 | **P1 — frais et pays** | Le formulaire propose France, plusieurs pays de l'UE, Suisse et Royaume-Uni, tandis que les frais sont définis par des variables standard/express/seuil gratuit, sans matrice de livraison par pays visible. | Frais insuffisants, zones non desservies, surprises de droits/taxes ou délais irréalistes. | Définir les pays réellement livrables, frais/délais par zone, taxes et éventuels frais douaniers ; afficher ces informations avant le paiement et refuser côté serveur les destinations non prises en charge. |
| A-14 | **P2 — paiement affiché** | Le footer affiche Visa, Mastercard et PayPal. Le dépôt montre Stripe Checkout, mais ne prouve pas que PayPal est activé et disponible dans la configuration commerciale. | Promesse de moyen de paiement non disponible au checkout. | N'afficher que les moyens réellement activés et vérifiés dans l'environnement Stripe concerné. |
| A-15 | **P2 — contenu produit** | La fiche produit utilise aussi des images Unsplash pour certains produits apparentés ; la page d'accueil contient des médias Pexels/Unsplash et des contenus de démonstration. Le README avertit que contenus, avis, prix et preuves sociales de démonstration doivent être vérifiés avant ouverture. | Décalage entre la photographie, le produit réellement expédié et l'identité de marque ; risques de droits d'utilisation ou de confiance. | Remplacer les visuels génériques par des photos des produits réellement vendus, contrôler les licences, les couleurs, dimensions, matières et accessoires inclus. |
| A-16 | **P2 — conversion/UX** | Le footer présente une remise newsletter de 10 % mais le formulaire n'est pas raccordé ; les liens d'aide et de suivi ne mènent pas à un parcours réel. | Le client rencontre des impasses au moment où il cherche une réponse ou une réassurance. | Terminer ces fonctionnalités ou retirer temporairement les promesses et liens concernés. Tester chaque CTA sur mobile. |
| A-17 | **P2 — administration** | Les contrôles de taille/dimensions et validation Pillow existent pour les images via les formulaires, et les URL externes doivent être HTTPS. Il reste nécessaire de vérifier que chaque voie d'écriture passe bien par les formulaires/validators, car `Model.save()` n'appelle pas automatiquement `full_clean()`. | Une future tâche d'import ou un script interne pourrait contourner une validation portée seulement par `clean()`. | Centraliser les validations critiques dans des services/formulaires et contraintes DB lorsque possible ; tester upload MIME réel, extension, taille, dimensions, suppression et remplacement de médias. Ne pas considérer l'attribut HTML `accept="image/*"` comme une mesure de sécurité. |
| A-18 | **P2 — robustesse opérationnelle** | Le stock est réservé avant l'appel réseau à Stripe. Le code traite les erreurs Stripe interceptées, mais un arrêt brutal du processus entre la réservation et l'association de session peut laisser une commande en attente et du stock réservé. Ce risque est déjà noté dans `docs/BUY_FLOW_AUDIT.md`. | Stock immobilisé, commandes orphelines et disponibilité incorrecte. | Ajouter un traitement périodique des commandes bloquées, une expiration/réconciliation contrôlée, des alertes et des tests d'arrêt/reprise. Libérer le stock uniquement selon des transitions de commande sûres. |

## 3. Points positifs déjà présents

- Les montants et la disponibilité sont recalculés côté serveur ; le navigateur ne constitue pas la source de vérité du prix.
- Le panier valide les identifiants, quantités, lignes et sélections d'accessoires et limite la taille des requêtes.
- Les opérations d'ajout/modification du panier utilisent des requêtes POST et le middleware CSRF de Django.
- Les formulaires de gestion sont protégés par un contrôle d'accès superutilisateur ; les suppressions passent par POST.
- L'administration Django personnalisée refuse l'accès aux utilisateurs qui ne sont pas superutilisateurs.
- Le webhook Stripe vérifie la signature et les événements sont dédupliqués ; le navigateur ne marque pas lui-même une commande comme payée.
- Des contraintes de base de données protègent notamment les stocks non négatifs, les prix et la référence de prix.
- Les settings de production imposent une clé secrète, les hôtes autorisés, les origines CSRF, HTTPS et les cookies sécurisés.
- Les tests couvrent plusieurs cas du catalogue, du panier et du paiement ; la CI constitue un filet de sécurité utile.

Ces points réduisent certains risques, mais ne remplacent ni les tests sur le serveur réel ni une revue complète des dépendances, des en-têtes HTTP et des procédures d'exploitation.

## 4. Audit du parcours client et des leviers de conversion

### Parcours à valider

1. **Arrivée / accueil** : promesse de marque compréhensible, photos réelles, bénéfices concrets, CTA visible sans défilement.
2. **Catalogue** : navigation par catégorie, recherche, filtres et tri réellement fonctionnels ; états de chargement, erreurs et absence de résultats compréhensibles.
3. **Fiche produit** : photos cohérentes et zoom, couleurs disponibles, dimensions, matières, capacité, contenu exact de chaque offre, prix total, disponibilité et livraison.
4. **Panier** : quantités et prix actualisés, suppression simple, frais estimés, seuil de livraison gratuite exact, possibilité de revenir aux produits.
5. **Checkout** : champs minimaux, erreurs précises, coût final avant départ chez Stripe, délais/pays clairement indiqués, aucun compte obligatoire si le modèle est invité.
6. **Stripe / retour** : paiement réel de test, annulation et reprise du panier, confirmation exclusivement après événement Stripe vérifié.
7. **Après-vente** : e-mail de confirmation, statut de commande, contact, livraison, retours et réclamation accessibles.

### Améliorations à privilégier pour augmenter la conversion

- **Réduire les doutes avant le panier** : afficher des photos originales multi-angles, dimensions, matière, poids/capacité, photos portées si disponibles, contenu inclus et limites du produit.
- **Rendre le prix final prévisible** : expliquer livraison, délai, retour et éventuels frais dès la fiche produit ou au plus tard avant le bouton qui ouvre Stripe.
- **Clarifier les offres** : comparer simplement Essentiel / Medium / Premium, nommer les accessoires inclus, indiquer les quantités et variantes, éviter que « livraison offerte » soit confondu avec la politique de livraison globale.
- **Renforcer la confiance avec des preuves authentiques** : avis réels et modérés, mention « achat vérifié » seulement si vérifiée, coordonnées de contact et politique de retour réelles. Supprimer les notifications d'achat fictives.
- **Rendre le mobile prioritaire** : optimiser les logos et images, limiter les vidéos lourdes au-dessus de la ligne de flottaison, garantir des boutons assez grands, conserver le panier pendant les retours Stripe et tester les appareils réels.
- **Remplacer les impasses par des actions réelles** : newsletter, FAQ, contact, suivi, livraison, retours et CGV doivent fonctionner avant de pousser du trafic.
- **Éviter les fausses incitations** : aucune remise, urgence, quantité restante ou activité récente ne doit être affichée sans donnée réelle et règle commerciale vérifiable.
- **Mesurer avant d'optimiser** : suivre des événements minimaux — vue produit, sélection variante/offre, ajout panier, début checkout, redirection Stripe, paiement confirmé, annulation — sans envoyer de données personnelles inutiles. Mettre en place le consentement requis avant tout traceur non essentiel.
- **Faire des tests A/B uniquement après stabilisation** : comparer une variable à la fois (photo principale, texte CTA, ordre des informations), avec des données suffisantes ; ne pas confondre hausse de clics et hausse des achats rentables.

### Indicateurs à suivre

- Taux d'ajout au panier = sessions avec ajout / sessions avec vue produit.
- Taux de démarrage du checkout = sessions checkout / sessions avec panier.
- Taux de paiement confirmé = commandes payées / sessions checkout.
- Abandon par étape, erreurs de formulaire, échecs Stripe et taux de retour.
- Conversion mobile vs desktop, vitesse réelle, panier moyen, marge après frais de paiement/livraison et coût d'acquisition.
- Newsletter : inscriptions confirmées, désinscriptions et conversion réelle de la campagne de bienvenue.

Ne fixe pas d'objectifs arbitraires sans données de départ : établir une période de référence, segmenter par source de trafic et appareil, puis suivre les changements.

## 5. Plan de remédiation recommandé

### P0 — avant toute ouverture commerciale

- [ ] Créer les pages réelles Mentions légales, CGV, confidentialité, livraison, retours et contact ; vérifier le contenu juridique applicable.
- [ ] Remplacer les liens `#` et supprimer les promesses de fonctionnalités non disponibles.
- [ ] Raccorder la newsletter ou masquer la remise annoncée ; documenter le consentement et la désinscription.
- [ ] Désactiver la preuve sociale simulée.
- [ ] Rendre la vente flash réellement pilotée côté serveur, ou retirer le compte à rebours et la réduction.
- [ ] Vérifier chaque prix de référence, chaque promotion et chaque offre commerciale avec les prix réellement pratiqués.
- [ ] Tester tout le parcours de paiement avec le compte Stripe de test propre à My Line Collection, y compris annulation, refus, 3-D Secure, webhook invalide, doublon et reprise.
- [ ] Valider pays, livraison, délais, retours, taxes et contenu des e-mails avant d'accepter des commandes.

### P1 — sécurité et fiabilité avant trafic payant

- [ ] Sortir le chargement de `.env` des settings communs et séparer strictement développement/production.
- [ ] Choisir et tester le moteur de base de données de production.
- [ ] Configurer et tester le stockage statique et média sur l'hébergement réel.
- [ ] Mettre en place limitation de débit du login et MFA administrateur.
- [ ] Définir une CSP en report-only puis la durcir ; exécuter `python manage.py check --deploy --settings=config.settings.production` sur l'environnement cible.
- [ ] Mettre en place la surveillance des erreurs, commandes bloquées, webhooks en échec et réservations de stock.
- [ ] Ajouter les e-mails transactionnels idempotents.
- [ ] Réduire le poids des logos et optimiser les images LCP ; mesurer Lighthouse et Core Web Vitals sur mobile.
- [ ] Ajouter sitemap, robots, canonical, Open Graph et données structurées appropriées ; tester l'indexabilité.

### P2 — qualité et optimisation continue

- [ ] Uniformiser la marque « My Line Collection » dans titres, alt, textes, e-mails et métadonnées.
- [ ] Remplacer les photos génériques par les visuels exacts des articles vendus et vérifier les droits.
- [ ] Vérifier l'accessibilité clavier, lecteurs d'écran, contrastes, erreurs de formulaire et modales sur mobile.
- [ ] Tester les cas de concurrence de stock, double clic, réseau interrompu, session expirée et retour Stripe.
- [ ] Ajouter des tests de parcours navigateur automatisés sur un environnement de test.
- [ ] Définir les événements analytiques, le consentement associé et un tableau de bord de conversion.

## 6. Tests techniques à exécuter avant déploiement

Depuis l'environnement local, après synchronisation de la branche :

```powershell
python manage.py check --settings=config.settings.development
python manage.py makemigrations --check --dry-run --settings=config.settings.development
python manage.py test --settings=config.settings.development
```

Dans un environnement configuré avec les variables de production — jamais en bricolant les secrets dans le code :

```bash
python manage.py check --deploy --settings=config.settings.production
python manage.py migrate --check --settings=config.settings.production
```

Compléter ensuite par des tests navigateur réels : téléphone et desktop, connexion lente, navigation clavier, JavaScript désactivé/erreur JS, parcours catalogue → fiche → panier → checkout → Stripe → retour, annulation et réessai. Vérifier les en-têtes HTTP, les cookies, les médias, les logs, les sauvegardes et la restauration sur l'hébergement réel.

## 7. Limites de cette revue

Cette revue s'appuie sur les fichiers et configurations du dépôt à la révision indiquée. Elle ne constitue pas :
- un test d'intrusion ou une certification ;
- une analyse dynamique du site déployé ;
- une vérification de la configuration réelle cPanel/o2switch, DNS, TLS, CDN ou des en-têtes reçus par navigateur ;
- une vérification juridique des textes ou de la conformité réelle des pratiques ;
- une validation end-to-end du paiement sur le compte Stripe du commerçant ;
- une mesure Lighthouse/Core Web Vitals sur appareils réels.

Les constats doivent être confirmés lors de la correction et du test de recette. **Le statut « aucun problème détecté » ne doit jamais être déduit de la seule réussite des tests Django.**
