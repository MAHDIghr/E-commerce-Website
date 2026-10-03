"use strict";
/* product.js — interactions de la page produit. Dépend de base.js (addToCart).
   Lit les données depuis #product-data (json_script) : aucun contenu produit en dur ici. */
(() => {
    const data = JSON.parse(document.getElementById("product-data").textContent);
    const media = data.media;
    const $ = (s, r = document) => r.querySelector(s);
    const $$ = (s, r = document) => [...r.querySelectorAll(s)];
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    document.body.classList.add("p-js");

    /* ---------- Galerie ---------- */
    const track = $(".gal__track"), slides = $$(".gal__slide"), thumbs = $$(".gal__thumb"), count = $("#gal-count");
    let cur = -1;
    const pad = () => parseFloat(getComputedStyle(track).paddingLeft) || 0;
    const go = (i) => {
        i = (i + slides.length) % slides.length;
        track.scrollTo({ left: slides[i].offsetLeft - pad(), behavior: reduced ? "auto" : "smooth" });
    };
    const mark = () => {
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
    thumbs.forEach((t) => t.addEventListener("click", () => go(+t.dataset.go)));
    $$("[data-nav]").forEach((b) => b.addEventListener("click", () => go(cur + +b.dataset.nav)));
    mark();

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
        $("#price-now").textContent = o.label;
        $("#price-old").lastChild.textContent = o.old;
        $("#price-off").textContent = `-${o.off} %`;
        $("#sbar-price").textContent = o.label;
        $("#sbar-offer").textContent = o.name;
        $("#color-label").textContent = colorIn().dataset.label;
    };
    $$("input[name=offer], input[name=color]").forEach((i) => i.addEventListener("change", sync));

    /* ---------- Ajout au panier (réutilise addToCart de base.js) ---------- */
    $$(".js-add").forEach((btn) => btn.addEventListener("click", () => {
        const o = offerIn().dataset, label = btn.textContent;
        btn.disabled = true; btn.textContent = "Ajout…";
        window.setTimeout(() => {
            addToCart({ id: `${data.slug}:${offerIn().value}:${colorIn().value}`, name: `${data.name} — ${o.name} (${colorIn().dataset.label})`, price: parseFloat(o.price), image: media[0].src });
            btn.disabled = false; btn.textContent = "Ajouté ✓"; btn.classList.add("is-done");
            window.setTimeout(() => { btn.textContent = label; btn.classList.remove("is-done"); }, 1400);
        }, reduced ? 0 : 450);
    }));

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