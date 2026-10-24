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
}());
