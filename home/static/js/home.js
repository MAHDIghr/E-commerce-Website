"use strict";


/* ==========================================================================
   Mobile navigation
   ========================================================================== */

const menuToggle = document.querySelector(".menu-toggle");
const mainNavigation = document.querySelector("#main-navigation");


if (menuToggle && mainNavigation) {

    menuToggle.addEventListener("click", () => {

        const isOpen =
            mainNavigation.classList.toggle("is-open");

        menuToggle.setAttribute(
            "aria-expanded",
            String(isOpen)
        );

    });


    const navigationLinks =
        mainNavigation.querySelectorAll("a");


    navigationLinks.forEach((link) => {

        link.addEventListener("click", () => {

            mainNavigation.classList.remove("is-open");

            menuToggle.setAttribute(
                "aria-expanded",
                "false"
            );

        });

    });

}


/* ==========================================================================
   Search button
   ========================================================================== */

const searchButton =
    document.querySelector(
        '[data-action="search"]'
    );


if (searchButton) {

    searchButton.addEventListener("click", () => {

        console.log(
            "La fonctionnalité de recherche sera ajoutée ultérieurement."
        );

    });

}


/* ==========================================================================
   Newsletter
   ========================================================================== */

const newsletterForm =
    document.querySelector(".newsletter-form");


if (newsletterForm) {

    newsletterForm.addEventListener("submit", (event) => {

        /*
         * Pour le moment, le formulaire n'est pas encore connecté
         * à une vue Django.
         *
         * La gestion réelle de l'inscription sera ajoutée
         * lorsque nous créerons la fonctionnalité newsletter.
         */

        event.preventDefault();

        const emailInput =
            newsletterForm.querySelector(
                'input[type="email"]'
            );

        if (!emailInput) {
            return;
        }

        console.log(
            "Newsletter :",
            emailInput.value
        );

    });

}