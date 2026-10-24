(function () {
  "use strict";
  const sidebar = document.getElementById("sidebar");
  const toggle = document.getElementById("menuToggle");
  const scrim = document.getElementById("sidebarScrim");
  if (!sidebar || !toggle || !scrim) return;

  function setOpen(open) {
    sidebar.classList.toggle("is-open", open);
    scrim.classList.toggle("is-visible", open);
    scrim.hidden = !open;
    toggle.setAttribute("aria-expanded", String(open));
    document.body.style.overflow = open ? "hidden" : "";
    if (open) {
      const firstLink = sidebar.querySelector("a, button");
      if (firstLink) firstLink.focus();
    } else {
      toggle.focus();
    }
  }

  toggle.addEventListener("click", function () {
    setOpen(toggle.getAttribute("aria-expanded") !== "true");
  });
  scrim.addEventListener("click", function () { setOpen(false); });
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && toggle.getAttribute("aria-expanded") === "true") setOpen(false);
  });
  window.addEventListener("resize", function () {
    if (window.innerWidth > 760 && toggle.getAttribute("aria-expanded") === "true") {
      sidebar.classList.remove("is-open");
      scrim.classList.remove("is-visible");
      scrim.hidden = true;
      toggle.setAttribute("aria-expanded", "false");
      document.body.style.overflow = "";
    }
  });

  // Formsets dynamiques : plusieurs couleurs, médias et jusqu'à trois offres.
  const formsetConfig = {
    variant: { prefix: "variants", rows: "variant-rows", template: "variant-empty-form" },
    media: { prefix: "media", rows: "media-rows", template: "media-empty-form" },
    offer: { prefix: "offers", rows: "offer-rows", template: "offer-empty-form", max: 3 }
  };

  function activeFormCount(rows) {
    return Array.from(rows.querySelectorAll(".formset-row")).filter((row) => {
      const deletion = row.querySelector('input[name$="-DELETE"]');
      return !deletion || !deletion.checked;
    }).length;
  }

  function refreshAddButtons() {
    document.querySelectorAll("[data-add-formset]").forEach((button) => {
      const config = formsetConfig[button.dataset.addFormset];
      const rows = config && document.getElementById(config.rows);
      button.disabled = Boolean(config && config.max && rows && activeFormCount(rows) >= config.max);
    });
  }

  document.querySelectorAll("[data-add-formset]").forEach((button) => {
    button.addEventListener("click", () => {
      const config = formsetConfig[button.dataset.addFormset];
      if (!config) return;
      const rows = document.getElementById(config.rows);
      const total = document.getElementById("id_" + config.prefix + "-TOTAL_FORMS");
      const template = document.getElementById(config.template);
      if (!rows || !total || !template) return;
      if (config.max && activeFormCount(rows) >= config.max) return;
      const index = Number(total.value);
      const holder = document.createElement("div");
      holder.innerHTML = template.innerHTML.replace(/__prefix__/g, String(index)).trim();
      const row = holder.firstElementChild;
      if (!row) return;
      rows.appendChild(row);
      total.value = String(index + 1);
      refreshAddButtons();
    });
  });

  document.addEventListener("change", (event) => {
    const target = event.target;
    if (target.matches('input[name$="-DELETE"]')) refreshAddButtons();

    if (target.matches('input[name$="-is_primary"]') && target.checked) {
      document.querySelectorAll('input[name$="-is_primary"]').forEach((input) => {
        if (input !== target) input.checked = false;
      });
    }
    if (target.matches('input[name$="-is_featured"]') && target.checked) {
      document.querySelectorAll('input[name$="-is_featured"]').forEach((input) => {
        if (input !== target) input.checked = false;
      });
    }

    if (target.matches('input[type="file"]') && target.files && target.files[0]) {
      const row = target.closest(".media-row");
      const form = target.closest("form");
      const preview = row ? row.querySelector("[data-media-preview]") : form?.querySelector("[data-media-preview]");
      if (preview && target.files[0].type.startsWith("image/")) {
        const img = document.createElement("img");
        img.alt = "Aperçu du fichier sélectionné";
        img.src = URL.createObjectURL(target.files[0]);
        preview.replaceChildren(img);
      }
    }

    const row = target.closest(".media-row");
    if (row && target.name && (target.name.endsWith("-source_url") || target.name.endsWith("-poster_url") || target.name.endsWith("-media_type"))) {
      const type = row.querySelector('select[name$="-media_type"]')?.value;
      const source = row.querySelector('input[name$="-source_url"]')?.value;
      const poster = row.querySelector('input[name$="-poster_url"]')?.value;
      const file = row.querySelector('input[type="file"]');
      const preview = row.querySelector("[data-media-preview]");
      if (preview && !(file && file.files && file.files.length)) {
        const url = type === "video" ? poster : source;
        if (url) {
          const img = document.createElement("img");
          img.alt = type === "video" ? "Aperçu de la vignette vidéo" : "Aperçu de l'image externe";
          img.src = url;
          preview.replaceChildren(img);
        }
      }
    }

    if (target.name === "image_url") {
      const form = target.closest("form");
      const preview = form?.querySelector("[data-media-preview]");
      const file = form?.querySelector('input[type="file"]');
      if (preview && target.value && !(file && file.files && file.files.length)) {
        const img = document.createElement("img");
        img.alt = "Aperçu de l'image de catégorie";
        img.src = target.value;
        preview.replaceChildren(img);
      }
    }
  });
  refreshAddButtons();

}());
