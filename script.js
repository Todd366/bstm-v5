/* ============================================================
   BSTM THRESHOLD — onboarding logic

   Youth self-registration (POST /youth) is wired to the real
   BSTM V5 API — see registerYouth() below. The business-audit
   flow and trial/field-audit submission are still local-only;
   those backend endpoints require an existing business/opportunity
   context that this UI doesn't collect yet — still marked with
   // API: ... where they belong.
   ============================================================ */

// POST /youth is deliberately public (no key) on the backend — the
// admin API key must never be embedded in code shipped to a browser,
// since anyone can view-source it. Every other BSTM V5 route requires
// that key and is NOT safe to call directly from this frontend.
const API_BASE = "https://bstm-v5.vercel.app";

// Maps the wizard's raw field names to what POST /youth actually
// accepts. Fields with no direct match (age, position, education,
// skillLevel, income, capital, challenges) go into `intake` as a full
// raw snapshot, alongside everything else, rather than being dropped.
function mapYouthPayload(y) {
  const { password, ...intakeSnapshot } = y;
  return {
    name: y.name,
    location: y.location,
    goal: y.aspiration,
    email: y.email,
    password: y.password,
    passion: (y.interests || []).join(", ") || null,
    availability: y.availability || null,
    equipment: (y.resources || []).join(", ") || null,
    intake: intakeSnapshot,
  };
}

async function registerYouth(y) {
  const response = await fetch(`${API_BASE}/youth`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(mapYouthPayload(y)),
  });

  const body = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(body.detail || `Registration failed (${response.status})`);
  }

  return body.id;
}

async function createBusinessRecord(b) {
  const response = await fetch(`${API_BASE}/businesses`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: b.name,
      owner: b.owner,
      sector: b.sector,
      location: b.location,
      main_problem: b.problem,
    }),
  });

  const body = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(body.detail || `Business registration failed (${response.status})`);
  }

  return body.id;
}

// Token lives in localStorage so a returning youth doesn't have to log
// in on every visit — this is a real deployed site (not a sandboxed
// Claude artifact), so localStorage is the normal, correct tool here.
const TOKEN_STORAGE_KEY = "bstm_access_token";

