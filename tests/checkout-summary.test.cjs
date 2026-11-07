// DOM tests with mocked network; no browser/layout or real Stripe payment.
// NODE_PATH=<temporary npm prefix>/node_modules node --test tests/checkout-summary.test.cjs
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {JSDOM} = require('jsdom');
const script = fs.readFileSync(path.join(__dirname, '../checkout/static/checkout/checkout-summary.js'), 'utf8');
const tick = () => new Promise(resolve => setTimeout(resolve, 12));
const summaryHTML = (code = '', total = '89,90') => `<details id="checkout-summary-details" open><summary><span id="summary-title">Afficher le résumé</span><strong id="summary-amount">${total} € TTC</strong></summary><div>
<details class="checkout-promo" ${code ? 'open' : ''}><summary>Promotion</summary><div id="checkout-promo-status" role="status">${code ? 'Code appliqué.' : ''}</div>
<input id="checkout-promo-code" name="promo_code" form="checkout-form" value="${code}"><button id="apply" type="submit" form="checkout-form" name="promo_action" value="apply">Appliquer</button>
${code ? '<button id="remove" type="submit" form="checkout-form" name="promo_action" value="remove">Retirer</button>' : ''}</details>
<dl><dd id="shipping-preview">Offerte</dd><dd id="checkout-total-preview">${total} €</dd></dl></div></details>`;
const data = (code = '', total = '89.90') => ({summary_html:summaryHTML(code), quote_valid:true, errors:{},cart_error:'',can_pay:true,options:[{method:'free',label:'Livraison offerte',amount:'0.00',total}]});
const response = payload => ({ok:true,json:async()=>payload});
const deferred = () => {let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};};
async function setup(t) {
    const dom = new JSDOM(`<!doctype html><html><body>
<script id="commercial-config" type="application/json">{"currency":"EUR"}</script>
<div class="checkout-layout"><form id="checkout-form" data-update-url="/checkout/">
<input name="csrfmiddlewaretoken" value="unit-csrf"><input name="first_name" id="id_first_name" value="Camille"><input id="id_address_line1" name="address_line1" value="15 rue PRIVEE">
<select id="id_country" name="country"><option value="FR">France</option><option value="BE">Belgique</option></select><input id="id_postal_code" name="postal_code" value="75001">
<input type="checkbox" id="id_billing_same_as_shipping" checked><div id="billing-fields"><input name="billing_address_line1" value="20 rue Facture"></div>
<div id="checkout-errors" role="alert" tabindex="-1" hidden></div><p id="shipping-status"></p><fieldset id="shipping-options"><input type="radio" name="shipping_method" value="free" checked></fieldset>
<button id="checkout-submit" data-server-disabled="false">Payer</button></form>
<aside class="checkout-summary"><p id="checkout-update-status" tabindex="-1"></p><button id="checkout-retry" hidden>Réessayer</button><div id="checkout-summary-content">${summaryHTML()}</div></aside></div>
</body></html>`, {url:'https://shop.example.test/checkout/',runScripts:'outside-only',pretendToBeVisual:true});
    t.after(()=>dom.window.close());
    const w=dom.window;
    w.matchMedia=()=>({matches:true,addEventListener(){}});
    const timeout=w.setTimeout.bind(w); w.setTimeout=(fn,delay)=>timeout(fn,delay===250?1:delay);
    const requests=[]; let handler=async()=>response(data());
    w.fetch=(url,options)=>{requests.push({url,options});return handler(url,options);};
    w.eval(script); await tick(); await tick();
    return {w,doc:w.document,requests,setHandler(fn){handler=fn;},
        submit(id){const event=new w.SubmitEvent('submit',{bubbles:true,cancelable:true,submitter:w.document.getElementById(id)});w.document.getElementById('checkout-form').dispatchEvent(event);return event;},
        changePostal(value){const field=w.document.getElementById('id_postal_code');field.value=value;field.dispatchEvent(new w.Event('input',{bubbles:true}));}};
}

