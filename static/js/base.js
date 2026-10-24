"use strict";

/* base.js — scripts partagés par toutes les pages : helpers, header, recherche, panier, langue. */

/* ==========================================================================
   Helpers
   ========================================================================== */

/**
 * Lecture sécurisée du localStorage : toute donnée corrompue ou modifiée
 * manuellement par l'utilisateur est ignorée plutôt que de casser la page.
 */
function readStorage(key, fallback) {
    try {
        const raw = window.localStorage.getItem(key);
        if (!raw) {
            return fallback;
        }
        const parsed = JSON.parse(raw);
        return parsed ?? fallback;
    } catch (error) {
        return fallback;
    }
}

function writeStorage(key, value) {
    try {
        window.localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
        /* Stockage plein ou indisponible (navigation privée) : on ignore. */
    }
}

function formatPrice(amount) {
    return `${amount.toFixed(2).replace(".", ",")} €`;
}

function prefersReducedMotion() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

const isTouchDevice = window.matchMedia("(hover: none), (pointer: coarse)").matches;
const isFinePointer = window.matchMedia("(hover: hover) and (pointer: fine)").matches;


/* ==========================================================================
   Sticky header
   ========================================================================== */

const siteHeader = document.querySelector(".site-header");

function updateHeaderState() {
    if (!siteHeader) return;
    siteHeader.classList.toggle("is-scrolled", window.scrollY > 8);
}

updateHeaderState();
window.addEventListener("scroll", updateHeaderState, { passive: true });


/* ==========================================================================
   Mobile navigation
   ========================================================================== */

const menuToggle = document.querySelector(".menu-toggle");
const mainNavigation = document.querySelector("#main-navigation");

if (menuToggle && mainNavigation) {

    menuToggle.addEventListener("click", () => {
        const isOpen = mainNavigation.classList.toggle("is-open");
        menuToggle.setAttribute("aria-expanded", String(isOpen));
    });

    mainNavigation.querySelectorAll("a").forEach((link) => {
        link.addEventListener("click", () => {
            mainNavigation.classList.remove("is-open");
            menuToggle.setAttribute("aria-expanded", "false");
        });
    });
}


/* ==========================================================================
   Search overlay (UI uniquement, pas de recherche pour le moment)
   ========================================================================== */

const searchTrigger = document.querySelector('[data-action="open-search"]');
const searchOverlay = document.querySelector("#search-overlay");
const searchClose = document.querySelector('[data-action="close-search"]');
const searchInput = document.querySelector("#search-input");

function openSearch() {
    if (!searchOverlay) return;
    searchOverlay.classList.add("is-open");
    searchOverlay.setAttribute("aria-hidden", "false");
    window.requestAnimationFrame(() => searchInput && searchInput.focus());
}

function closeSearch() {
    if (!searchOverlay) return;
    searchOverlay.classList.remove("is-open");
    searchOverlay.setAttribute("aria-hidden", "true");
}

if (searchTrigger) searchTrigger.addEventListener("click", openSearch);
if (searchClose) searchClose.addEventListener("click", closeSearch);
if (searchOverlay) {
    searchOverlay.addEventListener("click", (event) => {
        if (event.target === searchOverlay) closeSearch();
    });
}

