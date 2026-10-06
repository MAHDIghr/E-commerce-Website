/* ==========================================================================
   COMMUNITY MEDIA
   Stories + Reels : aperçu vidéo automatique, muet, en boucle.
   Le clic ouvre la modale communautaire existante.
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

        video.src = source;
        video.autoplay = true;
        video.muted = true;
        video.defaultMuted = true;
        video.loop = true;
        video.playsInline = true;
        video.preload = "auto";
        video.setAttribute("autoplay", "");
        video.setAttribute("muted", "");
        video.setAttribute("playsinline", "");
        video.setAttribute("aria-hidden", "true");

        if (poster) {
            video.poster = poster.currentSrc || poster.src;
            poster.replaceWith(video);
        } else {
            item.prepend(video);
        }

        const start = () => {
            video.play().catch(() => {
                /* Le navigateur peut refuser l'autoplay selon ses réglages. */
            });
        };

        video.addEventListener("loadeddata", start, { once: true });
        video.addEventListener("canplay", start, { once: true });
        start();

        return video;
    }

    function initCommunityVideos() {
        document.querySelectorAll(".story, .reel").forEach((item) => {
            const key = getVideoKey(item);
            const source = VIDEO_SOURCES[key];
            if (!source) return;

            item.dataset.communityVideo = source;
            createVideo(item, source);
        });
    }

    initCommunityVideos();
})();
