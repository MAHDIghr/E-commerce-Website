"use strict";
/* Les cartes, filtres GET et pages sont rendus par Django. Aucun rerendu client. */
(() => {
    document.querySelectorAll(".catalog-add").forEach(button => {
        if (typeof addProductFromCard !== "function") return;
        button.addEventListener("click", async () => {
            button.disabled = true;
            try { await addProductFromCard(button); } catch (error) {
                if (typeof showCartStatus === "function") showCartStatus("Ouvrez la fiche produit pour poursuivre ou réessayez.", true);
            } finally { button.disabled = false; }
        });
        button.hidden = false;
    });
    const saved = typeof readStorage === "function" ? readStorage("wishlist_v1", []) : [];
    const wishes = new Set(Array.isArray(saved) ? saved : []);
    document.querySelectorAll(".catalog-wish").forEach(button => {
        if (typeof readStorage !== "function" || typeof writeStorage !== "function") return;
        const slug = button.closest("[data-product-slug]").dataset.productSlug;
        button.setAttribute("aria-pressed", String(wishes.has(slug)));
        button.addEventListener("click", () => {
            wishes.has(slug) ? wishes.delete(slug) : wishes.add(slug);
            writeStorage("wishlist_v1", [...wishes]);
            button.setAttribute("aria-pressed", String(wishes.has(slug)));
        });
        button.hidden = false;
    });
    // Traduction des libellés fixes uniquement : ne reconstruit ni les cartes ni les champs.
    const labels = {"Notre boutique":"Our shop", "Rechercher":"Search", "Catégories":"Categories", "Couleurs":"Colours",
        "Prix minimum (€)":"Minimum price (€)", "Prix maximum (€)":"Maximum price (€)", "En promotion":"On sale",
        "Stock disponible ≤ 5":"Available stock ≤ 5", "Trier":"Sort", "Pertinence":"Featured", "Nouveautés":"New in",
        "Prix croissant":"Price: low to high", "Prix décroissant":"Price: high to low", "Meilleures notes":"Top rated",
        "Appliquer les filtres":"Apply filters", "Réinitialiser les filtres":"Reset filters", "Page précédente":"Previous page",
        "Page suivante":"Next page", "Choisir une offre":"Choose an offer", "Ajouter au panier":"Add to cart"};
    const originals = new Map();
    document.querySelectorAll('.catalog-filters,.catalog-pagination,.shop-head,.pcard').forEach(root => {
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
        while (walker.nextNode()) { const node = walker.currentNode; if (labels[node.textContent.trim()]) originals.set(node,node.textContent); }
    });
    function translate() {
        const english = document.documentElement.lang === "en";
        originals.forEach((text,node) => { node.textContent = english ? text.replace(text.trim(), labels[text.trim()]) : text; });
    }
    document.addEventListener("languagechange", translate); translate();
    const bar = document.getElementById("cart-bar");
    if (!bar) return;
    function update() {
        if (typeof getCart !== "function") return;
        const items = getCart();
        const count = items.reduce((sum, item) => sum + Number(item.quantity || 0), 0);
        bar.hidden = !count;
        document.body.classList.toggle("has-cart-bar", count > 0);
        document.getElementById("cart-bar-count").textContent = String(count);
        document.getElementById("cart-bar-label").textContent = count > 1 ? "articles" : "article";
        document.getElementById("cart-bar-total").textContent = formatPrice(items.reduce((sum, item) => sum + Number(item.line_total || 0), 0));
        const commercial = JSON.parse(document.getElementById("commercial-config").textContent);
        document.getElementById("cart-bar-ship").textContent = commercial.sales_ready ? "Livraison confirmée au checkout" : commercial.sales_unavailable;
    }
    if (typeof openCart !== "function") return;
    bar.querySelector("button").addEventListener("click", openCart);
    document.addEventListener("cart:updated", update);
    update();
})();
