import assert from 'node:assert/strict';
import { chromium } from 'playwright';

const origin = 'http://127.0.0.1:8765';
const cities = [
  ['groveland', 'Groveland', new Set(['meadow-pointe', 'hidden-ridge'])],
  ['st-cloud', 'St. Cloud', new Set(['bridgewalk', 'waterlin'])],
  ['haines-city', 'Haines City', new Set(['crosswinds'])],
  ['clermont', 'Clermont', new Set()],
  ['davenport', 'Davenport', new Set()],
];

const browser = await chromium.launch({ headless: true });
try {
  for (const viewport of [{width: 1440, height: 900}, {width: 390, height: 844}]) {
    for (const [slug, city, allowed] of cities) {
      const page = await browser.newPage({ viewport });
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.goto(origin + '/areas/' + slug + '.html', {waitUntil: 'domcontentloaded'});
      await page.waitForFunction(() => /^\d+ communities$/.test(document.querySelector('#community-count')?.textContent||''), {timeout:30000});
      assert.match(await page.locator('h1').first().innerText(), new RegExp(city.replace('.', '\.'), 'i'));
      assert.equal(await page.locator('link[rel=canonical]').getAttribute('href'), 'https://jus3d.com/areas/' + slug + '.html');
      assert.equal(await page.locator('#city').inputValue(),city);
      assert.equal(await page.locator('#community-city').inputValue(),city);
      assert.equal(await page.locator('#city').isDisabled(),true);
      assert.equal(await page.locator('#community-city').isDisabled(),true);
      const links=await page.locator('#community-results a[href^="/communities/"]').evaluateAll(nodes=>nodes.map(n=>n.getAttribute('href')));
      const actual=new Set(links.map(link=>link.split('/').pop().replace('.html','')));
      assert.deepEqual(actual,allowed,city+' community visibility');
      assert.equal(Number.parseInt(await page.locator('#community-count').innerText()),allowed.size);
      const count=Number.parseInt(await page.locator('#count').innerText());
      const expected={Groveland:44,'St. Cloud':43,'Haines City':21,Clermont:0,Davenport:0}[city];
      // All 108 active homes are distributed by community, plus one Coming Soon in Villa Mar.
      const counts={Groveland:44,'St. Cloud':43,'Haines City':21,Clermont:0,Davenport:0};
      assert.equal(count,counts[city],city+' filtered home count');
      assert.equal(await page.locator('body').evaluate(el=>el.scrollWidth>innerWidth+2),false,city+' horizontal overflow');
      assert.deepEqual(errors,[],city+' page JavaScript errors');
      await page.close();
    }

    const page=await browser.newPage({viewport});
    await page.goto(origin + '/', {waitUntil:'domcontentloaded'});
    await page.waitForFunction(()=>/^\d+ communities$/.test(document.querySelector('#community-count')?.textContent||''));
    assert.equal(await page.locator('#community-count').innerText(),'5 communities');
    assert.equal(await page.locator('#community-results a[href="/communities/villa-mar.html"]').count(),0);
    assert.equal(await page.request.get(origin+'/communities/villa-mar.html').then(r=>r.ok()),true);
    const villa=await browser.newPage({viewport});
    await villa.goto(origin+'/communities/villa-mar.html');
    assert.equal(await villa.getByRole('heading',{name:/Still interested in Villa Mar/i}).count(),1);
    assert.equal(await villa.getByRole('link',{name:'Inquire About Future Availability'}).count(),1);
    await villa.close();
    await page.close();
  }
  console.log('PASS: desktop/mobile city visibility, counts, SEO fallback, filters, layout');
} finally { await browser.close(); }
