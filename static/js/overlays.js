"use strict";
/* Une seule surcouche personnalisée active ; les dialogs natifs gardent leur modèle. */
window.ShopOverlays = (() => {
    let active = null;
    const selector = 'a[href],button:not(:disabled),input:not(:disabled):not([type="hidden"]),select:not(:disabled),textarea:not(:disabled),video[controls],[tabindex]:not([tabindex="-1"])';
    const focusables = node => [...node.querySelectorAll(selector)].filter(el => !el.closest('[hidden],[inert],[aria-hidden="true"]') && getComputedStyle(el).display !== 'none' && getComputedStyle(el).visibility !== 'hidden');
    function close(root) {
        if (!active || active.root !== root) return false;
        const old = active; active = null;
        old.cleanup?.();
        old.mask.forEach(([node, inert]) => { node.inert = inert; });
        document.body.style.overflow = old.overflow;
        root.setAttribute('aria-hidden', 'true'); root.inert = true;
        old.trigger?.setAttribute('aria-expanded', 'false');
        if (old.trigger?.isConnected && !old.trigger.closest('[inert],[hidden]')) old.trigger.focus({preventScroll:true});
        return true;
    }
    function open(root, {focus, trigger = document.activeElement, close: cleanup} = {}) {
        if (active || document.querySelector('dialog[open]')) return false;
        const mask = [];
        let branch = root;
        while (branch.parentElement) {
            for (const sibling of branch.parentElement.children) {
                if (sibling !== branch && !sibling.matches('.cart-backdrop,.filters-backdrop') && !['SCRIPT','STYLE','LINK'].includes(sibling.tagName)) {
                    mask.push([sibling, sibling.inert]); sibling.inert = true;
                }
            }
            branch = branch.parentElement;
            if (branch === document.body) break;
        }
        active = {root, trigger, cleanup, mask, overflow: document.body.style.overflow};
        root.inert = false; root.setAttribute('aria-hidden','false');
        trigger?.setAttribute('aria-expanded','true'); document.body.style.overflow = 'hidden';
        (focus || focusables(root)[0] || root).focus({preventScroll:true});
        requestAnimationFrame(() => { if (active?.root === root) (focus || focusables(root)[0] || root).focus({preventScroll:true}); });
        return true;
    }
    document.addEventListener('keydown', event => {
        if (!active || document.querySelector('dialog[open]')) return;
        if (event.key === 'Escape') { event.preventDefault(); event.stopImmediatePropagation(); close(active.root); }
        else if (event.key === 'Tab') {
            const items = focusables(active.root), first = items[0] || active.root, last = items.at(-1) || active.root;
            if (!items.length || !active.root.contains(document.activeElement) || (event.shiftKey && document.activeElement === first) || (!event.shiftKey && document.activeElement === last)) {
                event.preventDefault(); (event.shiftKey ? last : first).focus();
            }
        }
    }, true);
    document.addEventListener('focusin', event => {
        if (active && !document.querySelector('dialog[open]') && !active.root.contains(event.target)) (focusables(active.root)[0] || active.root).focus();
    });
    return {open, close, busy: () => Boolean(active || document.querySelector('dialog[open]'))};
})();
