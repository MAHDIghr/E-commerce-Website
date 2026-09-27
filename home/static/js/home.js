"use strict";

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
   Favoris (visuel uniquement pour le moment)
   ========================================================================== */

document.querySelectorAll(".product-wishlist").forEach((button) => {
    button.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();

        const isActive = button.classList.toggle("is-active");
        button.setAttribute("aria-pressed", String(isActive));

        if (isActive) {
            button.classList.remove("is-popping");
            void button.offsetWidth;
            button.classList.add("is-popping");
        }
    });
});


/* ==========================================================================
   Historique de navigation — "vus récemment" (localStorage)
   ========================================================================== */

const RECENT_KEY = "recently_viewed_v1";
const RECENT_LIMIT = 4;

function addToRecentlyViewed(product) {
    let recent = readStorage(RECENT_KEY, []);
    if (!Array.isArray(recent)) recent = [];

    recent = recent.filter((item) => item.id !== product.id);
    recent.unshift(product);
    recent = recent.slice(0, RECENT_LIMIT);

    writeStorage(RECENT_KEY, recent);
    renderRecentlyViewed();
}

function renderRecentlyViewed() {
    const section = document.querySelector("#recently-viewed");
    const grid = document.querySelector("#recently-viewed-grid");
    if (!section || !grid) return;

    const recent = readStorage(RECENT_KEY, []);

    if (!Array.isArray(recent) || recent.length === 0) {
        section.classList.remove("is-visible");
        return;
    }

    grid.innerHTML = "";

    recent.forEach((product) => {
        const article = document.createElement("article");
        article.className = "product-card";

        const link = document.createElement("a");
        link.className = "product-image";
        link.href = "#";

        const img = document.createElement("img");
        img.src = product.image;
        img.alt = product.name;
        img.loading = "lazy";

        link.appendChild(img);

        const info = document.createElement("div");
        info.className = "product-info";

        const name = document.createElement("h3");
        name.textContent = product.name;

        const price = document.createElement("p");
        price.className = "product-price";
        price.textContent = formatPrice(product.price);

        info.append(name, price);
        article.append(link, info);
        grid.appendChild(article);
    });

    section.classList.add("is-visible");
}

document.querySelectorAll(".product-image[data-product-id]").forEach((link) => {
    link.addEventListener("click", () => {
        addToRecentlyViewed({
            id: link.dataset.productId,
            name: link.dataset.productName,
            price: parseFloat(link.dataset.productPrice),
            image: link.dataset.productImage,
        });
    });
});

renderRecentlyViewed();


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
   Newsletter
   ========================================================================== */

const newsletterForm = document.querySelector(".newsletter-form");

if (newsletterForm) {
    newsletterForm.addEventListener("submit", (event) => {
        /* Le formulaire n'est pas encore relié à une vue Django. */
        event.preventDefault();
    });
}


/* ==========================================================================
   Apparition au scroll (toutes les sections marquées .reveal)
   ========================================================================== */

(function initScrollReveal() {
    const revealTargets = document.querySelectorAll(".reveal");
    if (revealTargets.length === 0) return;

    if (prefersReducedMotion() || !("IntersectionObserver" in window)) {
        revealTargets.forEach((el) => el.classList.add("is-visible"));
        return;
    }

    const observer = new IntersectionObserver(
        (entries) => {
            entries.forEach((entry) => {
                if (!entry.isIntersecting) return;
                entry.target.classList.add("is-visible");
                observer.unobserve(entry.target);
            });
        },
        { threshold: 0.15 }
    );

    revealTargets.forEach((el, index) => {
        el.style.setProperty("--reveal-delay", `${Math.min(index % 4, 3) * 90}ms`);
        observer.observe(el);
    });
})();


/* ==========================================================================
   Mobile : le bouton "Ajouter au panier" apparaît quand le produit passe
   au centre de l'écran (pas de survol possible sans souris), puis
   disparaît au scroll suivant.
   ========================================================================== */