function saveToken(token) {
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

function loadToken() {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

function clearToken() {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
}

async function loginYouth(email, password) {
  const response = await fetch(`${API_BASE}/youth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  const body = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(body.detail || `Login failed (${response.status})`);
  }

  return body.access_token;
}

async function fetchMyProfile(token) {
  const response = await fetch(`${API_BASE}/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!response.ok) {
    throw new Error("Session expired or invalid");
  }

  return response.json();
}

async function fetchMyTrials(token) {
  const response = await fetch(`${API_BASE}/me/trials`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return response.ok ? response.json() : [];
}

async function fetchMyEvidence(token) {
  const response = await fetch(`${API_BASE}/me/evidence`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return response.ok ? response.json() : [];
}

// No escaping helper existed anywhere in this file before this change —
// a pre-existing gap across the whole app, not something introduced
// here. Not retrofitting every existing template string in this pass
// (that's a separate audit), but anything new being written now
// (the dashboard) uses this rather than adding to the problem.
function escapeHtml(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

const DEPARTMENTS = [
  { id: "ai-ml", name: "AI & Machine Learning", cat: "Technology", tags: ["technology", "research"], resource: "high", entry: "Telegram AI bot builds" },
  { id: "trading", name: "Trading Automation", cat: "Technology", tags: ["technology", "finance"], resource: "medium", entry: "Custom MT5 indicators" },
  { id: "vpn-security", name: "VPN & Network Security", cat: "Technology", tags: ["technology"], resource: "high", entry: "Privacy tooling" },
  { id: "web-dev", name: "Web Development", cat: "Technology", tags: ["technology"], resource: "low", entry: "Business websites" },
  { id: "mobile-dev", name: "Mobile Applications", cat: "Technology", tags: ["technology"], resource: "medium", entry: "Progressive web apps" },
  { id: "system-integration", name: "System Integration & API", cat: "Technology", tags: ["technology"], resource: "medium", entry: "Connecting BSTM platforms" },
  { id: "data-science", name: "Data Science & Analytics", cat: "Technology", tags: ["technology", "research"], resource: "medium", entry: "Business dashboards" },
  { id: "blockchain", name: "Blockchain & Cryptocurrency", cat: "Technology", tags: ["technology", "finance"], resource: "high", entry: "THoBoCoin wallet work" },
  { id: "design", name: "Graphic Design & Branding", cat: "Creative", tags: ["creative"], resource: "low", entry: "Logos and brand kits" },
  { id: "content", name: "Content Creation & Copywriting", cat: "Creative", tags: ["creative"], resource: "low", entry: "Documentation and books" },
  { id: "social-media", name: "Social Media Management", cat: "Creative", tags: ["creative", "community"], resource: "low", entry: "Daily content for a business" },
  { id: "marketing", name: "Digital Marketing & Advertising", cat: "Creative", tags: ["creative", "community"], resource: "low", entry: "Growth campaigns" },
  { id: "tutorial-center", name: "BSTM Tutorial Center", cat: "Creative", tags: ["community"], resource: "medium", entry: "Course creation" },
  { id: "music", name: "Music Department", cat: "Creative", tags: ["creative"], resource: "low", entry: "Production and publishing" },
  { id: "clothing", name: "BSTM Clothing Brand", cat: "Creative", tags: ["creative", "trades"], resource: "medium", entry: "Merchandise design" },
  { id: "security", name: "Private Security", cat: "Operations", tags: ["trades"], resource: "medium", entry: "Field security roles" },
  { id: "cablink", name: "CabLink Transportation", cat: "Operations", tags: ["trades", "business"], resource: "medium", entry: "Driving and logistics" },
  { id: "finance", name: "Finance & Accounting", cat: "Operations", tags: ["finance", "business"], resource: "low", entry: "FlowLedger bookkeeping" },
  { id: "marketplace", name: "Marketplace & E-Commerce", cat: "Operations", tags: ["business", "technology"], resource: "low", entry: "Vendor onboarding" },
  { id: "hr", name: "Human Resources & Talent Development", cat: "Operations", tags: ["business", "community"], resource: "low", entry: "Recruitment support" },
  { id: "pmo", name: "Project Management Office", cat: "Operations", tags: ["business"], resource: "low", entry: "100 Trials coordination" },
  { id: "legal", name: "Legal & Compliance", cat: "Operations", tags: ["business", "research"], resource: "medium", entry: "Documentation and policy" },
  { id: "rnd", name: "Research & Development", cat: "Research", tags: ["research", "technology"], resource: "medium", entry: "100 Trials field research" },
  { id: "healthcare", name: "Healthcare Information & Wellness", cat: "Research", tags: ["research", "community"], resource: "high", entry: "Health information systems" },
  { id: "nutrition", name: "Nutrition & Health Products", cat: "Research", tags: ["research", "trades"], resource: "medium", entry: "Product development" },
  { id: "gin", name: "G.I.N — Global Intelligence Network", cat: "Research", tags: ["research"], resource: "medium", entry: "Knowledge network building" },
  { id: "spiritual", name: "Spiritual Guidance & Consciousness", cat: "Research", tags: ["community", "research"], resource: "low", entry: "Personal growth content" },
  { id: "farming", name: "Micro Farming & Urban Agriculture", cat: "Agriculture", tags: ["agriculture", "trades"], resource: "medium", entry: "Urban farming pilots" },
  { id: "sustainability", name: "Sustainability & Environment", cat: "Agriculture", tags: ["agriculture", "research"], resource: "medium", entry: "GreenCycle projects" },
  { id: "bhd", name: "BHD — Black Hole Drive", cat: "Research", tags: ["research", "technology"], resource: "high", entry: "Advanced computing research" },
];

const CAT_COLOR = {
  Technology: "#4fd8c4",
  Creative: "#d9a441",
  Operations: "#e2665a",
  Research: "#8b8ff2",
  Agriculture: "#6fbf73",
};

const YOUTH_STEPS = [
  {
    id: "identity",
    eyebrow: "Step 1 — Identity",
    title: "Who are you, and where do you stand?",
    render: (s) => `
      <div class="field-row">
        <label class="field-label">Name</label>
        <input type="text" id="f-name" value="${s.name || ""}" placeholder="Your name">
      </div>
      <div class="field-row">
        <label class="field-label">Age</label>
        <input type="number" id="f-age" value="${s.age || ""}" placeholder="18" min="14" max="80">
      </div>
      <div class="field-row">
        <label class="field-label">Location</label>
        <input type="text" id="f-location" value="${s.location || ""}" placeholder="Gaborone, Mochudi, Maun...">
      </div>
      <div class="field-row">
        <label class="field-label">Email</label>
        <input type="email" id="f-email" value="${s.email || ""}" placeholder="you@example.com">
      </div>
      <div class="field-row">
        <label class="field-label">Password</label>
        <input type="password" id="f-password" value="${s.password || ""}" placeholder="At least 8 characters">
      </div>`,
    read: (s) => {
      s.name = document.getElementById("f-name").value.trim();
      s.age = document.getElementById("f-age").value;
      s.location = document.getElementById("f-location").value.trim();
      s.email = document.getElementById("f-email").value.trim();
      s.password = document.getElementById("f-password").value;
    },
    valid: (s) => s.name && s.age && s.location && s.email && s.email.includes("@") && s.password && s.password.length >= 8,
  },
  {
    id: "position",
    eyebrow: "Step 2 — Life position",
    title: "Where are you in life right now?",
    render: (s) => chipGroup("position", ["Student", "Unemployed", "Employed", "Entrepreneur", "Graduate", "Other"], s.position, false),
    read: (s) => (s.position = readSingle("position")),
    valid: (s) => !!s.position,
  },
  {
    id: "education",
    eyebrow: "Step 3 — Education",
    title: "What's your education background?",
    render: (s) => chipGroup("education", ["None yet", "Primary", "Junior Certificate", "Senior Certificate", "Certificate / Diploma", "Degree", "Postgraduate"], s.education, false),
    read: (s) => (s.education = readSingle("education")),
    valid: (s) => !!s.education,
  },
  {
    id: "interests",
    eyebrow: "Step 4 — Interests",
    title: "What pulls your attention?",
    sub: "Pick as many as feel true.",
    render: (s) => chipGroup("interests", ["Technology", "Business", "Creative", "Agriculture", "Trades", "Finance", "Research", "Community"], s.interests || [], true),
    read: (s) => (s.interests = readMulti("interests")),
    valid: (s) => (s.interests || []).length > 0,
  },
  {
    id: "skills",
    eyebrow: "Step 5 — Skills",
    title: "How would you rate what you can already do?",
    render: (s) => chipGroup("skills", ["Beginner", "Developing", "Intermediate", "Advanced", "Expert"], s.skillLevel, false),
    read: (s) => (s.skillLevel = readSingle("skills")),
    valid: (s) => !!s.skillLevel,
  },
  {
    id: "resources",
    eyebrow: "Step 6 — Resources",
    title: "What do you have to work with?",
    sub: "Be honest — this shapes what's realistic first.",
    render: (s) => chipGroup("resources", ["Smartphone", "Computer", "Internet access", "Transport", "A workspace"], s.resources || [], true),
    read: (s) => (s.resources = readMulti("resources")),
    valid: (s) => (s.resources || []).length > 0,
  },
  {
    id: "financial",
    eyebrow: "Step 7 — Financial reality",
    title: "What's your financial position today?",
    render: (s) => `
      <div class="field-row">
        <label class="field-label">Income</label>
        ${selectField("f-income", ["None", "Irregular", "Steady"], s.income)}
      </div>
      <div class="field-row">
        <label class="field-label">Capital available</label>
        ${selectField("f-capital", ["None", "Small (under P500)", "Moderate (P500+)"], s.capital)}
      </div>`,
    read: (s) => {
      s.income = document.getElementById("f-income").value;
      s.capital = document.getElementById("f-capital").value;
    },
    valid: (s) => s.income && s.capital,
  },
  {
    id: "availability",
    eyebrow: "Step 8 — Availability",
    title: "How much time can you give this?",
    render: (s) => chipGroup("availability", ["Full-time", "Part-time", "Weekends", "Evenings only"], s.availability, false),
    read: (s) => (s.availability = readSingle("availability")),
    valid: (s) => !!s.availability,
  },
  {
    id: "challenges",
    eyebrow: "Step 9 — What's in the way",
    title: "What's been standing between you and this?",
    render: (s) => chipGroup("challenges", ["No experience", "No money", "No network", "No direction", "No equipment", "Confidence"], s.challenges || [], true),
    read: (s) => (s.challenges = readMulti("challenges")),
    valid: () => true,
  },
  {
    id: "aspiration",
    eyebrow: "Step 10 — Aspiration",
    title: "Where do you want this to take you?",
    render: (s) => chipGroup("aspiration", ["A steady job", "My own business", "A real skill", "To earn right now", "To learn and explore"], s.aspiration, false),
    read: (s) => (s.aspiration = readSingle("aspiration")),
    valid: (s) => !!s.aspiration,
  },
];

const state = {
  route: "boot",
  youthStep: 0,
  youth: {},
  business: {},
  audit: { ratings: {}, rooms: [] },
  myProfile: null,
};

/* ---------------- helpers ---------------- */

function chipGroup(name, options, current, multi) {
  const selected = multi ? current || [] : [current];
  return `<div class="chip-group" data-group="${name}" data-multi="${multi}">
    ${options.map(o => `<button type="button" class="chip ${selected.includes(o) ? "selected" : ""}" data-value="${o}">${o}</button>`).join("")}
  </div>`;
}

function selectField(id, options, current) {
  return `<select id="${id}">
    <option value="">Select...</option>
    ${options.map(o => `<option value="${o}" ${o === current ? "selected" : ""}>${o}</option>`).join("")}
  </select>`;
}

function readSingle(name) {
  const el = document.querySelector(`.chip-group[data-group="${name}"] .chip.selected`);
  return el ? el.dataset.value : null;
}

function readMulti(name) {
  return Array.from(document.querySelectorAll(`.chip-group[data-group="${name}"] .chip.selected`)).map(c => c.dataset.value);
}

function attachChipEvents() {
  document.querySelectorAll(".chip-group").forEach(group => {
    const multi = group.dataset.multi === "true";
    group.querySelectorAll(".chip").forEach(chip => {
      chip.addEventListener("click", () => {
        if (!multi) {
          group.querySelectorAll(".chip").forEach(c => c.classList.remove("selected"));
          chip.classList.add("selected");
        } else {
          chip.classList.toggle("selected");
        }
      });
    });
  });
}

/* ---------------- matching engine ---------------- */

const TAG_MAP = {
  Technology: "technology", Business: "business", Creative: "creative",
  Agriculture: "agriculture", Trades: "trades", Finance: "finance",
  Research: "research", Community: "community",
};

function scoreDepartments(youth) {
  const interestTags = (youth.interests || []).map(i => TAG_MAP[i]).filter(Boolean);
  const resourceLevel = (youth.resources || []).length >= 4 ? "high" : (youth.resources || []).length >= 2 ? "medium" : "low";
  const resourceRank = { low: 0, medium: 1, high: 2 };

  return DEPARTMENTS.map(dept => {
    let score = 0;
    dept.tags.forEach(tag => { if (interestTags.includes(tag)) score += 34; });
    if (resourceRank[dept.resource] <= resourceRank[resourceLevel]) score += 20;
    else score -= 15;
    if (youth.availability === "Full-time") score += 8;
    return { ...dept, score: Math.max(0, Math.min(100, score)) };
  }).sort((a, b) => b.score - a.score);
}

function buildBrief(primary, youth) {
  const missionByCat = {
    Technology: `Build and ship a working ${primary.entry.toLowerCase()} for a real BSTM-connected business.`,
    Creative: `Produce a first body of ${primary.entry.toLowerCase()} for an active BSTM client or trial business.`,
    Operations: `Take ownership of one real operational task inside ${primary.name} — ${primary.entry.toLowerCase()}.`,
    Research: `Contribute field evidence to ${primary.name} through ${primary.entry.toLowerCase()}.`,
    Agriculture: `Run a small, documented pilot in ${primary.entry.toLowerCase()}.`,
  };

  const priorities = [
    `Complete your first BSTM trial inside ${primary.name}`,
    `Document evidence — every trial builds your capability profile`,
    youth.challenges && youth.challenges.includes("No network")
      ? "Get introduced to one other builder in this department"
      : "Ask for a second opportunity once the first is reviewed",
  ];

  const learningPath = [
    `Orientation — how ${primary.name} works inside BSTM`,
    `Shadow or study one completed example`,
    `Attempt your first guided trial`,
    `Submit for review and receive feedback`,
  ];

  const resourceMultiplier = { low: 1, medium: 1.6, high: 2.4 }[primary.resource];
  const availMultiplier = youth.availability === "Full-time" ? 1.4 : youth.availability === "Part-time" ? 1 : 0.7;
  const base = 80;
  const min = Math.round(base * resourceMultiplier * availMultiplier * 0.7);
  const max = Math.round(base * resourceMultiplier * availMultiplier * 1.6);

  return {
    mission: missionByCat[primary.cat],
    priorities,
    learningPath,
    coinMin: min,
    coinMax: max,
  };
}

/* ---------------- render: boot ---------------- */

function renderBoot() {
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const lines = [
    "> initialising threshold sequence",
    "> reading identity matrix",
    "> calibrating ecosystem — 30 departments online",
    "> cutting the first facet",
  ];

  document.getElementById("stage").innerHTML = `
    <div class="center-fill">
      <div class="stone-wrap">
        <div class="stone-glow"></div>
        ${stoneSVG()}
      </div>
      <div class="boot-log">
        ${lines.map((l, i) => `<div class="boot-line" style="animation-delay:${reduced ? 0 : i * 0.45}s">${l}</div>`).join("")}
      </div>
      <div class="threshold-title">BSTM</div>
      <div class="threshold-sub">You are standing at the threshold</div>
    </div>
    <button class="skip-link" id="skip-btn">Enter →</button>
  `;

  document.getElementById("skip-btn").addEventListener("click", () => go("doors"));
  if (!reduced) setTimeout(() => go("doors"), 3600);
}

function stoneSVG() {
  return `<svg viewBox="0 0 180 180" width="180" height="180">
    <polygon points="90,10 150,55 130,150 50,150 30,55" fill="none" stroke="#d9a441" stroke-width="1.2" opacity="0.9"/>
    <polygon points="90,10 90,90 150,55" fill="#d9a441" opacity="0.12"/>
    <polygon points="90,10 90,90 30,55" fill="#4fd8c4" opacity="0.10"/>
    <polygon points="30,55 90,90 50,150" fill="#d9a441" opacity="0.08"/>
    <polygon points="150,55 90,90 130,150" fill="#4fd8c4" opacity="0.08"/>
    <polygon points="50,150 90,90 130,150" fill="#f6f3ec" opacity="0.06"/>
    <line x1="90" y1="10" x2="90" y2="90" stroke="#f6f3ec" stroke-width="0.6" opacity="0.4"/>
  </svg>`;
}

/* ---------------- render: doors ---------------- */

function renderDoors() {
  document.getElementById("stage").innerHTML = `
    <div class="center-fill" style="min-height:auto;padding-top:64px;">
      <div class="threshold-sub" style="margin-bottom:10px;">Three doors stand open</div>
      <div class="threshold-title" style="font-size:clamp(24px,5vw,36px);">Which one is yours?</div>
    </div>
    <div class="doors">
      <button class="door" id="door-youth">
        <div class="door-eyebrow">Door One</div>
        <div class="door-title">I'm here to build myself</div>
        <div class="door-desc">Youth activation — discover your capability, get matched to a department, and start your first real trial.</div>
      </button>
      <button class="door" id="door-business">
        <div class="door-eyebrow">Door Two</div>
        <div class="door-title">I run a business</div>
        <div class="door-desc">Business activation — run a health diagnosis and get matched to the departments that solve your real problems.</div>
      </button>
      <button class="door" id="door-audit">
        <div class="door-eyebrow">Door Three</div>
        <div class="door-title">I'm logging a field trial</div>
        <div class="door-desc">Fast-mode 100 Trials field audit — built for filling in minutes, not pages.</div>
      </button>
    </div>
    <button class="skip-link" id="login-link" style="margin-top:24px;">Already have an account? Log in →</button>
  `;
  document.getElementById("door-youth").addEventListener("click", () => go("youth", 0));
  document.getElementById("door-business").addEventListener("click", () => go("business-intake"));
  document.getElementById("door-audit").addEventListener("click", () => go("audit"));
  document.getElementById("login-link").addEventListener("click", () => go("login"));
}

/* ---------------- render: youth wizard ---------------- */

function renderYouth() {
  const step = YOUTH_STEPS[state.youthStep];
  const total = YOUTH_STEPS.length;

  document.getElementById("stage").innerHTML = `
    <div class="wizard">
      <div class="facet-progress">
        ${YOUTH_STEPS.map((_, i) => `<div class="facet-cut ${i <= state.youthStep ? "done" : ""}"></div>`).join("")}
      </div>
      <div class="step-eyebrow">${step.eyebrow}</div>
      <div class="step-title">${step.title}</div>
      ${step.sub ? `<div class="field-label" style="margin-top:-18px;margin-bottom:20px;">${step.sub}</div>` : ""}
      ${step.render(state.youth)}
    </div>
    <div class="wizard-nav">
      <button class="btn btn-ghost" id="wiz-back">${state.youthStep === 0 ? "← Doors" : "← Back"}</button>
      <button class="btn btn-primary" id="wiz-next">${state.youthStep === total - 1 ? "Reveal my Kgotla" : "Continue"}</button>
    </div>
  `;

  attachChipEvents();

  document.getElementById("wiz-back").addEventListener("click", () => {
    if (state.youthStep === 0) { go("doors"); return; }
    state.youthStep -= 1;
    renderYouth();
  });

  document.getElementById("wiz-next").addEventListener("click", async () => {
    step.read(state.youth);
    if (!step.valid(state.youth)) {
      flashInvalid();
      return;
    }
    if (state.youthStep === total - 1) {
      const btn = document.getElementById("wiz-next");
      const originalLabel = btn.textContent;
      btn.disabled = true;
      btn.textContent = "Submitting...";

      try {
        state.youth.id = await registerYouth(state.youth);
        go("kgotla");
      } catch (err) {
        btn.disabled = false;
        btn.textContent = originalLabel;
        showSubmissionError(err.message);
      }
      return;
    }
    state.youthStep += 1;
    renderYouth();
  });
}

function flashInvalid() {
  const nav = document.getElementById("wiz-next");
  nav.style.borderColor = "var(--warn)";
  setTimeout(() => (nav.style.borderColor = ""), 500);
}

function showSubmissionError(message) {
  const nav = document.querySelector(".wizard-nav");
  if (!nav) return;

  let banner = document.getElementById("submission-error");
  if (!banner) {
    banner = document.createElement("div");
    banner.id = "submission-error";
    banner.style.color = "var(--warn)";
    banner.style.fontSize = "0.85em";
    banner.style.marginTop = "8px";
    banner.style.textAlign = "center";
    nav.insertAdjacentElement("afterend", banner);
  }
  banner.textContent = message;
}

/* ---------------- render: kgotla ---------------- */

function renderKgotla() {
  const ranked = scoreDepartments(state.youth);
  const primary = ranked[0];
  const secondary = ranked.slice(1, 3);
  const brief = buildBrief(primary, state.youth);

  document.getElementById("stage").innerHTML = `
    <div class="kgotla">
      <div class="kgotla-header">
        <div class="kgotla-eyebrow">Your Kgotla</div>
        <div class="kgotla-title">${state.youth.name}, your paths have gathered</div>
        <div class="field-label">Every builder's Kgotla looks different. This one is yours.</div>
      </div>
      <div class="kgotla-grid">
        <div class="orbit-wrap">${orbitSVG(primary, secondary)}</div>
        <div>
          <div class="brief-card">
            <div class="brief-label">Primary match — ${primary.name}</div>
            <div class="brief-body">${brief.mission}</div>
            <div style="margin-top:14px;">
              ${secondary.map(d => `<span class="dept-tag">${d.name}</span>`).join("")}
            </div>
          </div>
          <div class="brief-card">
            <div class="brief-label">Priorities</div>
            <ul class="priority-list">
              ${brief.priorities.map((p, i) => `<li><span class="step-index">${String(i + 1).padStart(2, "0")}</span>${p}</li>`).join("")}
            </ul>
          </div>
          <div class="brief-card">
            <div class="brief-label">Learning path</div>
            <ul class="learning-list">
              ${brief.learningPath.map((l, i) => `<li><span class="step-index">${String(i + 1).padStart(2, "0")}</span>${l}</li>`).join("")}
            </ul>
          </div>
          <div class="brief-card">
            <div class="brief-label">Projected THoBoCoin — first trial</div>
            <div class="coin-band">
              <div class="coin-value">${brief.coinMin}–${brief.coinMax}</div>
              <div class="coin-note">based on current program rates, not a guarantee</div>
            </div>
          </div>
          <button class="btn btn-primary enter-cta" id="enter-ecosystem">Enter the ecosystem</button>
        </div>
      </div>
    </div>
  `;

  document.getElementById("enter-ecosystem").addEventListener("click", () => {
    // Registration already happened at the end of the wizard (see
    // registerYouth() above) — this button is just navigation.
    // Auto-matching this youth to a real opportunity here would need
    // real opportunities to exist for their matched department, which
    // isn't guaranteed at this point in the flow. Revisit once there's
    // a "browse open opportunities for me" screen to send them to
    // instead of straight back to the doors.
    go("doors");
  });
}

function orbitSVG(primary, secondary) {
  const size = 340, cx = size / 2, cy = size / 2;
  const initials = (state.youth.name || "?").split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase();
  const nodes = secondary.map((d, i) => {
    const angle = (i / secondary.length) * Math.PI * 2 - Math.PI / 2;
    const r = 130;
    const x = cx + r * Math.cos(angle);
    const y = cy + r * Math.sin(angle);
    return { d, x, y };
  });

  return `<svg viewBox="0 0 ${size} ${size}" width="${size}" height="${size}">
    <circle cx="${cx}" cy="${cy}" r="150" fill="none" stroke="var(--line)" stroke-dasharray="2 6" />
    ${nodes.map(n => `<line x1="${cx}" y1="${cy}" x2="${n.x}" y2="${n.y}" stroke="${CAT_COLOR[n.d.cat]}" stroke-width="1" opacity="0.4"/>`).join("")}
    <circle cx="${cx}" cy="${cy}" r="46" fill="${CAT_COLOR[primary.cat]}" opacity="0.9"/>
    <text x="${cx}" y="${cy + 6}" text-anchor="middle" font-family="Space Grotesk" font-size="20" fill="#090c14" font-weight="700">${initials}</text>
    ${nodes.map(n => `
      <circle cx="${n.x}" cy="${n.y}" r="24" fill="${CAT_COLOR[n.d.cat]}" opacity="0.75"/>
    `).join("")}
    ${nodes.map(n => `
      <text x="${n.x}" y="${n.y + 40}" text-anchor="middle" font-family="IBM Plex Mono" font-size="9" fill="#98a0b8">${n.d.name.split(" ")[0]}</text>
    `).join("")}
  </svg>`;
}

/* ---------------- render: business flow ---------------- */

function renderBusinessIntake() {
  document.getElementById("stage").innerHTML = `
    <div class="wizard">
      <div class="step-eyebrow">Business activation</div>
      <div class="step-title">Tell us about the business</div>
      <div class="field-row"><label class="field-label">Business name</label><input type="text" id="b-name" value="${state.business.name || ""}"></div>
      <div class="field-row"><label class="field-label">Owner</label><input type="text" id="b-owner" value="${state.business.owner || ""}"></div>
      <div class="field-row"><label class="field-label">Sector</label><input type="text" id="b-sector" value="${state.business.sector || ""}"></div>
      <div class="field-row"><label class="field-label">Location</label><input type="text" id="b-location" value="${state.business.location || ""}"></div>
      <div class="field-row"><label class="field-label">Main problem</label><textarea id="b-problem">${state.business.problem || ""}</textarea></div>
    </div>
    <div class="wizard-nav">
      <button class="btn btn-ghost" id="biz-back">← Doors</button>
      <button class="btn btn-primary" id="biz-next">Request Business Health Diagnosis</button>
    </div>
  `;
  document.getElementById("biz-back").addEventListener("click", () => go("doors"));
  document.getElementById("biz-next").addEventListener("click", async () => {
    state.business.name = document.getElementById("b-name").value.trim();
    state.business.owner = document.getElementById("b-owner").value.trim();
    state.business.sector = document.getElementById("b-sector").value.trim();
    state.business.location = document.getElementById("b-location").value.trim();
    state.business.problem = document.getElementById("b-problem").value.trim();
    if (!state.business.name || !state.business.problem) { flashInvalidNav("biz-next"); return; }

    const btn = document.getElementById("biz-next");
    const originalLabel = btn.textContent;
    btn.disabled = true;
    btn.textContent = "Submitting...";

    try {
      state.business.id = await createBusinessRecord(state.business);
      go("business-loading");
    } catch (err) {
      btn.disabled = false;
      btn.textContent = originalLabel;
      showSubmissionError(err.message);
    }
  });
}

function flashInvalidNav(id) {
  const btn = document.getElementById(id);
  btn.style.borderColor = "var(--warn)";
  setTimeout(() => (btn.style.borderColor = ""), 500);
}

function renderBusinessLoading() {
  const lines = [
    "> handing off to Business Health Diagnosis System",
    "> scanning: operations, marketing, technology, finance",
    "> cross-referencing 30-department capability map",
    "> compiling opportunity breakdown",
  ];
  document.getElementById("stage").innerHTML = `
    <div class="center-fill">
      <div class="threshold-sub" style="margin-bottom:24px;">Diagnosis in progress</div>
      <div class="boot-log">${lines.map((l, i) => `<div class="scan-line" style="animation-delay:${i * 0.5}s">${l}</div>`).join("")}</div>
    </div>`;
  setTimeout(() => go("business-result"), lines.length * 550 + 400);
}

function renderBusinessResult() {
  const problems = mockDiagnosis(state.business);
  document.getElementById("stage").innerHTML = `
    <div class="kgotla">
      <div class="kgotla-header">
        <div class="kgotla-eyebrow">Diagnosis complete</div>
        <div class="kgotla-title">${state.business.name}'s opportunity map</div>
      </div>
      ${problems.map(p => `
        <div class="problem-card">
          <div class="problem-title">${p.title}</div>
          <div class="problem-depts">→ Matched: ${p.depts.join(", ")}</div>
        </div>
      `).join("")}
      <button class="btn btn-primary enter-cta" id="biz-continue">Continue the journey</button>
    </div>
  `;
  document.getElementById("biz-continue").addEventListener("click", () => {
    // Deliberately NOT wired to create_opportunity: mockDiagnosis()
    // below is naive client-side keyword matching, not a real
    // diagnosis. Auto-creating real opportunity records from it would
    // put junk data into the same table that youth-matching logic
    // relies on being genuine. Wire this once a real Business Health
    // Audit methodology produces the findings instead.
    go("doors");
  });
}

function mockDiagnosis(business) {
  const problem = (business.problem || "").toLowerCase();
  const findings = [];
  if (problem.includes("website") || problem.includes("online") || problem.includes("digital")) {
    findings.push({ title: "No usable digital presence", depts: ["Web Development", "Digital Marketing & Advertising"] });
  }
  if (problem.includes("money") || problem.includes("account") || problem.includes("financ")) {
    findings.push({ title: "No structured financial tracking", depts: ["Finance & Accounting"] });
  }
  if (problem.includes("customer") || problem.includes("market") || problem.includes("sales")) {
    findings.push({ title: "Weak customer acquisition", depts: ["Social Media Management", "Digital Marketing & Advertising"] });
  }
  if (problem.includes("deliver") || problem.includes("logistic") || problem.includes("transport")) {
    findings.push({ title: "Delivery and logistics gap", depts: ["CabLink Transportation"] });
  }
  if (findings.length === 0) {
    findings.push({ title: business.problem || "General operations review needed", depts: ["Research & Development", "Project Management Office"] });
  }
  return findings;
}

/* ---------------- render: field audit (fast mode) ---------------- */

function renderAudit() {
  const checklist = ["Customer traffic", "Staff and roles", "Products or services", "Technology in use", "Marketing and branding", "Cleanliness and organisation"];

  document.getElementById("stage").innerHTML = `
    <div class="audit-wrap">
      <div class="step-eyebrow">Door Three</div>
      <div class="step-title">Field Audit — fast mode</div>

      <div class="audit-section">
        <h3>Trial identification</h3>
        <div class="field-row"><label class="field-label">Business name</label><input type="text" id="a-business"></div>
        <div class="field-row"><label class="field-label">Location / area</label><input type="text" id="a-location"></div>
      </div>

      <div class="audit-section">
        <h3>Observation checklist</h3>
        ${checklist.map(item => `
          <div class="rating-row">
            <div class="rating-label">${item}</div>
            <div class="rating-toggle" data-item="${item}">
              <button class="rating-btn good" data-r="G">G</button>
              <button class="rating-btn fair" data-r="F">F</button>
              <button class="rating-btn poor" data-r="P">P</button>
            </div>
          </div>
        `).join("")}
      </div>

      <div class="audit-section">
        <h3>BSTM room mapping (1–63)</h3>
        <div class="room-grid">${Array.from({ length: 63 }, (_, i) => `<button class="room-chip" data-room="${i + 1}">${i + 1}</button>`).join("")}</div>
      </div>

      <div class="audit-section">
        <h3>Quick reflection</h3>
        <div class="field-row"><label class="field-label">Biggest insight (one sentence)</label><textarea id="a-insight"></textarea></div>
        <div class="field-row">
          <label class="field-label">Overall trial score</label>
          <div class="slider-row">
            <input type="range" id="a-score" min="1" max="10" value="7">
            <span id="a-score-val" style="font-family:var(--mono);color:var(--ochre);">7</span>
          </div>
        </div>
      </div>

      <button class="btn btn-primary enter-cta" id="save-audit">Save trial</button>
      <button class="btn btn-ghost enter-cta" id="audit-back">← Doors</button>
    </div>
  `;

  document.querySelectorAll(".rating-toggle").forEach(group => {
    group.querySelectorAll(".rating-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        group.querySelectorAll(".rating-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        state.audit.ratings[group.dataset.item] = btn.dataset.r;
      });
    });
  });

  document.querySelectorAll(".room-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      chip.classList.toggle("selected");
      const room = Number(chip.dataset.room);
      state.audit.rooms = chip.classList.contains("selected")
        ? [...state.audit.rooms, room]
        : state.audit.rooms.filter(r => r !== room);
    });
  });

  const scoreInput = document.getElementById("a-score");
  scoreInput.addEventListener("input", () => (document.getElementById("a-score-val").textContent = scoreInput.value));

  document.getElementById("audit-back").addEventListener("click", () => go("doors"));
  document.getElementById("save-audit").addEventListener("click", () => {
    state.audit.business = document.getElementById("a-business").value.trim();
    state.audit.location = document.getElementById("a-location").value.trim();
    state.audit.insight = document.getElementById("a-insight").value.trim();
    state.audit.score = scoreInput.value;
    // API: POST this trial record once the V5 field-audit endpoint exists
    showToast("Trial saved.");
  });
}

