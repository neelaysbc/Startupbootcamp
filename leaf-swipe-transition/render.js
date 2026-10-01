// Render the stinger to a transparent PNG sequence.
// usage: node render.js <fps> <outdir> [samples=10] [only-frames e.g. 0,30,47]
const { chromium } = require(process.env.PLAYWRIGHT_PATH || '/opt/node22/lib/node_modules/playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const fps = parseFloat(process.argv[2] || '60');
  const outdir = process.argv[3] || `frames_${fps}`;
  const samples = parseInt(process.argv[4] || '10', 10);
  const only = process.argv[5] ? process.argv[5].split(',').map(Number) : null;
  fs.mkdirSync(outdir, { recursive: true });

  const browser = await chromium.launch({
    executablePath: process.env.CHROME_PATH || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
  });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  await page.goto('file://' + path.resolve(__dirname, 'stinger.html'));
  await page.waitForFunction('window.ready === true');
  const duration = await page.evaluate('window.DURATION');
  const n = Math.round(duration * fps);
  const frames = only || [...Array(n).keys()];
  for (const f of frames) {
    const url = await page.evaluate(([t, fps, s]) => window.renderFrame(t, fps, s), [f / fps, fps, samples]);
    fs.writeFileSync(path.join(outdir, `frame_${String(f).padStart(4, '0')}.png`),
      Buffer.from(url.split(',')[1], 'base64'));
  }
  await browser.close();
  console.log(`rendered ${frames.length} frames @ ${fps} fps -> ${outdir}`);
})();
