/* ==========================================================================
   COMMUNITY MEDIA — stories + reels, previews différées et visionneuse
   ========================================================================== */
(() => {
    "use strict";

    const items = Array.from(document.querySelectorAll(".community .story, .community .reel"));
    const backdrop = document.querySelector("#community-modal-backdrop");
    const modal = backdrop?.querySelector(".community-modal");
    const mediaHost = document.querySelector("#community-modal-media");
    const typeHost = document.querySelector("#community-modal-type");
    const titleHost = document.querySelector("#community-modal-title");
    const captionHost = document.querySelector("#community-modal-caption");
    const closeButton = document.querySelector('[data-action="close-community-modal"]');
    if (!items.length) return;

    let lastTrigger = null;
    let activeModalVideo = null;
    const visibleItems = new Set();
    const previewVideos = new Map();

    const labelFor = (item) => {
        const caption = item.querySelector(".reel__caption");
        if (caption) return caption.textContent.trim();
        const aria = item.getAttribute("aria-label") || "";
        return aria.replace(/^Story\s*:\s*/i, "").trim();
    };

    function createPreview(item) {
        if (previewVideos.has(item)) return previewVideos.get(item);
        // Les stories gardent leur vignette statique : aucune vidéo ne se lance
        // avant l'ouverture volontaire. Les aperçus animés restent réservés aux reels.
        if (item.classList.contains("story")) return null;
        const source = item.dataset.videoSrc;
        const poster = item.querySelector("img");
        if (!source) return null;

        const video = document.createElement("video");
        video.muted = true;
        video.defaultMuted = true;
        video.loop = true;
        video.autoplay = true;
        video.playsInline = true;
        video.preload = "none";
        video.setAttribute("muted", "");
        video.setAttribute("playsinline", "");
        video.setAttribute("aria-hidden", "true");
        if (poster?.src) video.poster = poster.currentSrc || poster.src;
        video.src = source;
        if (poster) poster.replaceWith(video);
        else (item.querySelector(".story__ring") || item).prepend(video);
        previewVideos.set(item, video);
        return video;
    }

    function syncPreviewPlayback() {
        const allowed = new Set(Array.from(visibleItems).filter((item) => item.classList.contains("reel")).slice(0, 2));
        previewVideos.forEach((video, item) => {
            if (backdrop?.classList.contains("is-open") || document.hidden || !allowed.has(item)) {
                video.pause();
            } else {
                const play = video.play();
                if (play && typeof play.catch === "function") play.catch(() => {});
            }
        });
    }

    function closeModal() {
        if (!backdrop?.classList.contains("is-open")) return;
        backdrop.classList.remove("is-open");
        backdrop.setAttribute("aria-hidden", "true");
        document.body.classList.remove("community-modal-open");
        if (activeModalVideo) {
            activeModalVideo.pause();
            activeModalVideo.removeAttribute("src");
            activeModalVideo.load();
            activeModalVideo = null;
        }
        if (mediaHost) mediaHost.replaceChildren();
        lastTrigger?.focus({ preventScroll: true });
        syncPreviewPlayback();
    }

    function openModal(item) {
        if (!backdrop || !mediaHost) return;
        const source = item.dataset.videoSrc;
        if (!source) return;
        lastTrigger = item;
        previewVideos.forEach((video) => video.pause());
        const video = document.createElement("video");
        video.src = source;
        const poster = item.querySelector("video, img")?.poster || item.querySelector("img")?.currentSrc || "";
        if (poster) video.poster = poster;
        video.controls = true;
        video.autoplay = true;
        video.playsInline = true;
        video.preload = "metadata";
        video.setAttribute("playsinline", "");
        video.setAttribute("aria-label", labelFor(item));
        mediaHost.replaceChildren(video);
        activeModalVideo = video;
        const isStory = item.classList.contains("story");
        if (typeHost) typeHost.textContent = isStory ? "Story" : "Reel";
        if (titleHost) titleHost.textContent = labelFor(item);
        if (captionHost) captionHost.textContent = isStory
            ? "Découvrez les coulisses et les nouveautés de notre communauté."
            : "Une inspiration vidéo de la communauté.";
        backdrop.classList.add("is-open");
        backdrop.setAttribute("aria-hidden", "false");
        document.body.classList.add("community-modal-open");
        closeButton?.focus({ preventScroll: true });
        const play = video.play();
        if (play && typeof play.catch === "function") play.catch(() => {});
    }

    items.forEach((item) => {
        item.setAttribute("role", "button");
        item.setAttribute("tabindex", "0");
        item.addEventListener("click", (event) => {
            event.preventDefault();
            openModal(item);
        });
        item.addEventListener("keydown", (event) => {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                openModal(item);
            }
        });
    });

    if ("IntersectionObserver" in window) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                const item = entry.target;
                if (entry.isIntersecting) {
                    visibleItems.add(item);
                    if (item.classList.contains("reel")) createPreview(item);
                } else {
                    visibleItems.delete(item);
                }
            });
            syncPreviewPlayback();
        }, { rootMargin: "100px 0px", threshold: 0.25 });
        items.forEach((item) => observer.observe(item));
    } else {
        items.filter((item) => item.classList.contains("reel")).slice(0, 2).forEach((item) => {
            visibleItems.add(item);
            createPreview(item);
        });
        syncPreviewPlayback();
    }

    closeButton?.addEventListener("click", closeModal);
    backdrop?.addEventListener("click", (event) => {
        if (event.target === backdrop) closeModal();
    });
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") closeModal();
        if (event.key === "Tab" && backdrop?.classList.contains("is-open") && modal) {
            const focusables = Array.from(modal.querySelectorAll("button, video[controls], [tabindex]:not([tabindex='-1'])"))
                .filter((element) => !element.disabled);
            if (!focusables.length) return;
            const first = focusables[0];
            const last = focusables[focusables.length - 1];
            if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
            }
        }
    });
    document.addEventListener("visibilitychange", syncPreviewPlayback);
})();