const searchForm = document.querySelector("#search-form");
const searchSuggestions = document.querySelector("#search-suggestions");
let searchDebounce = 0, searchAbortController = null;
function renderSearchSuggestions(results, query) {
    if (!searchSuggestions) return;
    searchSuggestions.replaceChildren();
    if (!query || query.length < 2 || !results.length) {
        const p = document.createElement("p"); p.className = "search-suggestions__hint";
        p.textContent = query.length < 2 ? "Saisissez au moins deux caractères pour découvrir les produits." : "Aucun produit trouvé. Essayez un autre terme.";
        searchSuggestions.appendChild(p); return;
    }
    const list = document.createElement("ul"); list.className = "search-suggestions__list";
    results.forEach((item) => {
        if (typeof item.url !== "string" || !item.url.startsWith("/produit/")) return;
        const li = document.createElement("li"), link = document.createElement("a");
        link.className = "search-suggestion"; link.href = item.url;
        if (item.image) { const img = document.createElement("img"); img.src = item.image; img.alt = ""; img.loading = "lazy"; link.appendChild(img); }
        const details = document.createElement("span"); details.className = "search-suggestion__details";
        const name = document.createElement("strong"); name.textContent = item.name;
        const category = document.createElement("small"); category.textContent = item.category;
        details.append(name, category);
        const price = document.createElement("span"); price.className = "search-suggestion__price"; price.textContent = formatPrice(Number(item.price));
        link.append(details, price); li.appendChild(link); list.appendChild(li);
    });
    searchSuggestions.appendChild(list);
}
if (searchSuggestions) {
    const p = document.createElement("p"); p.className = "search-suggestions__hint";
    p.textContent = "Recherchez par nom, type de produit, matière ou catégorie."; searchSuggestions.appendChild(p);
}
if (searchForm && searchInput) {
    searchForm.addEventListener("submit", (event) => {
        event.preventDefault();
        const query = searchInput.value.trim().replace(/\s+/g, " ").slice(0, 100);
        if (query.length < 2) { renderSearchSuggestions([], query); searchInput.focus(); return; }
        const target = new URL(searchForm.action, window.location.origin);
        target.searchParams.set("q", query); window.location.assign(target.toString());
    });
    searchInput.addEventListener("input", () => {
        window.clearTimeout(searchDebounce); if (searchAbortController) searchAbortController.abort();
        const query = searchInput.value.trim().replace(/\s+/g, " ").slice(0, 100);
        if (query.length < 2) { renderSearchSuggestions([], query); return; }
        searchDebounce = window.setTimeout(async () => {
            try {
                searchAbortController = new AbortController();
                const url = new URL(searchForm.dataset.suggestUrl, window.location.origin); url.searchParams.set("q", query);
                const response = await fetch(url, { headers: { "Accept": "application/json" }, credentials: "same-origin", signal: searchAbortController.signal });
                if (!response.ok) throw new Error("Recherche indisponible");
                const data = await response.json();
                if (searchInput.value.trim().replace(/\s+/g, " ").slice(0, 100) === query) renderSearchSuggestions(data.results || [], query);
            } catch (error) { if (error.name !== "AbortError") renderSearchSuggestions([], query); }
        }, 220);
    });
}

/* Panier invité : session Django, prix et disponibilité recalculés côté serveur. */

