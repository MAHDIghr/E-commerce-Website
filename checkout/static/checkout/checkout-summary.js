"use strict";

/* Résumé de commande progressif : affichage indicatif seulement.
   Les montants définitifs restent recalculés côté serveur avant Stripe. */
(() => {
    const form = document.querySelector("#checkout-form");
    if (!form) return;
    const config = JSON.parse(document.querySelector("#commercial-config").textContent);

    const subtotal = Number(form.dataset.discountedSubtotal || "0");
    const shippingPreview = document.querySelector("#shipping-preview");
    const totalPreview = document.querySelector("#checkout-total-preview");
    const money = (value) => new Intl.NumberFormat("fr-FR", { style: "currency", currency: config.currency }).format(value);

    function selectedShipping() {
        const selected = form.querySelector('input[name="shipping_method"]:checked') || form.querySelector('select[name="shipping_method"]');
        return selected ? selected.value : (form.dataset.freeShipping === "true" ? "free" : "standard");
    }

    function updateSummary() {
        const method = selectedShipping();
        let shipping = 0;
        if (method === "standard") shipping = Number(config.standard_shipping);
        else if (method === "express") shipping = Number(config.express_shipping);

        if (!Number.isFinite(subtotal) || !Number.isFinite(shipping)) return;
        const totalLabel = document.querySelector("#checkout-total-label");
        if (totalLabel) totalLabel.textContent = "Total estimé, livraison incluse";
        if (shippingPreview) shippingPreview.textContent = shipping === 0 ? "Offerte" : money(shipping);
        if (totalPreview) totalPreview.textContent = money(subtotal + shipping);
    }

    form.querySelectorAll('[name="shipping_method"]').forEach((input) => {
        input.addEventListener("change", updateSummary);
    });
    updateSummary();
})();