test('promo apply/remove preserves the same address nodes, sends only destination in POST',async t=>{
    const h=await setup(t), address=h.doc.getElementById('id_address_line1');
    let applied=false;
    h.setHandler(async(url,opts)=>{
        const body=new URLSearchParams(opts.body); if(body.get('promo_action')==='apply')applied=true; if(body.get('promo_action')==='remove')applied=false;
        assert.equal(opts.method,'POST');assert.equal(url,'/checkout/');assert.equal(opts.headers['X-CSRFToken'],'unit-csrf');
        assert.equal(body.has('address_line1'),false);assert.equal(body.has('first_name'),false);
        return response(data(applied?'TEST20':''));
    });
    h.doc.getElementById('checkout-promo-code').value='TEST20'; h.submit('apply');await tick();
    assert.strictEqual(h.doc.getElementById('id_address_line1'),address);assert.equal(address.value,'15 rue PRIVEE');assert.ok(h.doc.getElementById('remove'));
    h.submit('remove');await tick();assert.strictEqual(h.doc.getElementById('id_address_line1'),address);assert.equal(address.value,'15 rue PRIVEE');assert.equal(h.doc.getElementById('remove'),null);
    assert.equal(h.w.localStorage.length,0);assert.equal(h.w.sessionStorage.length,0);
});

test('clearing destination invalidates amounts immediately and late response cannot restore quote',async t=>{
    const h=await setup(t), old=deferred();h.setHandler(()=>old.promise);
    h.changePostal('69001');await tick();
    h.changePostal('');
    for(const id of ['shipping-preview','checkout-total-preview','summary-amount'])assert.equal(h.doc.getElementById(id).textContent,'À recalculer');
    assert.equal(h.doc.getElementById('checkout-submit').disabled,true);
    old.resolve(response(data('', '999.00')));await tick();
    assert.equal(h.doc.getElementById('summary-amount').textContent,'À recalculer');
    assert.equal(h.doc.getElementById('checkout-submit').disabled,true);
});

test('rapid edits abort old read and ignore stale response before accepting latest destination',async t=>{
    const h=await setup(t), first=deferred();let calls=0;
    h.setHandler(async()=>{calls++;return calls===1?first.promise:response(data('', '45.00'));});
    h.changePostal('1000');await tick();const old=h.requests.at(-1);
    h.changePostal('2000');assert.equal(old.options.signal.aborted,true);
    first.resolve(response(data('', '999.00')));await tick();await tick();
    assert.match(h.doc.getElementById('summary-amount').textContent,/45/);assert.doesNotMatch(h.doc.getElementById('summary-amount').textContent,/999/);
    assert.equal(new URLSearchParams(h.requests.at(-1).options.body).get('postal_code'),'2000');
});

test('network failure clears confirmed amounts, shows retry and allows recovery',async t=>{
    const h=await setup(t);h.setHandler(async()=>{throw new TypeError('offline');});h.changePostal('1000');await tick();await tick();
    assert.equal(h.doc.getElementById('checkout-total-preview').textContent,'À recalculer');assert.equal(h.doc.getElementById('checkout-retry').hidden,false);assert.equal(h.doc.getElementById('checkout-submit').disabled,true);
    assert.equal(h.doc.getElementById('id_address_line1').value,'15 rue PRIVEE');
    h.setHandler(async()=>response(data('', '52.00')));h.doc.getElementById('checkout-retry').click();await tick();
    assert.equal(h.doc.getElementById('checkout-submit').disabled,false);assert.match(h.doc.getElementById('summary-amount').textContent,/52/);
});

test('cart update disables payment at mutation start and preserves address while refreshing summary',async t=>{
    const h=await setup(t), address=h.doc.getElementById('id_address_line1');
    h.doc.dispatchEvent(new h.w.CustomEvent('cart:changing'));assert.equal(h.doc.getElementById('checkout-submit').disabled,true);assert.equal(h.doc.getElementById('summary-amount').textContent,'À recalculer');
    h.setHandler(async()=>response(data('', '179.80')));h.doc.dispatchEvent(new h.w.CustomEvent('cart:updated'));h.doc.dispatchEvent(new h.w.CustomEvent('cart:settled'));await tick();
    assert.strictEqual(h.doc.getElementById('id_address_line1'),address);assert.equal(address.value,'15 rue PRIVEE');assert.match(h.doc.getElementById('summary-amount').textContent,/179/);
});

