"""Page produit — FRONT-END ONLY. Toutes les données ci-dessous sont FICTIVES.
Remplacer build_product() par Product/ProductVariant/ProductMedia/ProductOffer/
Review/RelatedProduct : le template ne dépend que de la forme du dict `product`."""
from django.shortcuts import render


def eur(v):
    return f"{v:.2f}".replace(".", ",") + " €"


def img(photo_id, w=900):
    return f"https://images.unsplash.com/photo-{photo_id}?auto=format&fit=crop&w={w}&q=80"


def media(kind, photo_id, alt, src=None):
    return {"type": kind, "src": src or img(photo_id), "poster": img(photo_id) if kind == "video" else None,
            "thumb": img(photo_id, 160), "alt": alt}


def offer(id, title, items, price, old, ship, badge="", featured=False):
    return {"id": id, "title": title, "items": items, "price": price, "old": old, "price_label": eur(price),
            "old_label": eur(old), "off": round((1 - price / old) * 100), "ship": ship, "badge": badge,
            "featured": featured}


def build_product():
    offers = [
        offer("basic", "Basic", "1 sac", 89.90, 129.90, "Livraison payante", "Essentiel"),
        offer("plus", "Essential+", "1 sac + 1 portefeuille", 109.90, 159.90, "Livraison payante", "Le plus populaire", True),
        offer("complete", "Complete Pack", "1 sac + portefeuille + porte-cartes", 139.90, 199.90, "Livraison offerte", "Meilleure valeur"),
    ]
    return {
        "slug": "sac-cabas-camel", "name": "Sac cabas camel", "brand_line": "Collection signature",
        "tagline": "Le cabas du quotidien : il tient votre journée entière sans perdre sa ligne.",
        "rating": 4.8, "reviews_count": 326,
        "media": [
            media("image", "1590874103328-eac38a683ce7", "Sac cabas camel, vue de face"),
            media("image", "1548036328-c9fa89d128fa", "Le sac porté à l'épaule en ville"),
            media("video", "1584917865442-de89df76afd3", "Le sac en mouvement", "/static/product/media/demo.mp4"),
            media("image", "1591561954557-26941169b49e", "Intérieur du sac et poche zippée"),
            media("image", "1553062407-98eeb64c6a62", "Contenu rangé dans le sac"),
            media("image", "1594223274512-ad4803739b7c", "Détail de la couture et du fermoir"),
            media("image", "1607344645866-009c320c5ab8", "Le sac en situation, soirée"),
            media("image", "1548863227-3af567fc3b27", "Le sac avec ses accessoires"),
        ],
        "colors": [{"id": "camel", "label": "Camel", "hex": "#b07a4a"}, {"id": "noir", "label": "Noir", "hex": "#1c1613"},
                   {"id": "creme", "label": "Crème", "hex": "#e9dcc6"}],
        "offers": offers, "selected": offers[1],
        "benefits": [
            {"t": "Tout est à sa place", "d": "Une poche zippée et deux poches plaquées pour retrouver clés et téléphone sans fouiller."},
            {"t": "Confortable toute la journée", "d": "Anses larges pensées pour porter à l'épaule ou à la main."},
            {"t": "Une allure qui reste", "d": "Une ligne structurée et une teinte camel qui se marie à tout."},
            {"t": "Assez grand, jamais encombrant", "d": "Le format d'un 13 pouces, sans le volume d'un sac de voyage."},
        ],
        "fits": [("Smartphone", True), ("Portefeuille", True), ("Clés", True), ("Lunettes", True), ("Chargeur", True),
                 ("Carnet A5", True), ("Tablette 11\"", True), ("Ordinateur 15\"", False)],
        "dims": {"w": 34, "h": 28, "d": 14, "weight": "0,8 kg", "volume": "11 L"},
        "craft": [
            {"t": "Matière", "d": "Surface grainée qui résiste aux frottements du quotidien.", "img": img("1590874103328-eac38a683ce7", 600)},
            {"t": "Coutures", "d": "Piqûres renforcées aux points de charge des anses.", "img": img("1594223274512-ad4803739b7c", 600)},
            {"t": "Fermeture", "d": "Zip métallisé fluide, sans accroc.", "img": img("1591561954557-26941169b49e", 600)},
            {"t": "Doublure", "d": "Intérieur clair pour voir ce qu'on cherche.", "img": img("1553062407-98eeb64c6a62", 600)},
        ],
        "lifestyle": [("Au bureau", "1584917865442-de89df76afd3"), ("Au quotidien", "1548036328-c9fa89d128fa"),
                      ("En voyage", "1591561954557-26941169b49e"), ("Shopping", "1548863227-3af567fc3b27"),
                      ("En soirée", "1607344645866-009c320c5ab8")],
        "dist": [{"n": 5, "pct": 82}, {"n": 4, "pct": 12}, {"n": 3, "pct": 4}, {"n": 2, "pct": 1}, {"n": 1, "pct": 1}],
        "reviews": [  # FICTIFS — à remplacer par de vrais avis vérifiés
            {"who": "Camille D.", "stars": 5, "t": "Plus grand qu'il n'y paraît, et la couleur est superbe."},
            {"who": "Sarah M.", "stars": 5, "t": "Mon ordinateur 13 pouces rentre sans forcer."},
            {"who": "Léa B.", "stars": 4, "t": "Très beau, les anses sont confortables."},
        ],
        "faq": [
            ("Quelles sont les dimensions ?", "34 × 28 × 14 cm, pour environ 0,8 kg."),
            ("Que peut-on y ranger ?", "Un ordinateur jusqu'à 13\", un carnet A5, un portefeuille, des clés et un téléphone."),
            ("De quelle matière est-il fait ?", "Information fictive : à compléter avec la fiche matière réelle."),
            ("Comment l'entretenir ?", "Essuyer avec un chiffon doux et sec ; éviter l'exposition prolongée à l'eau."),
            ("Quels sont les délais de livraison ?", "Information fictive : à relier aux vraies conditions d'expédition."),
            ("Puis-je retourner mon achat ?", "Oui, retours gratuits sous 30 jours."),
            ("Que contiennent les offres ?", "Basic : le sac. Essential+ : sac et portefeuille. Complete Pack : sac, portefeuille et porte-cartes."),
            ("Quelle offre choisir ?", "Basic si vous n'avez besoin que du sac ; Complete Pack pour tout assortir avec la livraison offerte."),
        ],
        "related": [("Portefeuille compact beige", "45,00 €", "1591344395067-98c9a56b1a1a"),
                    ("Sac bandoulière noir", "89,90 €", "1548863227-3af567fc3b27"),
                    ("Foulard en soie", "39,90 €", "1601924994987-69e26d50dc26"),
                    ("Sac à main crème", "149,00 €", "1548036328-c9fa89d128fa")],
    }


def detail(request, slug):
    return render(request, "product_detail.html", {"product": build_product()})