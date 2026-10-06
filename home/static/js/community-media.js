/* ==========================================================================
   COMMUNITY MEDIA
   Stories + Reels : chargement progressif et lecture automatique visible.
   Les mêmes vidéos publiques sont conservées ; seules la stratégie de
   chargement et la gestion de lecture sont optimisées.
   ========================================================================== */

(() => {
    const VIDEO_SOURCES = {
        "Nouveautés": "https://videos.pexels.com/video-files/18211069/18211069-uhd_2160_3840_30fps.mp4",
        "Coulisses": "https://videos.pexels.com/video-files/7668415/7668415-uhd_4096_2160_25fps.mp4",
        "Styling": "https://videos.pexels.com/video-files/8798286/uhd_25fps.mp4",
        "Promos": "https://videos.pexels.com/video-files/5924993/5924993-uhd_2160_3840_24fps.mp4",
        "Avis": "https://videos.pexels.com/video-files/12909804/12909804-uhd_2160_3840_24fps.mp4",
        "Atelier": "https://videos.pexels.com/video-files/18211069/18211069-uhd_2160_3840_30fps.mp4",
        "Comment porter le cabas camel": "https://videos.pexels.com/video-files/18211069/18211069-uhd_2160_3840_30fps.mp4",
        "Unboxing de la collection": "https://videos.pexels.com/video-files/8798286/uhd_25fps.mp4",
        "3 looks, 1 sac": "https://videos.pexels.com/video-files/5924993/5924993-uhd_2160_3840_24fps.mp4",
        "Dans les coulisses": "https://videos.pexels.com/video-files/12909804/12909804-uhd_2160_3840_24fps.mp4",
        "Le détail qui change tout": "https://videos.pexels.com/video-files/7668415/7668415-uhd_4096_2160_25fps.mp4",
    };

    function getVideoKey(item) {
        const label = item.getAttribute("aria-label") || "";
        const labelMatch = label.match(/: (.+)$/);
        if (labelMatch) return labelMatch[1].trim();

        const caption = item.querySelector(".reel__caption");
        return caption ? caption.textContent.trim() : "";
    }

    function createVideo(item, source) {
        const existing = item.querySelector("video");
        if (existing) return existing;

        const poster = item.querySelector("img");
        const video = document.createElement("video");

        video.preload = "metadata";
        video.loading = "lazy";
        video.muted = true;
        video.defaultMuted = true;
        video.loop = true;
        video.playsInline = true;
        video.autoplay = true;

        video.setAttribute("autoplay", "");
        video.setAttribute("muted", "");
        video.setAttribute("playsinline", "");
        video.setAttribute("loading", "lazy");
        video.setAttribute("aria-hidden", "true");

        if (poster) {
            video.poster = poster.currentSrc || poster.src;
            poster.replaceWith(video);
        } else {
            item.prepend(video);
        }

        video.src = source;
        item.dataset.communityVideoLoaded = "true";

        video.play().catch(() => {});
        return video;
    }

    function loadAndPlay(item) {
        const source = item.dataset.communityVideo;
        if (!source) return;

        const video = createVideo(item, source);
        video.play().catch(() => {});
    }

    function updatePlayback(item, isVisible) {
        const video = item.querySelector("video");

        if (!video) {
            if (isVisible) loadAndPlay(item);
            return;
        }

        if (isVisible && !document.hidden) {
            video.play().catch(() => {});
        } else {
            video.pause();
        }
    }

    function initCommunityVideos() {
        const items = Array.from(document.querySelectorAll(".story, .reel"));

        items.forEach((item) => {
            const key = getVideoKey(item);
            const source = VIDEO_SOURCES[key];
            if (source) item.dataset.communityVideo = source;
        });

        if (items.length === 0) return;

        if (!("IntersectionObserver" in window)) {
            items.forEach((item) => loadAndPlay(item));
            return;
        }

        /*
         * Le chargement commence quand la communauté approche du viewport.
         * Sur desktop, les 5 reels visibles sont donc chargés et joués
         * ensemble. Sur mobile, seuls les reels visibles/à proximité
         * sont activés, ce qui réduit la charge simultanée.
         */
        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    updatePlayback(entry.target, entry.isIntersecting);
                });
            },
            {
                root: null,
                rootMargin: "300px 0px",
                threshold: 0.2,
            }
        );

        items.forEach((item) => observer.observe(item));

        document.addEventListener("visibilitychange", () => {
            items.forEach((item) => {
                const video = item.querySelector("video");
                if (!video) return;

                if (document.hidden) {
                    video.pause();
                    return;
                }

                const rect = item.getBoundingClientRect();
                const visible =
                    rect.bottom > -100 &&
                    rect.top < window.innerHeight + 100 &&
                    rect.right > -100 &&
                    rect.left < window.innerWidth + 100;

                if (visible) video.play().catch(() => {});
            });
        });
    }

    initCommunityVideos();
})();
