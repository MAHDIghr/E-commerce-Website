/* =========================================================
   ELEMENTS
   ========================================================= */

const carousel = document.getElementById("carousel");
const cards = Array.from(document.querySelectorAll(".card"));

const prevButton = document.getElementById("prevButton");
const nextButton = document.getElementById("nextButton");


/* =========================================================
   CONFIGURATION
   ========================================================= */

let currentIndex = 0;

let isAnimating = false;

let autoPlayTimer = null;

const AUTO_PLAY_DELAY = 2000;

const totalCards = cards.length;


/* =========================================================
   OUTILS
   ========================================================= */

function modulo(number, total) {
    return ((number % total) + total) % total;
}


function getOffset(cardIndex) {

    let offset = cardIndex - currentIndex;

    if (offset > totalCards / 2) {
        offset -= totalCards;
    }

    if (offset < -totalCards / 2) {
        offset += totalCards;
    }

    return offset;
}


/* =========================================================
   POSITIONNEMENT 3D
   ========================================================= */

function updateCarousel(previousOffsets = null) {

    const cardWidth =
        cards[0].getBoundingClientRect().width;


    /*
        DISTANCE ENTRE LES CARTES

        0 = centre
        1 = première carte à gauche/droite
        2 = deuxième
        3 = troisième

        La distance est maintenant fixe.
    */
    const spacing = cardWidth * 1.10;


    cards.forEach((card, index) => {

        const offset = getOffset(index);

        const absoluteOffset = Math.abs(offset);


        /*
            Si une carte passe directement de
            l'autre côté du carrousel, on la repositionne
            sans animation.

            Cela évite l'effet où elle traverse le centre.
        */
        let shouldJump = false;

        if (previousOffsets) {

            const oldOffset = previousOffsets[index];

            if (
                Math.abs(offset - oldOffset) > 1.5
            ) {
                shouldJump = true;
            }
        }


        if (shouldJump) {

            card.style.transition = "none";

        } else {

            card.style.transition = "";
        }


        /* =================================================
           CENTRE
           ================================================= */

        if (offset === 0) {

            card.style.transform = `
                translate(-50%, -50%)
                translateX(0px)
                translateZ(${cardWidth * 0.42}px)
                rotateY(0deg)
                scale(1)
            `;

            card.style.opacity = "1";

            card.style.filter =
                "brightness(1) saturate(1)";

            card.style.zIndex = "50";

            return;
        }


        /* =================================================
           PREMIÈRES CARTES LATÉRALES
           ================================================= */

        if (absoluteOffset === 1) {

            const direction = offset < 0 ? -1 : 1;

            /*
                Position horizontale FIXE.
            */
            const x =
                direction * spacing;

            /*
                Inclinaison vers le centre.
            */
            const rotation =
                direction * -32;


            card.style.transform = `
                translate(-50%, -50%)
                translateX(${x}px)
                translateZ(0px)
                rotateY(${rotation}deg)
                scale(0.78)
            `;

            card.style.opacity = "0.80";

            card.style.filter =
                "brightness(0.68) saturate(0.85)";

            card.style.zIndex = "40";

            return;
        }


        /* =================================================
           DEUXIÈMES CARTES LATÉRALES
           ================================================= */

        if (absoluteOffset === 2) {

            const direction =
                offset < 0 ? -1 : 1;

            /*
                Toujours le même écart.
            */
            const x =
                direction * spacing * 2;

            const rotation =
                direction * -42;


            card.style.transform = `
                translate(-50%, -50%)
                translateX(${x}px)
                translateZ(-60px)
                rotateY(${rotation}deg)
                scale(0.62)
            `;

            card.style.opacity = "0.42";

            card.style.filter =
                "brightness(0.45) saturate(0.65)";

            card.style.zIndex = "30";

            return;
        }


        /* =================================================
           CARTES TRÈS ÉLOIGNÉES
           ================================================= */

        const direction =
            offset < 0 ? -1 : 1;

        const x =
            direction * spacing * 3;

        const rotation =
            direction * -48;


        card.style.transform = `
            translate(-50%, -50%)
            translateX(${x}px)
            translateZ(-130px)
            rotateY(${rotation}deg)
            scale(0.52)
        `;

        card.style.opacity = "0";

        card.style.filter =
            "brightness(0.30) saturate(0.40)";

        card.style.zIndex = "10";

    });


    /*
        On réactive l'animation après avoir
        repositionné les cartes qui font la boucle.
    */
    if (previousOffsets) {

        requestAnimationFrame(() => {

            requestAnimationFrame(() => {

                cards.forEach(card => {

                    card.style.transition = "";

                });

            });

        });

    }
}