test('double payment submit is blocked; pageshow restores controls and revalidates without losing form',async t=>{
    const h=await setup(t);const first=h.submit('checkout-submit');const second=h.submit('checkout-submit');
    assert.equal(first.defaultPrevented,false);assert.equal(second.defaultPrevented,true);assert.equal(h.doc.getElementById('checkout-submit').disabled,true);
    h.w.dispatchEvent(new h.w.PageTransitionEvent('pagehide'));h.w.dispatchEvent(new h.w.PageTransitionEvent('pageshow',{persisted:true}));
    assert.equal(h.doc.getElementById('checkout-submit').disabled,true);await tick();
    assert.equal(h.doc.getElementById('checkout-submit').disabled,false);assert.equal(h.doc.getElementById('id_address_line1').value,'15 rue PRIVEE');
});

test('promo double submit is serialized and useful status receives focus',async t=>{
    const h=await setup(t), pending=deferred();let calls=0;h.setHandler(()=>{calls++;return pending.promise;});
    h.doc.getElementById('checkout-promo-code').value='TEST20';h.submit('apply');h.submit('apply');await tick();assert.equal(calls,1);
    pending.resolve(response(data('TEST20')));await tick();assert.equal(h.doc.activeElement.id,'checkout-promo-status');
});

test('server-disabled sales cannot be enabled by a valid quote',async t=>{
    const h=await setup(t);h.doc.getElementById('checkout-submit').dataset.serverDisabled='true';h.changePostal('1000');await tick();await tick();assert.equal(h.doc.getElementById('checkout-submit').disabled,true);
    assert.equal(h.submit('checkout-submit').defaultPrevented,true);assert.equal(h.doc.activeElement.id,'checkout-errors');
});

test('editing an unapplied promo draft survives an unrelated refresh',async t=>{
    const h=await setup(t);const input=h.doc.getElementById('checkout-promo-code');input.value='DRAFT';input.focus();input.setSelectionRange(2,2);
    h.doc.dispatchEvent(new h.w.CustomEvent('cart:updated'));await tick();
    assert.equal(h.doc.getElementById('checkout-promo-code').value,'DRAFT');assert.equal(h.doc.activeElement.id,'checkout-promo-code');assert.equal(h.doc.activeElement.selectionStart,2);
});

test('Enter in the promotion field applies the code rather than submitting payment',async t=>{
    const h=await setup(t);let action='';h.setHandler(async(url,opts)=>{action=new URLSearchParams(opts.body).get('promo_action');return response(data('ENTER20'));});
    const input=h.doc.getElementById('checkout-promo-code');input.value='ENTER20';
    const event=new h.w.KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true});input.dispatchEvent(event);await tick();
    assert.equal(event.defaultPrevented,true);assert.equal(action,'apply');assert.ok(h.doc.getElementById('remove'));
});

test('free standard and paid express use server totals and preserve express during refresh', async t => {
    const h = await setup(t);
    const options = [{method:'free',label:'Standard offert — 0,00 €',amount:'0.00',total:'39.92'},
                     {method:'express',label:'Express — 9,90 €',amount:'9.90',total:'49.82'}];
    h.setHandler(async () => response({...data(), options}));
    h.changePostal('69001'); await tick(); await tick();
    const express = h.doc.getElementById('shipping-express');
    express.checked = true; express.dispatchEvent(new h.w.Event('change', {bubbles:true}));
    assert.match(h.doc.getElementById('checkout-total-preview').textContent, /49,82/);
    assert.match(h.doc.getElementById('shipping-preview').textContent, /9,90/);
    h.changePostal('75001'); await tick(); await tick();
    assert.equal(new URLSearchParams(h.requests.at(-1).options.body).get('shipping_method'), 'express');
    assert.equal(h.doc.getElementById('shipping-express').checked, true);
    assert.match(h.doc.getElementById('checkout-total-preview').textContent, /49,82/);
    assert.equal(h.doc.getElementById('id_address_line1').value, '15 rue PRIVEE');
});
