"use strict";

/* ==========================================================================
   Catalogue — dépend de base.js (readStorage, writeStorage, formatPrice,
   addToCart, getCart, openCart, playAddedFeedback).
   Les produits, catégories, variantes et couleurs sont chargés depuis Django.
   ========================================================================== */

(function initCatalog() {

    const grid = document.getElementById("product-grid");
    if (!grid) return;

    /* Données rendues par Django via json_script. */
    const catalogDataNode = document.getElementById("catalog-data");
    const commercial = JSON.parse(document.querySelector("#commercial-config").textContent);
    const catalogData = catalogDataNode ? JSON.parse(catalogDataNode.textContent) : { products: [], categories: [], colors: {} };
    const CATEGORIES = Array.isArray(catalogData.categories) ? catalogData.categories : [];
    const COLORS = Object.fromEntries(Object.entries(catalogData.colors || {}).map(([slug, details]) => [slug, details.hex]));
    const COLOR_NAMES = Object.fromEntries(Object.entries(catalogData.colors || {}).map(([slug, details]) => [slug, details.name || slug]));
    const categoryLabel = (slug) => CATEGORIES.find((category) => category.slug === slug)?.name || t()["cat_" + slug] || slug;
    const WISH_KEY = "wishlist_v1";

    /* ---------- Textes FR / EN ---------- */
    const T = {
        fr: {
            bc_home: "Accueil", bc_shop: "Boutique", title: "Notre boutique",
            subtitle: "",
            filters: "Filtres", f_category: "Catégorie", f_price: "Prix (€)", f_color: "Couleur", f_more: "Autres",
            f_sale: "En promotion", f_lowstock: "Stock ≤ 5", unavailable: "Indisponible", reset: "Réinitialiser", show: "Voir",
            sort_label: "Trier par", empty_title: "Aucun produit ne correspond",
            empty_text: "Essayez d'élargir vos critères ou de retirer un filtre.", load_more: "Voir plus de produits",
            cat_handbags: "Sacs à main", cat_shoulder: "Sacs bandoulière", cat_wallets: "Portefeuilles", cat_accessories: "Accessoires",
            all: "Tout voir", results: (n) => `${n} produit${n > 1 ? "s" : ""}`,
            shown: (a, b) => `${a} sur ${b} produits affichés`,
            sort: { pop: "Pertinence", new: "Nouveautés", best: "Meilleures notes", asc: "Prix croissant", desc: "Prix décroissant" },
            newTag: "Nouveau",
            add: (n) => `Ajouter ${n} au panier`, wish: "Ajouter aux favoris", reviews: "avis",
            clear: "Tout effacer", remove: "Retirer le filtre", sale: "Promo", lowstock: "Stock ≤ 5",
            ra_ship: "", ra_ret: "Retours et rétractation",
            ra_ret_s: "Consultez les modalités", ra_pay: "Paiement sécurisé", ra_pay_s: "Stripe Checkout",
            item: (n) => (n > 1 ? "articles" : "article"),
            shipInfo: "Livraison confirmée au checkout",
        },
        en: {
            bc_home: "Home", bc_shop: "Shop", title: "Our shop",
            subtitle: "",
            filters: "Filters", f_category: "Category", f_price: "Price (€)", f_color: "Colour", f_more: "More",
            f_sale: "On sale", f_lowstock: "Stock ≤ 5", unavailable: "Unavailable", reset: "Reset", show: "Show",
            sort_label: "Sort by", empty_title: "No products match",
            empty_text: "Try widening your criteria or removing a filter.", load_more: "Show more products",
            cat_handbags: "Handbags", cat_shoulder: "Shoulder bags", cat_wallets: "Wallets", cat_accessories: "Accessories",
            all: "All", results: (n) => `${n} product${n > 1 ? "s" : ""}`,
            shown: (a, b) => `${a} of ${b} products shown`,
            sort: { pop: "Featured", new: "New in", best: "Top rated", asc: "Price: low to high", desc: "Price: high to low" },
            newTag: "New",
            add: (n) => `Add ${n} to cart`, wish: "Add to wishlist", reviews: "reviews",
            clear: "Clear all", remove: "Remove filter", sale: "Sale", lowstock: "Stock ≤ 5",
            ra_ship: "", ra_ret: "Returns and withdrawal",
            ra_ret_s: "See the conditions", ra_pay: "Secure payment", ra_pay_s: "Stripe Checkout",
            item: (n) => (n > 1 ? "items" : "item"),
            shipInfo: "Delivery confirmed at checkout",
        },
    };
    T.fr.ra_ship = T.en.ra_ship = commercial.shipping_message;
    T.fr.subtitle = "Découvrez nos sacs et accessoires et consultez les caractéristiques de chaque produit.";
    T.en.subtitle = "Explore our bags and accessories. See each product page for its specifications.";
    let lang = document.documentElement.lang === "en" ? "en" : "fr";
    const t = () => T[lang];

    /* ---------- État (synchronisé avec l'URL pour un partage facile) ---------- */
    const CATS = CATEGORIES.map((category) => category.slug);
    const SORTS = ["pop", "new", "best", "asc", "desc"];

    const state = { cats: new Set(), colors: new Set(), min: null, max: null, sale: false, low: false, sort: "pop", page: 1 };

    function readUrl() {
        const p = new URLSearchParams(window.location.search);
        state.cats.clear(); state.colors.clear();
        p.getAll("cat").flatMap(v => v.split(",")).filter((c) => CATS.includes(c)).forEach((c) => state.cats.add(c));
        p.getAll("color").flatMap(v => v.split(",")).filter((c) => COLORS[c]).forEach((c) => state.colors.add(c));
        const num = (v) => { const n = parseFloat(v); return Number.isFinite(n) && n >= 0 && n <= 5000 ? n : null; };
        state.min = num(p.get("min"));
        state.max = num(p.get("max"));
        state.sale = p.get("sale") === "1";
        state.low = p.get("low") === "1";
        state.sort = SORTS.includes(p.get("sort")) ? p.get("sort") : "pop";
        state.page = Math.max(1, Number.parseInt(p.get("page"), 10) || 1);
    }

    function stateUrl() {
        const p = new URLSearchParams(window.location.search);
        ["cat", "color", "min", "max", "sale", "low", "sort", "page"].forEach(key => p.delete(key));
        const currentQuery = new URLSearchParams(window.location.search).get("q");
        if (currentQuery) p.set("q", currentQuery);
        if (state.cats.size) p.set("cat", [...state.cats].join(","));
        if (state.colors.size) p.set("color", [...state.colors].join(","));
        if (state.min !== null) p.set("min", state.min);
        if (state.max !== null) p.set("max", state.max);
        if (state.sale) p.set("sale", "1");
        if (state.low) p.set("low", "1");
        if (state.sort !== "pop") p.set("sort", state.sort);
        if (state.page > 1) p.set("page", state.page);
        const qs = p.toString();
        return window.location.pathname + (qs ? `?${qs}` : "") + window.location.hash;
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

    const PLUS = "M12 5v14M5 12h14";
    const CHECK = "M5 12.5l4.5 4.5L19 7.5";
    const CLOSE = "M6 6l12 12M6 18L18 6";

    const storedWishlist = readStorage(WISH_KEY, []);
    const wishlist = new Set(
        (Array.isArray(storedWishlist) ? storedWishlist : [])
            .filter((id) => typeof id === "string" && /^[a-z0-9-]{1,180}$/i.test(id))
    );

    function refreshWishlist() {
        const saved = readStorage(WISH_KEY, [...wishlist]);
        if (!Array.isArray(saved)) return;
        wishlist.clear(); saved.filter(id => typeof id === "string" && /^[a-z0-9-]{1,180}$/i.test(id)).forEach(id => wishlist.add(id));
        grid.querySelectorAll(".pcard").forEach(card => card.querySelector(".pcard__wish").setAttribute("aria-pressed", String(wishlist.has(card.dataset.productSlug))));
    }
    window.addEventListener("pageshow", refreshWishlist);
    window.addEventListener("storage", event => { if (!event.key || event.key === WISH_KEY) refreshWishlist(); });

    /* ---------- Carte produit ---------- */
    function bindCards() {
        grid.querySelectorAll(".pcard").forEach(card => {
            if (card.dataset.bound) return;
            card.dataset.bound = "true";
            const slug = card.dataset.productSlug;
            const wish = card.querySelector(".pcard__wish");
            wish.setAttribute("aria-pressed", String(wishlist.has(slug)));
            wish.addEventListener("click", () => {
                // Read the latest persisted selection, including changes in another tab.
                const saved = readStorage(WISH_KEY, [...wishlist]);
                if (Array.isArray(saved)) {
                    wishlist.clear(); saved.filter(id => typeof id === "string" && /^[a-z0-9-]{1,180}$/i.test(id)).forEach(id => wishlist.add(id));
                }
                const on = !wishlist.has(slug);
                on ? wishlist.add(slug) : wishlist.delete(slug);
                wish.setAttribute("aria-pressed", String(on));
                writeStorage(WISH_KEY, [...wishlist]);
            });
            const add = card.querySelector(".pcard__add");
            const unavailable = add.disabled;
            add.addEventListener("click", async () => {
                if (add.disabled) return;
                add.disabled = true;
                try {
                    const added = await addProductFromCard(add);
                    if (added) {
                        add.classList.add("is-added"); add.replaceChildren(svgIcon([CHECK]));
                        window.setTimeout(() => {
                            add.classList.remove("is-added"); add.replaceChildren(svgIcon([PLUS]));
                            add.disabled = unavailable;
                        }, 1200);
                    } else add.disabled = unavailable;
                } catch (_) { add.disabled = unavailable; }
            });
        });
    }

    /* ---------- Rendu ---------- */
    const $ = (id) => document.getElementById(id);
    const countEl = $("results-count");
    const emptyEl = $("empty-state");
    const moreWrap = $("more-wrap");

    function activeFilterCount() {
        return state.cats.size + state.colors.size + (state.min !== null || state.max !== null ? 1 : 0) + (state.sale ? 1 : 0) + (state.low ? 1 : 0);
    }

    let requestRevision = 0;
    let pendingRequest;
    function updateResults(total, visible, hasMore) {
        countEl.textContent = t().results(total);
        $("filters-count").textContent = String(total);
        emptyEl.hidden = total !== 0;
        moreWrap.hidden = !hasMore;
        $("more-progress").textContent = t().shown(visible, total);
        $("more-fill").style.width = `${total ? (visible / total) * 100 : 0}%`;
        $("load-more").value = String(state.page + 1);
        const n = activeFilterCount();
        const badge = $("filters-badge"); badge.hidden = n === 0; badge.textContent = String(n);
        renderPills(); renderChips();
    }
    async function render({ keepPage = false, history = true } = {}) {
        if (!keepPage) state.page = 1;
        const url = stateUrl();
        const revision = ++requestRevision;
        pendingRequest?.abort(); pendingRequest = new AbortController();
        grid.setAttribute("aria-busy", "true");
        $("load-more").disabled = true;
        try {
            const response = await fetch(url, {headers: {"X-Catalog-Update": "1"}, signal: pendingRequest.signal});
            if (!response.ok) throw new Error("catalog");
            const data = await response.json();
            if (revision !== requestRevision) return;
            if (typeof data.html !== "string" || !Number.isInteger(data.total)) throw new Error("catalog");
            const template = document.createElement("template");
            template.innerHTML = data.html; // Same-origin Django template; all product fields are escaped.
            grid.classList.remove("is-ready");
            grid.replaceChildren(template.content); bindCards();
            void grid.offsetWidth; grid.classList.add("is-ready");
            state.page = data.page;
            updateResults(data.total, data.visible, data.has_more);
            if (history && stateUrl() !== location.pathname + location.search + location.hash) {
                window.history.pushState(null, "", stateUrl());
            }
        } catch (error) {
            if (revision === requestRevision && error.name !== "AbortError") {
                // Standard GET fallback keeps the selected state and uses the same server cards.
                window.location.assign(url);
            }
        } finally {
            if (revision === requestRevision) {
                grid.setAttribute("aria-busy", "false"); $("load-more").disabled = false;
            }
        }
    }

    function renderPills() {
        const list = $("category-pills");
        const focused = list.contains(document.activeElement) ? document.activeElement.dataset.category : null;
        list.replaceChildren();
        const make = (label, value) => {
            const li = document.createElement("li");
            const b = el("button", "", label);
            b.type = "button";
            b.dataset.category = value || "";
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
        CATEGORIES.forEach((category) => make(category.name, category.slug));
        if (focused !== null) [...list.querySelectorAll("button")].find(b => b.dataset.category === focused)?.focus({preventScroll: true});
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
        state.cats.forEach((c) => box.appendChild(chip(categoryLabel(c), () => state.cats.delete(c))));
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

    function resetAll(event) {
        event?.preventDefault();
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
        btn.addEventListener("click", event => {
            event.preventDefault();
            const [min, max] = btn.dataset.price.split("-");
            state.min = min === "" ? null : Number(min);
            state.max = max === "" ? null : Number(max);
            syncInputs();
            render();
        });
    });

    $("filters-reset").addEventListener("click", resetAll);
    $("empty-reset").addEventListener("click", resetAll);
    $("load-more").addEventListener("click", event => { event.preventDefault(); state.page += 1; render({ keepPage: true }); });
    $("catalog-form").addEventListener("submit", event => { event.preventDefault(); });
    window.addEventListener("popstate", () => { readUrl(); syncInputs(); render({keepPage: true, history: false}); });

    /* ---------- Tiroir de filtres (mobile) ---------- */
    const drawer = $("filters");
    const backdrop = $("filters-backdrop");
    const mobileMQ = window.matchMedia("(max-width: 959px)");

    function openFilters() {
        if (!mobileMQ.matches || !ShopOverlays.open(drawer, {close: () => {
            drawer.classList.remove("is-open"); backdrop.classList.remove("is-open");
            document.querySelectorAll('[data-action="open-filters"]').forEach(b => b.setAttribute("aria-expanded", "false"));
        }})) return;
        drawer.classList.add("is-open"); backdrop.classList.add("is-open");
        drawer.setAttribute("aria-hidden", "false");
        document.querySelectorAll('[data-action="open-filters"]').forEach(b => b.setAttribute("aria-expanded", "true"));
        const first = drawer.querySelector("input, button");
        if (first) first.focus();
    }
    function closeFilters() {
        ShopOverlays.close(drawer);
        drawer.classList.remove("is-open"); backdrop.classList.remove("is-open");
        drawer.inert = mobileMQ.matches;
        drawer.setAttribute("aria-hidden", String(mobileMQ.matches));
    }
    document.querySelectorAll('[data-action="open-filters"]').forEach((b) => b.addEventListener("click", openFilters));
    document.querySelectorAll('[data-action="close-filters"]').forEach((b) => b.addEventListener("click", closeFilters));
    backdrop.addEventListener("click", closeFilters);

    mobileMQ.addEventListener("change", () => { drawer.setAttribute("aria-hidden", String(mobileMQ.matches)); closeFilters(); });
    drawer.setAttribute("aria-hidden", String(mobileMQ.matches));
    drawer.inert = mobileMQ.matches;
    function filterRole() { if (mobileMQ.matches) { drawer.setAttribute("role", "dialog"); drawer.setAttribute("aria-modal", "true"); drawer.setAttribute("aria-label", "Filtres"); } else { drawer.removeAttribute("role"); drawer.removeAttribute("aria-modal"); drawer.inert = false; } }
    mobileMQ.addEventListener("change", filterRole); filterRole();

    /* ---------- Barre panier collante (mobile) ---------- */
    const bar = $("cart-bar");

    function updateCartBar() {
        const cart = getCart();
        const count = cart.reduce((sum, item) => sum + Number(item.quantity || 0), 0);
        const total = cart.reduce((sum, item) => sum + Number(item.line_total || 0), 0);
        bar.hidden = count === 0;
        document.body.classList.toggle("has-cart-bar", count > 0);
        if (count === 0) return;
        $("cart-bar-count").textContent = String(count);
        $("cart-bar-label").textContent = t().item(count);
        $("cart-bar-total").textContent = formatPrice(total);
        $("cart-bar-ship").textContent = commercial.sales_ready
            ? t().shipInfo
            : commercial.sales_unavailable;
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
        updateCartBar();
    }
    document.addEventListener("languagechange", applyShopLang);

    /* Attach behavior to the existing server cards without replacing them. */
    readUrl();
    state.page = catalogData.page;
    buildSortOptions();
    syncInputs();
    bindCards();
    updateResults(catalogData.total, grid.children.length, !moreWrap.hidden);
    window.requestAnimationFrame(() => { grid.classList.add("is-ready"); applyShopLang(); });

})();
