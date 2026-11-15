// Backup video of the demo's TYPED path (docs/demo_script.md, fallback for "screen fails"). Synthetic sentences only.
// Run against a THROWAWAY server (its own temp database), never the demo database:
//   node web/e2e/demo_video.mjs http://127.0.0.1:8767 <out dir>      (needs Playwright's chromium installed once)
// Writes <out dir>/*.webm (Playwright screen recording, no audio) and prints its path.
import { chromium } from "playwright";
import { mkdirSync, readdirSync } from "node:fs";

const [base = "http://127.0.0.1:8767", out = "/tmp/jatayu-video"] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const SENTENCES = [
  "gave point three milligrams adrenaline IM two minutes ago",
  "patient is allergic to morphine",
  "ondansetron eight, no sorry, four milligrams IV",
  "gave ten milligrams adrenaline IM just now",
  "gave diclofenac seventy five milligrams IM",
  "started CPR at ten forty",
];
const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1280, height: 860 }, recordVideo: { dir: out, size: { width: 1280, height: 860 } } });
const page = await ctx.newPage();
const pause = (ms) => page.waitForTimeout(ms);
await page.goto(base + "/", { waitUntil: "networkidle" });
await pause(1500);
await page.getByLabel("New incident label").fill("Demo — synthetic patient");
await page.getByRole("button", { name: "New incident" }).click();
await pause(1200);
for (const s of SENTENCES) {
  await page.getByLabel("Type an utterance").pressSequentially(s, { delay: 25 });
  await page.getByRole("button", { name: "Send" }).click();
  await page.waitForFunction((n) => document.querySelectorAll("article.entry").length >= n, SENTENCES.indexOf(s) + 1);
  await pause(2500);
}
// Confirm the first adrenaline entry (no high flags) and the allergy (every check ticked: it stays NOT GIVEN).
const cards = page.locator("article.entry");
const byTitle = (t) => cards.filter({ has: page.locator(".drug-name", { hasText: new RegExp(`^${t}$`, "i") }) });
await byTitle("epinephrine").last().getByRole("button", { name: "Confirm" }).click();
await pause(1500);
await byTitle("morphine").getByRole("button", { name: "Confirm" }).click();
await page.waitForSelector("dialog[open]");
await pause(1500);
for (const box of await page.locator("dialog[open] input[type=checkbox]").all()) { await box.check(); await pause(500); }
await pause(800);
await page.locator("dialog[open]").getByRole("button", { name: /^Confirm/ }).click();
await pause(1500);
// Reject the 10 mg adrenaline (out of range, too soon).
await byTitle("epinephrine").first().getByRole("button", { name: "Reject" }).click();
await pause(2000);
await page.getByRole("link", { name: "Audit" }).click();
await pause(1000);
await page.getByRole("button", { name: "Verify chain" }).click();
await pause(2500);
await page.getByRole("link", { name: "Incidents" }).click();
await pause(2500);
await ctx.close();
await browser.close();
console.log(readdirSync(out).filter((f) => f.endsWith(".webm")).map((f) => `${out}/${f}`).join("\n"));
