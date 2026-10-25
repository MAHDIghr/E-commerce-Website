"use strict";

(() => {
  const form = document.getElementById("checkout-form");
  const button = document.getElementById("checkout-submit");
  if (!form || !button) return;
  const preview = document.getElementById("shipping-preview");
  const totalPreview = document.getElementById("checkout-total-preview");
  const subtotalCell = document.querySelector(".checkout-totals div dd");
  const subtotal = subtotalCell ? Number(subtotalCell.textContent.replace(",", ".").replace(/[^\\d.]/g, "")) : NaN;
  const formatEUR = (amount) => amount.toLocaleString("fr-FR", { style: "currency", currency: "EUR" });

  function updateShipping() {
    if (!preview) return;
    if (!Number.isFinite(subtotal)) {
      preview.textContent = "Calculée par le serveur";
      return;
    }
    if (form.dataset.freeShipping === "true") {
      preview.textContent = "Offerte";
      if (totalPreview) totalPreview.textContent = formatEUR(subtotal);
      return;
    }
    const selected = form.querySelector('input[name="shipping_method"]:checked');
    if (!selected) {
      preview.textContent = "Choisissez un mode de livraison";
      if (totalPreview) totalPreview.textContent = formatEUR(subtotal);
      return;
    }
    const standard = Number(form.dataset.standardShipping || "4.90");
    const express = Number(form.dataset.expressShipping || "9.90");
    const shipping = selected.value === "express" ? express : standard;
    preview.textContent = formatEUR(shipping);
    if (totalPreview) totalPreview.textContent = formatEUR(subtotal + shipping);
  }

  form.querySelectorAll('input[name="shipping_method"]').forEach((input) => input.addEventListener("change", updateShipping));
  updateShipping();
  form.addEventListener("submit", (event) => {
    if (!form.reportValidity()) {
      event.preventDefault();
      return;
    }
    button.disabled = true;
    button.classList.add("is-loading");
    const label = button.querySelector(".checkout-pay-label");
    if (label) label.textContent = "Vérification de la commande…";
  });
})();