const cartDrawer = document.querySelector("#cart-drawer");
if (cartDrawer) cartDrawer.inert = true;
const cartBackdrop = document.querySelector("#cart-backdrop");
const cartClose = document.querySelector('[data-action="close-cart"]');
const cartItemsContainer = document.querySelector("#cart-items");
const cartDrawerBody = document.querySelector("#cart-body");
const cartEmptyState = document.querySelector("#cart-empty");
const cartFooter = document.querySelector("#cart-footer");
const cartSubtotalEl = document.querySelector("#cart-subtotal");
const cartCountBadges = document.querySelectorAll(".cart-count");
const cartActionButtons = document.querySelectorAll('[data-action="open-cart"]');
const cartStatus = document.querySelector("#cart-status");
const cartTitleCount = document.querySelector("#cart-title-count");
const shippingProgress = document.querySelector(".shipping-progress");
const cartClearButton = document.querySelector("#cart-clear");
const shippingFill = document.querySelector("#shipping-fill");
const shippingText = document.querySelector("#shipping-text");
const cartApiUrl = cartDrawer?.dataset.cartUrl || "/boutique/panier/";
const cartMutationUrl = cartDrawer?.dataset.cartMutationUrl || "/boutique/panier/modifier/";
const FREE_SHIPPING_THRESHOLD = 80;
let cartSnapshot = { items: [], count: 0, subtotal: "0.00" };
let cartMutationQueue = Promise.resolve();
let cartReady = Promise.resolve();
function csrfToken() { const m = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/); return m ? decodeURIComponent(m[1]) : ""; }
function showCartStatus(message, isError = false) {
    if (!cartStatus) return; cartStatus.textContent = message || "";
    cartStatus.classList.toggle("is-error", Boolean(isError)); cartStatus.hidden = !message;
}
function cartKeyParts(key) { const p = String(key).split(":"); return { variant_id: Number(p[0]), offer_id: Number(p[1] || 0) }; }
async function cartRequest(url, method = "GET", payload = null) {
    const opts = { method, credentials: "same-origin", headers: { "Accept": "application/json" } };
    if (payload) { opts.headers["Content-Type"] = "application/json"; opts.headers["X-CSRFToken"] = csrfToken(); opts.body = JSON.stringify(payload); }
    const response = await fetch(url, opts), result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.error || "Le panier n'a pas pu être mis à jour."); return result;
}
function getCart() { return Array.isArray(cartSnapshot.items) ? cartSnapshot.items : []; }
function renderCartBadge() {
    const count = Number(cartSnapshot.count ?? getCart().reduce((n, i) => n + Number(i.quantity || 0), 0));
    cartCountBadges.forEach((b) => { b.textContent = String(count); b.hidden = count === 0; });
    if (cartTitleCount) {
        cartTitleCount.textContent = count ? `(${count})` : "";
        cartTitleCount.hidden = count === 0;
    }
}
function buildCartItemNode(item) {
    const row = document.createElement("li"); row.className = "cart-item"; row.dataset.id = item.key;
    const img = document.createElement("img");
    img.className = "cart-item__image";
    img.alt = "";
    img.loading = "lazy";
    img.decoding = "async";
    if (item.image) {
        img.src = item.image;
    } else {
        img.hidden = true;
    }

    const details = document.createElement("div");
    details.className = "cart-item__details";
    const name = document.createElement("h3");
    const productLink = document.createElement("a");
    productLink.className = "cart-item__product-link";
    productLink.textContent = item.name;
    if (typeof item.product_slug === "string" && item.product_slug) {
        productLink.href = `/produit/${encodeURIComponent(item.product_slug)}/`;
    } else {
        productLink.href = "#";
        productLink.setAttribute("aria-disabled", "true");
    }
    name.className = "cart-item__name";
    name.appendChild(productLink);
    const price = document.createElement("p");
    price.className = "cart-item__price";
    price.textContent = `${formatPrice(Number(item.unit_price))} / ${item.offer_id ? "offre" : "article"}`;
    const qtyWrap = document.createElement("div"); qtyWrap.className = "cart-item__qty";
    const minus = document.createElement("button"); minus.type = "button"; minus.textContent = "−"; minus.setAttribute("aria-label", "Diminuer la quantité"); minus.addEventListener("click", async () => { minus.disabled = true; await updateQuantity(item.key, item.quantity - 1); if (minus.isConnected) minus.disabled = false; });
    const qty = document.createElement("span"); qty.textContent = String(item.quantity);
    const plus = document.createElement("button"); plus.type = "button"; plus.textContent = "+"; plus.setAttribute("aria-label", "Augmenter la quantité"); plus.disabled = !item.available || item.quantity >= item.available_quantity; plus.addEventListener("click", async () => { plus.disabled = true; await updateQuantity(item.key, item.quantity + 1); if (plus.isConnected) plus.disabled = false; });
    qtyWrap.append(minus, qty, plus);
    const remove = document.createElement("button"); remove.type = "button"; remove.className = "cart-item__remove"; remove.textContent = "Retirer"; remove.addEventListener("click", async () => { remove.disabled = true; await removeFromCart(item.key); if (remove.isConnected) remove.disabled = false; });
    const actions = document.createElement("div");
    actions.className = "cart-item__actions";
    const total = document.createElement("p");
    total.className = "cart-item__total";
    total.textContent = formatPrice(Number(item.line_total));
    actions.appendChild(total);
    details.append(name, price);
    if (Array.isArray(item.components) && item.components.length) {
        const components = document.createElement("p");
        components.className = "cart-item__components";
        components.textContent = "Comprend : " + item.components.map((component) =>
            (component.quantity > 1 ? `${component.quantity} × ` : "")
            + component.name
            + (component.variant_name ? ` — ${component.variant_name}` : "")
        ).join(" · ");
        details.appendChild(components);
    }
    details.append(qtyWrap, remove);
    row.append(img, details, actions);
    if (!item.available) { const warning = document.createElement("p"); warning.className = "cart-item__warning"; warning.textContent = item.available_quantity > 0 ? "Stock insuffisant : réduisez la quantité." : "Indisponible : retirez cet article pour continuer."; details.appendChild(warning); }
    return row;
}
function updateShippingProgress() {
    if (!shippingFill || !shippingText) return;
    const subtotal = Number(cartSnapshot.subtotal || 0);
    const threshold = Number(cartSnapshot.free_shipping_threshold || FREE_SHIPPING_THRESHOLD);
    const progress = threshold > 0 ? Math.min(subtotal / threshold, 1) * 100 : 0;
    shippingFill.style.width = progress + "%";
    shippingFill.setAttribute("aria-valuemax", String(threshold));
    shippingFill.setAttribute("aria-valuenow", String(Math.min(subtotal, threshold)));
    shippingText.textContent = threshold > 0 && subtotal >= threshold
        ? "✦ Livraison offerte débloquée !"
        : "Plus que " + formatPrice(Math.max(threshold - subtotal, 0)) + " pour la livraison offerte";
}
function renderCartDrawer() {
    if (!cartItemsContainer) return;
    cartItemsContainer.replaceChildren();
    const items = getCart();
    const isEmpty = items.length === 0;

    if (cartEmptyState) cartEmptyState.hidden = !isEmpty;
    if (cartFooter) cartFooter.hidden = isEmpty;
    if (cartDrawerBody) cartDrawerBody.hidden = isEmpty;
    if (shippingProgress) shippingProgress.hidden = isEmpty;

    if (isEmpty) {
        if (cartSubtotalEl) cartSubtotalEl.textContent = formatPrice(0);
        return;
    }

    items.forEach((item) => cartItemsContainer.appendChild(buildCartItemNode(item)));
    if (cartSubtotalEl) cartSubtotalEl.textContent = formatPrice(Number(cartSnapshot.subtotal || 0));
}
function applyCartPayload(payload) {
    if (payload && Array.isArray(payload.items)) cartSnapshot = payload;
    renderCartBadge(); renderCartDrawer(); updateShippingProgress(); document.dispatchEvent(new CustomEvent("cart:updated"));
}
async function refreshCartUI() { try { applyCartPayload(await cartRequest(cartApiUrl)); } catch (e) { showCartStatus(e.message || "Le panier est momentanément indisponible.", true); } }
function mutateCart(payload) {
    /* Sérialise les mutations pour éviter les pertes d'état lors de clics rapprochés. */
    const operation = cartMutationQueue.then(async () => {
        await cartReady;
        showCartStatus("");
        const result = await cartRequest(cartMutationUrl, "POST", payload);
        applyCartPayload(result);
        return result;
    });
    cartMutationQueue = operation.catch(() => null);
    return operation.catch((error) => {
        showCartStatus(error.message || "Le panier n'a pas pu être mis à jour.", true);
        throw error;
    });
}
async function addToCart(product) {
    try {
        const result = await mutateCart({ action: "add", variant_id: Number(product.variantId), offer_id: Number(product.offerId || 0), quantity: 1 });
        if (result) { bumpCartIcon(); openCart(); } return Boolean(result);
    } catch (e) { openCart(); return false; }
}
function playAddedFeedback(button) {
    if (!button) return; const label = button.textContent; button.classList.add("button--added"); button.textContent = "Ajouté ✓"; button.disabled = true;
    window.setTimeout(() => { button.classList.remove("button--added"); button.disabled = false; button.textContent = label; }, 1200);
}

