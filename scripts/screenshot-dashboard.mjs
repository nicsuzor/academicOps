#!/usr/bin/env node
/**
 * screenshot-dashboard.mjs — Automated UX audit screenshots for the overwhelm dashboard.
 *
 * Usage:
 *   node scripts/screenshot-dashboard.mjs [--url URL] [--out DIR]
 *
 * Defaults:
 *   --url  http://localhost:5173/
 *   --out  ./screenshots/dashboard-audit-YYYYMMDD/
 *
 * Requires: npx playwright (chromium browser installed)
 *   Install if needed: npx playwright install chromium
 */

import { chromium } from "playwright";
import { mkdirSync, existsSync } from "fs";
import { resolve } from "path";

const args = process.argv.slice(2);
function getArg(name, fallback) {
  const idx = args.indexOf(name);
  return idx !== -1 && args[idx + 1] ? args[idx + 1] : fallback;
}

const BASE_URL = getArg(
  "--url",
  "http://localhost:5173/",
);
const today = new Date().toISOString().slice(0, 10).replace(/-/g, "");
const OUT_DIR = resolve(
  getArg("--out", `./screenshots/dashboard-audit-${today}`),
);

if (!existsSync(OUT_DIR)) mkdirSync(OUT_DIR, { recursive: true });

const VIEWPORT = { width: 1920, height: 1080 };
const WAIT_MS = 3000; // time to let D3/iframe views render

async function clickButton(page, text) {
  const btn = page.locator(`button`, { hasText: text }).first();
  await btn.click();
  await page.waitForTimeout(WAIT_MS);
}

async function shot(page, name, { fullPage = false } = {}) {
  const path = resolve(OUT_DIR, `${name}.png`);
  await page.screenshot({ path, fullPage, type: "png" });
  console.log(`  -> ${name}.png`);
}

async function main() {
  console.log(`Dashboard screenshot audit`);
  console.log(`  URL: ${BASE_URL}`);
  console.log(`  Output: ${OUT_DIR}\n`);

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: VIEWPORT });
  const page = await context.newPage();

  // ── 1. Dashboard (home) view — viewport ──────────────────────────
  console.log("[1/9] Dashboard home (viewport)...");
  await page.goto(BASE_URL, { waitUntil: "networkidle" });
  await page.waitForTimeout(WAIT_MS);
  await shot(page, "01-dashboard-home");

  // ── 2. Dashboard (home) view — full page ─────────────────────────
  console.log("[2/9] Dashboard home (full page)...");
  await shot(page, "01-dashboard-home-full", { fullPage: true });

  // ── 3. Task Graph — Treemap ───────────────────────────────────────
  console.log("[3/9] Task Graph — Treemap...");
  await clickButton(page, "TASK GRAPH");
  // Treemap is the default view
  await shot(page, "02-taskgraph-treemap");

  // ── 4. Task Graph — Circle Pack ───────────────────────────────────
  console.log("[4/9] Task Graph — Circle Pack...");
  await clickButton(page, "Circle Pack");
  await shot(page, "03-taskgraph-circlepack");

  // ── 5. Task Graph — Force Atlas 2 ────────────────────────────────
  console.log("[5/9] Task Graph — Force Atlas 2...");
  await clickButton(page, "Force Atlas 2");
  await shot(page, "04-taskgraph-forceatlas");

  // ── 6. Task Graph — SFDP ─────────────────────────────────────────
  console.log("[6/9] Task Graph — SFDP...");
  await clickButton(page, "SFDP");
  await shot(page, "05-taskgraph-sfdp");

  // ── 7. Task Graph — Arc Diagram ──────────────────────────────────
  console.log("[7/9] Task Graph — Arc Diagram...");
  await clickButton(page, "Arc Diagram");
  await shot(page, "06-taskgraph-arc");

  // ── 8. Threaded Tasks view ────────────────────────────────────────
  console.log("[8/9] Threaded Tasks...");
  await clickButton(page, "THREADED TASKS");
  await shot(page, "07-threaded-tasks");

  // ── 9. Threaded Tasks — task detail panel ─────────────────────────
  console.log("[9/9] Threaded Tasks — detail panel...");
  // Click the first data row in the task table (skip header row)
  const dataRows = page.locator("table tr").filter({ hasText: /aops-|overwhel|framewor|archive/ });
  if (await dataRows.count()) {
    await dataRows.first().click();
    await page.waitForTimeout(2000);
    await shot(page, "08-threaded-task-detail");
  } else {
    // Fallback: try clicking any table cell that looks like a task ID
    const taskCell = page.locator("td").filter({ hasText: /^[a-z]+-[a-z0-9]/ }).first();
    if (await taskCell.count()) {
      await taskCell.click();
      await page.waitForTimeout(2000);
      await shot(page, "08-threaded-task-detail");
    } else {
      console.log("  (no task rows found, skipping detail screenshot)");
    }
  }

  // ── Sidebar open (bonus, conditional) ───────────────────────────
  console.log("[+] Sidebar open state...");
  const sidebarBtn = page.locator("button", { hasText: "SIDEBAR" }).first();
  if (await sidebarBtn.count()) {
    await sidebarBtn.click();
    await page.waitForTimeout(1000);
    await shot(page, "09-sidebar-open");
  }

  await browser.close();
  console.log(`\nDone! ${OUT_DIR}`);
}

main().catch((err) => {
  console.error("Screenshot script failed:", err);
  process.exit(1);
});