function showToast(msg) {
  const toast = document.createElement("div");
  toast.className = "saved-toast";
  toast.textContent = msg;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 2200);
}

/* ---------------- render: login ---------------- */

function renderLogin() {
  document.getElementById("stage").innerHTML = `
    <div class="wizard">
      <div class="step-eyebrow">Welcome back</div>
      <div class="step-title">Log in to your BSTM account</div>
      <div class="field-row">
        <label class="field-label">Email</label>
        <input type="email" id="l-email" placeholder="you@example.com">
      </div>
      <div class="field-row">
        <label class="field-label">Password</label>
        <input type="password" id="l-password" placeholder="Your password">
      </div>
    </div>
    <div class="wizard-nav">
      <button class="btn btn-ghost" id="login-back">← Doors</button>
      <button class="btn btn-primary" id="login-submit">Log in</button>
    </div>
  `;
  document.getElementById("login-back").addEventListener("click", () => go("doors"));
  document.getElementById("login-submit").addEventListener("click", async () => {
    const email = document.getElementById("l-email").value.trim();
    const password = document.getElementById("l-password").value;
    if (!email || !password) { flashInvalidNav("login-submit"); return; }

    const btn = document.getElementById("login-submit");
    const originalLabel = btn.textContent;
    btn.disabled = true;
    btn.textContent = "Logging in...";

    try {
      const token = await loginYouth(email, password);
      saveToken(token);
      const [profile, trials, evidence] = await Promise.all([
        fetchMyProfile(token),
        fetchMyTrials(token),
        fetchMyEvidence(token),
      ]);
      state.myProfile = profile;
      state.myTrials = trials;
      state.myEvidence = evidence;
      go("dashboard");
    } catch (err) {
      btn.disabled = false;
      btn.textContent = originalLabel;
      showSubmissionError(err.message);
    }
  });
}