const offerPicker = document.querySelector("#offer-picker");
const offerPickerForm = document.querySelector("#offer-picker-form");
const offerPickerOptions = document.querySelector("#offer-picker-options");
const offerPickerProduct = document.querySelector("#offer-picker-product");
const offerPickerStatus = document.querySelector("#offer-picker-status");
const offerPickerClose = document.querySelector('[data-action="close-offer-picker"]');
let resolveOfferPicker = null;
let offerPickerCancelHandler = null;

function finishOfferPicker(value) {
    if (offerPicker && offerPickerCancelHandler) {
        offerPicker.removeEventListener("cancel", offerPickerCancelHandler);
        offerPickerCancelHandler = null;
    }
    if (offerPicker && offerPicker.open) offerPicker.close();
    const resolve = resolveOfferPicker;
    resolveOfferPicker = null;
    if (resolve) resolve(value);
}

function chooseProductOffer(product, offers) {
    if (!offerPicker || !offerPickerForm || !offerPickerOptions || !offers.length) return Promise.resolve(null);
    offerPickerOptions.replaceChildren();
    if (offerPickerProduct) offerPickerProduct.textContent = product.name
        ? `Choisissez la formule qui vous convient pour ${product.name}.`
        : "Choisissez la formule qui vous convient.";
    if (offerPickerStatus) { offerPickerStatus.hidden = true; offerPickerStatus.textContent = ""; }

    offers.forEach((offer, index) => {
        const label = document.createElement("label");
        label.className = "offer-picker__option" + (offer.featured ? " is-featured" : "");
        const radio = document.createElement("input");
        radio.type = "radio";
        radio.name = "selected-offer";
        radio.value = String(offer.id);
        radio.checked = Boolean(offer.featured) || (!offers.some((item) => item.featured) && index === 0);
        const content = document.createElement("span");
        content.className = "offer-picker__option-content";
        const top = document.createElement("span");
        top.className = "offer-picker__option-top";
        const title = document.createElement("strong");
        title.className = "offer-picker__option-title";
        title.textContent = offer.title;
        const price = document.createElement("strong");
        price.className = "offer-picker__option-price";
        price.textContent = formatPrice(Number(offer.price));
        top.append(title, price);
        content.appendChild(top);

        if (offer.badge) {
            const badge = document.createElement("span");
            badge.className = "offer-picker__badge";
            badge.textContent = offer.badge;
            content.appendChild(badge);
        }

        const included = document.createElement("span");
        included.className = "offer-picker__included";
        const parts = (offer.components || []).map((item) =>
            item.quantity > 1 ? `${item.name} × ${item.quantity}` : item.name
        );
        included.textContent = parts.join(" · ");
        content.appendChild(included);

        const saving = Number(offer.saving || 0);
        if (saving > 0) {
            const savingLabel = document.createElement("span");
            savingLabel.className = "offer-picker__saving";
            savingLabel.textContent = `Vous économisez ${formatPrice(saving)} par rapport aux prix séparés`;
            content.appendChild(savingLabel);
        }
        label.append(radio, content);
        offerPickerOptions.appendChild(label);
    });

    return new Promise((resolve) => {
        resolveOfferPicker = resolve;
        offerPickerCancelHandler = (event) => {
            event.preventDefault();
            finishOfferPicker(null);
        };
        offerPicker.addEventListener("cancel", offerPickerCancelHandler);
        offerPicker.showModal();
        const selected = offerPicker.querySelector('input[name="selected-offer"]:checked');
        if (selected) selected.focus({ preventScroll: true });
    });
}

