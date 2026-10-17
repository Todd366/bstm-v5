// Browser smoke test: serves public/ and answers the API with canned data,
// then drives every role's main screens in real Chromium. Catches script
// errors, broken wiring and missing screens. It does NOT test the backend.
// Run: NODE_PATH=<playwright module dir> node tests/e2e/smoke.mjs
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const PUB = path.resolve(path.dirname(new URL(import.meta.url).pathname), "../../public");
const YID = "11111111-1111-1111-1111-111111111111";
const seen = [];
const T = { "app.js": "application/javascript", "app.css": "text/css", "index.html": "text/html", "favicon.svg": "image/svg+xml" };

const server = http.createServer((req, res) => {
  const f = req.url === "/" ? "index.html" : req.url.slice(1).split("?")[0];
  const p = path.join(PUB, f);
  if (fs.existsSync(p) && fs.statSync(p).isFile()) { res.writeHead(200, { "Content-Type": T[f] || "text/plain" }); return res.end(fs.readFileSync(p)); }
  res.writeHead(404); res.end("nf");
});
await new Promise((r) => server.listen(0, r));
const base = "http://localhost:" + server.address().port;

const ok = (b) => ({ status: 200, contentType: "application/json", body: JSON.stringify(b) });
const API = (m, u, h, body) => {
  const p = u.pathname;
  seen.push({ m, p, q: u.search, key: h["idempotency-key"], body });
  if (p === "/catalog/capabilities") return ok([{ id: "c1", name: "Web design", category: "Technology" }]);
  if (p === "/catalog/departments") return ok(["Web Development", "Music"]);
  if (p === "/youth/login") return ok({ access_token: "yt" });
  if (p === "/businesses/login") return ok({ access_token: "bt" });
  if (p === "/me") return ok({ id: YID, name: "Thobo Test", level: "Seed", completed_trials: 1, completed_opportunities: 1, reputation_score: 55, revenue: 70, bio: "Builder", public_profile: true, location: "Maun", availability: "Weekends", equipment: "Phone" });
  if (p === "/me/assignments") return ok([
    { assignment_id: "a1", opportunity_title: "Paint wall", status: "Accepted", trial_id: "t1", trial_status: "Active", opportunity_status: "InProgress", budget: 500, business_name: "Shop" },
    { assignment_id: "a2", opportunity_title: "Old job", status: "Completed", trial_id: "t2", trial_status: "Completed", opportunity_status: "Completed", budget: 100 }]);
  if (p === "/me/opportunities") return ok([]);
  if (p === "/me/trials") return ok([]);
  if (p === "/me/brief") return { status: 404, contentType: "application/json", body: '{"detail":"none"}' };
  if (p === "/me/opportunities/browse") return ok([{ id: "o9", title: "Fix website", business_name: "Biz", business_location: "Maun", budget: 300, description: "d" }]);
  if (p === "/me/capabilities") return ok([{ capability_id: "c1", capability_name: "Web design", level: "Beginner", verified: true }]);
  if (p === "/me/evidence") return ok([]);
  if (p === "/me/earnings") return ok({ totals: { awaiting_business: 350, pending_payout: 70, paid_out: 140, earned: 560 }, payouts: [{ id: "p1", amount: 70, status: "Pending", destination: null, invoice_reference: "BSTM-1000", opportunity_title: "Old job" }, { id: "p2", amount: 140, status: "Paid", destination: "Thobo · 71234567", provider_ref: "MZ-77", paid_at: "2026-10-01T00:00:00Z", opportunity_title: "X" }] });
  if (p === "/me/payout-account") return { status: 200, contentType: "application/json", body: "null" };
  if (p === "/me/notifications") return ok({ unread: 2, items: [{ title: "You got the job", body: "Open My work", created_at: "2026-10-01T00:00:00Z", read_at: null }] });
  if (p === "/me/notifications/read") return ok({ ok: true });
  if (p === "/me/profile" || p === "/me/payout-account") return ok({ status: "saved" });
  if (p.startsWith("/public/profiles/")) return ok({ name: "Thobo Test", location: "Maun", level: "Seed", bio: "Builder", completed_jobs: 1, completed_trials: 1, verified_skills: [{ name: "Web design", level: "Beginner", verified: true }], declared_skills: [] });
  if (p === "/biz") return ok({ id: "b1", name: "Test Shop", payment_instructions: "MyZaka 71234567 - use invoice number" });
  if (p === "/biz/opportunities" && m === "GET") return ok([{ id: "o1", title: "Paint wall", department: null, budget: 500, status: "Open", approval_status: "Approved", people: 1 }, { id: "o2", title: "New logo", budget: 0, status: "Open", approval_status: "Pending", people: 0 }]);
  if (p === "/biz/opportunities" && m === "POST") return ok({ status: "pending_approval", id: "o3" });
  if (p === "/biz/opportunities/o1/people") return ok([{ assignment_id: "a1", name: "Thobo", location: "Maun", level: "Seed", status: "Accepted", opportunity_status: "InProgress", trial_id: "t1", trial_status: "Submitted", submission: { summary: "Painted it", link: "https://example.com/x" }, verified_skills: 1 }]);
  if (p === "/biz/trials/t1/approve") return ok({ status: "approved" });
  if (p === "/biz/invoices" && m === "GET") return ok([{ id: "i1", reference: "BSTM-1000", amount: 500, paid_amount: 0, pending_payments: 0, status: "Issued", opportunity_title: "Paint wall", created_at: "2026-10-01T00:00:00Z" }]);
  if (p === "/biz/invoices/i1/payments") return ok({ status: "submitted", id: "pay1" });
  if (p === "/biz/notifications") return ok({ unread: 0, items: [] });
  if (p === "/admin/stats") return ok({ counts: { youth: 21, businesses: 3, opportunities: 4, trials: 2 } });
  if (p === "/admin/queue") return ok({
    applications: [], trials: [],
    jobs: [{ opportunity_id: "o2", title: "New logo", business_name: "Test Shop", business_location: "Maun", budget: 0, description: "Make logo" }],
    payments: [{ payment_id: "pay1", amount: 500, method: "MyZaka", provider_ref: "MZ12345", invoice_reference: "BSTM-1000", business_name: "Test Shop", created_at: "2026-10-01T00:00:00Z" }],
    payouts: [{ payout_id: "po1", amount: 350, method: "MyZaka", destination: "Thobo · 71234567", youth_name: "Thobo", invoice_reference: "BSTM-1000" }],
    unmatched: [{ id: "u1", provider: "sms-bridge", provider_ref: "UNK-1", invoice_reference: "BSTM-9", amount: 100, reason: "No invoice with that reference", created_at: "2026-10-01T00:00:00Z" }] });
  if (p === "/admin/activity") return ok([]);
  if (p === "/invoices") return ok([{ id: "i1", reference: "BSTM-1000", amount: 500, youth_share: 350, platform_share: 150, paid_amount: 0, pending_payments: 0, status: "Issued", business_name: "Test Shop", opportunity_title: "Paint wall", created_at: "2026-10-01T00:00:00Z" }]);
  if (p === "/invoices/i1/payments") return ok({ status: "submitted" });
  if (p === "/payments/pay1/confirm") return ok({ ok: true });
  return { status: 404, contentType: "application/json", body: '{"detail":"not mocked: ' + p + '"}' };
};