(function initTouchProductFocus() {
    if (!isTouchDevice || !("IntersectionObserver" in window)) return;

    const cards = document.querySelectorAll(".product-card[data-product-id]");
    if (cards.length === 0) return;

    const observer = new IntersectionObserver(
        (entries) => {
            entries.forEach((entry) => {
                entry.target.classList.toggle("is-in-focus", entry.isIntersecting);
            });
        },
        {
            /* Ne considère la carte "au centre" que sur une fine bande
               autour du milieu vertical de l'écran. */
            rootMargin: "-42% 0px -42% 0px",
            threshold: 0,
        }
    );

    cards.forEach((card) => observer.observe(card));
})();


/* ==========================================================================
   Desktop : légère inclinaison 3D des visuels produits au mouvement
   de la souris (jamais activé sur tactile, ni si mouvement réduit demandé).
   ========================================================================== */

(function initProductTilt() {
    if (!isFinePointer || prefersReducedMotion()) return;

    const MAX_TILT_DEGREES = 6;

    document.querySelectorAll(".product-image").forEach((image) => {
        image.addEventListener("mousemove", (event) => {
            const rect = image.getBoundingClientRect();
            const relativeX = (event.clientX - rect.left) / rect.width - 0.5;
            const relativeY = (event.clientY - rect.top) / rect.height - 0.5;

            image.style.setProperty("--tilt-x", `${relativeX * MAX_TILT_DEGREES * 2}deg`);
            image.style.setProperty("--tilt-y", `${relativeY * -MAX_TILT_DEGREES * 2}deg`);
        });

        image.addEventListener("mouseleave", () => {
            image.style.setProperty("--tilt-x", "0deg");
            image.style.setProperty("--tilt-y", "0deg");
        });
    });
})();


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
   Parallax léger du visuel héro (desktop uniquement, scroll performant)
   ========================================================================== */

(function initHeroParallax() {
    if (isTouchDevice || prefersReducedMotion()) return;

    const heroImage = document.querySelector(".hero-media img");
    if (!heroImage) return;

    let ticking = false;

    function applyParallax() {
        const offset = Math.min(window.scrollY, 600) * 0.15;
        heroImage.style.transform = `translateY(${offset}px)`;
        ticking = false;
    }

    window.addEventListener(
        "scroll",
        () => {
            if (ticking) return;
            ticking = true;
            window.requestAnimationFrame(applyParallax);
        },
        { passive: true }
    );
})();


/* ==========================================================================
   Vente flash — compte à rebours réel, sans réinitialisation trompeuse.
   La date de fin est calculée une seule fois puis conservée le temps de
   la session (sessionStorage) : elle n'est jamais recalculée à chaque
   rafraîchissement pour éviter un faux sentiment d'urgence.
   ========================================================================== */

(function initFlashSaleCountdown() {
    const banner = document.querySelector("#flash-sale");
    if (!banner) return;

    const hoursEl = banner.querySelector("[data-hours]");
    const minutesEl = banner.querySelector("[data-minutes]");
    const secondsEl = banner.querySelector("[data-seconds]");

    const DURATION_HOURS = parseFloat(banner.dataset.durationHours || "6");
    const DEADLINE_KEY = "flash_sale_deadline";

    let deadline = parseInt(readStorage(DEADLINE_KEY, 0), 10);
    const now = Date.now();

    if (!deadline || deadline < now) {
        deadline = now + DURATION_HOURS * 60 * 60 * 1000;
        writeStorage(DEADLINE_KEY, deadline);
    }

    function tick() {
        const remaining = deadline - Date.now();

        if (remaining <= 0) {
            banner.classList.add("is-ended");
            const textEl = banner.querySelector(".flash-sale__text");
            if (textEl) textEl.textContent = "L'offre du jour est terminée — revenez demain !";
            window.clearInterval(intervalId);
            return;
        }

        const totalSeconds = Math.floor(remaining / 1000);
        const hours = String(Math.floor(totalSeconds / 3600)).padStart(2, "0");
        const minutes = String(Math.floor((totalSeconds % 3600) / 60)).padStart(2, "0");
        const seconds = String(totalSeconds % 60).padStart(2, "0");

        if (hoursEl) hoursEl.textContent = hours;
        if (minutesEl) minutesEl.textContent = minutes;
        if (secondsEl) secondsEl.textContent = seconds;
    }

    tick();
    const intervalId = window.setInterval(tick, 1000);
})();


/* ==========================================================================
   Pop-up de bienvenue avec code de réduction — une fois par semaine max,
   jamais de manière insistante.
   ========================================================================== */

