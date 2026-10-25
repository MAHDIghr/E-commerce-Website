(() => {
  "use strict";
  const form = document.getElementById("checkout-form");
  const button = document.getElementById("checkout-submit");
  if (!form || !button) return;
  form.addEventListener("submit", () => {
    if (!form.reportValidity()) return;
    button.disabled = true;
    button.classList.add("is-loading");
    const label = button.querySelector(".checkout-pay-label");
    if (label) label.textContent = "Vérification de la commande…";
  });
  const shipping = form.querySelectorAll('input[name="shipping_method"]');
  const preview = document.getElementById("shipping-preview");
  const subtotalText = document.querySelector(".checkout-totals div dd");
  const subtotal = subtotalText ? Number(subtotalText.textContent.replace(",", ".").replace(/[^\d.]/g, "")) : NaN;
  const updateShipping = () => {
    if (!preview) return;
    const selected = form.querySelector('input[name="shipping_method"]:checked');
    if (!selected || !Number.isFinite(subtotal)) { preview.textContent = "Calculée par le serveur"; return; }
    const threshold = Number(form.dataset.freeShippingThreshold || "80");
    const standard = Number(form.dataset.standardShipping || "4.90");
    const express = Number(form.dataset.expressShipping || "9.90");
    const price = subtotal >= threshold ? 0 : selected.value === "express" ? express : standard;
    preview.textContent = price === 0 ? "Offerte" : price.toLocaleString("fr-FR", {style:"currency", currency:"EUR"});
  };
  shipping.forEach((input) => input.addEventListener("change", updateShipping));
  updateShipping();
})();