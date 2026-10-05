// Render out/<market>.html in headless Chromium and fail on script errors or horizontal overflow.
// Usage: NODE_PATH=$(npm root -g) node scripts/check_render.js kr us
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

(async () => {
  const markets = process.argv.slice(2).length ? process.argv.slice(2) : ['kr', 'us'];
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' }).catch(() => chromium.launch());
  let failed = false;
  for (const m of markets) {
    const file = path.join(__dirname, '..', 'out', m + '.html');
    const doc = '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body>' + fs.readFileSync(file, 'utf8') + '</body></html>';
    for (const [w, scheme] of [[1180, 'light'], [390, 'dark']]) {
      const page = await browser.newPage({ viewport: { width: w, height: 900 }, colorScheme: scheme });
      const errs = [];
      page.on('pageerror', e => errs.push(e.message));
      page.on('console', msg => { if (msg.type() === 'error' && !/ERR_CERT|fonts\.g|net::/.test(msg.text())) errs.push(msg.text()); });
      await page.setContent(doc, { waitUntil: 'load' }).catch(() => {});
      await page.waitForTimeout(500);
      const [sw, iw, cards] = await page.evaluate(() => [document.documentElement.scrollWidth, innerWidth, document.querySelectorAll('.vc-card').length]);
      const ok = !errs.length && sw <= iw && cards > 0;
      failed = failed || !ok;
      console.log(`${m} ${w}px ${scheme}: ${ok ? 'ok' : 'FAIL'} (cards ${cards}, scrollWidth ${sw}/${iw})${errs.length ? ' errors: ' + errs.join(' | ') : ''}`);
      await page.close();
    }
  }
  await browser.close();
  process.exit(failed ? 1 : 0);
})();
