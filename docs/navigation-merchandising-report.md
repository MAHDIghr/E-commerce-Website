# Lot 8 — Navigation et merchandising

Branche `fix/commercial-information`, départ `c5f18a2`. Un commit cohérent, sans changement de modèle ni migration. Instructions de contribution, fichiers demandés, modèles, sélecteurs et tests équivalents lus avant modification ; arbre de travail initial propre.

## Constat et contrat avant / après

- Le hero annonçait une collection mais ciblait le carrousel `#selection`. Il mène maintenant au catalogue Django. Le lien « En savoir plus » menait déjà à `pages:about` : destination conservée, sans régression vers les avis.
- La construction JS `t()[cat_…]` n’existe plus depuis le lot 7. Les cartes serveur reçoivent désormais `category_label` du sélecteur partagé : nom administré, sinon slug rendu lisible. Catalogue et favoris utilisent le même partial.
- `SignatureSelection.image` était exigée, puis ignorée au profit d’une image produit/variante. Le comportement retenu respecte le modèle éditorial existant : **image dédiée et son alt dédié**, produit et prix toujours liés au catalogue serveur. Aucun média inventé, aucune image remplacée dans les données.
- Bénéfices, contenu/dimensions, fabrication, usages et FAQ étaient affichés même sans données. Leurs sections sont maintenant conditionnelles. La matière et la description viennent des champs administrés existants, échappés par Django. Seules les dimensions renseignées sont listées ; le schéma de proportions exige largeur et hauteur. Les titres neutres « Pourquoi choisir ce produit », « Contenu et dimensions », « Usages du produit » conviennent aux sacs comme aux accessoires. Un titre d’usage personnalisé reste conservé.
- Les favoris étaient enregistrables mais ne disposaient d’aucune liste consultable. La navigation conduit à une page de favoris locaux, avec liens réels, retrait persistant et pages de huit identifiants. La résolution serveur n’expose que des produits publiés et reste bornée à huit. Les identifiants ne créent aucune donnée serveur ; l’endpoint est en GET, cache privé/no-store. Les favoris indisponibles restent retirables. Une erreur réseau conserve la liste et propose Réessayer. Les réponses obsolètes sont ignorées ; la liste se synchronise sur l’événement storage entre onglets.
- L’action principale est « Acheter maintenant » sur la fiche, en bas de page et dans la barre mobile. L’action secondaire garde son icône mais ajoute le texte visible « Ajouter au panier ». Les gestionnaires prix/offres/accessoires existants sont conservés. Sous 600 px, les deux actions peuvent occuper chacune une ligne, sans refonte de la charte.

## Fichiers modifiés et raison

| Fichier | Changement |
|---|---|
| `home/templates/home.html` | Hero vers le catalogue, image et alt dédiés Signature. |
| `home/tests.py` | Attente du média éditorial configuré et de son alt, tout en contrôlant lien et prix. |
| `product/selectors.py` | Nom administré de catégorie et repli lisible dans la source commune des cartes. |
| `shop/templates/shop/_product_card.html` | Affichage du nom de catégorie sur catalogue et favoris. |
| `product/views.py` | Matière/description existantes, présence de dimensions, titre d’usage neutre si l’ancien titre générique est utilisé. |
| `product/templates/product.html` | Sections conditionnelles, faits renseignés uniquement et actions d’achat explicitement libellées. |
| `product/static/css/product.css` | Retour à la ligne des deux actions lisibles sur téléphone. |
| `product/tests.py` | Attentes de la classe et du libellé de l’action secondaire devenue textuelle. |
| `templates/partials/_header.html` | Accès à Mes favoris dans la navigation. |
| `shop/urls.py` | Route nommée `shop:favorites`. |
| `shop/views.py` | Page de favoris et résolution publique bornée de huit identifiants. |
| `shop/templates/shop/favorites.html` | Liste, statut accessible, reprise, navigation et explication du stockage local/noscript. |
| `shop/static/js/favorites.js` | Lecture locale, rendu du partial serveur, retrait, pagination, erreurs/reprise et synchronisation d’onglets. |
| `shop/test_merchandising.py` | Quatre tests de publication, borne, confidentialité de session, catégories, sections et faits échappés. |
| `tests/favorites.test.cjs` | Deux tests DOM du parcours retrouver/ouvrir/retirer et de la conservation sur panne réseau. |
| `README.md` et ce rapport | Contrat et limites documentés. |

Les fichiers `home/views.py`, `home/models.py` et `shop/static/js/shop.js` ont été relus sans nécessiter de modification. Le contrat média du modèle Signature était déjà celui d’une image dédiée ; les favoris existants du catalogue et de l’accueil partagent déjà la clé locale `wishlist_v1`.

