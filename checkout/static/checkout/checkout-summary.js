"use strict";

/* Le formulaire reste en place ; seuls les fragments calculés par Django changent. */
(() => {
    const form = document.querySelector("#checkout-form");
    if (!form) return;
    const layout = document.querySelector(".checkout-layout");
    const summary = document.querySelector(".checkout-summary");
    const content = document.querySelector("#checkout-summary-content");
    const status = document.querySelector("#checkout-update-status");
    const shippingStatus = document.querySelector("#shipping-status");
    const retry = document.querySelector("#checkout-retry");
    const errors = document.querySelector("#checkout-errors");
    const country = document.querySelector("#id_country");
    const postal = document.querySelector("#id_postal_code");
    const options = document.querySelector("#shipping-options");
    const pay = document.querySelector("#checkout-submit");
    const billingSame = document.querySelector("#id_billing_same_as_shipping");
    const billingFields = document.querySelector("#billing-fields");
    const mobile = window.matchMedia("(max-width: 820px)");
    const config = JSON.parse(document.querySelector("#commercial-config").textContent);
    const money = amount => new Intl.NumberFormat("fr-FR", { style: "currency", currency: config.currency }).format(Number(amount));
    let revision = 0;
    let quote = null;
    let controller = null;
    let updateQueue = Promise.resolve();
    let updating = false;
    let submitting = false;
    let cartPending = 0;
    let debounce;
    let destinationTouched = false;
    let preferredMethod = options.querySelector('input[name="shipping_method"]:checked')?.value || "";

    function placeSummary(wasOpen = false) {
        const details = document.querySelector("#checkout-summary-details");
        const title = document.querySelector("#summary-title");
        if (!details) return;
        if (mobile.matches) {
            layout.insertBefore(summary, form);
            details.open = wasOpen || Boolean(document.querySelector(".checkout-promo[open]"));
        } else {
            layout.append(summary);
            details.open = true;
        }
        const updateTitle = () => {
            title.textContent = title.textContent.replace(/^(Afficher|Masquer)/, details.open ? "Masquer" : "Afficher");
        };
        details.addEventListener("toggle", updateTitle);
        updateTitle();
    }
    placeSummary();
    mobile.addEventListener("change", () => placeSummary());

    function updateBilling() {
        billingFields.hidden = billingSame.checked;
        billingFields.querySelectorAll("input, select").forEach(field => {
            field.disabled = billingSame.checked;
            field.required = !billingSame.checked;
        });
    }
    billingSame.addEventListener("change", updateBilling);
    updateBilling();

    function updateControls() {
        pay.disabled = pay.dataset.serverDisabled === "true" || !quote || !quote.canPay || updating || submitting || cartPending > 0;
        form.setAttribute("aria-busy", String(updating || submitting));
        pay.classList.toggle("is-loading", submitting);
        document.querySelectorAll('[name="promo_action"]').forEach(button => { button.disabled = updating || submitting || cartPending > 0; });
    }

    function invalidate(message = "Estimation à recalculer.") {
        revision += 1;
        // Ne pas interrompre une mutation promo : elle pourrait déjà être appliquée côté serveur.
        if (controller && controller.readOnly) controller.abort();
        quote = null;
        clearTimeout(debounce);
        preferredMethod = options.querySelector('input[name="shipping_method"]:checked')?.value || preferredMethod;
        options.disabled = true;
        const legend = document.createElement("legend");
        legend.className = "visually-hidden"; legend.textContent = "Mode de livraison";
        options.replaceChildren(legend);
        for (const id of ["shipping-preview", "checkout-total-preview", "summary-amount"]) {
            const node = document.getElementById(id);
            if (node) node.textContent = "À recalculer";
        }
        shippingStatus.textContent = message;
        updateControls();
    }

    function fieldError(name, message) {
        const field = document.getElementById("id_" + name);
        if (!field) return;
        let node = document.getElementById(field.id + "_error");
        if (!node) {
            node = document.createElement("p");
            node.id = field.id + "_error";
            node.className = "checkout-field__error";
            field.insertAdjacentElement("afterend", node);
        }
        node.textContent = message;
        node.hidden = !message;
        field.setAttribute("aria-invalid", String(Boolean(message)));
        field.setAttribute("aria-describedby", node.id);
    }

    function showError(message, fieldErrors = {}, focus = false) {
        const list = document.createElement("ul");
        if (message) {
            const item = document.createElement("li"); item.textContent = message; list.append(item);
        }
        for (const name of ["country", "postal_code"]) {
            const text = (fieldErrors[name] || []).map(error => error.message).join(" ");
            fieldError(name, text);
            if (text) {
                const item = document.createElement("li"), link = document.createElement("a");
                link.href = "#id_" + name; link.textContent = text; item.append(link); list.append(item);
            }
        }
        const serverErrors = Array.from(errors.querySelectorAll("[data-server-error]"), node => node.cloneNode(true));
        list.prepend(...serverErrors);
        errors.replaceChildren(list);
        errors.hidden = list.children.length === 0;
        if (focus && !errors.hidden) errors.focus();
    }

    function updateTotals() {
        if (!quote) return;
        const selected = options.querySelector('input[name="shipping_method"]:checked');
        preferredMethod = selected?.value || preferredMethod;
        const option = selected && quote.options.find(item => item.method === selected.value);
        if (!option) { invalidate(); return; }
        document.querySelector("#shipping-preview").textContent = Number(option.amount) === 0 ? "Offerte" : money(option.amount);
        document.querySelector("#checkout-total-preview").textContent = money(option.total);
        document.querySelector("#summary-amount").textContent = money(option.total) + " TTC";
    }

    function renderOptions(data, previous) {
        const nodes = data.options.map((option, index) => {
            const label = document.createElement("label"), row = document.createElement("span");
            const input = document.createElement("input"), name = document.createElement("strong");
            label.className = "shipping-choice";
            input.type = "radio"; input.name = "shipping_method"; input.value = option.method;
            input.id = "shipping-" + option.method;
            input.required = true;
            input.checked = option.method === previous || (!data.options.some(item => item.method === previous) && index === 0);
            name.textContent = option.label;
            row.append(input, name); label.append(row); return label;
        });
        const legend = document.createElement("legend"); legend.className = "visually-hidden"; legend.textContent = "Mode de livraison";
        options.replaceChildren(legend, ...nodes);
        options.disabled = false;
        quote = { options: data.options, canPay: data.can_pay };
        updateTotals();
    }
    options.addEventListener("change", updateTotals);

    function destinationPresent() { return Boolean(country.value && postal.value.trim()); }

    function enqueueUpdate(action = "refresh") {
        const requestedRevision = revision;
        const operation = updateQueue.then(async () => {
            // Les seules actions modifiantes sont sérialisées, jamais abandonnées en vol.
            if (action === "refresh" && (requestedRevision !== revision || cartPending > 0)) return;
            const requestRevision = revision;
            const previous = preferredMethod;
            const body = new URLSearchParams({ country: country.value, postal_code: postal.value.trim(), shipping_method: previous });
            if (action !== "refresh") {
                body.set("promo_action", action);
                body.set("promo_code", document.querySelector("#checkout-promo-code").value);
            }
            const active = new AbortController();
            active.readOnly = action === "refresh";
            controller = active;
            updating = true; retry.hidden = true; status.textContent = "Actualisation de votre commande…"; updateControls();
            try {
                const response = await fetch(form.dataset.updateUrl, {
                    method: "POST", credentials: "same-origin", cache: "no-store", signal: active.signal,
                    headers: { "X-Checkout-Update": "1", "X-CSRFToken": form.elements.csrfmiddlewaretoken.value }, body,
                });
                const data = await response.json();
                if (!response.ok || typeof data.summary_html !== "string" || !Array.isArray(data.options)) throw new Error("update-failed");
                if (requestRevision !== revision) return;
                const wasOpen = Boolean(document.querySelector("#checkout-summary-details")?.open);
                const draft = document.querySelector("#checkout-promo-code");
                const draftValue = draft?.value || "";
                const draftFocused = draft === document.activeElement;
                const draftSelection = [draft?.selectionStart, draft?.selectionEnd];
                // Fragment exclusivement rendu et échappé par le template Django de cette origine.
                const template = document.createElement("template"); template.innerHTML = data.summary_html;
                content.replaceChildren(template.content.cloneNode(true));
                placeSummary(wasOpen);
                if (action === "refresh" || data.promo_error) {
                    const restored = document.querySelector("#checkout-promo-code");
                    restored.value = draftValue;
                    if (draftFocused && action === "refresh") {
                        restored.focus(); restored.setSelectionRange(...draftSelection);
                    }
                }
                if (data.quote_valid && data.options.length) {
                    renderOptions(data, previous);
                    shippingStatus.textContent = "Estimation actualisée pour la destination et le panier actuels.";
                    status.textContent = "Votre commande a été actualisée.";
                    showError(data.cart_error || data.promo_error || "", data.errors);
                } else {
                    invalidate("Renseignez une destination valide et vérifiez votre panier avant de payer.");
                    status.textContent = data.cart_error || "L’estimation de livraison n’est pas disponible.";
                    showError(data.cart_error || data.promo_error || "", destinationTouched || action !== "refresh" ? data.errors : {});
                }
                if (action !== "refresh") {
                    const promoStatus = document.querySelector("#checkout-promo-status");
                    promoStatus.tabIndex = -1;
                    promoStatus.focus();
                }
            } catch (error) {
                if (requestRevision !== revision || error.name === "AbortError") return;
                invalidate("Devis indisponible : aucun ancien tarif n’est confirmé.");
                status.textContent = "Actualisation impossible. Vos coordonnées sont conservées ; réessayez.";
                retry.hidden = false;
                showError(status.textContent, {}, action !== "refresh");
            } finally {
                if (controller === active) controller = null;
                updating = false; updateControls();
            }
        });
        updateQueue = operation.catch(() => {});
        return operation;
    }

    function destinationChanged() {
        destinationTouched = true;
        invalidate("Destination modifiée : estimation à recalculer.");
        if (destinationPresent()) debounce = setTimeout(() => enqueueUpdate(), 250);
        else status.textContent = "Renseignez votre pays et votre code postal pour obtenir une estimation.";
    }
    country.addEventListener("change", destinationChanged);
    postal.addEventListener("input", destinationChanged);
    retry.addEventListener("click", () => { invalidate(); enqueueUpdate(); });

    document.addEventListener("cart:changing", () => { cartPending += 1; invalidate("Panier en cours de modification…"); });
    document.addEventListener("cart:updated", () => { invalidate("Panier modifié : estimation à recalculer."); if (!cartPending) enqueueUpdate(); });
    document.addEventListener("cart:settled", () => { cartPending = Math.max(0, cartPending - 1); if (!cartPending) enqueueUpdate(); });

    document.addEventListener("keydown", event => {
        if (event.key !== "Enter" || event.target.id !== "checkout-promo-code") return;
        event.preventDefault();
        const apply = document.querySelector('[name="promo_action"][value="apply"]');
        if (apply && !apply.disabled) form.requestSubmit(apply);
    });
    form.addEventListener("input", event => {
        const name = event.target.name;
        if (!name) return;
        errors.querySelectorAll("[data-field-error]").forEach(node => {
            if (node.dataset.fieldError === name) node.remove();
        });
        if (!["country", "postal_code"].includes(name)) fieldError(name, "");
        if (!errors.querySelector("li")) errors.hidden = true;
    });
    form.addEventListener("submit", event => {
        if (submitting || updating || cartPending) { event.preventDefault(); return; }
        const action = event.submitter?.name === "promo_action" ? event.submitter.value : "";
        if (action) {
            event.preventDefault(); invalidate("Remise modifiée : estimation à recalculer.");
            updating = true; updateControls(); enqueueUpdate(action); return;
        }
        if (!quote || !quote.canPay || pay.dataset.serverDisabled === "true") {
            event.preventDefault(); showError("Actualisez le devis et vérifiez les informations avant de payer.", {}, true); return;
        }
        submitting = true; updateControls();
    });
    window.addEventListener("pageshow", () => { submitting = false; invalidate(); enqueueUpdate(); });
    window.addEventListener("pagehide", () => { invalidate(); });
    if (!errors.hidden) errors.focus();
    invalidate("Renseignez la destination pour obtenir une estimation à jour.");
    enqueueUpdate();
})();
