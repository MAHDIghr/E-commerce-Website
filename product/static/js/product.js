"use strict";
/* product.js — interactions de la page produit. Dépend de base.js (addToCart).
   Lit les données depuis #product-data (json_script) : aucun contenu produit en dur ici. */
(() => {
    const data = JSON.parse(document.getElementById("product-data").textContent);
    let media = data.media;
    const allMedia = data.media;
    const $ = (s, r = document) => r.querySelector(s);
    const $$ = (s, r = document) => [...r.querySelectorAll(s)];
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    document.body.classList.add("p-js");

    /*
     * Achat de la fiche produit : gestion locale et explicite des trois CTA
     * (principal, final et barre collante). On arrête la propagation afin que
     * le contrôleur partagé ne traite pas une seconde fois ce même clic.
     * Cette initialisation est placée avant la galerie pour ne pas dépendre
     * de ses interactions secondaires.
     */
    $$(".js-add, .js-buy").forEach((button) => {
        button.addEventListener("click", async (event) => {
            event.preventDefault();
            event.stopPropagation();
            if (button.disabled || button.getAttribute("aria-busy") === "true") return;

            const variant = $('input[name="color"]:checked');
            const offer = $('input[name="offer"]:checked');
            const variantId = Number(variant && variant.value);
            const offerId = Number(offer && offer.value);
            const status = $("#variant-stock-status");

            if (!Number.isSafeInteger(variantId) || variantId < 1 ||
                !Number.isSafeInteger(offerId) || offerId < 1) {
                const message = "Choisissez une variante et une offre disponible avant de continuer.";
                if (status) status.textContent = message;
                if (typeof showCartStatus === "function") showCartStatus(message, true);
                return;
            }
            if (typeof addToCart !== "function") {
                const message = "Le panier n'est pas initialisé. Actualisez la page puis réessayez.";
                if (status) status.textContent = message;
                return;
            }

            const originalMarkup = button.innerHTML;
            button.disabled = true;
            button.setAttribute("aria-busy", "true");
            button.textContent = "Ajout en cours…";
            try {
                const offerDetails = (data.offers || []).find((item) => Number(item.id) === offerId);
                let selectedItemIds = [];
                if (offerDetails && Array.isArray(offerDetails.accessories) && offerDetails.accessories.length) {
                    if (typeof chooseProductOffer !== "function") throw new Error("La sélection des accessoires n'est pas disponible. Actualisez la page.");
                    const selection = await chooseProductOffer({ name: data.name }, [offerDetails]);
                    if (!selection || !selection.offerId) return;
                    selectedItemIds = selection.selectedItemIds || [];
                }
                const added = await addToCart({ variantId, offerId, selectedItemIds }, { openDrawer: button.matches(".js-add") });
                if (added && button.matches(".js-buy")) {
                    const checkoutUrl = document.querySelector("#cart-drawer")?.dataset.checkoutUrl || "/checkout/";
                    window.location.assign(checkoutUrl);
                    return;
                }
                if (added) {
                    button.classList.add("is-done");
                    button.textContent = "Ajouté ✓";
                } else {
                    button.innerHTML = originalMarkup;
                }
            } catch (error) {
                const message = error && error.message || "L'ajout au panier a échoué. Réessayez.";
                if (status) status.textContent = message;
                if (typeof showCartStatus === "function") showCartStatus(message, true);
                button.innerHTML = originalMarkup;
            } finally {
                button.removeAttribute("aria-busy");
                const selectedVariant = $('input[name="color"]:checked');
                const selectedOffer = $('input[name="offer"]:checked');
                const stock = Number(selectedVariant && selectedVariant.dataset.stock || 0);
                const required = Math.max(1, Number(selectedOffer && selectedOffer.dataset.mainQuantity || 1));
                button.disabled = !selectedVariant || !selectedOffer || stock < required;
                window.setTimeout(() => {
                    if (!button.isConnected) return;
                    button.classList.remove("is-done");
                    button.innerHTML = originalMarkup;
                    button.disabled = !selectedVariant || !selectedOffer || stock < required;
                }, 1400);
            }
        });
    });

    /* ---------- Galerie ---------- */
    const track = $(".gal__track"), allSlides = $$(".gal__slide"), allThumbs = $$(".gal__thumb"), count = $("#gal-count");
    let slides = allSlides;
    let thumbs = allThumbs;
    let cur = -1;
    const pad = () => parseFloat(getComputedStyle(track).paddingLeft) || 0;
    const go = (i) => {
        if (!slides.length) return;
        i = (i + slides.length) % slides.length;
        track.scrollTo({ left: slides[i].offsetLeft - pad(), behavior: reduced ? "auto" : "smooth" });
    };
    const mark = () => {
        if (!slides.length) { count.textContent = "0 / 0"; cur = -1; return; }
        let best = 0, d = Infinity;
        slides.forEach((s, i) => { const x = Math.abs(s.offsetLeft - pad() - track.scrollLeft); if (x < d) { d = x; best = i; } });
        if (best === cur) return;
        cur = best;
        count.textContent = `${cur + 1} / ${slides.length}`;
        thumbs.forEach((t, i) => (i === cur ? t.setAttribute("aria-current", "true") : t.removeAttribute("aria-current")));
        $$("video", track).forEach((v) => { if (!slides[cur].contains(v)) v.pause(); });
    };
    let raf = 0;
    track.addEventListener("scroll", () => { cancelAnimationFrame(raf); raf = requestAnimationFrame(mark); }, { passive: true });
    track.addEventListener("keydown", (e) => {
        if (e.key === "ArrowRight") { e.preventDefault(); go(cur + 1); }
        if (e.key === "ArrowLeft") { e.preventDefault(); go(cur - 1); }
    });
    allThumbs.forEach((t) => t.addEventListener("click", () => go(thumbs.indexOf(t))));
    $$("[data-nav]").forEach((b) => b.addEventListener("click", () => go(cur + +b.dataset.nav)));
    // Tous les médias appartiennent au produit : le changement de couleur ne filtre pas la galerie.

    /* Vidéo : chargée au clic, muette, avec repli sur le poster si le fichier est absent */
    $$("[data-video]").forEach((b) => b.addEventListener("click", () => {
        const v = document.createElement("video");
        Object.assign(v, { src: b.dataset.video, poster: b.querySelector("img").src, muted: true, loop: true, controls: true, playsInline: true, autoplay: true, className: "gal__media" });
        v.onerror = () => { b.classList.add("is-err"); v.replaceWith(b); };
        b.replaceWith(v);
    }));

    /* ---------- Lightbox ---------- */
    const lb = $("#lb"), stage = $(".lb__stage", lb);
    let li = 0, x0 = null;
    const show = (i) => {
        li = (i + media.length) % media.length;
        const m = media[li];
        let n;
        if (m.type === "video") {
            n = document.createElement("video");
            Object.assign(n, { src: m.src, poster: m.poster, controls: true, muted: true, autoplay: true, playsInline: true });
        } else {
            n = new Image(); n.src = m.src; n.alt = m.alt;
            n.addEventListener("click", () => n.classList.toggle("is-zoom"));
        }
        stage.replaceChildren(n);
        $(".lb__n", lb).textContent = `${li + 1} / ${media.length}`;
    };
    $$("[data-zoom]").forEach((b) => b.addEventListener("click", () => { lb.showModal(); show(slides.indexOf(b.closest(".gal__slide"))); }));
    $(".lb__close", lb).addEventListener("click", () => lb.close());
    $(".lb__prev", lb).addEventListener("click", () => show(li - 1));
    $(".lb__next", lb).addEventListener("click", () => show(li + 1));
    lb.addEventListener("keydown", (e) => { if (e.key === "ArrowRight") show(li + 1); if (e.key === "ArrowLeft") show(li - 1); });
    lb.addEventListener("close", () => { stage.replaceChildren(); go(li); });
    stage.addEventListener("pointerdown", (e) => { x0 = e.clientX; });
    stage.addEventListener("pointerup", (e) => {
        if (x0 !== null && Math.abs(e.clientX - x0) > 60) show(li + (e.clientX < x0 ? 1 : -1));
        x0 = null;
    });

    /* ---------- Offres, couleur, prix ---------- */
    const offerIn = () => $("input[name=offer]:checked");
    const colorIn = () => $("input[name=color]:checked");
    const sync = () => {
        const o = offerIn().dataset;
        const color = colorIn().dataset;
        const priceLabel = o.label;
        const oldLabel = o.old || "";
        const discount = Number(o.off || 0);

        $("#price-now").textContent = priceLabel;
        $("#price-old").lastChild.textContent = oldLabel;
        $("#price-old").hidden = !oldLabel;
        $("#price-off").textContent = discount > 0 ? `-${discount} %` : "";
        $("#price-off").hidden = discount <= 0;
        $("#sbar-price").textContent = priceLabel;
        $("#sbar-offer").textContent = o.name;
        $("#color-label").textContent = color.label;

        // Le prix est propre à l'offre choisie et ne varie pas avec la couleur.
        $$('input[name="offer"]').forEach((input) => {
            const oldPrice = input.closest(".offer").querySelector(".offer__price del");
            if (oldPrice) {
                oldPrice.textContent = input.dataset.old || "";
                oldPrice.hidden = !input.dataset.old;
            }
        });
    };
    const updateAvailability = () => {
        const stock = Number(colorIn().dataset.stock);
        const required = Math.max(1, Number(offerIn().dataset.mainQuantity || 1));
        const available = stock >= required;
        $$(".js-add, .js-buy").forEach((button) => {
            button.disabled = !available;
            button.setAttribute("aria-disabled", String(!available));
        });
        const status = $("#variant-stock-status");
        if (stock <= 0) status.textContent = "Indisponible pour le moment.";
        else if (!available) status.textContent = "Stock insuffisant pour cette offre.";
        else if (stock <= 5) status.textContent = `Plus que ${stock} en stock.`;
        else status.textContent = "En stock.";
    };

    $$("input[name=offer]").forEach((i) => i.addEventListener("change", () => {
        sync();
        updateAvailability();
    }));
    $$("input[name=color]").forEach((i) => i.addEventListener("change", () => {
        sync();
        updateAvailability();
    }));
    sync();
    updateAvailability();

    /* Les CTA .js-buy et .js-add utilisent le panier partagé ; la fiche gère le sélecteur d’accessoires. */

    /* ---------- Barre collante : visible quand aucun CTA de page n'est à l'écran ---------- */
    const sbar = $("#sbar"), seen = new Set();
    const sbIo = new IntersectionObserver((es) => {
        es.forEach((e) => (e.isIntersecting ? seen.add(e.target) : seen.delete(e.target)));
        const on = seen.size === 0;
        sbar.classList.toggle("is-on", on);
        sbar.inert = !on;
    }, { rootMargin: "0px 0px -64px 0px" });
    sbIo.observe($("#cta")); sbIo.observe($("#cta-final"));

    /* ---------- Apparition au scroll (une seule fois) ---------- */
    const rv = $$(".p-rv");
    if (reduced || !("IntersectionObserver" in window)) rv.forEach((e) => e.classList.add("in"));
    else {
        const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } }), { threshold: 0.12 });
        rv.forEach((e) => io.observe(e));
    }
})();