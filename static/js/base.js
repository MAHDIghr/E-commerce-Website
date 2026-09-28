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
if (searchForm) {
    searchForm.addEventListener("submit", (event) => {
        /* La recherche n'est pas encore branchée côté serveur. */
        event.preventDefault();
    });
}


/* ==========================================================================
   Panier invité — persistant via localStorage (aucun compte requis)
   ========================================================================== */

const CART_KEY = "shop_cart_v1";

const cartTrigger = document.querySelector('[data-action="open-cart"]');
const cartDrawer = document.querySelector("#cart-drawer");
const cartBackdrop = document.querySelector("#cart-backdrop");
const cartClose = document.querySelector('[data-action="close-cart"]');
const cartItemsContainer = document.querySelector("#cart-items");
const cartEmptyState = document.querySelector("#cart-empty");
const cartFooter = document.querySelector("#cart-footer");
const cartSubtotalEl = document.querySelector("#cart-subtotal");
const cartCountBadges = document.querySelectorAll(".cart-count");
const cartActionButtons = document.querySelectorAll('[data-action="open-cart"]');

const FREE_SHIPPING_THRESHOLD = 80;
const shippingFill = document.querySelector("#shipping-fill");
const shippingText = document.querySelector("#shipping-text");

function updateShippingProgress(cart) {
    if (!shippingFill || !shippingText) return;

    const subtotal = cart.reduce((total, item) => total + item.price * item.qty, 0);
    const ratio = Math.min(subtotal / FREE_SHIPPING_THRESHOLD, 1);
    shippingFill.style.width = `${ratio * 100}%`;

    if (subtotal >= FREE_SHIPPING_THRESHOLD) {
        shippingText.innerHTML = "🎉 Livraison gratuite débloquée !";
    } else {
        const remaining = formatPrice(FREE_SHIPPING_THRESHOLD - subtotal);
        shippingText.innerHTML = `Plus que <strong>${remaining}</strong> pour la livraison gratuite`;
    }
}

function bumpCartIcon() {
    cartActionButtons.forEach((button) => {
        button.classList.remove("is-bumping");
        /* Force le navigateur à relancer l'animation même si elle vient de jouer. */
        void button.offsetWidth;
        button.classList.add("is-bumping");
    });
}

function getCart() {
    const cart = readStorage(CART_KEY, []);
    return Array.isArray(cart) ? cart : [];
}

function saveCart(cart) {
    writeStorage(CART_KEY, cart);
}

function getCartCount(cart) {
    return cart.reduce((total, item) => total + item.qty, 0);
}

function renderCartBadge() {
    const count = getCartCount(getCart());
    cartCountBadges.forEach((badge) => {
        badge.textContent = String(count);
        badge.hidden = count === 0;
    });
}

function buildCartItemNode(item) {
    const row = document.createElement("li");
    row.className = "cart-item";
    row.dataset.id = item.id;

    const image = document.createElement("img");
    image.className = "cart-item__image";
    image.src = item.image;
    image.alt = "";
    image.loading = "lazy";

    const details = document.createElement("div");

    const name = document.createElement("h3");
    name.className = "cart-item__name";
    name.textContent = item.name;

    const price = document.createElement("p");
    price.className = "cart-item__price";
    price.textContent = formatPrice(item.price);

    const qtyWrap = document.createElement("div");
    qtyWrap.className = "cart-item__qty";

    const minusBtn = document.createElement("button");
    minusBtn.type = "button";
    minusBtn.textContent = "−";
    minusBtn.setAttribute("aria-label", "Diminuer la quantité");
    minusBtn.addEventListener("click", () => updateQuantity(item.id, item.qty - 1));

    const qtyValue = document.createElement("span");
    qtyValue.textContent = String(item.qty);

    const plusBtn = document.createElement("button");
    plusBtn.type = "button";
    plusBtn.textContent = "+";
    plusBtn.setAttribute("aria-label", "Augmenter la quantité");
    plusBtn.addEventListener("click", () => updateQuantity(item.id, item.qty + 1));

    qtyWrap.append(minusBtn, qtyValue, plusBtn);

    const removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.className = "cart-item__remove";
    removeBtn.textContent = "Retirer";
    removeBtn.addEventListener("click", () => removeFromCart(item.id));

    details.append(name, price, qtyWrap, removeBtn);

    const actions = document.createElement("div");
    actions.style.textAlign = "right";
    const lineTotal = document.createElement("p");
    lineTotal.className = "cart-item__price";
    lineTotal.textContent = formatPrice(item.price * item.qty);
    actions.append(lineTotal);

    row.append(image, details, actions);
    return row;
}

