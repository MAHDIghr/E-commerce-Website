// Local live server only. Never creates a Stripe session or clicks payment.
const {chromium}=require('playwright');
const fs=require('node:fs');const assert=require('node:assert/strict');
const origin=process.argv[2],slug=process.argv[3];
if(!/^http:\/\/(localhost|127\.0\.0\.1):\d+$/.test(origin))throw Error('Local test server required');
const output=process.env.QA_OUTPUT_DIR||'qa-output';fs.mkdirSync(output,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true});
 const evidence=[];
 try{
  for(const width of [320,390,1366]){
   const context=await browser.newContext({viewport:{width,height:900}});const page=await context.newPage();
   const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',message=>{if(message.type()==='error')errors.push(message.text());});
   await page.goto(origin+'/');await page.locator(`a[href="/produit/${slug}/"]`).first().click();await page.waitForURL('**/produit/'+slug+'/');
   await page.goto(origin+'/boutique/');await page.locator('#product-grid a').first().click();
   await page.getByRole('button',{name:'Acheter maintenant',exact:true}).first().click();await page.waitForURL('**/checkout/');
   await page.locator('#id_first_name').fill('Client QA');await page.locator('#id_address_line1').fill('Adresse fictive QA');
   await page.locator('#id_postal_code').fill('75001');await page.locator('#id_country').selectOption('FR');
   await page.locator('.checkout-promo > summary').click();await page.locator('#checkout-promo-code').fill('QA20');
   await page.locator('[name="promo_action"][value="apply"]').click();
   await page.waitForFunction(()=>document.querySelector('[name="promo_action"][value="remove"]'));
   assert.equal(await page.locator('#id_address_line1').inputValue(),'Adresse fictive QA');
   assert.match(await page.locator('#checkout-summary-content').innerText(),/17,98/);
   await page.screenshot({path:`${output}/checkout-${width}.png`,fullPage:true});
   await page.locator('[name="promo_action"][value="remove"]').click();
   await page.waitForFunction(()=>!document.querySelector('[name="promo_action"][value="remove"]'));
   assert.equal(await page.locator('#id_first_name').inputValue(),'Client QA');
   await page.locator('#id_postal_code').fill('');
   assert.equal(await page.locator('#checkout-submit').isDisabled(),true);
   assert.match(await page.locator('#checkout-total-preview').innerText(),/recalculer/);
   const overflow=await page.evaluate(()=>{document.documentElement.style.overflowX='visible';document.body.style.overflowX='visible';return document.documentElement.scrollWidth>innerWidth;});
   assert.equal(overflow,false,'Viewport overflow');assert.deepEqual(errors,[],'Browser console errors');
   evidence.push({width,scenario:'home/catalog/product/cart/promo/address/invalid-quote',result:'passed',utc:new Date().toISOString()});
   await context.close();
   const noJS=await browser.newContext({javaScriptEnabled:false,viewport:{width,height:900}});const plain=await noJS.newPage();await plain.goto(origin+'/boutique/');
   assert.ok(await plain.locator('#product-grid a').count());await plain.getByRole('button',{name:'Appliquer les filtres'}).click();assert.ok(await plain.locator('#product-grid a').count());await noJS.close();
  }
 }finally{fs.writeFileSync(`${output}/results.json`,JSON.stringify(evidence,null,2));await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
