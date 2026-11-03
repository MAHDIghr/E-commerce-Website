"use strict";

/* Devis et totaux d'affichage renvoyés par Django ; Stripe confirme le montant final. */
(() => {
    const form = document.querySelector("#checkout-form");
    if (!form) return;

    const layout = document.querySelector(".checkout-layout");
    const summary = document.querySelector(".checkout-summary");
    const details = document.querySelector("#checkout-summary-details");
    const summaryTitle = document.querySelector("#summary-title");
    const mobile = window.matchMedia("(max-width: 820px)");
    function updateSummaryTitle() {
        summaryTitle.textContent = summaryTitle.textContent.replace(/^(Afficher|Masquer)/, details.open ? "Masquer" : "Afficher");
    }
    function placeSummary() {
        if (mobile.matches) {
            layout.insertBefore(summary, form);
            // Une promotion appliquée ou un résultat ne doit pas être masqué sur mobile.
            const promoDetails = document.querySelector(".checkout-promo");
            details.open = Boolean(promoDetails && promoDetails.open);
        } else {
            layout.append(summary);
            details.open = true;
        }
    }
    placeSummary();
    mobile.addEventListener("change", placeSummary);
    details.addEventListener("toggle", updateSummaryTitle);
    updateSummaryTitle();

    const billingSame = document.querySelector("#id_billing_same_as_shipping");
    const billingFields = document.querySelector("#billing-fields");
    function updateBilling() {
        billingFields.hidden = billingSame.checked;
        billingFields.querySelectorAll("input, select").forEach((field) => {
            field.disabled = billingSame.checked;
            field.required = !billingSame.checked;
        });
    }
    billingSame.addEventListener("change", updateBilling);
    updateBilling();

    const country = document.querySelector("#id_country");
    const postal = document.querySelector("#id_postal_code");
    const options = document.querySelector("#shipping-options");
    const status = document.querySelector("#shipping-status");
    const shippingPreview = document.querySelector("#shipping-preview");
    const totalPreview = document.querySelector("#checkout-total-preview");
    const summaryAmount = document.querySelector("#summary-amount");
    const currency = JSON.parse(document.querySelector("#commercial-config").textContent).currency;
    const money = (amount) => new Intl.NumberFormat("fr-FR", { style: "currency", currency }).format(Number(amount));
    let quote = null;
    let controller = null;
    let debounce;

    function updateTotals() {
        const selected = options.querySelector('input[name="shipping_method"]:checked');
        const selectedQuote = quote && quote.options.find((option) => option.method === (selected && selected.value));
        if (!selectedQuote) return;
        shippingPreview.textContent = Number(selectedQuote.amount) === 0 ? "Offerte" : money(selectedQuote.amount);
        totalPreview.textContent = money(selectedQuote.total);
        summaryAmount.textContent = money(selectedQuote.total) + " TTC";
    }

    function renderOptions(data) {
        const previous = options.querySelector('input[name="shipping_method"]:checked');
        const previousValue = previous && previous.value;
        const nodes = data.options.map((option) => {
            const label = document.createElement("label");
            label.className = "shipping-choice";
            const row = document.createElement("span");
            const input = document.createElement("input");
            input.type = "radio";
            input.name = "shipping_method";
            input.value = option.method;
            input.required = true;
            input.checked = option.method === previousValue || (!data.options.some((item) => item.method === previousValue) && option === data.options[0]);
            input.addEventListener("change", updateTotals);
            const name = document.createElement("strong");
            name.textContent = option.label;
            row.append(input, name);
            label.append(row);
            return label;
        });
        quote = data;
        options.replaceChildren(...nodes);
        status.textContent = "Modes et frais confirmés pour le panier actuel.";
        updateTotals();
    }

    async function requestQuote() {
        if (controller) controller.abort();
        if (!country.value || !postal.value.trim()) {
            quote = null;
            status.textContent = "Renseignez votre pays et votre code postal pour confirmer les modes disponibles.";
            return;
        }
        controller = new AbortController();
        status.textContent = "Calcul des frais de livraison…";
        try {
            const url = new URL(form.dataset.quoteUrl, window.location.href);
            url.searchParams.set("country", country.value);
            url.searchParams.set("postal_code", postal.value.trim());
            const response = await fetch(url, { credentials: "same-origin", signal: controller.signal });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || "Devis indisponible.");
            renderOptions(data);
        } catch (error) {
            if (error.name !== "AbortError") status.textContent = "Frais indisponibles. Actualisez la page avant de payer.";
        }
    }
    options.querySelectorAll('input[name="shipping_method"]').forEach((input) => input.addEventListener("change", updateTotals));
    country.addEventListener("change", requestQuote);
    postal.addEventListener("input", () => { clearTimeout(debounce); debounce = setTimeout(requestQuote, 250); });
    if (postal.value.trim()) requestQuote();

    /* Les modifications du panier latéral déclenchent une nouvelle validation serveur. */
    Promise.resolve(typeof cartReady !== "undefined" ? cartReady : null).then(() => {
        document.addEventListener("cart:updated", () => window.location.reload());
    });
})();
