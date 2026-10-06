"use strict";

/* ==========================================================================
   checkout.js — page de paiement (FRONT-END UNIQUEMENT).

   Dépend de base.js (chargé avant) pour : getCart() (panier localStorage),
   tiroir panier et pastille. Tout est dans une IIFE pour ne pas entrer en
   collision avec les `const` globaux de base.js.

   Points de branchement backend (tous marqués "MOCK" / "TODO") :
     - CheckoutData      : source des articles (serveur à la place du mock)
     - ShippingService   : modes de livraison et prix
     - PromoService      : validation d'un code promo
     - AddressService    : autocomplétion d'adresse
     - getTotals()       : totaux (state.serverTotals les remplace)
     - submitCheckout()  : création Order / Payment / Stripe

   AUCUNE donnée de carte n'est lue, stockée ou envoyée ici : la zone carte
   est une maquette sans <input>, destinée à Stripe Payment Element.
   ========================================================================== */

(function () {

    /* ---------- Helpers ---------- */
    const $ = (selector, root = document) => root.querySelector(selector);
    const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
    const wait = (ms) => new Promise((resolve) => window.setTimeout(resolve, ms));
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    function el(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    }

    function normalize(text) {
        return String(text).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
    }

    /* ---------- État ---------- */
    const state = {
        data: null,
        items: [],
        isMock: false,
        promo: { status: "idle", code: "" },
        shipping: { methods: [], selectedId: null },
        serverTotals: null,            // TODO: renseigné par le backend (remplace getTotals)
        submitting: false,
    };

    let moneyFormatter = null;
    function formatMoney(amount) {
        return moneyFormatter.format(amount);
    }

    /* ==========================================================================
       Données : serveur (json_script) + panier localStorage
       ========================================================================== */

    function readServerData() {
        const node = $("#checkout-data");
        try {
            return JSON.parse(node ? node.textContent : "{}");
        } catch (error) {
            return {};
        }
    }

    function safeImageUrl(value) {
        try {
            const url = new URL(String(value), window.location.href);
            return url.protocol === "https:" || url.protocol === "http:" ? url.href : "";
        } catch (error) {
            return "";
        }
    }

    /* Articles du panier existant (base.js). Le panier est une donnée
       utilisateur : on ne fait confiance à aucun champ. */
    function readCartItems() {
        if (typeof getCart !== "function") return [];
        return getCart()
            .filter((item) => item && typeof item.name === "string"
                && Number.isFinite(Number(item.price)) && Number(item.price) >= 0
                && Number.isInteger(Number(item.qty)) && Number(item.qty) > 0)
            .map((item) => ({
                id: String(item.id),
                name: item.name,
                variant: "",
                image: safeImageUrl(item.image),
                quantity: Number(item.qty),
                unitPrice: Number(item.price),
            }));
    }

    /* Panier réel s'il existe, sinon articles de démonstration. */
    function resolveItems() {
        const cartItems = readCartItems();
        if (cartItems.length > 0) {
            state.items = cartItems;
            state.isMock = false;
        } else {
            state.items = Array.isArray(state.data.items) ? state.data.items : [];
            state.isMock = Boolean(state.data.isMock);
        }
    }

    /* ==========================================================================
       Totaux — MOCK : à remplacer par les montants calculés côté serveur.
       Quand le backend fournira les totaux : state.serverTotals = {...}.
       ========================================================================== */

    function getSelectedShipping() {
        return state.shipping.methods.find((m) => m.id === state.shipping.selectedId) || null;
    }

    function getTotals() {
        if (state.serverTotals) return state.serverTotals;

        const subtotalCents = state.items.reduce(
            (sum, item) => sum + Math.round(item.unitPrice * 100) * item.quantity, 0);
        const method = getSelectedShipping();
        const shippingCents = method ? Math.round(method.price * 100) : null;

        return {
            subtotal: subtotalCents / 100,
            shipping: shippingCents === null ? null : shippingCents / 100,
            total: (subtotalCents + (shippingCents || 0)) / 100,
        };
    }

    /* ==========================================================================
       Services mockés (remplaçables par des appels fetch() vers Django)
       ========================================================================== */

    const MOCK_PROMO_CODES = ["BIENVENUE10"];

    const PromoService = {
        /* TODO backend : POST /commande/promo/ → { valid, message, totals } */
        async apply(code) {
            await wait(700);
            const valid = MOCK_PROMO_CODES.includes(code.trim().toUpperCase());
            return valid
                ? { valid: true, code: code.trim().toUpperCase(), message: "Code appliqué ✓", totals: null }
                : { valid: false, message: "Code promo invalide ou expiré." };
        },
    };

    const ShippingService = {
        /* TODO backend : prix et délais selon adresse, poids, promotions. */
        async quote(address, subtotal) {
            await wait(150);
            const threshold = Number(state.data.freeShippingThreshold) || 0;
            return (state.data.shippingMethods || []).map((method) => ({
                ...method,
                price: method.id === "standard" && threshold > 0 && subtotal >= threshold ? 0 : method.price,
            }));
        },
    };

    const MOCK_ADDRESSES = [
        { label: "12 Rue de Paris, 78000 Versailles", number: "12", street: "Rue de Paris", postalCode: "78000", city: "Versailles", country: "FR" },
        { label: "12 Rue de Paris, 75001 Paris", number: "12", street: "Rue de Paris", postalCode: "75001", city: "Paris", country: "FR" },
        { label: "12 Rue de Paris, 92100 Boulogne-Billancourt", number: "12", street: "Rue de Paris", postalCode: "92100", city: "Boulogne-Billancourt", country: "FR" },
        { label: "8 Rue de la Paix, 75002 Paris", number: "8", street: "Rue de la Paix", postalCode: "75002", city: "Paris", country: "FR" },
        { label: "25 Avenue Jean Jaurès, 69007 Lyon", number: "25", street: "Avenue Jean Jaurès", postalCode: "69007", city: "Lyon", country: "FR" },
        { label: "7 Place Bellecour, 69002 Lyon", number: "7", street: "Place Bellecour", postalCode: "69002", city: "Lyon", country: "FR" },
        { label: "3 Rue Sainte-Catherine, 33000 Bordeaux", number: "3", street: "Rue Sainte-Catherine", postalCode: "33000", city: "Bordeaux", country: "FR" },
        { label: "18 Rue de la République, 13001 Marseille", number: "18", street: "Rue de la République", postalCode: "13001", city: "Marseille", country: "FR" },
    ];

    /* Contrat prévu pour l'API réelle : search(query) → [{ label, number, street, postalCode, city, country }] */
    const AddressService = {
        async search(query) {
            await wait(150);
            const tokens = normalize(query).split(/\s+/).filter(Boolean);
            return MOCK_ADDRESSES
                .filter((a) => tokens.every((token) => normalize(a.label).includes(token)))
                .slice(0, 5);
        },
    };

    /* ==========================================================================
       Résumé de la commande (colonne + résumé compact)
       ========================================================================== */

    function renderSummary() {
        const totals = getTotals();

        /* Articles */
        const list = $("#summary-items");
        list.replaceChildren();
        state.items.forEach((item) => {
            const row = el("li", "co-item");

            const image = document.createElement("img");
            image.className = "co-item__img";
            image.alt = "";
            image.width = 64;
            image.height = 80;
            image.loading = "lazy";
            if (item.image) image.src = item.image;

            const info = el("div");
            info.appendChild(el("p", "co-item__name", item.name));
            if (item.variant) info.appendChild(el("p", "co-item__meta", item.variant));
            info.appendChild(el("p", "co-item__meta", `× ${item.quantity}`));

            const linePrice = Math.round(item.unitPrice * 100) * item.quantity / 100;
            row.append(image, info, el("p", "co-item__price", formatMoney(linePrice)));
            list.appendChild(row);
        });

        $("#mock-note").hidden = !state.isMock;

        /* Totaux */
        const hasShipping = totals.shipping !== null && totals.shipping !== undefined;
        $("#t-subtotal").textContent = formatMoney(totals.subtotal);
        $("#t-shipping").textContent = hasShipping
            ? (totals.shipping === 0 ? "Gratuite" : formatMoney(totals.shipping))
            : "Calculée à l'étape suivante";
        $("#t-total").textContent = formatMoney(totals.total);
        $("#t-currency").textContent = state.data.currency || "";
        $("#t-note").textContent = hasShipping ? "" : "(hors livraison)";

        /* Résumé compact avant validation */
        $("#review-total").textContent = formatMoney(totals.total);
        const lines = $("#review-lines");
        lines.replaceChildren();
        const addLine = (label, value, modifier) => {
            const row = el("div", "co-review__row" + (modifier ? ` co-review__row--${modifier}` : ""));
            row.append(el("dt", "", label), el("dd", "", value));
            lines.appendChild(row);
        };
        state.items.forEach((item) => {
            addLine(`${item.name} × ${item.quantity}`,
                formatMoney(Math.round(item.unitPrice * 100) * item.quantity / 100));
        });
        addLine("Sous-total", formatMoney(totals.subtotal));
        addLine("Livraison", hasShipping ? (totals.shipping === 0 ? "Gratuite" : formatMoney(totals.shipping)) : "—");
        addLine("Total", formatMoney(totals.total), "total");
    }

    function initOrderSummary() {
        const toggle = $("#review-toggle");
        const body = $("#review-body");
        if (!toggle || !body) return;

        toggle.addEventListener("click", () => {
            const open = toggle.getAttribute("aria-expanded") !== "true";
            toggle.setAttribute("aria-expanded", String(open));
            body.inert = !open;
        });

        /* Le panier peut changer via le tiroir (quantité, suppression). */
        document.addEventListener("cart:updated", () => {
            resolveItems();
            renderSummary();
            updateSubmitAvailability();
        });
    }

    /* ==========================================================================
       Code promo (simulé — ne recalcule JAMAIS le prix côté front)
       ========================================================================== */

    function initPromoCode() {
        const form = $("#promo-form");
        const input = $("#promo-code");
        const button = $("#promo-btn");
        const label = $(".co-promo__btn-label", form);
        const message = $("#promo-message");

        function setState(status, text) {
            state.promo.status = status;
            form.dataset.state = status;
            message.textContent = text || "";
            input.readOnly = status === "success";
            label.textContent = status === "success" ? "Retirer" : "Appliquer";
        }

        form.addEventListener("submit", async (event) => {
            event.preventDefault();

            if (state.promo.status === "loading") return;

            if (state.promo.status === "success") {
                state.promo.code = "";
                input.value = "";
                setState("idle", "");
                state.serverTotals = null;   // TODO: redemander les totaux au serveur
                renderSummary();
                return;
            }

            const code = input.value.trim();
            if (!code) {
                setState("error", "Saisissez un code promo.");
                input.focus();
                return;
            }

            setState("loading", "Vérification du code…");
            button.setAttribute("aria-busy", "true");

            try {
                const result = await PromoService.apply(code);
                if (result.valid) {
                    state.promo.code = result.code;
                    input.value = result.code;
                    setState("success", `${result.message} La réduction sera confirmée dans le total final.`);
                    /* TODO backend : if (result.totals) { state.serverTotals = result.totals; renderSummary(); } */
                } else {
                    setState("error", result.message);
                }
            } catch (error) {
                setState("error", "Impossible de vérifier le code pour le moment. Réessayez.");
            } finally {
                button.removeAttribute("aria-busy");
            }
        });

        input.addEventListener("input", () => {
            if (state.promo.status === "error") setState("idle", "");
        });
    }

    /* ==========================================================================
       Champs du formulaire : lecture, erreurs, validation
       ========================================================================== */

    const form = () => $("#checkout-form");
    const field = (name) => $(`#${name}`);
    const value = (name) => (field(name) ? field(name).value.trim() : "");

    const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

    const validators = {
        email: (v) => (!v ? "Saisissez votre adresse e-mail."
            : !EMAIL_PATTERN.test(v) ? "Cette adresse e-mail semble incomplète (exemple : nom@exemple.fr)." : ""),
        lastName: (v) => (v ? "" : "Saisissez votre nom."),
        country: (v) => (v ? "" : "Sélectionnez votre pays."),
        street: (v) => (v ? "" : "Saisissez le nom de votre rue."),
        postalCode: (v) => {
            if (!v) return "Saisissez votre code postal.";
            if (value("country") === "FR" && !/^\d{5}$/.test(v)) return "Un code postal français comporte 5 chiffres.";
            return "";
        },
        city: (v) => (v ? "" : "Saisissez votre ville."),
    };

    function setFieldError(name, message) {
        const input = field(name);
        const error = $(`#${name}-error`);
        if (!input || !error) return;
        if (message) {
            input.setAttribute("aria-invalid", "true");
            error.textContent = message;
            error.hidden = false;
        } else {
            input.removeAttribute("aria-invalid");
            error.textContent = "";
            error.hidden = true;
        }
    }

    function validateField(name) {
        const message = validators[name](value(name));
        setFieldError(name, message);
        return !message;
    }

    function initFormValidation() {
        const checkout = form();

        Object.keys(validators).forEach((name) => {
            const input = field(name);
            if (!input) return;
            /* Validation à la sortie du champ, puis en direct une fois corrigé. */
            input.addEventListener("blur", () => { if (input.value !== "" || input.hasAttribute("aria-invalid")) validateField(name); });
            input.addEventListener("input", () => { if (input.hasAttribute("aria-invalid")) validateField(name); });
            input.addEventListener("change", () => { if (input.hasAttribute("aria-invalid")) validateField(name); });
        });

        checkout.addEventListener("submit", async (event) => {
            event.preventDefault();
            if (state.submitting) return;

            const invalid = validateAll();
            if (invalid.length > 0) {
                showStatus("error", invalid.length === 1
                    ? "Un champ est à corriger avant de continuer."
                    : `${invalid.length} champs sont à corriger avant de continuer.`);
                const first = invalid[0];
                if (first) first.focus();
                return;
            }
            hideStatus();

            setSubmitting(true);
            try {
                const result = await submitCheckout(buildOrderPayload());
                if (result.ok) {
                    showStatus("info", result.message);
                    $("#form-status").focus();
                }
            } catch (error) {
                showStatus("error", "Une erreur est survenue. Vos informations ont été conservées, vous pouvez réessayer.");
            } finally {
                setSubmitting(false);
            }
        });
    }

    /* Retourne la liste des éléments invalides (dans l'ordre de la page). */
    function validateAll() {
        const invalid = [];
        ["email", "lastName", "country", "street", "postalCode", "city"].forEach((name) => {
            if (!validateField(name)) invalid.push(field(name));
        });

        const shippingVisible = !$("#shipping-section").hidden;
        const shippingError = $("#shipping-error");
        if (!state.shipping.selectedId) {
            shippingError.textContent = shippingVisible
                ? "Choisissez un mode de livraison."
                : "Complétez votre adresse pour choisir un mode de livraison.";
            shippingError.hidden = false;
            const firstRadio = $('input[name="shipping"]');
            if (shippingVisible) invalid.push(firstRadio);
            else invalid.push(field("street"));
        } else {
            shippingError.hidden = true;
        }

        const paymentError = $("#payment-error");
        if (!$('input[name="payment"]:checked')) {
            paymentError.textContent = "Choisissez un moyen de paiement.";
            paymentError.hidden = false;
            invalid.push($('input[name="payment"]'));
        } else {
            paymentError.hidden = true;
        }

        return invalid.filter(Boolean);
    }

    function showStatus(kind, text) {
        const status = $("#form-status");
        status.dataset.kind = kind;
        status.textContent = text;
        status.hidden = false;
    }

    function hideStatus() {
        const status = $("#form-status");
        status.hidden = true;
        status.textContent = "";
    }

    /* ==========================================================================
       Bouton final : état chargement / désactivé, payload prêt pour le backend
       ========================================================================== */

    function setSubmitting(isLoading) {
        state.submitting = isLoading;
        const button = $("#submit-btn");
        button.dataset.loading = String(isLoading);
        button.setAttribute("aria-busy", String(isLoading));
        button.disabled = isLoading || state.items.length === 0;
        $(".co-submit__label", button).textContent = isLoading ? "Vérification…" : "Vérifier la commande";
    }

    function updateSubmitAvailability() {
        $("#submit-btn").disabled = state.submitting || state.items.length === 0;
    }

    /* Données destinées au backend. Aucune donnée de carte : elle sera
       gérée uniquement par Stripe Payment Element. */
    function buildOrderPayload() {
        return {
            contact: { email: value("email") },
            shippingAddress: {
                lastName: value("lastName"),
                firstName: value("firstName"),
                country: value("country"),
                number: value("number"),
                street: value("street"),
                complement: value("complement"),
                postalCode: value("postalCode"),
                city: value("city"),
                phone: value("phone"),
            },
            shippingMethodId: state.shipping.selectedId,
            paymentMethod: ($('input[name="payment"]:checked') || {}).value || null,
            promoCode: state.promo.status === "success" ? state.promo.code : null,
            items: state.items.map((item) => ({ id: item.id, quantity: item.quantity })),
        };
    }

    /* TODO backend (étape 2) : POST payload → création Order → Payment →
       Stripe PaymentIntent → confirmation via Payment Element. */
    async function submitCheckout(payload) {
        await wait(1100);
        return {
            ok: true,
            message: "Aperçu : vos informations sont valides. La création de la commande et le paiement seront branchés à l'étape suivante — rien n'a été envoyé ni débité.",
        };
    }

    /* ==========================================================================
       Recherche d'adresse (combobox) — searchAddress / selectAddress / fillAddressFields
       ========================================================================== */

    function searchAddress(query) {
        return AddressService.search(query);
    }

    function fillAddressFields(address) {
        const map = { number: address.number, street: address.street, postalCode: address.postalCode, city: address.city };
        if (address.country && $(`#country option[value="${address.country}"]`)) {
            field("country").value = address.country;
            syncPostalCodeHints();
        }
        Object.entries(map).forEach(([name, val]) => {
            if (field(name)) field(name).value = val || "";
            if (validators[name]) setFieldError(name, "");
        });
        setFieldError("country", "");
        updateShippingVisibility();
    }

    function selectAddress(address) {
        fillAddressFields(address);
        $("#address-search").value = address.label;
        $("#address-live").textContent = `Adresse sélectionnée : ${address.label}`;
        field("complement").focus();
    }

    function initAddressSearch() {
        const input = $("#address-search");
        const list = $("#address-listbox");
        let results = [];
        let active = -1;
        let sequence = 0;
        let timer = null;

        function close() {
            list.hidden = true;
            input.setAttribute("aria-expanded", "false");
            input.removeAttribute("aria-activedescendant");
            active = -1;
        }

        function setActive(index) {
            const options = $$('[role="option"]:not([aria-disabled="true"])', list);
            if (options.length === 0) return;
            active = (index + options.length) % options.length;
            options.forEach((option, i) => option.setAttribute("aria-selected", String(i === active)));
            input.setAttribute("aria-activedescendant", options[active].id);
            options[active].scrollIntoView({ block: "nearest" });
        }

        function highlight(label, query) {
            const fragment = document.createDocumentFragment();
            const tokens = normalize(query).split(/\s+/).filter(Boolean);
            const normalized = normalize(label);
            const marks = new Array(label.length).fill(false);
            tokens.forEach((token) => {
                let from = 0;
                let index;
                while ((index = normalized.indexOf(token, from)) !== -1) {
                    for (let i = index; i < index + token.length; i += 1) marks[i] = true;
                    from = index + token.length;
                }
            });
            let buffer = "";
            let current = false;
            const flush = () => {
                if (!buffer) return;
                fragment.appendChild(current ? el("mark", "", buffer) : document.createTextNode(buffer));
                buffer = "";
            };
            Array.from(label).forEach((char, i) => {
                if (marks[i] !== current) { flush(); current = marks[i]; }
                buffer += char;
            });
            flush();
            return fragment;
        }

        function render(query) {
            list.replaceChildren();
            if (results.length === 0) {
                const empty = el("li", "", "Aucune suggestion. Remplissez les champs ci-dessous.");
                empty.setAttribute("role", "option");
                empty.setAttribute("aria-disabled", "true");
                empty.id = "address-option-empty";
                list.appendChild(empty);
                $("#address-live").textContent = "Aucune suggestion.";
            } else {
                results.forEach((address, i) => {
                    const option = el("li");
                    option.id = `address-option-${i}`;
                    option.setAttribute("role", "option");
                    option.setAttribute("aria-selected", "false");
                    option.appendChild(highlight(address.label, query));
                    /* mousedown : évite que le blur du champ ferme la liste avant le clic */
                    option.addEventListener("mousedown", (event) => event.preventDefault());
                    option.addEventListener("click", () => { selectAddress(address); close(); });
                    list.appendChild(option);
                });
                $("#address-live").textContent = `${results.length} suggestion${results.length > 1 ? "s" : ""} disponible${results.length > 1 ? "s" : ""}.`;
            }
            list.hidden = false;
            input.setAttribute("aria-expanded", "true");
            active = -1;
        }

        input.addEventListener("input", () => {
            window.clearTimeout(timer);
            const query = input.value.trim();
            if (query.length < 3) { close(); return; }

            timer = window.setTimeout(async () => {
                const mine = ++sequence;
                try {
                    const found = await searchAddress(query);
                    if (mine !== sequence) return;   // réponse périmée
                    results = found;
                    render(query);
                } catch (error) {
                    close();
                }
            }, 250);
        });

        input.addEventListener("keydown", (event) => {
            const isOpen = !list.hidden;
            if (event.key === "ArrowDown") { event.preventDefault(); if (isOpen) setActive(active + 1); }
            else if (event.key === "ArrowUp") { event.preventDefault(); if (isOpen) setActive(active - 1); }
            else if (event.key === "Enter" && isOpen && active >= 0) {
                event.preventDefault();
                selectAddress(results[active]);
                close();
            } else if (event.key === "Escape" && isOpen) { event.preventDefault(); close(); }
        });

        input.addEventListener("blur", () => window.setTimeout(close, 120));
        input.addEventListener("focus", () => { if (results.length && input.value.trim().length >= 3) list.hidden = false, input.setAttribute("aria-expanded", "true"); });
    }

    /* ==========================================================================
       Pays, méthodes de livraison (affichées après l'adresse)
       ========================================================================== */

    function renderCountries() {
        const select = $("#country");
        select.replaceChildren();
        (state.data.countries || []).forEach((country) => {
            const option = el("option", "", country.name);
            option.value = country.code;
            select.appendChild(option);
        });
        select.value = state.data.defaultCountry || "FR";
        syncPostalCodeHints();
    }

    function syncPostalCodeHints() {
        const isFrance = value("country") === "FR";
        field("postalCode").setAttribute("inputmode", isFrance ? "numeric" : "text");
        field("postalCode").setAttribute("maxlength", isFrance ? "5" : "10");
    }

    function isAddressComplete() {
        return ["lastName", "country", "street", "postalCode", "city"].every((name) => !validators[name](value(name)));
    }

    async function updateShippingVisibility() {
        const section = $("#shipping-section");
        const complete = isAddressComplete();

        if (!complete) {
            if (!section.hidden) {
                section.hidden = true;
                state.shipping.methods = [];
                state.shipping.selectedId = null;
                renderSummary();
            }
            return;
        }

        if (!section.hidden || state.shipping.loading) return;
        state.shipping.loading = true;
        try {
            const subtotal = getTotals().subtotal;
            state.shipping.methods = await ShippingService.quote(buildOrderPayload().shippingAddress, subtotal);
            renderShippingMethods();
            section.hidden = false;
            $("#address-live").textContent = "Les méthodes de livraison sont maintenant disponibles.";
        } finally {
            state.shipping.loading = false;
        }
    }

    function renderShippingMethods() {
        const box = $("#shipping-options");
        box.replaceChildren();
        state.shipping.methods.forEach((method) => {
            const label = el("label", "co-option");

            const input = document.createElement("input");
            input.type = "radio";
            input.name = "shipping";
            input.value = method.id;
            input.checked = method.id === state.shipping.selectedId;

            const boxEl = el("span", "co-option__box");
            const dot = el("span", "co-option__dot");
            dot.setAttribute("aria-hidden", "true");
            const text = el("span", "co-option__text");
            text.append(el("strong", "", method.label), el("span", "", method.eta));
            const price = el("span", "co-option__price" + (method.price === 0 ? " co-option__price--free" : ""),
                method.price === 0 ? "GRATUIT" : formatMoney(method.price));

            boxEl.append(dot, text, price);
            label.append(input, boxEl);
            box.appendChild(label);
        });
    }

    function initShippingMethods() {
        $("#shipping-options").addEventListener("change", (event) => {
            if (event.target.name !== "shipping") return;
            state.shipping.selectedId = event.target.value;
            $("#shipping-error").hidden = true;
            renderSummary();
        });

        /* Révèle / masque les méthodes selon la complétude de l'adresse. */
        ["lastName", "country", "street", "postalCode", "city"].forEach((name) => {
            field(name).addEventListener("input", updateShippingVisibility);
            field(name).addEventListener("change", updateShippingVisibility);
        });
        field("country").addEventListener("change", syncPostalCodeHints);
    }

    /* ==========================================================================
       Paiement : méthodes classiques + paiement express (maquettes)
       ========================================================================== */

    function initPaymentMethods() {
        const radios = $$('input[name="payment"]');
        const sync = () => {
            const selected = (radios.find((r) => r.checked) || {}).value;
            radios.forEach((radio) => {
                const panel = $(`#panel-${radio.value}`);
                if (panel) panel.hidden = radio.value !== selected;
            });
            $("#payment-error").hidden = true;
        };
        radios.forEach((radio) => radio.addEventListener("change", sync));
        sync();
    }

    function initExpressPayment() {
        const message = $("#express-message");
        $$("[data-express]").forEach((button) => {
            button.addEventListener("click", () => {
                /* TODO : remplacer par les boutons officiels PayPal / Apple Pay / Google Pay. */
                message.textContent = `${button.dataset.express} : intégration prévue à l'étape suivante. Aucun paiement n'a été lancé.`;
            });
        });
    }

    /* ==========================================================================
       Initialisation
       ========================================================================== */

    function initCheckout() {
        state.data = readServerData();
        moneyFormatter = new Intl.NumberFormat(state.data.locale || "fr-FR", {
            style: "currency",
            currency: state.data.currency || "EUR",
        });

        resolveItems();
        renderCountries();
        renderSummary();

        initOrderSummary();
        initPromoCode();
        initExpressPayment();
        initAddressSearch();
        initShippingMethods();
        initPaymentMethods();
        initFormValidation();
        updateSubmitAvailability();
    }

    initCheckout();

})();