/* ---------------- render: dashboard ---------------- */

function renderDashboard() {
  const p = state.myProfile;

  if (!p) {
    // Reached directly (e.g. page reload) without a profile loaded
    // into state yet — go through the boot-time auto-login check
    // instead of rendering with nothing to show.
    go("boot");
    return;
  }

  const trials = state.myTrials || [];
  const evidence = state.myEvidence || [];

  const trialsList = trials.length
    ? trials.map((t) => `
        <div class="door" style="cursor:default;">
          <div class="door-eyebrow">${escapeHtml(t.status)}</div>
          <div class="door-title" style="font-size:16px;">${escapeHtml(t.title || t.opportunity_title)}</div>
        </div>
      `).join("")
    : `<div class="door" style="cursor:default;"><div class="door-title" style="font-size:15px;">No trials yet</div></div>`;

  const evidenceList = evidence.length
    ? evidence.map((e) => `
        <div class="door" style="cursor:default;">
          <div class="door-eyebrow">${escapeHtml(e.kind)}</div>
          <div class="door-title" style="font-size:16px;">${escapeHtml(e.notes || e.url || "—")}</div>
        </div>
      `).join("")
    : `<div class="door" style="cursor:default;"><div class="door-title" style="font-size:15px;">No evidence submitted yet</div></div>`;

  document.getElementById("stage").innerHTML = `
    <div class="center-fill" style="min-height:auto;padding-top:48px;">
      <div class="threshold-sub">My BSTM</div>
      <div class="threshold-title" style="font-size:clamp(22px,5vw,32px);">${escapeHtml(p.name)}</div>
    </div>
    <div class="doors" style="grid-template-columns:1fr 1fr;">
      <div class="door" style="cursor:default;">
        <div class="door-eyebrow">Level</div>
        <div class="door-title">${escapeHtml(p.level)}</div>
      </div>
      <div class="door" style="cursor:default;">
        <div class="door-eyebrow">Capability score</div>
        <div class="door-title">${escapeHtml(p.capability_score)}</div>
      </div>
      <div class="door" style="cursor:default;">
        <div class="door-eyebrow">Reliability score</div>
        <div class="door-title">${escapeHtml(p.reliability_score)}</div>
      </div>
      <div class="door" style="cursor:default;">
        <div class="door-eyebrow">Completed trials</div>
        <div class="door-title">${escapeHtml(p.completed_trials)}</div>
      </div>
      <div class="door" style="cursor:default;">
        <div class="door-eyebrow">Completed opportunities</div>
        <div class="door-title">${escapeHtml(p.completed_opportunities)}</div>
      </div>
      <div class="door" style="cursor:default;">
        <div class="door-eyebrow">Goal</div>
        <div class="door-title" style="font-size:16px;">${escapeHtml(p.goal) || "—"}</div>
      </div>
    </div>

    <div class="threshold-sub" style="margin-top:32px;">My trials</div>
    <div class="doors" style="grid-template-columns:1fr;">
      ${trialsList}
    </div>

    <div class="threshold-sub" style="margin-top:32px;">My evidence</div>
    <div class="doors" style="grid-template-columns:1fr;">
      ${evidenceList}
    </div>

    <button class="skip-link" id="logout-link" style="margin-top:24px;">Log out</button>
  `;
  document.getElementById("logout-link").addEventListener("click", () => {
    clearToken();
    state.myProfile = null;
    state.myTrials = null;
    state.myEvidence = null;
    go("doors");
  });
}

