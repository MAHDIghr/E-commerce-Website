const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {JSDOM} = require('jsdom');
// Fixture exported by CatalogRenderingTests using an isolated test database.
const fixture = JSON.parse(fs.readFileSync(process.env.CATALOG_DOM_FIXTURE, 'utf8'));
const script = fs.readFileSync('shop/static/js/shop.js', 'utf8');
function setup(t, source = script) {
    const dom = new JSDOM(fixture.html, {url: 'http://testserver/boutique/?q=Sac&campaign=test&sort=asc', runScripts: 'outside-only', pretendToBeVisual: true});
    const w = dom.window; t.after(() => w.close());
    const requests = [], storage = new Map(), mediaListeners = [];
    const mq = {matches: true, addEventListener: (_, cb) => mediaListeners.push(cb)};
    // jsdom does not reflect these image properties; browsers do.
    for (const name of ['loading','decoding']) Object.defineProperty(w.HTMLImageElement.prototype,name,{get(){return this.getAttribute(name);},set(value){this.setAttribute(name,value);},configurable:true});
    w.matchMedia = () => mq;
    w.readStorage = (key, fallback) => storage.get(key) || fallback;
    w.writeStorage = (key, value) => storage.set(key, value);
    w.getCart = () => []; w.openCart = () => {};
    w.formatPrice = n => new Intl.NumberFormat('fr-FR', {style:'currency',currency:'EUR'}).format(n);
    let additions = 0;
    w.addProductFromCard = async () => { additions++; return false; };
    w.fetch = (url, options) => new Promise(resolve => requests.push({url, options, resolve}));
    w.eval(fs.readFileSync('static/js/overlays.js', 'utf8'));
    w.eval(source);
    return {w, doc: w.document, requests, storage, mq, mediaListeners, additions: () => additions};
}
const tick = () => new Promise(resolve => setTimeout(resolve, 25));
function reply(request, data=fixture.second) { request.resolve({ok:true, json:async()=>data}); }
function change(h, id, value) { const n=h.doc.getElementById(id); n.value=value; n.dispatchEvent(new h.w.Event('change',{bubbles:true})); }
function tree(node) {
    if (node.nodeType === 3) return node.textContent.trim() ? node.textContent : null;
    if (node.nodeType !== 1) return null;
    const attrs = [...node.attributes].filter(a=>a.name!=='data-bound').map(a=>[a.name,a.name==='style'?node.style.cssText:a.value]).sort((a,b)=>a[0].localeCompare(b[0]));
    return [node.tagName, attrs, [...node.childNodes].map(tree).filter(v=>v!==null)];
}
test('server cards stay in place on initialization; no duplicate or initial fetch', async t => {
    const h=setup(t); const first=h.doc.querySelector('.pcard'); await tick();
    assert.equal(h.doc.querySelector('.pcard'),first); assert.equal(h.doc.querySelectorAll('.pcard').length,8); assert.equal(h.requests.length,0);
});
test('pagination keeps parameters, updates once, and suppresses double click', async t=>{
    const h=setup(t); const more=h.doc.getElementById('load-more'); more.click();more.click();
    assert.equal(h.requests.length,1); assert.match(h.requests[0].url,/page=2/);assert.match(h.requests[0].url,/campaign=test/);
    reply(h.requests[0]); await tick();assert.equal(h.doc.querySelectorAll('.pcard').length,11);assert.equal(h.w.location.search.includes('page=2'),true);assert.equal(more.disabled,false);
});
test('late response is ignored and previous request is aborted',async t=>{
    const h=setup(t);change(h,'sort','desc');change(h,'sort','asc');
    assert.equal(h.requests[0].options.signal.aborted,true);
    reply(h.requests[1]);await tick();reply(h.requests[0],{...fixture.second,html:'',total:0,visible:0});await tick();
    assert.equal(h.doc.querySelectorAll('.pcard').length,11);assert.equal(h.doc.getElementById('sort').value,'asc');
});
test('history restores controls and requests the saved page without adding history',async t=>{
    const h=setup(t);h.w.history.replaceState(null,'','?cat=handbags&sort=desc&page=2&campaign=test');
    const length=h.w.history.length;h.w.dispatchEvent(new h.w.PopStateEvent('popstate'));
    assert.equal(h.doc.getElementById('sort').value,'desc');assert.equal(h.doc.querySelector('input[name=cat]').checked,true);
    reply(h.requests[0]);await tick();assert.equal(h.w.history.length,length);
});
test('wishlist persists and quick add has only one handler with retry',async t=>{
    const h=setup(t);const card=h.doc.querySelector('.pcard');card.querySelector('.pcard__wish').click();
    assert.deepEqual(Array.from(h.storage.get('wishlist_v1')),[card.dataset.productSlug]);
    const add=h.doc.querySelector('.pcard__add:not(:disabled)');add.click();add.click();await tick();assert.equal(h.additions(),1);assert.equal(add.disabled,false);
});
test('mobile filter state and inert reset across breakpoints', t=>{
    const h=setup(t), trigger=h.doc.querySelector('[data-action=open-filters]'),drawer=h.doc.getElementById('filters');
    trigger.click();assert.equal(trigger.getAttribute('aria-expanded'),'true');
    h.mq.matches=false;h.mediaListeners.forEach(cb=>cb());assert.equal(drawer.inert,false);assert.equal(trigger.getAttribute('aria-expanded'),'false');
    h.mq.matches=true;h.mediaListeners.forEach(cb=>cb());assert.equal(drawer.inert,true);
});
if (process.env.CATALOG_BASELINE_JS) test('server card DOM equals previous JS card DOM with identical fixture',async t=>{
    const before=setup(t,fs.readFileSync(process.env.CATALOG_BASELINE_JS,'utf8'));
    const after=setup(t);await tick();
    assert.equal(after.doc.querySelectorAll('.pcard').length,8);
    assert.deepEqual([...after.doc.querySelectorAll('.pcard')].map(tree),[...before.doc.querySelectorAll('.pcard')].map(tree));
});
test('category keyboard focus survives the async rerender',async t=>{
    const h=setup(t), button=h.doc.querySelector('#category-pills button[data-category=handbags]');button.focus();button.click();
    reply(h.requests[0]);await tick();assert.equal(h.doc.activeElement.dataset.category,'handbags');
});
test('wishlist is refreshed on back-forward cache return and another tab update',t=>{
    const h=setup(t),card=h.doc.querySelector('.pcard'),slug=card.dataset.productSlug;
    h.storage.set('wishlist_v1',[slug]);h.w.dispatchEvent(new h.w.Event('pageshow'));
    assert.equal(card.querySelector('.pcard__wish').getAttribute('aria-pressed'),'true');
    h.storage.set('wishlist_v1',[]);h.w.dispatchEvent(new h.w.StorageEvent('storage',{key:'wishlist_v1'}));
    assert.equal(card.querySelector('.pcard__wish').getAttribute('aria-pressed'),'false');
});
test('home favorite click preserves selections made in a different page',t=>{
    const h=setup(t);const card=h.doc.createElement('article');card.className='product-card';card.dataset.productSlug='home-product';
    card.innerHTML='<button class="product-wishlist" type="button"></button>';h.doc.body.append(card);
    const home=fs.readFileSync('home/static/js/home.js','utf8');
    const start=home.indexOf('const HOME_WISHLIST_KEY');const end=home.indexOf('/*',start);
    h.w.eval(home.slice(start,end));h.storage.set('wishlist_v1',['elsewhere']);card.querySelector('button').click();
    assert.deepEqual(Array.from(h.storage.get('wishlist_v1')),['elsewhere','home-product']);
    h.storage.set('wishlist_v1',[]);h.w.dispatchEvent(new h.w.Event('pageshow'));
    assert.equal(card.querySelector('button').getAttribute('aria-pressed'),'false');
});
