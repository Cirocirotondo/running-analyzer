// Which frame does a real browser show when the player seeks to a row of a Playback Video?
//   node browser_frames.mjs <video.mp4> <times.json>   -> prints the barcode index seen at each time
// Playwright is resolved from PLAYWRIGHT_DIR (a folder with node_modules/playwright).
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { join } from "node:path";

const require = createRequire(join(process.env.PLAYWRIGHT_DIR ?? process.cwd(), "package.json"));
const { chromium } = require("playwright");
const [video, timesFile] = process.argv.slice(2);
const times = JSON.parse(readFileSync(timesFile, "utf8"));
const BITS = 12;

const browser = await chromium.launch();
const page = await browser.newPage();
await page.setContent("<video id=v muted preload=auto></video><canvas id=c></canvas>");
// A blob URL keeps the video same-origin (the canvas stays readable) and fully seekable.
await page.evaluate(async (b64) => {
  const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
  const v = document.getElementById("v");
  v.src = URL.createObjectURL(new Blob([bytes], { type: "video/mp4" }));
  await new Promise((r, e) => { v.onloadeddata = r; v.onerror = () => e(new Error("cannot decode the video")); });
}, readFileSync(video).toString("base64"));

const seen = [];
for (const t of times) {
  seen.push(await page.evaluate(async ({ t, BITS }) => {
    const v = document.getElementById("v");
    const c = document.getElementById("c");
    await new Promise((r) => { v.addEventListener("seeked", r, { once: true }); v.currentTime = t; });
    await new Promise((r) => { if (v.requestVideoFrameCallback) v.requestVideoFrameCallback(() => r()); setTimeout(r, 300); });
    c.width = v.videoWidth; c.height = v.videoHeight;
    const ctx = c.getContext("2d");
    ctx.drawImage(v, 0, 0);
    const col = Math.floor(c.width / BITS);
    let index = 0;
    for (let b = 0; b < BITS; b++) {
      const d = ctx.getImageData(b * col + col / 4, 0, col / 2, c.height).data;
      let sum = 0;
      for (let i = 0; i < d.length; i += 4) sum += d[i + 1];
      if (sum / (d.length / 4) > 127) index |= 1 << b;
    }
    return index;
  }, { t, BITS }));
}
console.log(JSON.stringify(seen));
await browser.close();