function renderCartDrawer() {
    if (!cartItemsContainer) return;

    const cart = getCart();

    cartItemsContainer.innerHTML = "";

    if (cart.length === 0) {
        if (cartEmptyState) cartEmptyState.hidden = false;
        if (cartFooter) cartFooter.hidden = true;
        return;
    }

    if (cartEmptyState) cartEmptyState.hidden = true;
    if (cartFooter) cartFooter.hidden = false;

    cart.forEach((item) => {
        cartItemsContainer.appendChild(buildCartItemNode(item));
    });

    const subtotal = cart.reduce((total, item) => total + item.price * item.qty, 0);
    if (cartSubtotalEl) cartSubtotalEl.textContent = formatPrice(subtotal);
}

function refreshCartUI() {
    renderCartBadge();
    renderCartDrawer();
    updateShippingProgress(getCart());
    /* Prévient les autres scripts (ex. barre panier du catalogue). */
    document.dispatchEvent(new CustomEvent("cart:updated"));
}

function addToCart(product) {
    const cart = getCart();
    const existing = cart.find((item) => item.id === product.id);

    if (existing) {
        existing.qty += 1;
    } else {
        cart.push({ ...product, qty: 1 });
    }

    saveCart(cart);
    refreshCartUI();
    bumpCartIcon();
    openCart();
}

function playAddedFeedback(button) {
    if (!button) return;

    const originalLabel = button.textContent;
    const key = button.dataset.i18n;

    button.classList.add("button--added");
    button.textContent = "Ajouté ✓";
    button.disabled = true;

    window.setTimeout(() => {
        button.classList.remove("button--added");
        button.disabled = false;
        button.textContent = originalLabel;
        if (key) button.dataset.i18n = key;
    }, 1200);
}

function updateQuantity(id, qty) {
    let cart = getCart();

    if (qty <= 0) {
        cart = cart.filter((item) => item.id !== id);
    } else {
        const item = cart.find((entry) => entry.id === id);
        if (item) item.qty = qty;
    }

    saveCart(cart);
    refreshCartUI();
}

function removeFromCart(id) {
    const cart = getCart().filter((item) => item.id !== id);
    saveCart(cart);
    refreshCartUI();
}

function openCart() {
    if (!cartDrawer) return;
    cartDrawer.classList.add("is-open");
    cartBackdrop && cartBackdrop.classList.add("is-open");
    cartDrawer.setAttribute("aria-hidden", "false");
}

function closeCart() {
    if (!cartDrawer) return;
    cartDrawer.classList.remove("is-open");
    cartBackdrop && cartBackdrop.classList.remove("is-open");
    cartDrawer.setAttribute("aria-hidden", "true");
}

if (cartTrigger) cartTrigger.addEventListener("click", openCart);
if (cartClose) cartClose.addEventListener("click", closeCart);
if (cartBackdrop) cartBackdrop.addEventListener("click", closeCart);

document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    closeCart();
    closeSearch();
});

document.querySelectorAll('[data-action="add-to-cart"]').forEach((button) => {
    button.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();

        const card = button.closest("[data-product-id]");
        if (!card) return;

        addToCart({
            id: card.dataset.productId,
            name: card.dataset.productName,
            price: parseFloat(card.dataset.productPrice),
            image: card.dataset.productImage,
        });

        playAddedFeedback(button);
    });
});

refreshCartUI();


/* ==========================================================================
   Bilingue FR / EN (contenu statique de la page d'accueil)
   ========================================================================== */

const LANG_KEY = "site_lang";

const translations = {
    fr: {
        nav_new: "Nouveautés",
        nav_bags: "Sacs",
        nav_accessories: "Accessoires",
        nav_collections: "Collections",
        nav_about: "À propos",
        search_placeholder: "Rechercher un sac, un accessoire…",
        search_hint: "La recherche sera bientôt disponible.",
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
        search_hint: "Search will be available soon.",
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