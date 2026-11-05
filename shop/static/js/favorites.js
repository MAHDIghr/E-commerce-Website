"use strict";
(() => {
    const grid = document.getElementById("favorites-grid"), status = document.getElementById("favorites-status");
    const prev = document.getElementById("favorites-prev"), next = document.getElementById("favorites-next"), retry = document.getElementById("favorites-retry");
    if (typeof readStorage !== "function" || typeof writeStorage !== "function") { status.textContent = "Les favoris sont indisponibles. Rechargez la page ou consultez le catalogue."; return; }
    let page = 0, revision = 0;
    const read = () => { const data = readStorage("wishlist_v1", []); return Array.isArray(data) ? [...new Set(data.filter(x => typeof x === "string" && /^[a-z0-9-]{1,200}$/i.test(x)))] : []; };
    async function render() {
        const current = ++revision, all = read();
        page = Math.min(page, Math.max(0, Math.ceil(all.length / 8) - 1));
        const slugs = all.slice(page * 8, page * 8 + 8);
        grid.replaceChildren(); retry.hidden = true; prev.hidden = next.hidden = true;
        if (!slugs.length) { status.textContent = "Aucun favori enregistré."; return; }
        status.textContent = "Chargement des favoris…";
        const query = new URLSearchParams({format:"cards"}); slugs.forEach(slug => query.append("slug",slug));
        try {
            const response = await fetch(grid.dataset.url + "?" + query, {credentials:"same-origin", cache:"no-store"});
            if (!response.ok) throw new Error("unavailable");
            const data = await response.json(); if (current !== revision) return;
            if (typeof data.html !== "string" || !Array.isArray(data.found)) throw new Error("invalid");
            // HTML rendu et échappé par Django, jamais reconstruit à partir du stockage local.
            const template = document.createElement("template"); template.innerHTML = data.html; grid.append(template.content);
            for (const slug of slugs) {
                const card = [...grid.querySelectorAll("[data-product-slug]")].find(node => node.dataset.productSlug === slug);
                const holder = card || document.createElement("article");
                if (!card) { const text = document.createElement("p"); text.textContent = "Ce favori n’est plus disponible : " + slug; holder.append(text); grid.append(holder); }
                const remove = document.createElement("button"); remove.type = "button"; remove.className = "button button-outline"; remove.textContent = "Retirer des favoris";
                remove.addEventListener("click", () => { writeStorage("wishlist_v1", read().filter(value => value !== slug)); render().then(() => { status.tabIndex = -1; status.focus(); }); });
                holder.append(remove);
            }
            prev.hidden = page === 0; next.hidden = (page + 1) * 8 >= all.length;
            status.textContent = "Page " + (page + 1) + " des favoris. " + data.found.length + " produit(s) disponible(s).";
        } catch (error) { if (current !== revision) return; status.textContent = "Impossible de charger les favoris. Votre liste est conservée ; réessayez."; retry.hidden = false; }
    }
    const focusStatus = () => { status.tabIndex = -1; status.focus(); };
    prev.addEventListener("click", () => { page--; render().then(focusStatus); }); next.addEventListener("click", () => { page++; render().then(focusStatus); }); retry.addEventListener("click", () => render().then(focusStatus));
    window.addEventListener("storage", event => { if (event.key === "wishlist_v1" || event.key === null) render(); }); render();
})();