if (offerPickerForm) {
    offerPickerForm.addEventListener("submit", (event) => {
        event.preventDefault();
        const selected = offerPickerForm.querySelector('input[name="selected-offer"]:checked');
        if (!selected) {
            if (offerPickerStatus) {
                offerPickerStatus.textContent = "Sélectionnez une offre pour continuer.";
                offerPickerStatus.hidden = false;
            }
            return;
        }
        finishOfferPicker(Number(selected.value));
    });
}
if (offerPickerClose) offerPickerClose.addEventListener("click", () => finishOfferPicker(null));
if (offerPicker) offerPicker.addEventListener("click", (event) => {
    if (event.target === offerPicker) finishOfferPicker(null);
});

async function addProductFromCard(button) {
    if (offerPicker && (offerPicker.open || resolveOfferPicker)) return false;
    const card = button && button.closest("[data-product-slug]");
    if (!card) {
        showCartStatus("Impossible d'identifier ce produit. Ouvrez sa fiche pour réessayer.", true);
        return false;
    }
    const variantId = Number(card.dataset.variantId);
    const slug = card.dataset.productSlug;
    const offersUrl = card.dataset.offersUrl;
    if (!Number.isSafeInteger(variantId) || variantId < 1 || !slug || !offersUrl) {
        showCartStatus("Les offres de ce produit ne sont pas disponibles pour le moment.", true);
        return false;
    }

    try {
        const url = new URL(offersUrl, window.location.origin);
        url.searchParams.set("variant_id", String(variantId));
        const response = await fetch(url.toString(), {
            method: "GET",
            credentials: "same-origin",
            headers: { "Accept": "application/json" },
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(payload.error || "Impossible de charger les offres de ce produit.");
        if (!Array.isArray(payload.offers) || payload.offers.length === 0) {
            throw new Error("Aucune offre n'est disponible pour cette variante.");
        }

        let offerId;
        if (payload.offers.length === 1) {
            offerId = Number(payload.offers[0].id);
        } else {
            offerId = await chooseProductOffer(payload.product || {}, payload.offers);
            if (!offerId) return false;
        }
        lastCartTrigger = button;
        return await addToCart({ variantId, offerId });
    } catch (error) {
        showCartStatus(error.message || "L'ajout au panier a échoué.", true);
        openCart();
        return false;
    }
}

async function updateQuantity(key, quantity) {
    const parts = cartKeyParts(key); if (!Number.isInteger(parts.variant_id) || !Number.isInteger(parts.offer_id)) return;
    if (quantity <= 0) return removeFromCart(key);
    try { await mutateCart({ action: "update", ...parts, quantity }); } catch (e) {}
}
async function removeFromCart(key) { try { await mutateCart({ action: "remove", ...cartKeyParts(key) }); } catch (e) {} }
if (cartDrawer) {
    cartDrawer.addEventListener("keydown", (event) => {
        if (event.key !== "Tab") return;
        const focusable = [...cartDrawer.querySelectorAll('a[href], button:not(:disabled), [tabindex]:not([tabindex="-1"])')]
            .filter((element) => !element.hidden && !element.closest("[hidden]"));
        if (!focusable.length) return;
        const first = focusable[0], last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) {
            event.preventDefault(); last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault(); first.focus();
        }
    });
}

let lastCartTrigger = null;
function openCart() {
    if (!cartDrawer) return;
    const active = document.activeElement;
    if (active instanceof HTMLElement && active.matches('[data-action="open-cart"], .js-add')) lastCartTrigger = active;
    cartDrawer.inert = false;
    cartDrawer.classList.add("is-open");
    if (cartBackdrop) cartBackdrop.classList.add("is-open");
    cartDrawer.setAttribute("aria-hidden", "false");
    document.body.classList.add("cart-open");
    window.requestAnimationFrame(() => cartClose && cartClose.focus());
}
function closeCart() {
    if (!cartDrawer) return;
    cartDrawer.classList.remove("is-open");
    if (cartBackdrop) cartBackdrop.classList.remove("is-open");
    cartDrawer.setAttribute("aria-hidden", "true");
    cartDrawer.inert = true;
    document.body.classList.remove("cart-open");
    if (lastCartTrigger && lastCartTrigger.isConnected) lastCartTrigger.focus();
}
function bumpCartIcon() { cartActionButtons.forEach((b) => { b.classList.remove("is-bumping"); void b.offsetWidth; b.classList.add("is-bumping"); }); }
cartActionButtons.forEach((button) => button.addEventListener("click", openCart));
if (cartClose) cartClose.addEventListener("click", closeCart);
if (cartBackdrop) cartBackdrop.addEventListener("click", closeCart);
if (cartClearButton) cartClearButton.addEventListener("click", async () => { try { await mutateCart({ action: "clear" }); showCartStatus("Le panier a été vidé."); } catch (e) {} });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") { closeCart(); closeSearch(); } });
document.querySelectorAll('[data-action="add-to-cart"], [data-action="quick-add"]').forEach((button) => {
    button.addEventListener("click", async (event) => {
        event.preventDefault();
        event.stopPropagation();
        if (button.disabled) return;
        button.disabled = true;
        const added = await addProductFromCard(button);
        if (added) playAddedFeedback(button);
        else if (button.isConnected) button.disabled = false;
    });
});
cartReady = refreshCartUI();


const LANG_KEY = "site_lang";

const translations = {
    fr: {
        nav_new: "Nouveautés",
        nav_bags: "Sacs",
        nav_accessories: "Accessoires",
        nav_collections: "Collections",
        nav_about: "À propos",
        search_placeholder: "Rechercher un sac, un accessoire…",
        search_hint: "Recherchez par nom, type de produit, matière ou catégorie.",
        cart_title: "Votre panier",
        cart_empty_title: "Votre panier est vide",
        cart_empty_text: "Parcourez nos collections pour trouver votre prochain sac.",
        cart_subtotal: "Sous-total",
        cart_checkout: "Commander",
        hero_eyebrow: "Nouvelle collection",
        hero_title: "L'élégance\ns'accessoirise.",
        hero_desc: "Des sacs et accessoires façonnés pour accompagner chaque femme, avec exigence et raffinement.",
        hero_cta_primary: "Découvrir la collection",
        hero_cta_secondary: "Voir les sacs",
        trust_ship: "Livraison offerte dès 80€",
        trust_return: "Retours gratuits sous 30 jours",
        trust_secure: "Paiement 100% sécurisé",
        trust_support: "Service client 7j/7",
        categories_eyebrow: "Explorer",
        categories_title: "Nos catégories",
        categories_desc: "Une sélection pensée pour chaque usage, du quotidien aux grandes occasions.",
        cat_handbags: "Sacs à main",
        cat_shoulder: "Sacs bandoulière",
        cat_wallets: "Portefeuilles",
        cat_accessories: "Accessoires",
        discover: "Découvrir →",
        new_eyebrow: "À découvrir",
        new_title: "Nos nouveautés",
        view_all: "Voir tout →",
        badge_new: "Nouveau",
        badge_sale: "Promo",
        add_to_cart: "Ajouter au panier",
        promo_1: "Livraison gratuite dès 80€ d'achat",
        promo_2: "— 15% sur votre première commande avec le code BIENVENUE",
        promo_3: "Nouvelle collection disponible dès maintenant",
        banner_eyebrow: "Savoir-faire",
        banner_title: "Des pièces choisies\navec exigence.",
        banner_desc: "Cuirs sélectionnés, finitions soignées : chaque sac est pensé pour durer et s'accorder avec votre quotidien.",
        banner_cta: "En savoir plus",
        recent_eyebrow: "Votre historique",
        recent_title: "Vus récemment",
        testimonials_eyebrow: "Avis clients",
        testimonials_title: "Elles nous font confiance",
        instagram_eyebrow: "Communauté",
        instagram_title: "Suivez-nous @maboutique",
        newsletter_eyebrow: "Newsletter",
        newsletter_title: "Restez informée",
        newsletter_desc: "Inscrivez-vous pour recevoir nos nouveautés, nos offres exclusives et nos conseils styling.",
        newsletter_placeholder: "Votre adresse email",
        newsletter_button: "S'inscrire",
        newsletter_note: "En vous inscrivant, vous acceptez de recevoir nos communications par email.",
        footer_tagline: "Sacs et accessoires pensés pour l'élégance au quotidien.",
        footer_shop: "Boutique",
        footer_info: "Informations",
        footer_legal: "Légal",
        footer_shipping: "Livraison",
        footer_returns: "Retours",
        footer_contact: "Contact",
        footer_faq: "FAQ",
        footer_legal_mentions: "Mentions légales",
        footer_privacy: "Politique de confidentialité",
        footer_terms: "CGV",
        lang_toggle: "EN",
        flash_sale_text: "⚡ Vente flash : -20% sur une sélection de sacs",
        flash_sale_cta: "J'en profite",
        welcome_title: "Bienvenue chez nous !",
        welcome_desc: "Profitez de -10% sur votre première commande avec le code ci-dessous.",
        welcome_cta: "Découvrir la collection",
        welcome_copy: "Copier le code",
        social_proof_stock: "produit(s) restant(s)",
        social_proof_watching: "regardent ce produit",
        perk_ship: "Livraison offerte dès 80 €",
        perk_ret: "Retours gratuits 30 jours",
        perk_pay: "Paiement sécurisé",
        perk_help: "Service client 7j/7",
        footer_news_title: "-10 % sur votre première commande",
        footer_news_desc: "Rejoignez la newsletter : nouveautés, offres privées et conseils style.",
        footer_news_ok: "Merci ! Votre code : BIENVENUE10",
        footer_news_err: "Saisissez une adresse e-mail valide.",
        footer_sale: "Promotions",
        footer_help: "Aide",
        footer_track: "Suivre ma commande",
        footer_rights: "Tous droits réservés.",
    },
    en: {
        nav_new: "New in",
        nav_bags: "Bags",
        nav_accessories: "Accessories",
        nav_collections: "Collections",
        nav_about: "About",
        search_placeholder: "Search for a bag, an accessory…",
        search_hint: "Search by product name, type, material or category.",
        cart_title: "Your cart",
        cart_empty_title: "Your cart is empty",
        cart_empty_text: "Browse our collections to find your next bag.",
        cart_subtotal: "Subtotal",
        cart_checkout: "Checkout",
        hero_eyebrow: "New collection",
        hero_title: "Elegance,\naccessorised.",
        hero_desc: "Bags and accessories crafted to accompany every woman, with care and refinement.",
        hero_cta_primary: "Discover the collection",
        hero_cta_secondary: "Shop bags",
        trust_ship: "Free shipping over €80",
        trust_return: "Free returns within 30 days",
        trust_secure: "100% secure payment",
        trust_support: "Customer support 7/7",
        categories_eyebrow: "Explore",
        categories_title: "Our categories",
        categories_desc: "A selection designed for every occasion, from everyday to evening.",
        cat_handbags: "Handbags",
        cat_shoulder: "Shoulder bags",
        cat_wallets: "Wallets",
        cat_accessories: "Accessories",
        discover: "Discover →",
        new_eyebrow: "Just in",
        new_title: "New arrivals",
        view_all: "View all →",
        badge_new: "New",
        badge_sale: "Sale",
        add_to_cart: "Add to cart",
        promo_1: "Free shipping on orders over €80",
        promo_2: "15% off your first order with code WELCOME",
        promo_3: "New collection available now",
        banner_eyebrow: "Craftsmanship",
        banner_title: "Pieces chosen\nwith care.",
        banner_desc: "Selected leathers, careful finishes: every bag is designed to last and to fit seamlessly into your everyday life.",
        banner_cta: "Learn more",
        recent_eyebrow: "Your history",
        recent_title: "Recently viewed",
        testimonials_eyebrow: "Reviews",
        testimonials_title: "Loved by our customers",
        instagram_eyebrow: "Community",
        instagram_title: "Follow us @maboutique",
        newsletter_eyebrow: "Newsletter",
        newsletter_title: "Stay in the loop",
        newsletter_desc: "Sign up to receive new arrivals, exclusive offers and styling tips.",
        newsletter_placeholder: "Your email address",
        newsletter_button: "Subscribe",
        newsletter_note: "By signing up, you agree to receive our email communications.",
        footer_tagline: "Bags and accessories designed for everyday elegance.",
        footer_shop: "Shop",
        footer_info: "Information",
        footer_legal: "Legal",
        footer_shipping: "Shipping",
        footer_returns: "Returns",
        footer_contact: "Contact",
        footer_faq: "FAQ",
        footer_legal_mentions: "Legal notice",
        footer_privacy: "Privacy policy",
        footer_terms: "Terms of sale",
        lang_toggle: "FR",
        flash_sale_text: "⚡ Flash sale: -20% on selected bags",
        flash_sale_cta: "Shop the offer",
        welcome_title: "Welcome!",
        welcome_desc: "Enjoy -10% off your first order with the code below.",
        welcome_cta: "Discover the collection",
        welcome_copy: "Copy code",
        social_proof_stock: "left in stock",
        social_proof_watching: "watching this item",
        perk_ship: "Free shipping over €80",
        perk_ret: "Free returns, 30 days",
        perk_pay: "Secure payment",
        perk_help: "Customer support 7/7",
        footer_news_title: "10% off your first order",
        footer_news_desc: "Join the newsletter: new arrivals, private offers and styling tips.",
        footer_news_ok: "Thank you! Your code: BIENVENUE10",
        footer_news_err: "Please enter a valid email address.",
        footer_sale: "Sale",
        footer_help: "Help",
        footer_track: "Track my order",
        footer_rights: "All rights reserved.",
    },
};

function renderProductSocialProof(dict) {
    document.querySelectorAll("[data-watchers]").forEach((node) => {
        const count = node.dataset.watchers;
        node.textContent = `👀 ${count} ${dict.social_proof_watching}`;
    });
}

function applyLanguage(lang) {
    const dict = translations[lang] || translations.fr;

    document.documentElement.lang = lang;
    document.documentElement.dataset.lang = lang;

    renderProductSocialProof(dict);

    document.querySelectorAll("[data-i18n]").forEach((node) => {
        const key = node.dataset.i18n;
        if (dict[key] === undefined) return;
        node.textContent = dict[key];
    });

    document.querySelectorAll("[data-i18n-html]").forEach((node) => {
        const key = node.dataset.i18nHtml;
        if (dict[key] === undefined) return;
        /* Contenu interne (sauts de ligne) toujours issu du dictionnaire local,
           jamais d'une entrée utilisateur : pas de risque d'injection. */
        node.innerHTML = dict[key].replace(/\n/g, "<br>");
    });

    document.querySelectorAll("[data-i18n-placeholder]").forEach((node) => {
        const key = node.dataset.i18nPlaceholder;
        if (dict[key] === undefined) return;
        node.setAttribute("placeholder", dict[key]);
    });

    const langLabel = document.querySelector("[data-lang-label]");
    if (langLabel) langLabel.textContent = dict.lang_toggle;
    /* Prévient les autres scripts (ex. catalogue) du changement de langue. */
    document.dispatchEvent(new CustomEvent("languagechange", { detail: { lang } }));
}

function detectDefaultLanguage() {
    const stored = readStorage(LANG_KEY, null);
    if (stored === "fr" || stored === "en") return stored;
    return navigator.language && navigator.language.toLowerCase().startsWith("en") ? "en" : "fr";
}

let currentLang = detectDefaultLanguage();
applyLanguage(currentLang);

const langSwitch = document.querySelector("#lang-switch");
if (langSwitch) {
    langSwitch.addEventListener("click", () => {
        currentLang = currentLang === "fr" ? "en" : "fr";
        writeStorage(LANG_KEY, currentLang);
        applyLanguage(currentLang);
    });
}


/* ==========================================================================
   Effet "ripple" au clic/tap sur les boutons (souris et tactile)
   ========================================================================== */

(function initButtonRipple() {
    if (prefersReducedMotion()) return;

    document.querySelectorAll(".button").forEach((button) => {
        button.addEventListener("pointerdown", (event) => {
            const rect = button.getBoundingClientRect();
            const ripple = document.createElement("span");

            ripple.className = "button__ripple";
            ripple.style.left = `${event.clientX - rect.left}px`;
            ripple.style.top = `${event.clientY - rect.top}px`;

            button.appendChild(ripple);
            ripple.addEventListener("animationend", () => ripple.remove());
        });
    });
})();


/* ==========================================================================
   Bouton retour en haut
   ========================================================================== */

(function initScrollTop() {
    const button = document.querySelector("#scroll-top");
    if (!button) return;

    function toggleVisibility() {
        button.classList.toggle("is-visible", window.scrollY > 600);
    }

    button.addEventListener("click", () => {
        window.scrollTo({ top: 0, behavior: prefersReducedMotion() ? "auto" : "smooth" });
    });

    toggleVisibility();
    window.addEventListener("scroll", toggleVisibility, { passive: true });
})();


/* ==========================================================================
   Footer — accordéons (mobile) et newsletter
   ========================================================================== */

(function initFooter() {
    /* Accordéons : repliés sur mobile, toujours ouverts sur desktop. */
    const columns = document.querySelectorAll("[data-footer-col]");
    const desktop = window.matchMedia("(min-width: 900px)");

    function syncColumns() {
        columns.forEach((col) => {
            if (desktop.matches) col.setAttribute("open", "");
            else col.removeAttribute("open");
        });
    }

    columns.forEach((col) => {
        col.querySelector("summary").addEventListener("click", (event) => {
            if (desktop.matches) event.preventDefault();
        });
    });

    syncColumns();
    desktop.addEventListener("change", syncColumns);

    /* Newsletter : validation côté client uniquement pour l'instant.
       L'enregistrement réel de l'e-mail sera branché sur une vue Django. */
    const form = document.querySelector("#footer-news-form");
    const message = document.querySelector("#footer-news-msg");
    if (!form || !message) return;

    form.addEventListener("submit", (event) => {
        event.preventDefault();
        const input = form.querySelector("input[type='email']");
        const dict = translations[currentLang] || translations.fr;
        const valid = input.value.trim() !== "" && input.checkValidity();

        message.classList.toggle("is-error", !valid);
        message.textContent = valid ? dict.footer_news_ok : dict.footer_news_err;
        if (valid) form.reset();
        else input.focus();
    });
})();