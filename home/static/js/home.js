"use strict";

/* home.js — scripts spécifiques à la page d'accueil.
   Nécessite base.js chargé avant (readStorage, writeStorage, formatPrice,
   prefersReducedMotion, isTouchDevice, isFinePointer). */

/* ==========================================================================
   Favoris locaux persistés dans le navigateur
   ========================================================================== */

const HOME_WISHLIST_KEY = "wishlist_v1";
const storedHomeWishlist = readStorage(HOME_WISHLIST_KEY, []);
const homeWishlist = new Set(
    (Array.isArray(storedHomeWishlist) ? storedHomeWishlist : [])
        .filter((slug) => typeof slug === "string" && /^[a-z0-9-]{1,180}$/i.test(slug))
);

document.querySelectorAll(".product-card[data-product-slug] .product-wishlist").forEach((button) => {
    const card = button.closest(".product-card");
    const slug = card?.dataset.productSlug || "";
    const validSlug = /^[a-z0-9-]{1,180}$/i.test(slug);
    button.disabled = !validSlug;
    button.classList.toggle("is-active", validSlug && homeWishlist.has(slug));
    button.setAttribute("aria-pressed", String(validSlug && homeWishlist.has(slug)));

    button.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        if (!validSlug) return;

        const isActive = !homeWishlist.has(slug);
        if (isActive) homeWishlist.add(slug);
        else homeWishlist.delete(slug);
        writeStorage(HOME_WISHLIST_KEY, [...homeWishlist]);
        button.classList.toggle("is-active", isActive);
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

    grid.replaceChildren();

    recent.filter((product) => (
        product
        && typeof product.slug === "string"
        && /^[a-z0-9-]{1,180}$/i.test(product.slug)
        && typeof product.name === "string"
        && typeof product.image === "string"
        && Number.isFinite(Number(product.price))
        && Number(product.price) >= 0
    )).forEach((product) => {
        const slug = product.slug;
        let imageUrl;
        try {
            const parsedImageUrl = new URL(product.image, window.location.origin);
            if (parsedImageUrl.protocol !== "https:" && parsedImageUrl.origin !== window.location.origin) return;
            if (parsedImageUrl.protocol !== "https:" && parsedImageUrl.protocol !== "http:") return;
            imageUrl = parsedImageUrl.href;
        } catch (_error) {
            return;
        }

        const article = document.createElement("article");
        article.className = "product-card";

        const link = document.createElement("a");
        link.className = "product-image";
        link.href = `/produit/${encodeURIComponent(slug)}/`;

        const img = document.createElement("img");
        img.src = imageUrl;
        img.alt = product.name.slice(0, 240);
        img.loading = "lazy";
        img.decoding = "async";

        link.appendChild(img);

        const info = document.createElement("div");
        info.className = "product-info";

        const name = document.createElement("h3");
        name.textContent = product.name.slice(0, 180);

        const price = document.createElement("p");
        price.className = "product-price";
        price.textContent = formatPrice(Number(product.price));

        info.append(name, price);
        article.append(link, info);
        grid.appendChild(article);
    });

    section.classList.add("is-visible");
}

document.querySelectorAll(".product-card[data-product-id] .product-image").forEach((link) => {
    link.addEventListener("click", () => {
        const card = link.closest(".product-card");
        if (!card) return;
        const slug = card.dataset.productSlug || "";
        if (!/^[a-z0-9-]{1,180}$/i.test(slug)) return;
        const price = Number.parseFloat(card.dataset.productPrice || "");
        addToRecentlyViewed({
            id: card.dataset.productId,
            slug,
            name: card.dataset.productName || "",
            price: Number.isFinite(price) ? price : 0,
            image: card.dataset.productImage || "",
        });
    });
});

renderRecentlyViewed();


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
   Carrousel 3D — section "Notre sélection signature"
   (fusionné depuis test.js, encapsulé pour ne rien exposer au scope global)
   ========================================================================== */

(function initSignatureCarousel() {

    const carousel = document.getElementById("carousel");
    if (!carousel) return;

    const cards = Array.from(document.querySelectorAll(".card"));
    const prevButton = document.getElementById("prevButton");
    const nextButton = document.getElementById("nextButton");

    if (cards.length === 0 || !prevButton || !nextButton) return;

    let currentIndex = 0;
    let isAnimating = false;
    let autoPlayTimer = null;
    const AUTO_PLAY_DELAY = 2000;
    const totalCards = cards.length;

    function modulo(number, total) {
        return ((number % total) + total) % total;
    }

    function getOffset(cardIndex) {
        let offset = cardIndex - currentIndex;
        if (offset > totalCards / 2) offset -= totalCards;
        if (offset < -totalCards / 2) offset += totalCards;
        return offset;
    }

    function updateCarousel(previousOffsets = null) {
        const cardWidth = cards[0].getBoundingClientRect().width;
        const spacing = cardWidth * 1.10;

        cards.forEach((card, index) => {
            const offset = getOffset(index);
            const absoluteOffset = Math.abs(offset);

            let shouldJump = false;
            if (previousOffsets) {
                const oldOffset = previousOffsets[index];
                if (Math.abs(offset - oldOffset) > 1.5) shouldJump = true;
            }

            card.style.transition = shouldJump ? "none" : "";

            if (offset === 0) {
                card.style.transform = `
                    translate(-50%, -50%)
                    translateX(0px)
                    translateZ(${cardWidth * 0.42}px)
                    rotateY(0deg)
                    scale(1)
                `;
                card.style.opacity = "1";
                card.style.filter = "brightness(1) saturate(1)";
                card.style.zIndex = "50";
                return;
            }

            if (absoluteOffset === 1) {
                const direction = offset < 0 ? -1 : 1;
                const x = direction * spacing;
                const rotation = direction * -32;

                card.style.transform = `
                    translate(-50%, -50%)
                    translateX(${x}px)
                    translateZ(0px)
                    rotateY(${rotation}deg)
                    scale(0.78)
                `;
                card.style.opacity = "0.80";
                card.style.filter = "brightness(0.68) saturate(0.85)";
                card.style.zIndex = "40";
                return;
            }

            if (absoluteOffset === 2) {
                const direction = offset < 0 ? -1 : 1;
                const x = direction * spacing * 2;
                const rotation = direction * -42;

                card.style.transform = `
                    translate(-50%, -50%)
                    translateX(${x}px)
                    translateZ(-60px)
                    rotateY(${rotation}deg)
                    scale(0.62)
                `;
                card.style.opacity = "0.42";
                card.style.filter = "brightness(0.45) saturate(0.65)";
                card.style.zIndex = "30";
                return;
            }

            const direction = offset < 0 ? -1 : 1;
            const x = direction * spacing * 3;
            const rotation = direction * -48;

            card.style.transform = `
                translate(-50%, -50%)
                translateX(${x}px)
                translateZ(-130px)
                rotateY(${rotation}deg)
                scale(0.52)
            `;
            card.style.opacity = "0";
            card.style.filter = "brightness(0.30) saturate(0.40)";
            card.style.zIndex = "10";
        });

        if (previousOffsets) {
            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    cards.forEach((card) => {
                        card.style.transition = "";
                    });
                });
            });
        }
    }

    function goToSlide(index) {
        if (isAnimating) return;

        const newIndex = modulo(index, totalCards);
        if (newIndex === currentIndex) return;

        const previousOffsets = cards.map((_, i) => getOffset(i));

        isAnimating = true;
        currentIndex = newIndex;

        updateCarousel(previousOffsets);

        setTimeout(() => {
            isAnimating = false;
        }, 700);

        restartAutoPlay();
    }

    function nextSlide() {
        goToSlide(currentIndex + 1);
    }

    function previousSlide() {
        goToSlide(currentIndex - 1);
    }

    nextButton.addEventListener("click", nextSlide);
    prevButton.addEventListener("click", previousSlide);

    function startAutoPlay() {
        stopAutoPlay();
        autoPlayTimer = setInterval(() => {
            nextSlide();
        }, AUTO_PLAY_DELAY);
    }

    function stopAutoPlay() {
        if (autoPlayTimer !== null) {
            clearInterval(autoPlayTimer);
            autoPlayTimer = null;
        }
    }

    function restartAutoPlay() {
        startAutoPlay();
    }

    carousel.addEventListener("mouseenter", () => {
        stopAutoPlay();
    });

    carousel.addEventListener("mouseleave", () => {
        startAutoPlay();
    });

    /* Navigation clavier : n'agit que si le focus n'est pas dans un champ
       de saisie, pour ne pas gêner la recherche ou la newsletter. */
    document.addEventListener("keydown", (event) => {
        const targetTag = document.activeElement && document.activeElement.tagName;
        if (targetTag === "INPUT" || targetTag === "TEXTAREA") return;

        if (event.key === "ArrowRight") nextSlide();
        if (event.key === "ArrowLeft") previousSlide();
    });

    let isDragging = false;
    let dragStartX = 0;
    let dragCurrentX = 0;
    let dragDifference = 0;
    let suppressNextClick = false;

    function startDrag(clientX) {
        isDragging = true;
        dragStartX = clientX;
        dragCurrentX = clientX;
        dragDifference = 0;

        carousel.classList.add("is-dragging");
        stopAutoPlay();
    }

    function moveDrag(clientX) {
        if (!isDragging) return;

        dragCurrentX = clientX;
        dragDifference = dragCurrentX - dragStartX;
    }

    function endDrag() {
        if (!isDragging) return;

        isDragging = false;
        carousel.classList.remove("is-dragging");

        const minimumSwipeDistance = 60;

        if (Math.abs(dragDifference) >= minimumSwipeDistance) {
            suppressNextClick = true;
            window.setTimeout(() => { suppressNextClick = false; }, 0);
            if (dragDifference < 0) {
                nextSlide();
            } else {
                previousSlide();
            }
        } else {
            startAutoPlay();
        }
    }

    carousel.addEventListener("click", (event) => {
        if (!suppressNextClick) return;
        event.preventDefault();
        event.stopPropagation();
        suppressNextClick = false;
    }, true);

    carousel.addEventListener("mousedown", (event) => {
        event.preventDefault();
        startDrag(event.clientX);
    });

    window.addEventListener("mousemove", (event) => {
        moveDrag(event.clientX);
    });

    window.addEventListener("mouseup", () => {
        endDrag();
    });

    carousel.addEventListener(
        "touchstart",
        (event) => {
            const touch = event.touches[0];
            startDrag(touch.clientX);
        },
        { passive: true }
    );

    carousel.addEventListener(
        "touchmove",
        (event) => {
            const touch = event.touches[0];
            moveDrag(touch.clientX);
        },
        { passive: true }
    );

    carousel.addEventListener("touchend", () => {
        endDrag();
    });

    document.addEventListener("visibilitychange", () => {
        if (document.hidden) {
            stopAutoPlay();
        } else {
            startAutoPlay();
        }
    });

    updateCarousel();
    startAutoPlay();

})();