const fails = [];
const check = (name, cond) => { if (!cond) { fails.push(name); console.log("FAIL", name); } else console.log("ok  ", name); };

const browser = await chromium.launch({ executablePath: process.env.CHROME || "/opt/pw-browsers/chromium-1194/chrome-linux/chrome", args: ["--no-sandbox"] });
const ctx = await browser.newContext({ viewport: { width: 390, height: 800 }, serviceWorkers: "block" });
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push("pageerror: " + e.message));
page.on("console", (m) => { if (m.type() === "error" && !/Failed to load resource/.test(m.text())) errors.push("console: " + m.text()); });
await page.route("**/*", async (route) => {
  const u = new URL(route.request().url());
  if (u.origin !== base || !/^\/(catalog|youth|businesses|me|biz|admin|public|invoices|payments|payouts|opportunities|unmatched)/.test(u.pathname)) return route.continue();
  const r = route.request();
  let body = null; try { body = r.postData() ? JSON.parse(r.postData()) : null; } catch (e) {}
  await route.fulfill(API(r.method(), u, r.headers(), body));
});
const dismiss = () => page.on("dialog", (d) => d.accept());
dismiss();
const text = async (t) => (await page.getByText(t, { exact: false }).first().isVisible().catch(() => false));
const tab = (n) => page.locator("#tabs button").filter({ hasText: new RegExp(n + "$") }).click();
const click = (name, opt) => page.getByRole("button", { name, exact: !(opt && opt.exact === false) }).first().click();