/* ---------------- router ---------------- */

function go(route, youthStep) {
  state.route = route;
  if (typeof youthStep === "number") state.youthStep = youthStep;
  window.scrollTo(0, 0);
  render();
}

function render() {
  switch (state.route) {
    case "boot": return renderBoot();
    case "doors": return renderDoors();
    case "youth": return renderYouth();
    case "kgotla": return renderKgotla();
    case "business-intake": return renderBusinessIntake();
    case "business-loading": return renderBusinessLoading();
    case "business-result": return renderBusinessResult();
    case "audit": return renderAudit();
    case "login": return renderLogin();
    case "dashboard": return renderDashboard();
    default: return renderBoot();
  }
}

// On load, if a token is already stored (a returning youth), try it
// silently before showing the boot sequence at all. A dead/expired
// token just falls through to the normal boot flow rather than
// blocking anything.
(async function bootstrap() {
  const token = loadToken();

  if (token) {
    try {
      const [profile, trials, evidence] = await Promise.all([
        fetchMyProfile(token),
        fetchMyTrials(token),
        fetchMyEvidence(token),
      ]);
      state.myProfile = profile;
      state.myTrials = trials;
      state.myEvidence = evidence;
      state.route = "dashboard";
      render();
      return;
    } catch (err) {
      clearToken();
    }
  }

  render();
})();