(function initWelcomeModal() {
    const backdrop = document.querySelector("#welcome-modal-backdrop");
    if (!backdrop) return;

    const closeButton = backdrop.querySelector('[data-action="close-welcome"]');
    const copyButton = backdrop.querySelector('[data-action="copy-code"]');
    const codeEl = backdrop.querySelector("#welcome-code");

    const DISMISS_KEY = "welcome_modal_dismissed_until";
    const dismissedUntil = parseInt(readStorage(DISMISS_KEY, 0), 10);

    if (dismissedUntil && dismissedUntil > Date.now()) return;

    function openModal() {
        backdrop.classList.add("is-open");
        backdrop.setAttribute("aria-hidden", "false");
    }

    function closeModal(daysBeforeShowingAgain) {
        backdrop.classList.remove("is-open");
        backdrop.setAttribute("aria-hidden", "true");
        const until = Date.now() + daysBeforeShowingAgain * 24 * 60 * 60 * 1000;
        writeStorage(DISMISS_KEY, until);
    }

    window.setTimeout(openModal, 4000);

    if (closeButton) closeButton.addEventListener("click", () => closeModal(7));
    backdrop.addEventListener("click", (event) => {
        if (event.target === backdrop) closeModal(1);
    });

    if (copyButton && codeEl) {
        copyButton.addEventListener("click", async () => {
            const code = codeEl.textContent.trim();
            const originalLabel = copyButton.textContent;

            try {
                await navigator.clipboard.writeText(code);
                copyButton.textContent = "Copié ✓";
            } catch (error) {
                /* Presse-papiers indisponible : l'utilisateur peut sélectionner le code manuellement. */
                copyButton.textContent = "Sélectionnez le code";
            }

            window.setTimeout(() => {
                copyButton.textContent = originalLabel;
            }, 2000);
        });
    }
})();


/* ==========================================================================
   Notification de preuve sociale.
   ⚠️ Les entrées ci-dessous sont des exemples de démonstration : à
   remplacer par un flux réel (dernières commandes anonymisées côté
   Django) avant la mise en production, pour ne jamais afficher au
   client une information fausse.
   ========================================================================== */

(function initSocialProofToast() {
    const toast = document.querySelector("#social-proof-toast");
    if (!toast) return;

    const demoActivity = [
        { initials: "SM", name: "Sarah", city: "Lyon", product: "le sac cabas cuir camel", minutesAgo: 6 },
        { initials: "LB", name: "Léa", city: "Bordeaux", product: "le foulard imprimé en soie", minutesAgo: 14 },
        { initials: "CD", name: "Camille", city: "Nantes", product: "le sac bandoulière noir", minutesAgo: 21 },
    ];

    const avatarEl = toast.querySelector(".social-toast__avatar");
    const textEl = toast.querySelector(".social-toast__text");
    const timeEl = toast.querySelector(".social-toast__time");
    const closeButton = toast.querySelector('[data-action="close-toast"]');

    let index = 0;
    let intervalId = null;

    function showNext() {
        const entry = demoActivity[index % demoActivity.length];
        index += 1;

        if (avatarEl) avatarEl.textContent = entry.initials;
        if (textEl) {
            textEl.innerHTML = "";
            const strongName = document.createElement("strong");
            strongName.textContent = entry.name;
            textEl.append(strongName, document.createTextNode(` (${entry.city}) vient de consulter ${entry.product}`));
        }
        if (timeEl) timeEl.textContent = `il y a ${entry.minutesAgo} min`;

        toast.classList.add("is-visible");

        window.setTimeout(() => toast.classList.remove("is-visible"), 5000);
    }

    if (closeButton) {
        closeButton.addEventListener("click", () => {
            toast.classList.remove("is-visible");
        });
    }

    window.setTimeout(() => {
        showNext();
        intervalId = window.setInterval(showNext, 9000);
    }, 6000);

    /* Évite un minuteur qui tourne inutilement si l'onglet est masqué. */
    document.addEventListener("visibilitychange", () => {
        if (document.hidden && intervalId) {
            window.clearInterval(intervalId);
            intervalId = null;
        } else if (!document.hidden && !intervalId) {
            intervalId = window.setInterval(showNext, 9000);
        }
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