## Validation réellement exécutée

```bash
DJANGO_SECRET_KEY=local-tests-only ../venv/bin/python manage.py test home product shop --settings=config.settings.development
DJANGO_SECRET_KEY=local-tests-only ../venv/bin/python manage.py test --settings=config.settings.development
NODE_PATH=../checkout-test-runtime/node_modules node --test tests/favorites.test.cjs
node --check shop/static/js/favorites.js
DJANGO_SECRET_KEY=local-tests-only ../venv/bin/python manage.py check --settings=config.settings.development
DJANGO_SECRET_KEY=local-tests-only ../venv/bin/python manage.py makemigrations --check --dry-run --settings=config.settings.development
git diff --check
```

- **217 tests Django réussis**, 15,809 s, suite complète finale. Les anciens résultats d’audit ne sont pas présentés comme une validation nouvelle.
- **2 tests DOM réussis**, dernière passe 1,032 s : favori retrouvé avec lien de fiche, retrait enregistré localement, panne réseau sans perte et bouton Réessayer. Réseau et stockage simulés avec jsdom temporaire hors dépôt ; aucune dépendance de production ajoutée.
- Django check sans problème ; aucune migration détectée ; syntaxe JavaScript et diff sans erreur.
- La première passe ciblée de 87 tests avait deux échecs attendus d’ancien contrat (image produit et classe icône). La première passe complète avait deux échecs d’attente (ancien libellé Acheter et recherche d’un titre également présent dans le JSON). Les tests ont été ajustés au HTML réel puis la suite complète a été relancée avec succès. Aucun calcul ou contrôle serveur n’a été affaibli pour les faire passer.

Les quatre nouveaux tests Django couvrent la page liée et sa notice noscript, l’absence de favoris en session, la limite de huit et le refus des produits dépubliés, le nom de catégorie administré, la suppression des sections vides, les actions lisibles et les faits échappés. Les tests Signature vérifient média dédié, alt, destination et prix existant.

## Contrôles du code et protections

Les données de cartes viennent des mêmes sélecteurs et du même partial que le catalogue ; le serveur recalcule toujours les montants avant achat. Aucun changement de prix, remises, stock, CSRF, webhook signé, idempotence ou Stripe Checkout hébergé. Aucun compte ni favori persistant côté serveur ajouté. Le stockage local contient uniquement des identifiants de produits ; aucune coordonnée, secret ou prix faisant autorité.

Les textes administrés sont échappés par Django. Le HTML des favoris est rendu par le serveur de même origine, puis inséré ; les identifiants issus du stockage ne sont utilisés que comme valeurs URL encodées et texte via textContent. Les produits disparus ne deviennent pas des liens inventés. Le retrait relit l’état local courant pour limiter les pertes entre onglets.

## Décisions et données manquantes

L’exploitant doit fournir pour chaque produit concerné : dimensions et unités vérifiées, matière/composition et origine si annoncée, usages étayés, consignes d’entretien réelles, visuels et alt correspondants. Les champs existants de description, matière, usages, fabrication et FAQ peuvent porter ces faits ; aucun texte d’entretien générique n’est généré. En l’absence de données, le bloc reste absent. Les contenus de marque de `pages:about` attendent toujours leur validation dans le dossier commercial ; le lien est correct, mais une histoire de marque n’est pas inventée.

L’image Signature dédiée est choisie conformément au modèle existant. L’exploitant doit vérifier que les images déjà téléversées correspondent bien aux produits liés et sont disponibles dans le stockage média avant publication.

## Navigateur et recette restante

Tentative réelle de lancement Playwright/Chromium : échec, exécutable `chromium_headless_shell-1234` absent. **Aucune capture ni largeur 320/360/390/430/768/1366 px n’a été validée visuellement.** Les contrôles HTTP et les tests DOM ne valident pas l’emplacement des actions, le rendu du carrousel ou les usages réels.

Restent à faire sur préproduction : captures aux six largeurs, zoom texte 200 %, contraste et focus, navigation clavier/lecteur d’écran, Safari iPhone/Chrome Android, parcours utilisateur fiche → action principale/ajout, compréhension des deux actions, navigation vers les favoris depuis accueil/catalogue, retrait, pagination, onglets concurrents et refus de stockage local. Vérifier aussi l’absence d’images manquantes et le CTA de marque avec contenu approuvé. Les favoris dépendent de JavaScript et du stockage autorisé sur ce navigateur ; aucune synchronisation entre appareils n’est annoncée.

Le lot n’est pas entièrement validé pour le rendu et l’usage tant que les captures et essais utilisateur manquent. Les ventes demeurent bloquées sans dossier commercial complet. Aucun déploiement, fusion ou paiement réel.
