"use strict";

(() => {
    const root = document.querySelector("#cart-page");
    if (!root) return;

    const list = document.querySelector("#cart-page-items");
    const empty = document.querySelector("#cart-page-empty");
    const content = document.querySelector("#cart-page-content");
    const subtotalNode = document.querySelector("#cart-page-subtotal");
    const statusNode = document.querySelector("#cart-page-status");
    const checkoutButton = document.querySelector("#cart-page-checkout");
    const cartUrl = root.dataset.cartUrl;
    const mutationUrl = root.dataset.cartMutationUrl;
    const checkoutUrl = root.dataset.checkoutUrl;
    const catalogUrl = root.dataset.catalogUrl;

    const money = (value) => `${Number(value || 0).toFixed(2).replace(".", ",")} €`;
    const csrfToken = () => {
        const match = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/);
        return match ? decodeURIComponent(match[1]) : "";
    };
    const showStatus = (message, isError = true) => {
        statusNode.textContent = message || "";
        statusNode.hidden = !message;
        statusNode.dataset.error = String(isError);
    };
    async function request(url, method = "GET", payload = null) {
        const options = { method, credentials: "same-origin", headers: { Accept: "application/json" } };
        if (payload) {
            options.headers["Content-Type"] = "application/json";
            options.headers["X-CSRFToken"] = csrfToken();
            options.body = JSON.stringify(payload);
        }
        const response = await fetch(url, options);
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error || "Impossible de mettre à jour le panier.");
        return data;
    }
    function makeButton(text, action, label, disabled = false) {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = text;
        button.dataset.cartAction = action;
        button.setAttribute("aria-label", label);
        button.disabled = disabled;
        return button;
    }
    function renderItem(item) {
        const row = document.createElement("li");
        row.className = "cart-page-item";
        row.dataset.key = item.key;

        const imageLink = document.createElement("a");
        imageLink.className = "cart-page-item__image";
        imageLink.href = typeof item.product_slug === "string" && item.product_slug
            ? `/produit/${encodeURIComponent(item.product_slug)}/` : catalogUrl;
        if (item.image) {
            const image = document.createElement("img");
            image.src = item.image;
            image.alt = "";
            image.loading = "lazy";
            image.decoding = "async";
            imageLink.appendChild(image);
        }

        const details = document.createElement("div");
        details.className = "cart-page-item__details";
        const name = document.createElement("a");
        name.className = "cart-page-item__name";
        name.href = imageLink.href;
        name.textContent = item.name;
        details.appendChild(name);

        if (item.variant_name) {
            const variant = document.createElement("p");
            variant.className = "cart-page-item__variant";
            variant.textContent = item.variant_name;
            details.appendChild(variant);
        }
        if (Array.isArray(item.components)) {
            item.components.forEach((component) => {
                const note = document.createElement("p");
                note.className = "cart-page-item__component";
                note.textContent = `Inclus et offert : ${component.name}${component.variant_name ? ` — ${component.variant_name}` : ""}`;
                details.appendChild(note);
            });
        }

        const controls = document.createElement("div");
        controls.className = "cart-page-item__controls";
        controls.append(
            makeButton("−", "decrease", `Diminuer la quantité de ${item.name}`, false)
        );
        const quantity = document.createElement("span");
        quantity.className = "cart-page-item__quantity";
        quantity.textContent = String(item.quantity);
        controls.appendChild(quantity);
        controls.append(
            makeButton("+", "increase", `Augmenter la quantité de ${item.name}`,
                !item.available || item.quantity >= item.available_quantity)
        );
        const remove = makeButton("Retirer", "remove", `Retirer ${item.name} du panier`);
        remove.className = "cart-page-item__remove";
        controls.appendChild(remove);
        details.appendChild(controls);

        if (!item.available) {
            const warning = document.createElement("p");
            warning.className = "cart-page-item__warning";
            warning.textContent = item.available_quantity > 0
                ? "Stock insuffisant : réduisez la quantité."
                : "Article indisponible : retirez-le pour continuer.";
            details.appendChild(warning);
        }

        const total = document.createElement("strong");
        total.className = "cart-page-item__total";
        total.textContent = money(item.line_total);
        row.append(imageLink, details, total);
        return row;
    }
    function render(data) {
        list.replaceChildren();
        const items = Array.isArray(data.items) ? data.items : [];
        items.forEach((item) => list.appendChild(renderItem(item)));
        const isEmpty = items.length === 0;
        empty.hidden = !isEmpty;
        content.hidden = isEmpty;
        subtotalNode.textContent = money(data.subtotal);
        checkoutButton.disabled = isEmpty || items.some((item) => !item.available);
        checkoutButton.setAttribute("aria-disabled", String(checkoutButton.disabled));
    }
    async function refresh() {
        try {
            render(await request(cartUrl));
        } catch (error) {
            showStatus(error.message || "Le panier est momentanément indisponible.");
        }
    }
    async function mutate(payload, button) {
        if (button) button.disabled = true;
        showStatus("");
        try {
            render(await request(mutationUrl, "POST", payload));
        } catch (error) {
            showStatus(error.message || "Le panier n'a pas pu être mis à jour.");
            await refresh();
        } finally {
            if (button && button.isConnected) button.disabled = false;
        }
    }

    list.addEventListener("click", (event) => {
        const button = event.target instanceof Element ? event.target.closest("button[data-cart-action]") : null;
        const row = button && button.closest("[data-key]");
        if (!button || !row || button.disabled) return;
        const parts = row.dataset.key.split(":");
        const variantId = Number(parts[0]);
        const offerId = Number(parts[1] || 0);
        const selectedItemIds = parts[2] ? parts[2].split(",").map(Number) : [];
        if (!Number.isSafeInteger(variantId) || variantId < 1 || !Number.isSafeInteger(offerId) || offerId < 0) {
            showStatus("Cette ligne du panier est invalide. Actualisez la page.");
            return;
        }
        const quantityNode = row.querySelector(".cart-page-item__quantity");
        const quantity = Number(quantityNode && quantityNode.textContent);
        const action = button.dataset.cartAction;
        if (action === "remove") {
            mutate({ action: "remove", variant_id: variantId, offer_id: offerId, selected_item_ids: selectedItemIds }, button);
        } else if (action === "increase" || action === "decrease") {
            const next = quantity + (action === "increase" ? 1 : -1);
            if (!Number.isSafeInteger(next) || next < 1) {
                mutate({ action: "remove", variant_id: variantId, offer_id: offerId, selected_item_ids: selectedItemIds }, button);
            } else {
                mutate({ action: "update", variant_id: variantId, offer_id: offerId, selected_item_ids: selectedItemIds, quantity: next }, button);
            }
        }
    });
    checkoutButton.addEventListener("click", () => {
        if (checkoutButton.disabled) {
            showStatus("Vérifiez la disponibilité des articles avant de passer commande.");
            return;
        }
        window.location.assign(checkoutUrl);
    });
    refresh();
})();