// ---- youth
await page.goto(base + "/");
check("landing shows business login", await text("Log in as business"));
await click("Log in", { exact: true });
await page.fill("[name=email]", "t@example.com"); await page.fill("[name=password]", "correct-horse-battery");
await page.locator("form button[type=submit]").click();
await page.waitForSelector("text=Hello, Thobo");
check("youth home", await text("Hello, Thobo"));
check("home shows ledger label 'Paid to you'", await text("Paid to you"));
check("bell shows unread count", (await page.locator("#bellN").textContent()) === "2");
await tab("Money");
await page.waitForSelector("text=Waiting for business");
check("money: totals + payout form + payouts", (await text("Add where we should pay you")) && (await text("Being prepared")) && (await text("MZ-77")));
await page.fill("[name=account_name]", "Thobo"); await page.fill("[name=account_ref]", "71234567");
await page.locator("form button[type=submit]").click();
await page.waitForTimeout(300);
check("payout account sent as PUT", seen.some((s) => s.m === "PUT" && s.p === "/me/payout-account" && s.body.account_ref === "71234567"));
await tab("Me");
await page.waitForSelector("text=Your profile");
check("profile editor + public link", (await text("Your public link")) && (await text("Let businesses see my profile")));
await page.locator("form button[type=submit]").click(); await page.waitForTimeout(300);
check("profile saved as PUT", seen.some((s) => s.m === "PUT" && s.p === "/me/profile" && s.body.public_profile === true));
await click("Skills"); await page.waitForSelector("text=Web design");
check("skills sub-nav", await text("Verified"));
await click("Proof", { exact: true }); await page.waitForSelector("text=Add proof of your work");
await tab("Jobs");
await click("All open"); await page.waitForSelector("text=Fix website");
await page.fill("[name=q]", "web"); await page.fill("[name=location]", "Maun");
await page.getByRole("button", { name: "Search" }).click(); await page.waitForTimeout(300);
check("job search sends q + location", seen.some((s) => s.p === "/me/opportunities/browse" && s.q.includes("q=web") && s.q.includes("location=Maun")));
await tab("My work"); await page.waitForSelector("text=Paint wall");
check("my work: submit form, stop work, done message", (await text("Submit my work")) && (await text("Stop this work")) && (await text("See Money")));
await page.locator("#bellBtn").click(); await page.waitForSelector("text=You got the job");
check("alerts list", await text("You got the job"));
await page.evaluate(() => { location.hash = "#/p/11111111-1111-1111-1111-111111111111"; });
await page.waitForSelector("text=Verified skills");
check("public profile page", (await text("Thobo Test")) && (await text("Claimed skills")));
await page.evaluate(() => { location.hash = ""; });
await page.screenshot({ path: process.env.SHOTS ? process.env.SHOTS + "/youth.png" : "/tmp/youth.png" });
await page.getByRole("button", { name: "Log out" }).click();

// ---- business
await page.waitForSelector("text=Welcome to BSTM Activation");
await click("Log in as business");
await page.fill("[name=email]", "o@shop.bw"); await page.fill("[name=password]", "correct-horse-battery");
await page.locator("form button[type=submit]").click();
await page.waitForSelector("text=Test Shop");
check("business portal jobs + approval tags", (await text("Waiting for BSTM approval")) && (await text("Live")));
await page.getByRole("button", { name: "People on this job" }).first().click();
await page.waitForSelector("text=Painted it");
check("business sees submitted work + approve", await text("Approve work"));
await page.fill("input[aria-label=Score]", "90"); await click("Approve work"); await page.waitForTimeout(300);
check("approve work posts score", seen.some((s) => s.p === "/biz/trials/t1/approve" && s.body.score === 90));
await tab("Post a job"); await page.waitForSelector("text=What do you need done?");
await page.fill("[name=title]", "Make a poster"); await page.fill("[name=budget]", "200");
await page.locator("form button[type=submit]").click(); await page.waitForTimeout(300);
check("post job", seen.some((s) => s.m === "POST" && s.p === "/biz/opportunities" && s.body.title === "Make a poster" && s.body.budget === 200));
await tab("Invoices"); await page.waitForSelector("text=BSTM-1000");
check("invoice + payment instructions", (await text("MyZaka 71234567")) && (await text("I have paid")));
await page.fill("[name=provider_ref]", "MZ99887766"); await click("I have paid"); await page.waitForTimeout(300);
const pay = seen.find((s) => s.p === "/biz/invoices/i1/payments");
check("payment sent with Idempotency-Key and reference", pay && pay.key && pay.key.length > 8 && pay.body.provider_ref === "MZ99887766" && pay.body.method === "MyZaka");
await page.screenshot({ path: process.env.SHOTS ? process.env.SHOTS + "/biz.png" : "/tmp/biz.png" });
await page.getByRole("button", { name: "Log out" }).click();

// ---- staff
await page.waitForSelector("text=Welcome to BSTM Activation");
await click("Staff sign in");
await page.fill("[name=key]", "k"); await page.locator("form button[type=submit]").click();
await page.waitForSelector("text=Payments to confirm");
check("staff queue: money sections", (await text("Unmatched money")) && (await text("Payouts to send")) && (await text("Jobs to approve")) && (await text("Money received")));
await click("Money received"); await page.waitForTimeout(300);
check("confirm payment", seen.some((s) => s.p === "/payments/pay1/confirm"));
await tab("Money"); await page.waitForSelector("text=BSTM-1000");
check("staff money tab", (await text("Record a payment")) && (await text("Billed")));
await page.screenshot({ path: process.env.SHOTS ? process.env.SHOTS + "/staff.png" : "/tmp/staff.png" });

check("no script or console errors", errors.length === 0);
if (errors.length) console.log(errors.join("\n"));
await browser.close(); server.close();
console.log(fails.length ? "\n" + fails.length + " FAILED" : "\nALL BROWSER CHECKS PASSED");
process.exit(fails.length ? 1 : 0);