/* Les ajouts rapides sont gérés par base.js afin d'utiliser les offres et le panier serveur. */

/* Liens de démonstration (avis, stories, reels) : pas de redirection pour l'instant.
   Remplacer href="#" par les vrais liens puis retirer data-frontend-only. */
document.querySelectorAll("[data-frontend-only]").forEach((link) => {
    link.addEventListener("click", (event) => event.preventDefault());
});


/* ==========================================================================
   Glisser à la souris (desktop) pour stories, reels et avis.
   Sur tactile, le swipe natif (scroll-snap) fonctionne sans script.
   ========================================================================== */

document.querySelectorAll(".stories, .reels, .testimonials-grid").forEach((el) => {
    let down = false, moved = false, startX = 0, startLeft = 0;

    el.addEventListener("pointerdown", (event) => {
        if (event.pointerType !== "mouse") return;
        down = true; moved = false;
        startX = event.clientX; startLeft = el.scrollLeft;
    });
    window.addEventListener("pointermove", (event) => {
        if (!down) return;
        const dx = event.clientX - startX;
        if (Math.abs(dx) > 4) { moved = true; el.classList.add("is-grabbing"); }
        el.scrollLeft = startLeft - dx;
    });
    window.addEventListener("pointerup", () => {
        if (!down) return;
        down = false;
        el.classList.remove("is-grabbing");
    });
    el.addEventListener("click", (event) => {
        if (!moved) return;
        event.preventDefault(); event.stopPropagation(); moved = false;
    }, true);
    el.addEventListener("dragstart", (event) => event.preventDefault());
});