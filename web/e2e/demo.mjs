// Manual browser check of the demo flow (Phase 3 gate). Needs `npx playwright install chromium` once.
// Usage: node web/e2e/demo.mjs http://127.0.0.1:8000 /tmp/jatayu-shots
// Fails if the page requests anything that is not on the local server (proves the UI is offline-clean).
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

const [base = "http://127.0.0.1:8000", out = "/tmp/jatayu-shots"] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const origin = new URL(base).origin;
const offsite = [];
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
page.on("request", (r) => { if (!r.url().startsWith(origin) && !r.url().startsWith("data:")) offsite.push(r.url()); });

await page.goto(base + "/", { waitUntil: "networkidle" });
await page.fill('input[aria-label="New incident label"]', "E2E demo");
await page.click("text=New incident");
await page.fill('input[aria-label="Type an utterance"]', "gave 4 mg ondansetron IV two minutes ago");
await page.click("button:has-text('Send')");
await page.waitForSelector("article.entry h3:has-text('ondansetron')", { timeout: 60000 });
await page.screenshot({ path: `${out}/1-capture.png`, fullPage: true });
await page.click("article.entry button:has-text('Confirm')");
await page.waitForSelector("article.entry .status[data-status='confirmed']", { timeout: 20000 });
await page.screenshot({ path: `${out}/2-confirmed.png`, fullPage: true });
await page.click("nav >> text=Audit");
await page.click("button:has-text('Verify chain')");
await page.waitForSelector(".banner[data-tone='ok']", { timeout: 20000 });
await page.screenshot({ path: `${out}/3-audit.png`, fullPage: true });
await browser.close();

if (offsite.length) { console.error("OFF-SITE REQUESTS:", offsite); process.exit(1); }
console.log(`demo flow OK; screenshots in ${out}; 0 off-site requests`);