/* =========================================================
   NAVIGATION
   ========================================================= */

function goToSlide(index) {

    if (isAnimating) {
        return;
    }


    const newIndex =
        modulo(index, totalCards);


    if (newIndex === currentIndex) {
        return;
    }


    /*
        On mémorise la position actuelle de chaque carte
        avant de changer l'image centrale.
    */
    const previousOffsets =
        cards.map((_, index) => getOffset(index));


    isAnimating = true;

    currentIndex = newIndex;


    updateCarousel(previousOffsets);


    setTimeout(() => {

        isAnimating = false;

    }, 700);


    restartAutoPlay();
}


function nextSlide() {

    goToSlide(currentIndex + 1);
}


function previousSlide() {

    goToSlide(currentIndex - 1);
}


/* =========================================================
   BOUTONS
   ========================================================= */

nextButton.addEventListener(
    "click",
    nextSlide
);

prevButton.addEventListener(
    "click",
    previousSlide
);


/* =========================================================
   AUTOPLAY
   ========================================================= */

function startAutoPlay() {

    stopAutoPlay();

    autoPlayTimer =
        setInterval(() => {

            nextSlide();

        }, AUTO_PLAY_DELAY);
}


function stopAutoPlay() {

    if (autoPlayTimer !== null) {

        clearInterval(autoPlayTimer);

        autoPlayTimer = null;
    }
}


function restartAutoPlay() {

    startAutoPlay();
}


/* =========================================================
   SOURIS
   ========================================================= */

carousel.addEventListener(
    "mouseenter",
    () => {

        stopAutoPlay();

    }
);


carousel.addEventListener(
    "mouseleave",
    () => {

        startAutoPlay();

    }
);


/* =========================================================
   CLAVIER
   ========================================================= */

document.addEventListener(
    "keydown",
    (event) => {

        if (event.key === "ArrowRight") {

            nextSlide();

        }

        if (event.key === "ArrowLeft") {

            previousSlide();

        }

    }
);


/* =========================================================
   DRAG / SWIPE
   ========================================================= */

let isDragging = false;

let dragStartX = 0;

let dragCurrentX = 0;

let dragDifference = 0;


function startDrag(clientX) {

    isDragging = true;

    dragStartX = clientX;

    dragCurrentX = clientX;

    dragDifference = 0;

    carousel.classList.add(
        "is-dragging"
    );

    stopAutoPlay();
}


function moveDrag(clientX) {

    if (!isDragging) {
        return;
    }

    dragCurrentX = clientX;

    dragDifference =
        dragCurrentX - dragStartX;
}


function endDrag() {

    if (!isDragging) {
        return;
    }

    isDragging = false;

    carousel.classList.remove(
        "is-dragging"
    );


    const minimumSwipeDistance = 60;


    if (
        Math.abs(dragDifference) >=
        minimumSwipeDistance
    ) {

        if (dragDifference < 0) {

            nextSlide();

        } else {

            previousSlide();

        }

    } else {

        startAutoPlay();

    }
}


/* =========================================================
   SOURIS
   ========================================================= */

carousel.addEventListener(
    "mousedown",
    (event) => {

        event.preventDefault();

        startDrag(event.clientX);

    }
);


window.addEventListener(
    "mousemove",
    (event) => {

        moveDrag(event.clientX);

    }
);


window.addEventListener(
    "mouseup",
    () => {

        endDrag();

    }
);


/* =========================================================
   TOUCH
   ========================================================= */

carousel.addEventListener(
    "touchstart",
    (event) => {

        const touch =
            event.touches[0];

        startDrag(touch.clientX);

    },
    {
        passive: true
    }
);


carousel.addEventListener(
    "touchmove",
    (event) => {

        const touch =
            event.touches[0];

        moveDrag(touch.clientX);

    },
    {
        passive: true
    }
);


carousel.addEventListener(
    "touchend",
    () => {

        endDrag();

    }
);


/* =========================================================
   VISIBILITÉ DE LA PAGE
   ========================================================= */

document.addEventListener(
    "visibilitychange",
    () => {

        if (document.hidden) {

            stopAutoPlay();

        } else {

            startAutoPlay();

        }

    }
);


/* =========================================================
   INITIALISATION
   ========================================================= */

updateCarousel();

startAutoPlay();