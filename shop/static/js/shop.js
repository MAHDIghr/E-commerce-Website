"use strict";

/* ==========================================================================
   Catalogue — dépend de base.js (readStorage, writeStorage, formatPrice,
   addToCart, getCart, openCart, playAddedFeedback).
   Les produits ci-dessous sont des EXEMPLES : ils seront remplacés par des
   données Django (modèle Product) dans la phase back-end.
   ========================================================================== */

(function initCatalog() {

    const grid = document.getElementById("product-grid");
    if (!grid) return;

    /* URL de base de la page produit (fournie par Django via data-product-url) */
    const PRODUCT_URL = grid.dataset.productUrl || "#";

    /* ---------- Données d'exemple (images Unsplash temporaires) ---------- */
    const IMG = (id) => `https://images.unsplash.com/photo-${id}?auto=format&fit=crop&w=700&q=80`;

    const PRODUCTS = [
        { id: "sac-cuir-camel",       name: "Sac cabas cuir camel",          cat: "handbags",    price: 129.90, old: null,  colors: ["camel"],           rating: 4.8, reviews: 126, stock: 3,  isNew: true,  pop: 90, img: IMG("1590874103328-eac38a683ce7") },
        { id: "sac-bandouliere-noir", name: "Sac bandoulière noir matelassé", cat: "shoulder",    price: 89.90,  old: null,  colors: ["noir"],            rating: 4.9, reviews: 214, stock: 24, isNew: false, pop: 100, best: true, img: IMG("1548863227-3af567fc3b27") },
        { id: "portefeuille-beige",   name: "Portefeuille compact beige",     cat: "wallets",     price: 45.00,  old: 55.00, colors: ["beige"],           rating: 4.7, reviews: 88,  stock: 5,  isNew: false, pop: 70, img: IMG("1591344395067-98c9a56b1a1a") },
        { id: "foulard-soie",         name: "Foulard imprimé en soie",        cat: "accessories", price: 39.90,  old: null,  colors: ["beige", "rouge"],  rating: 4.6, reviews: 57,  stock: 30, isNew: true,  pop: 60, img: IMG("1601924994987-69e26d50dc26") },
        { id: "sac-main-creme",       name: "Sac à main structuré crème",     cat: "handbags",    price: 149.00, old: null,  colors: ["creme"],           rating: 4.8, reviews: 63,  stock: 12, isNew: false, pop: 65, img: IMG("1548036328-c9fa89d128fa") },
        { id: "mini-bandouliere-rouge", name: "Mini sac bandoulière rouge",   cat: "shoulder",    price: 74.90,  old: 94.90, colors: ["rouge", "noir"],   rating: 4.7, reviews: 102, stock: 18, isNew: false, pop: 80, img: IMG("1591561954557-26941169b49e") },
        { id: "portefeuille-noir",    name: "Portefeuille zippé noir",        cat: "wallets",     price: 49.00,  old: null,  colors: ["noir"],            rating: 4.9, reviews: 141, stock: 40, isNew: false, pop: 95, best: true, img: IMG("1553062407-98eeb64c6a62") },
        { id: "tote-toile",           name: "Tote bag toile et cuir",         cat: "handbags",    price: 59.90,  old: null,  colors: ["beige", "vert"],   rating: 4.5, reviews: 39,  stock: 22, isNew: true,  pop: 50, img: IMG("1584917865442-de89df76afd3") },
        { id: "ceinture-cuir",        name: "Ceinture cuir camel",            cat: "accessories", price: 34.90,  old: null,  colors: ["camel", "noir"],   rating: 4.6, reviews: 71,  stock: 35, isNew: false, pop: 55, img: IMG("1594223274512-ad4803739b7c") },
        { id: "pochette-soiree",      name: "Pochette de soirée verte",       cat: "shoulder",    price: 64.00,  old: 79.00, colors: ["vert"],            rating: 4.4, reviews: 28,  stock: 9,  isNew: false, pop: 40, img: IMG("1607344645866-009c320c5ab8") },
        { id: "porte-cartes-noir",    name: "Porte-cartes cuir noir",         cat: "wallets",     price: 24.90,  old: null,  colors: ["noir", "camel"],   rating: 4.8, reviews: 190, stock: 60, isNew: false, pop: 92, best: true, img: IMG("1591344395067-98c9a56b1a1a") },
        { id: "bandouliere-camel",    name: "Sac bandoulière camel",          cat: "shoulder",    price: 99.00,  old: null,  colors: ["camel"],           rating: 4.7, reviews: 77,  stock: 4,  isNew: true,  pop: 75, img: IMG("1548863227-3af567fc3b27") },
    ];

    const COLORS = { camel: "#b07a4a", noir: "#1c1613", beige: "#d8c3a5", creme: "#f3ead8", rouge: "#a3372f", vert: "#3f5d4b" };
    const PAGE_SIZE = 8;
    const LOW_STOCK = 5;
    const WISH_KEY = "wishlist_v1";

    /* ---------- Textes FR / EN ---------- */
    const T = {
        fr: {
            bc_home: "Accueil", bc_shop: "Boutique", title: "Notre boutique",
            subtitle: "Sacs et accessoires en cuir, choisis pour durer. Livraison offerte dès 80 €, retours gratuits sous 30 jours.",
            filters: "Filtres", f_category: "Catégorie", f_price: "Prix (€)", f_color: "Couleur", f_more: "Autres",
            f_sale: "En promotion", f_lowstock: "Derniers exemplaires", reset: "Réinitialiser", show: "Voir",
            sort_label: "Trier par", empty_title: "Aucun produit ne correspond",
            empty_text: "Essayez d'élargir vos critères ou de retirer un filtre.", load_more: "Voir plus de produits",
            cat_handbags: "Sacs à main", cat_shoulder: "Sacs bandoulière", cat_wallets: "Portefeuilles", cat_accessories: "Accessoires",
            all: "Tout voir", results: (n) => `${n} produit${n > 1 ? "s" : ""}`,
            shown: (a, b) => `${a} sur ${b} produits affichés`,
            sort: { pop: "Pertinence", new: "Nouveautés", best: "Meilleures notes", asc: "Prix croissant", desc: "Prix décroissant" },
            newTag: "Nouveau", bestTag: "Meilleure vente", left: (n) => `Plus que ${n}`,
            add: (n) => `Ajouter ${n} au panier`, wish: "Ajouter aux favoris", reviews: "avis",
            clear: "Tout effacer", remove: "Retirer le filtre", sale: "Promo", lowstock: "Derniers exemplaires",
            ra_ship: "Livraison offerte dès 80 €", ra_ship_s: "Expédition sous 24 h", ra_ret: "Retours gratuits 30 jours",
            ra_ret_s: "Sans condition", ra_pay: "Paiement sécurisé", ra_pay_s: "SSL & 3D Secure",
            item: (n) => (n > 1 ? "articles" : "article"),
            shipLeft: (r) => `Plus que ${r} pour la livraison offerte`, shipOk: "Livraison offerte",
        },
        en: {
            bc_home: "Home", bc_shop: "Shop", title: "Our shop",
            subtitle: "Leather bags and accessories, chosen to last. Free shipping over €80, free returns within 30 days.",
            filters: "Filters", f_category: "Category", f_price: "Price (€)", f_color: "Colour", f_more: "More",
            f_sale: "On sale", f_lowstock: "Last few left", reset: "Reset", show: "Show",
            sort_label: "Sort by", empty_title: "No products match",
            empty_text: "Try widening your criteria or removing a filter.", load_more: "Show more products",
            cat_handbags: "Handbags", cat_shoulder: "Shoulder bags", cat_wallets: "Wallets", cat_accessories: "Accessories",
            all: "All", results: (n) => `${n} product${n > 1 ? "s" : ""}`,
            shown: (a, b) => `${a} of ${b} products shown`,
            sort: { pop: "Featured", new: "New in", best: "Top rated", asc: "Price: low to high", desc: "Price: high to low" },
            newTag: "New", bestTag: "Best seller", left: (n) => `Only ${n} left`,
            add: (n) => `Add ${n} to cart`, wish: "Add to wishlist", reviews: "reviews",
            clear: "Clear all", remove: "Remove filter", sale: "Sale", lowstock: "Last few left",
            ra_ship: "Free shipping over €80", ra_ship_s: "Ships within 24h", ra_ret: "Free returns, 30 days",
            ra_ret_s: "No questions asked", ra_pay: "Secure payment", ra_pay_s: "SSL & 3D Secure",
            item: (n) => (n > 1 ? "items" : "item"),
            shipLeft: (r) => `${r} away from free shipping`, shipOk: "Free shipping unlocked",
        },
    };
    let lang = document.documentElement.lang === "en" ? "en" : "fr";
    const t = () => T[lang];

    /* ---------- État (synchronisé avec l'URL pour un partage facile) ---------- */
    const CATS = ["handbags", "shoulder", "wallets", "accessories"];
    const SORTS = ["pop", "new", "best", "asc", "desc"];

    const state = { cats: new Set(), colors: new Set(), min: null, max: null, sale: false, low: false, sort: "pop", page: 1 };

    function readUrl() {
        const p = new URLSearchParams(window.location.search);
        (p.get("cat") || "").split(",").filter((c) => CATS.includes(c)).forEach((c) => state.cats.add(c));
        (p.get("color") || "").split(",").filter((c) => COLORS[c]).forEach((c) => state.colors.add(c));
        const num = (v) => { const n = parseFloat(v); return Number.isFinite(n) && n >= 0 && n <= 5000 ? n : null; };
        state.min = num(p.get("min"));
        state.max = num(p.get("max"));
        state.sale = p.get("sale") === "1";
        state.low = p.get("low") === "1";
        state.sort = SORTS.includes(p.get("sort")) ? p.get("sort") : "pop";
    }

    function writeUrl() {
        const p = new URLSearchParams();
        if (state.cats.size) p.set("cat", [...state.cats].join(","));
        if (state.colors.size) p.set("color", [...state.colors].join(","));
        if (state.min !== null) p.set("min", state.min);
        if (state.max !== null) p.set("max", state.max);
        if (state.sale) p.set("sale", "1");
        if (state.low) p.set("low", "1");
        if (state.sort !== "pop") p.set("sort", state.sort);
        const qs = p.toString();
        window.history.replaceState(null, "", qs ? `?${qs}` : window.location.pathname);
    }

    /* ---------- Filtrage et tri ---------- */
    function matches(product) {
        if (state.cats.size && !state.cats.has(product.cat)) return false;
        if (state.colors.size && !product.colors.some((c) => state.colors.has(c))) return false;
        if (state.min !== null && product.price < state.min) return false;
        if (state.max !== null && product.price > state.max) return false;
        if (state.sale && !product.old) return false;
        if (state.low && product.stock > LOW_STOCK) return false;
        return true;
    }

    function sorted(list) {
        const copy = [...list];
        const by = {
            pop: (a, b) => b.pop - a.pop,
            new: (a, b) => Number(b.isNew) - Number(a.isNew) || b.pop - a.pop,
            best: (a, b) => b.rating - a.rating || b.reviews - a.reviews,
            asc: (a, b) => a.price - b.price,
            desc: (a, b) => b.price - a.price,
        };
        return copy.sort(by[state.sort]);
    }

    /* ---------- Helpers DOM (textContent uniquement : pas d'injection HTML) ---------- */
    function el(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    }

    function svgIcon(pathData, extra) {
        const ns = "http://www.w3.org/2000/svg";
        const svg = document.createElementNS(ns, "svg");
        svg.setAttribute("class", "icon");
        svg.setAttribute("viewBox", "0 0 24 24");
        svg.setAttribute("aria-hidden", "true");
        pathData.forEach((d) => {
            const path = document.createElementNS(ns, "path");
            path.setAttribute("d", d);
            svg.appendChild(path);
        });
        if (extra) svg.setAttribute("data-kind", extra);
        return svg;
    }

    const HEART = "M12 21s-7-4.5-9.5-8.5C.7 9 2 5.5 5.5 5c2-.3 3.7.7 4.5 2.2C10.8 5.7 12.5 4.7 14.5 5c3.5.5 4.8 4 3 7.5C19 16.5 12 21 12 21z";
    const PLUS = "M12 5v14M5 12h14";
    const CHECK = "M5 12.5l4.5 4.5L19 7.5";
    const CLOSE = "M6 6l12 12M6 18L18 6";

    const wishlist = new Set(readStorage(WISH_KEY, []).filter((id) => typeof id === "string"));

    /* ---------- Carte produit ---------- */
    function buildCard(p, index) {
        const card = el("article", "pcard");
        card.style.setProperty("--i", String(Math.min(index, 8)));

        const media = el("a", "pcard__media");
        media.href = `${PRODUCT_URL}${p.id}/`;
        media.setAttribute("aria-label", p.name);

        const img = document.createElement("img");
        img.src = p.img; img.alt = ""; img.loading = "lazy"; img.decoding = "async";
        img.width = 700; img.height = 875;
        media.appendChild(img);

        const tags = el("div", "pcard__tags");
        if (p.old) tags.appendChild(el("span", "tag tag--sale", `-${Math.round((1 - p.price / p.old) * 100)}%`));
        else if (p.isNew) tags.appendChild(el("span", "tag", t().newTag));
        if (p.best) tags.appendChild(el("span", "tag tag--best", t().bestTag));
        if (p.stock <= LOW_STOCK) tags.appendChild(el("span", "tag tag--stock", t().left(p.stock)));
        media.appendChild(tags);

        const wish = el("button", "pcard__wish");
        wish.type = "button";
        wish.setAttribute("aria-label", t().wish);
        wish.setAttribute("aria-pressed", String(wishlist.has(p.id)));
        wish.appendChild(svgIcon([HEART]));
        wish.addEventListener("click", () => {
            const on = !wishlist.has(p.id);
            on ? wishlist.add(p.id) : wishlist.delete(p.id);
            wish.setAttribute("aria-pressed", String(on));
            writeStorage(WISH_KEY, [...wishlist]);
        });

        const add = el("button", "pcard__add");
        add.type = "button";
        add.setAttribute("aria-label", t().add(p.name));
        add.appendChild(svgIcon([PLUS]));
        add.addEventListener("click", () => {
            addToCart({ id: p.id, name: p.name, price: p.price, image: p.img });
            add.classList.add("is-added");
            add.replaceChildren(svgIcon([CHECK]));
            window.setTimeout(() => {
                add.classList.remove("is-added");
                add.replaceChildren(svgIcon([PLUS]));
            }, 1200);
        });

        const mediaWrap = el("div");
        mediaWrap.style.position = "relative";
        mediaWrap.append(media, wish, add);

        const body = el("div", "pcard__body");
        body.appendChild(el("p", "pcard__cat", t()[`cat_${p.cat}`]));

        const h3 = el("h3", "pcard__name");
        const link = el("a", "", p.name);
        link.href = `${PRODUCT_URL}${p.id}/`;
        h3.appendChild(link);
        body.appendChild(h3);

        const rating = el("p", "rating");
        const full = Math.round(p.rating);
        rating.appendChild(el("span", "rating__stars", "★".repeat(full) + "☆".repeat(5 - full)));
        rating.appendChild(el("span", "", `${p.rating.toFixed(1)} (${p.reviews})`));
        rating.setAttribute("aria-label", `${p.rating} / 5, ${p.reviews} ${t().reviews}`);
        body.appendChild(rating);

        const price = el("p", "price");
        price.appendChild(el("span", "", formatPrice(p.price)));
        if (p.old) {
            price.appendChild(el("del", "", formatPrice(p.old)));
        }
        body.appendChild(price);

        const sw = el("ul", "swatches");
        sw.setAttribute("aria-hidden", "true");
        p.colors.forEach((c) => {
            const li = el("li", "swatch");
            li.style.backgroundColor = COLORS[c];
            sw.appendChild(li);
        });
        body.appendChild(sw);

        card.append(mediaWrap, body);
        return card;
    }

    /* ---------- Rendu ---------- */
    const $ = (id) => document.getElementById(id);
    const countEl = $("results-count");
    const emptyEl = $("empty-state");
    const moreWrap = $("more-wrap");

    function activeFilterCount() {
        return state.cats.size + state.colors.size + (state.min !== null || state.max !== null ? 1 : 0) + (state.sale ? 1 : 0) + (state.low ? 1 : 0);
    }

    function render({ keepPage = false } = {}) {
        if (!keepPage) state.page = 1;
        const all = sorted(PRODUCTS.filter(matches));
        const visible = all.slice(0, state.page * PAGE_SIZE);

        grid.classList.remove("is-ready");
        grid.replaceChildren(...visible.map(buildCard));
        void grid.offsetWidth;
        grid.classList.add("is-ready");
        grid.setAttribute("aria-busy", "false");

        countEl.textContent = t().results(all.length);
        $("filters-count").textContent = String(all.length);
        emptyEl.hidden = all.length !== 0;

        moreWrap.hidden = all.length <= visible.length;
        $("more-progress").textContent = t().shown(visible.length, all.length);
        $("more-fill").style.width = `${all.length ? (visible.length / all.length) * 100 : 0}%`;

        const n = activeFilterCount();
        const badge = $("filters-badge");
        badge.hidden = n === 0;
        badge.textContent = String(n);

        renderPills();
        renderChips();
        writeUrl();
    }

    function renderPills() {
        const list = $("category-pills");
        list.replaceChildren();
        const make = (label, value) => {
            const li = document.createElement("li");
            const b = el("button", "", label);
            b.type = "button";
            const active = value === null ? state.cats.size === 0 : state.cats.size === 1 && state.cats.has(value);
            b.setAttribute("aria-pressed", String(active));
            b.addEventListener("click", () => {
                state.cats.clear();
                if (value) state.cats.add(value);
                syncInputs();
                render();
            });
            li.appendChild(b);
            list.appendChild(li);
        };
        make(t().all, null);
        CATS.forEach((c) => make(t()[`cat_${c}`], c));
    }

    function chip(label, onRemove) {
        const c = el("span", "chip", label);
        const b = el("button");
        b.type = "button";
        b.setAttribute("aria-label", `${t().remove} : ${label}`);
        b.appendChild(svgIcon([CLOSE]));
        b.addEventListener("click", () => { onRemove(); syncInputs(); render(); });
        c.appendChild(b);
        return c;
    }

    function renderChips() {
        const box = $("active-chips");
        box.replaceChildren();
        state.cats.forEach((c) => box.appendChild(chip(t()[`cat_${c}`], () => state.cats.delete(c))));
        state.colors.forEach((c) => box.appendChild(chip(c, () => state.colors.delete(c))));
        if (state.min !== null || state.max !== null) {
            const label = `${state.min ?? 0} – ${state.max ?? "∞"} €`;
            box.appendChild(chip(label, () => { state.min = null; state.max = null; }));
        }
        if (state.sale) box.appendChild(chip(t().sale, () => { state.sale = false; }));
        if (state.low) box.appendChild(chip(t().lowstock, () => { state.low = false; }));
        if (activeFilterCount() > 1) {
            const clear = el("button", "chip chip--clear", t().clear);
            clear.type = "button";
            clear.addEventListener("click", resetAll);
            box.appendChild(clear);
        }
    }

    /* ---------- Formulaire de filtres ---------- */
    function buildColorFilters() {
        const box = $("color-filters");
        box.replaceChildren();
        Object.keys(COLORS).forEach((name) => {
            const label = el("label", "swatch-opt");
            const input = document.createElement("input");
            input.type = "checkbox"; input.value = name; input.name = "color";
            input.setAttribute("aria-label", name);
            const dot = el("span");
            dot.style.backgroundColor = COLORS[name];
            label.append(input, dot);
            box.appendChild(label);
        });
    }

    function buildSortOptions() {
        const select = $("sort");
        select.replaceChildren();
        SORTS.forEach((key) => {
            const opt = el("option", "", t().sort[key]);
            opt.value = key;
            select.appendChild(opt);
        });
        select.value = state.sort;
    }

    function syncInputs() {
        document.querySelectorAll('input[name="cat"]').forEach((i) => { i.checked = state.cats.has(i.value); });
        document.querySelectorAll('input[name="color"]').forEach((i) => { i.checked = state.colors.has(i.value); });
        $("price-min").value = state.min ?? "";
        $("price-max").value = state.max ?? "";
        $("filter-sale").checked = state.sale;
        $("filter-stock").checked = state.low;
        $("sort").value = state.sort;
    }

    function resetAll() {
        state.cats.clear(); state.colors.clear();
        state.min = null; state.max = null; state.sale = false; state.low = false;
        syncInputs();
        render();
    }

    function toggleSet(set, value, on) { on ? set.add(value) : set.delete(value); }

    document.addEventListener("change", (event) => {
        const target = event.target;
        if (!(target instanceof HTMLInputElement || target instanceof HTMLSelectElement)) return;

        if (target.name === "cat") toggleSet(state.cats, target.value, target.checked);
        else if (target.name === "color") toggleSet(state.colors, target.value, target.checked);
        else if (target.id === "filter-sale") state.sale = target.checked;
        else if (target.id === "filter-stock") state.low = target.checked;
        else if (target.id === "sort") state.sort = SORTS.includes(target.value) ? target.value : "pop";
        else if (target.id === "price-min" || target.id === "price-max") {
            const v = parseFloat(target.value);
            const value = Number.isFinite(v) && v >= 0 ? v : null;
            if (target.id === "price-min") state.min = value; else state.max = value;
        } else return;

        render();
    });

    document.querySelectorAll(".price-quick button").forEach((btn) => {
        btn.addEventListener("click", () => {
            const [min, max] = btn.dataset.price.split("-");
            state.min = min === "" ? null : Number(min);
            state.max = max === "" ? null : Number(max);
            syncInputs();
            render();
        });
    });

    $("filters-reset").addEventListener("click", resetAll);
    $("empty-reset").addEventListener("click", resetAll);
    $("load-more").addEventListener("click", () => { state.page += 1; render({ keepPage: true }); });

    /* ---------- Tiroir de filtres (mobile) ---------- */
    const drawer = $("filters");
    const backdrop = $("filters-backdrop");
    const mobileMQ = window.matchMedia("(max-width: 959px)");
    let lastFocus = null;

    function openFilters() {
        lastFocus = document.activeElement;
        drawer.classList.add("is-open"); backdrop.classList.add("is-open");
        drawer.setAttribute("aria-hidden", "false");
        document.body.style.overflow = "hidden";
        const first = drawer.querySelector("input, button");
        if (first) first.focus();
    }
    function closeFilters() {
        drawer.classList.remove("is-open"); backdrop.classList.remove("is-open");
        drawer.setAttribute("aria-hidden", String(mobileMQ.matches));
        document.body.style.overflow = "";
        if (lastFocus && mobileMQ.matches) lastFocus.focus();
    }
    document.querySelectorAll('[data-action="open-filters"]').forEach((b) => b.addEventListener("click", openFilters));
    document.querySelectorAll('[data-action="close-filters"]').forEach((b) => b.addEventListener("click", closeFilters));
    backdrop.addEventListener("click", closeFilters);
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && drawer.classList.contains("is-open")) closeFilters(); });
    mobileMQ.addEventListener("change", () => { drawer.setAttribute("aria-hidden", String(mobileMQ.matches)); if (!mobileMQ.matches) closeFilters(); });
    drawer.setAttribute("aria-hidden", String(mobileMQ.matches));

    /* ---------- Barre panier collante (mobile) ---------- */
    const bar = $("cart-bar");
    const FREE_SHIPPING = typeof FREE_SHIPPING_THRESHOLD === "number" ? FREE_SHIPPING_THRESHOLD : 80;

    function updateCartBar() {
        const cart = getCart();
        const count = cart.reduce((s, i) => s + i.qty, 0);
        const total = cart.reduce((s, i) => s + i.price * i.qty, 0);
        bar.hidden = count === 0;
        document.body.classList.toggle("has-cart-bar", count > 0);
        if (count === 0) return;
        $("cart-bar-count").textContent = String(count);
        $("cart-bar-label").textContent = t().item(count);
        $("cart-bar-total").textContent = formatPrice(total);
        $("cart-bar-ship").textContent = total >= FREE_SHIPPING ? t().shipOk : t().shipLeft(formatPrice(FREE_SHIPPING - total));
    }
    bar.querySelector("button").addEventListener("click", openCart);
    document.addEventListener("cart:updated", updateCartBar);

    /* ---------- Traductions de la page ---------- */
    function applyShopLang() {
        lang = document.documentElement.lang === "en" ? "en" : "fr";
        document.querySelectorAll("[data-shop-i18n]").forEach((node) => {
            const v = t()[node.dataset.shopI18n];
            if (typeof v === "string") node.textContent = v;
        });
        buildSortOptions();
        render({ keepPage: true });
        updateCartBar();
    }
    document.addEventListener("languagechange", applyShopLang);

    /* ---------- Initialisation : squelettes puis produits ---------- */
    function showSkeletons() {
        grid.replaceChildren(...Array.from({ length: 4 }, () => {
            const s = el("div");
            s.append(el("div", "skel skel--img"), el("div", "skel skel--line"), el("div", "skel skel--line s"));
            return s;
        }));
    }

    readUrl();
    buildColorFilters();
    buildSortOptions();
    syncInputs();
    showSkeletons();
    window.requestAnimationFrame(() => { applyShopLang(); });

})();