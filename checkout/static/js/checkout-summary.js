"use strict";

/* Résumé de commande progressif : affichage indicatif seulement.
   Les montants définitifs restent recalculés côté serveur avant Stripe. */
(() => {
    const form = document.querySelector("#checkout-form");
    if (!form) return;

    const subtotal = Number(form.dataset.discountedSubtotal || "0");
    const shippingPreview = document.querySelector("#shipping-preview");
    const totalPreview = document.querySelector("#checkout-total-preview");
    const money = (value) => new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(value);

    function selectedShipping() {
        const selected = form.querySelector('input[name="shipping_method"]:checked') || form.querySelector('select[name="shipping_method"]');
        return selected ? selected.value : (form.dataset.freeShipping === "true" ? "free" : "standard");
    }

    function updateSummary() {
        const method = selectedShipping();
        let shipping = 0;
        if (method === "standard") shipping = Number(form.dataset.standardShipping || "4.90");
        else if (method === "express") shipping = Number(form.dataset.expressShipping || "9.90");

        if (shippingPreview) shippingPreview.textContent = shipping === 0 ? "Offerte" : money(shipping);
        if (totalPreview) totalPreview.textContent = money(subtotal + shipping);
    }

    form.querySelectorAll('[name="shipping_method"]').forEach((input) => {
        input.addEventListener("change", updateSummary);
    });
    updateSummary();
})();
