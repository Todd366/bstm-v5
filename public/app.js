(function () {
  "use strict";

  var $ = function (id) { return document.getElementById(id); };
  var app = $("app"), tabs = $("tabs"), banner = $("banner");
  var S = { atab: "queue", btab: "bjobs", me: "profile", adminKey: null, staffToken: null, staffRole: null, staffName: null, token: null, btoken: null, lang: "en", tab: "home", profile: null, caps: null, depts: null };

  try { S.adminKey = sessionStorage.getItem("bstm_admin"); S.staffToken = sessionStorage.getItem("bstm_staff"); S.staffRole = sessionStorage.getItem("bstm_srole"); S.staffName = sessionStorage.getItem("bstm_sname"); } catch (e) {}
  function isStaff() { return !!(S.adminKey || S.staffToken); }
  try { S.token = localStorage.getItem("bstm_token"); S.btoken = localStorage.getItem("bstm_btoken"); S.lang = localStorage.getItem("bstm_lang") || "en"; } catch (e) {}
  function store(k, v) { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch (e) {} }

  // ---------- language ----------
  var TS = {
    "Home": "Gae", "Jobs": "Ditiro", "My work": "Tiro ya me", "Proof": "Bopaki", "Skills": "Dikgono",
    "Log in": "Tsena", "Log out": "Tswa", "Create account": "Ikwadisa", "Email": "Imeile", "Password": "Password",
    "Next": "Latelang", "Back": "Boela morago", "Name": "Leina", "Apply": "Kopa tiro", "Accept": "Amogela",
    "Decline": "Gana", "Withdraw": "Ikgogele morago", "Submit": "Romela", "Save": "Boloka",
    "Where do you live?": "O nna kae?", "Loading…": "Go a tsenngwa…", "Setswana": "English",
    "Money": "Madi", "Me": "Nna", "Alerts": "Dikitsiso", "Profile": "Porofaele", "Post a job": "Rekisa tiro", "Invoices": "Dikgetsi",
    "Search": "Batla", "Show more": "Bontsha tse dingwe", "Log in as business": "Tsena jaaka kgwebo"
  };
  function t(s) { return S.lang === "tn" && TS[s] ? TS[s] : s; }

  // ---------- helpers ----------
  function h(tag, attrs) {
    var el = document.createElement(tag);
    if (attrs) for (var k in attrs) {
      var v = attrs[k];
      if (v == null || v === false) continue;
      if (k === "class") el.className = v;
      else if (k === "text") el.textContent = v;
      else if (k.slice(0, 2) === "on") el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? "" : v);
    }
    for (var i = 2; i < arguments.length; i++) add(el, arguments[i]);
    return el;
  }
  function add(el, c) {
    if (c == null || c === false) return;
    if (Array.isArray(c)) c.forEach(function (x) { add(el, x); });
    else el.appendChild(typeof c === "object" ? c : document.createTextNode(String(c)));
  }
  function clear(el) { while (el.firstChild) el.removeChild(el.firstChild); }
  function show(node) { clear(app); app.appendChild(node); window.scrollTo(0, 0); }
  function say(msg, bad) {
    banner.textContent = msg || ""; banner.hidden = !msg;
    banner.className = "banner" + (bad ? " err" : "");
    if (msg && !bad) setTimeout(function () { if (banner.textContent === msg) banner.hidden = true; }, 4000);
  }
  function money(n) { n = Number(n) || 0; return n > 0 ? "P" + n.toLocaleString("en") : "Budget to agree"; }
  function when(d) { try { return new Date(d).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }); } catch (e) { return ""; } }

  // ---------- api ----------
  function api(path, opt) {
    opt = opt || {};
    var headers = { Accept: "application/json" };
    if (opt.body) headers["Content-Type"] = "application/json";
    if (opt.headers) for (var hk in opt.headers) headers[hk] = opt.headers[hk];
    var tok = path.indexOf("/biz") === 0 ? S.btoken : S.token;
    if (opt.admin) { if (S.staffToken) headers.Authorization = "Bearer " + S.staffToken; else headers["X-API-Key"] = S.adminKey; }
    else if (tok && !opt.anon) headers.Authorization = "Bearer " + tok;
    var ctl = typeof AbortController === "function" ? new AbortController() : null;
    var timer = ctl ? setTimeout(function () { ctl.abort(); }, 20000) : null;
    return fetch(path, {
      method: opt.method || (opt.body ? "POST" : "GET"), headers: headers,
      body: opt.body ? JSON.stringify(opt.body) : undefined, signal: ctl ? ctl.signal : undefined
    }).then(function (r) {
      if (timer) clearTimeout(timer);
      return r.text().then(function (txt) {
        var data = null; try { data = txt ? JSON.parse(txt) : null; } catch (e) {}
        if (!r.ok) {
          var d = data && data.detail, msg = typeof d === "string" ? d : (Array.isArray(d) && d[0] && d[0].msg) || "Something went wrong. Please try again.";
          if (r.status === 429) msg = "Too many tries. Please wait a few minutes.";
          var err = new Error(msg); err.status = r.status; throw err;
        }
        return data;
      });
    }, function () {
      if (timer) clearTimeout(timer);
      var err = new Error("No connection. Check your data or network and try again."); err.net = true; throw err;
    });
  }
  function fail(e) {
    if (isStaff() && e && e.status === 403) { say("Your role is not allowed to do that.", true); return; }
    if (isStaff() && e && e.status === 401) { adminLogout(); say("Please sign in again.", true); return; }
    if (e && e.status === 401 && S.btoken && !S.token) { logout(true); return; }
    if (e && e.status === 401 && S.token) { logout(true); return; }
    say(e && e.message || "Something went wrong.", true);
  }
  function busy(btn, p) {
    btn.disabled = true;
    return p.then(function (x) { btn.disabled = false; return x; }, function (e) { btn.disabled = false; throw e; });
  }

  // ---------- session ----------
  function logout(expired) {
    S.token = null; S.btoken = null; S.profile = null; store("bstm_token", null); store("bstm_btoken", null); bell(0);
    if (expired) say("Your session ended. Please log in again.", true);
    route();
  }
  function setToken(tok) { S.token = tok; S.btoken = null; store("bstm_token", tok); store("bstm_btoken", null); }
  function setBtoken(tok) { S.btoken = tok; S.token = null; store("bstm_btoken", tok); store("bstm_token", null); }
  function pula(n) { return "P" + (Number(n) || 0).toLocaleString("en", { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
  function idem() { try { return crypto.randomUUID(); } catch (e) { return Date.now() + "-" + Math.random().toString(36).slice(2); } }
  function bell(n) { var b = $("bellBtn"); if (!b) return; b.hidden = !(S.token || S.btoken); $("bellN").textContent = n > 0 ? String(n > 9 ? "9+" : n) : ""; }
  function refreshBell() {
    if (!(S.token || S.btoken)) return bell(0);
    api(S.btoken ? "/biz/notifications" : "/me/notifications").then(function (r) { bell(r && r.unread || 0); }, function () {});
  }
  function loadDepts() {
    if (S.depts) return Promise.resolve(S.depts);
    return api("/catalog/departments", { anon: true }).then(function (d) { S.depts = d || []; return S.depts; }, function () { return []; });
  }
  function subNav(cur) {
    return h("div", { class: "chips", style: "margin-bottom:12px" }, [["profile", "Profile"], ["skills", "Skills"], ["proof", "Proof"]].map(function (x) {
      return h("button", { class: "chip", type: "button", "aria-pressed": cur === x[0] ? "true" : "false", text: t(x[1]), onclick: function () { S.me = x[0]; route(); } });
    }));
  }

  // ---------- auth screens ----------
  function field(label, name, type, extra) {
    extra = extra || {};
    var id = "f_" + name;
    var input = h(extra.tag || "input", { id: id, name: name, type: extra.tag ? null : (type || "text"), autocomplete: extra.ac, maxlength: extra.max, list: extra.list, inputmode: extra.im, required: extra.req, placeholder: extra.ph });
    if (extra.value) input.value = extra.value;
    return h("div", null, h("label", { for: id, text: t(label) }), input);
  }
  function val(root, name) { var el = root.querySelector("[name=" + name + "]"); return el ? el.value.trim() : ""; }

  function landing() {
    show(h("div", null,
      h("h1", { text: "Welcome to BSTM Activation" }),
      h("p", { class: "m", text: "Real work, real proof, real progress for Batswana." }),
      h("div", { class: "card" }, h("h2", { text: "I am a young person" }), h("p", { class: "m", text: "Find work that fits your skills and build your record." }),
        h("button", { class: "btn", type: "button", text: t("Log in"), onclick: loginScreen }),
        h("button", { class: "btn sec", type: "button", text: t("Create account"), onclick: registerScreen })),
      h("div", { class: "card" }, h("h2", { text: "I own a business" }), h("p", { class: "m", text: "Tell us your problem. We find skilled youth to help." }),
        h("button", { class: "btn", type: "button", text: "Register my business", onclick: businessScreen }),
        h("button", { class: "btn sec", type: "button", text: t("Log in as business"), onclick: bizLoginScreen })),
      h("div", { class: "card" }, h("h2", { text: "BSTM staff" }),
        h("button", { class: "btn sec", type: "button", text: "Staff sign in", onclick: staffLogin }))));
  }

  function loginScreen() {
    var err = h("p", { class: "err", role: "alert" });
    var form = h("form", { class: "card", novalidate: true },
      h("h1", { text: t("Log in") }),
      field("Email or phone number", "email", "text", { ac: "username", max: 254 }),
      field("Password", "password", "password", { ac: "current-password", max: 128 }),
      err,
      h("button", { class: "btn", type: "submit", text: t("Log in") }));
    form.addEventListener("submit", function (ev) {
      ev.preventDefault(); err.textContent = "";
      var b = form.querySelector("button");
      busy(b, api("/youth/login", { anon: true, body: { email: val(form, "email"), password: form.querySelector("[name=password]").value } }))
        .then(function (r) { setToken(r.access_token); route(); })
        .catch(function (e) { err.textContent = e.message; });
    });
    show(h("div", null, form,
      h("div", { class: "card" }, h("p", { text: "New here?" }),
        h("button", { class: "btn sec", type: "button", text: t("Create account"), onclick: registerScreen }),
        h("button", { class: "btn sec", type: "button", text: "Forgot password?", onclick: function () { resetScreen("youth"); } }),
        h("button", { class: "btn sec", type: "button", text: t("Back"), onclick: landing }))));
  }

  var PLACES = ["Gaborone", "Francistown", "Maun", "Kasane", "Serowe", "Palapye", "Molepolole", "Mochudi", "Lobatse", "Selebi-Phikwe", "Kanye", "Mahalapye", "Ghanzi", "Jwaneng", "Orapa", "Tsabong", "Shakawe", "Tonota", "Letlhakane", "Mmadinare"];
  var OPT = {
    position: ["Student", "Unemployed", "Employed", "Entrepreneur", "Graduate", "Other"],
    education: ["None yet", "Primary", "Junior Certificate", "Senior Certificate", "Certificate / Diploma", "Degree", "Postgraduate"],
    interests: ["Technology", "Business", "Creative", "Agriculture", "Trades", "Finance", "Research", "Community"],
    skillLevel: ["Beginner", "Developing", "Intermediate", "Advanced", "Expert"],
    resources: ["Smartphone", "Computer", "Internet access", "Transport", "A workspace"],
    income: ["None", "Irregular", "Steady"],
    capital: ["None", "Small (under P500)", "Moderate (P500+)"],
    availability: ["Full-time", "Part-time", "Weekends", "Evenings only"],
    challenges: ["No experience", "No money", "No network", "No direction", "No equipment", "Confidence"],
    aspiration: ["A steady job", "My own business", "A real skill", "To earn right now", "To learn and explore"]
  };
  function chips(d, key, multi) {
    var row = h("div", { class: "chips", role: "group" });
    OPT[key].forEach(function (o) {
      var on = function () { return multi ? (d[key] || []).indexOf(o) > -1 : d[key] === o; };
      var b = h("button", { class: "chip", type: "button", "aria-pressed": on() ? "true" : "false", text: o });
      b.addEventListener("click", function () {
        if (multi) { var a = d[key] || []; var i = a.indexOf(o); if (i > -1) a.splice(i, 1); else a.push(o); d[key] = a; }
        else d[key] = o;
        Array.prototype.forEach.call(row.children, function (c) {
          var v = c.textContent; c.setAttribute("aria-pressed", (multi ? (d[key] || []).indexOf(v) > -1 : d[key] === v) ? "true" : "false");
        });
      });
      row.appendChild(b);
    });
    return row;
  }
  function q(label, node) { return h("div", null, h("label", { text: label }), node); }

  function registerScreen() {
    var d = { skills: {}, interests: [], resources: [], challenges: [] }, step = 0, LAST = 5;
    function render() {
      var err = h("p", { class: "err", role: "alert" });
      var bar = h("div", { class: "steps" }, [0, 1, 2, 3, 4, 5].map(function (i) { return h("span", { class: i <= step ? "on" : "" }); }));
      var nav = function (nextLabel) {
        return [h("button", { class: "btn", type: "submit", text: nextLabel || t("Next") }),
          step > 0 ? h("button", { class: "btn sec", type: "button", text: t("Back"), onclick: function () { step--; render(); } }) : h("button", { class: "btn sec", type: "button", text: t("Back"), onclick: landing })];
      };
      var body, problem = function (m) { err.textContent = m; };
      if (step === 0) {
        body = h("form", { novalidate: true }, h("h1", { text: "Create your account" }),
          field("Name", "name", "text", { ac: "name", max: 120, value: d.name }),
          field("Email or phone number", "email", "text", { ac: "username", max: 254, value: d.email }),
          h("p", { class: "m", text: "No email? Use your phone number, like 71 234 567." }),
          field("Password", "password", "password", { ac: "new-password", max: 128 }),
          h("p", { class: "m", text: "At least 8 characters." }), err, nav());
        body.addEventListener("submit", function (ev) {
          ev.preventDefault();
          d.name = val(body, "name"); d.email = val(body, "email"); d.password = body.querySelector("[name=password]").value;
          if (!d.name) return problem("Please enter your name.");
          if (d.email.indexOf("@") >= 0 ? !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(d.email) : !/^(\+?267|0)?\s?[3-7](\s?\d){7}$/.test(d.email)) return problem("Enter a valid email or a Botswana phone number.");
          if (d.password.length < 8) return problem("Password must be at least 8 characters.");
          step = 1; render();
        });
      } else if (step === 1) {
        var dl = h("datalist", { id: "places" }, PLACES.map(function (p) { return h("option", { value: p }); }));
        body = h("form", { novalidate: true }, h("h1", { text: "About you" }), dl,
          field("Where do you live?", "location", "text", { ac: "address-level2", max: 120, list: "places", value: d.location }),
          field("Age", "age", "number", { im: "numeric", value: d.age }),
          q("Where are you in life right now?", chips(d, "position")),
          q("Education", chips(d, "education")), err, nav());
        body.addEventListener("submit", function (ev) {
          ev.preventDefault();
          d.location = val(body, "location"); d.age = val(body, "age");
          var age = Number(d.age);
          if (!d.location) return problem("Please enter where you live.");
          if (!(age >= 14 && age <= 80)) return problem("Enter your age (14 to 80).");
          if (!d.position || !d.education) return problem("Please choose one option in each question.");
          step = 2; render();
        });
      } else if (step === 2) {
        body = h("form", { novalidate: true }, h("h1", { text: "What pulls your attention?" }),
          q("Pick as many as feel true", chips(d, "interests", true)),
          q("How would you rate what you can already do?", chips(d, "skillLevel")), err, nav());
        body.addEventListener("submit", function (ev) {
          ev.preventDefault();
          if (!d.interests.length || !d.skillLevel) return problem("Pick at least one interest and a level.");
          step = 3; render();
        });
      } else if (step === 3) {
        body = h("form", { novalidate: true }, h("h1", { text: "What do you have to work with?" }),
          h("p", { class: "m", text: "Be honest. This helps us give you realistic first steps." }),
          q("Resources", chips(d, "resources", true)), q("Income today", chips(d, "income")),
          q("Money you could use to start", chips(d, "capital")), q("Time you can give", chips(d, "availability")), err, nav());
        body.addEventListener("submit", function (ev) {
          ev.preventDefault();
          if (!d.resources.length || !d.income || !d.capital || !d.availability) return problem("Please answer every question.");
          step = 4; render();
        });
      } else if (step === 4) {
        body = h("form", { novalidate: true }, h("h1", { text: "What is in the way?" }),
          q("Choose any (optional)", chips(d, "challenges", true)),
          q("Where do you want this to take you?", chips(d, "aspiration")), err, nav());
        body.addEventListener("submit", function (ev) {
          ev.preventDefault();
          if (!d.aspiration) return problem("Please choose where you want this to take you.");
          step = 5; render();
        });
      } else {
        var holder = h("div", { class: "spin", text: t("Loading…") });
        body = h("div", null, h("h1", { text: "Pick your skills" }), h("p", { class: "m", text: "Choose what you can do. You can change this later." }), holder, err,
          h("button", { class: "btn", type: "button", text: t("Create account"), onclick: function (ev) {
            err.textContent = "";
            var caps = Object.keys(d.skills).map(function (id) { return { capability_id: id, level: d.skillLevel || "Beginner" }; });
            var payload = {
              name: d.name, email: d.email.indexOf("@") >= 0 ? d.email : null, phone: d.email.indexOf("@") >= 0 ? null : d.email, password: d.password, location: d.location, goal: d.aspiration,
              passion: d.interests.join(", "), availability: d.availability, equipment: d.resources.join(", "), capabilities: caps,
              intake: { age: Number(d.age), position: d.position, education: d.education, interests: d.interests, skillLevel: d.skillLevel, resources: d.resources, income: d.income, capital: d.capital, availability: d.availability, challenges: d.challenges, aspiration: d.aspiration }
            };
            busy(ev.target, api("/youth", { anon: true, body: payload }))
              .then(function (r) { setToken(r.access_token); say("Welcome to BSTM!"); S.tab = "home"; route(); })
              .catch(function (e) { err.textContent = e.message; });
          } }),
          h("button", { class: "btn sec", type: "button", text: t("Back"), onclick: function () { step = 4; render(); } }));
        loadCaps().then(function (caps) {
          var first = caps.filter(function (c) { return d.interests.indexOf(c.category) > -1; }), rest = caps.filter(function (c) { return d.interests.indexOf(c.category) < 0; });
          clear(holder); holder.className = "";
          holder.appendChild(skillPicker(first.concat(rest), d.skills));
        }).catch(function (e) { holder.className = "err"; holder.textContent = e.message; });
      }
      show(h("div", { class: "card" }, bar, body));
    }
    render();
  }

  function loadCaps() {
    if (S.caps) return Promise.resolve(S.caps);
    return api("/catalog/capabilities", { anon: true }).then(function (c) { S.caps = c || []; return S.caps; });
  }
  function skillPicker(caps, chosen) {
    var cats = {}, wrap = h("div");
    caps.forEach(function (c) { (cats[c.category] = cats[c.category] || []).push(c); });
    Object.keys(cats).forEach(function (cat) {
      var row = h("div", { class: "chips" });
      cats[cat].forEach(function (c) {
        var b = h("button", { class: "chip", type: "button", "aria-pressed": chosen[c.id] ? "true" : "false", text: c.name });
        b.addEventListener("click", function () { if (chosen[c.id]) delete chosen[c.id]; else chosen[c.id] = 1; b.setAttribute("aria-pressed", chosen[c.id] ? "true" : "false"); });
        row.appendChild(b);
      });
      wrap.appendChild(h("h2", { text: cat })); wrap.appendChild(row);
    });
    return wrap;
  }

  // ---------- app shell ----------
  var TABS = [["home", "🏠", "Home"], ["jobs", "🔎", "Jobs"], ["work", "💼", "My work"], ["money", "💰", "Money"], ["me", "👤", "Me"]];
  var ATABS = [["queue", "📋", "Queue"], ["money", "💰", "Money"], ["biz", "🏪", "Businesses"], ["jobs", "💼", "Jobs"], ["youth", "👥", "Youth"], ["audit", "📝", "Audit"], ["reset", "🔑", "Resets"], ["team", "🛡️", "Team"], ["agent", "📱", "Register"], ["rep", "📊", "Reports"], ["sys", "✅", "System"], ["owner", "👑", "Owner"]];
  var AROLE = { owner: null, admin: ["queue", "money", "biz", "jobs", "youth", "audit", "reset", "agent", "rep", "sys"], finance: ["queue", "money", "rep"], field: ["queue", "biz", "jobs", "youth", "audit", "agent"], agent: ["agent"], support: ["queue", "youth", "reset"] };
  function atabAllowed(k) { if (S.adminKey && !S.staffToken) return true; var r = AROLE[S.staffRole]; return r === undefined ? false : (r === null || r.indexOf(k) >= 0); }
  var BTABS = [["bjobs", "💼", "Jobs"], ["bpost", "➕", "Post a job"], ["binv", "🧾", "Invoices"]];
  function drawTabs() {
    clear(tabs); tabs.hidden = !S.token && !isStaff() && !S.btoken;
    if (isStaff()) {
      ATABS.filter(function (x) { return atabAllowed(x[0]); }).forEach(function (x) {
        tabs.appendChild(h("button", { type: "button", "aria-current": S.atab === x[0] ? "page" : null, onclick: function () { S.atab = x[0]; route(); } }, h("i", { text: x[1] }), x[2]));
      });
      return;
    }
    if (S.btoken) {
      BTABS.forEach(function (x) {
        tabs.appendChild(h("button", { type: "button", "aria-current": S.btab === x[0] ? "page" : null, onclick: function () { S.btab = x[0]; route(); } }, h("i", { text: x[1] }), t(x[2])));
      });
      return;
    }
    if (!S.token) return;
    TABS.forEach(function (x) {
      tabs.appendChild(h("button", { type: "button", "aria-current": S.tab === x[0] ? "page" : null, onclick: function () { S.tab = x[0]; route(); } }, h("i", { text: x[1] }), t(x[2])));
    });
  }
  var VIEWS = { home: homeView, jobs: jobsView, work: workView, money: moneyView, alerts: alertsView,
    me: function () { return ({ profile: profileView, skills: skillsView, proof: proofView }[S.me] || profileView)(); } };

  function route() {
    $("outBtn").hidden = !S.token && !isStaff() && !S.btoken; $("outBtn").textContent = t("Log out"); $("langBtn").textContent = t("Setswana");
    drawTabs();
    try { var cur = tabs.querySelector("[aria-current]"); if (cur && cur.scrollIntoView) cur.scrollIntoView({ inline: "center", block: "nearest" }); } catch (e) {}
    var pm = /^#\/p\/([0-9a-fA-F-]{36})$/.exec(location.hash || "");
    if (pm) return publicProfileView(pm[1]);
    if (isStaff()) { $("who").textContent = S.staffName || "Staff"; $("outBtn").hidden = false; return adminRoute(); }
    if (S.btoken) { $("who").textContent = ""; bell(0); refreshBell(); return bizRoute(); }
    if (!S.token) { $("who").textContent = ""; bell(0); return landing(); }
    show(h("div", { class: "spin", text: t("Loading…") }));
    refreshBell();
    (VIEWS[S.tab] || homeView)().catch(function (e) {
      if (e && e.status === 401) return fail(e);
      var retry = h("button", { class: "btn", type: "button", text: "Try again", onclick: route });
      show(h("div", { class: "card empty" }, h("p", { text: e.message || "Could not load." }), retry));
    });
  }
  function profile() { return api("/me").then(function (p) { S.profile = p; $("who").textContent = p.name; return p; }); }
  function empty(msg) { return h("div", { class: "card empty", text: msg }); }

  // ---------- views ----------
  var LEVELS = ["Seed", "Sprout", "Builder", "Professional", "Leader"];
  function homeView() {
    return Promise.all([profile(), api("/me/assignments"), api("/me/opportunities"), api("/me/brief").catch(function () { return null; })]).then(function (r) {
      var p = r[0], as = r[1] || [], ms = r[2] || [], brief = r[3];
      var active = as.filter(function (a) { return a.status === "Accepted"; });
      var pending = as.filter(function (a) { return a.status === "Pending"; });
      var node = h("div", null,
        h("h1", { text: (S.lang === "tn" ? "Dumela, " : "Hello, ") + p.name.split(" ")[0] }), p.must_change_password ? pwCard(p) : null,
        h("div", { class: "card" }, h("h3", { text: "Your level" }), h("p", { text: p.level || "Beginner" }),
          h("div", { class: "stat" },
            stat(p.completed_trials, "Trials done"), stat(p.completed_opportunities, "Jobs done"), stat(Math.round(p.reputation_score || 0), "Reputation"), stat(pula(p.revenue), "Paid to you"))));
      if (brief && brief.primary) node.appendChild(briefCard(brief));
      if (!ms.length && !as.length) node.appendChild(h("div", { class: "card" }, h("h3", { text: "Next step" }), h("p", { text: "Add your skills so we can match you to work." }), h("button", { class: "btn", type: "button", text: "Add skills", onclick: function () { S.tab = "skills"; route(); } })));
      if (active.length) node.appendChild(h("div", { class: "card" }, h("h3", { text: "Active work (" + active.length + ")" }), h("button", { class: "btn sm", type: "button", text: "Open my work", onclick: function () { S.tab = "work"; route(); } })));
      if (pending.length) node.appendChild(h("div", { class: "card" }, h("p", { text: pending.length + " application(s)/offer(s) waiting." })));
      if (ms.length) node.appendChild(h("div", { class: "card" }, h("h3", { text: ms.length + " job(s) match your skills" }), h("button", { class: "btn sm", type: "button", text: "See jobs", onclick: function () { S.tab = "jobs"; route(); } })));
      show(node);
    });
  }
  function briefCard(b) {
    return h("div", { class: "card" }, h("h3", { text: "Your best-fit department" }),
      h("p", null, h("strong", { text: b.primary.name }), " ", h("span", { class: "tag ok", text: b.primary.score + "% fit" })),
      h("p", { text: b.mission }),
      h("h3", { text: "Your first steps" }), h("ol", null, b.priorities.map(function (x) { return h("li", { text: x }); })),
      b.skills_to_learn && b.skills_to_learn.length ? h("div", null, h("h3", { text: "Skills to add next" }), h("p", null, b.skills_to_learn.map(function (x) { return h("span", { class: "tag", title: x.description || "", text: x.name }); })), h("p", { class: "m", text: "Add them under Me -> Skills, then prove them with work." })) : null,
      h("h3", { text: "Learning path" }), h("ol", null, b.learning_path.map(function (x) { return h("li", { text: x }); })),
      b.alternatives && b.alternatives.length ? h("p", { class: "m", text: "Also a fit: " + b.alternatives.map(function (x) { return x.name; }).join(", ") }) : null);
  }
  function stat(n, label) { return h("div", null, h("b", { text: String(n || 0) }), h("span", { class: "m", text: label })); }

  function oppCard(o, matched) {
    var card = h("div", { class: "card" },
      h("h3", { text: o.title }),
      h("p", { class: "m", text: [o.business_name || o.department || "BSTM", o.business_location].filter(Boolean).join(" · ") }),
      o.description ? h("p", { text: o.description.length > 220 ? o.description.slice(0, 220) + "…" : o.description }) : null,
      h("p", null, h("span", { class: "tag", text: money(o.budget) }), matched ? h("span", { class: "tag ok", text: "Fit " + o.match_score + "%" }) : null,
        (o.reasons || []).map(function (r) { return h("span", { class: "tag", text: r }); })),
      o.required_skills && o.required_skills.length ? h("p", { class: "m", text: "Skills needed: " + o.required_skills.join(", ") }) : null);
    var b = h("button", { class: "btn", type: "button", text: t("Apply") });
    b.addEventListener("click", function () {
      busy(b, api("/me/opportunities/" + encodeURIComponent(o.opportunity_id || o.id) + "/apply", { method: "POST", body: {} })).then(function () {
        say("Application sent. We will tell you when it is accepted."); b.textContent = "Applied ✓"; b.disabled = true;
      }).catch(fail);
    });
    card.appendChild(b); return card;
  }
  var jobsMode = "match", jf = { q: "", location: "", department: "" };
  function jobsView() {
    var all = jobsMode === "all", PAGE = 20;
    var qs = function (off) { return "?limit=" + PAGE + "&offset=" + off + (jf.q ? "&q=" + encodeURIComponent(jf.q) : "") + (jf.location ? "&location=" + encodeURIComponent(jf.location) : "") + (jf.department ? "&department=" + encodeURIComponent(jf.department) : ""); };
    return Promise.all([api(all ? "/me/opportunities/browse" + qs(0) : "/me/opportunities"), all ? loadDepts() : Promise.resolve([])]).then(function (r) {
      var list = r[0] || [], depts = r[1] || [];
      var tabsRow = h("div", { class: "chips" },
        ["match", "all"].map(function (m) { return h("button", { class: "chip", type: "button", "aria-pressed": jobsMode === m ? "true" : "false", text: m === "match" ? "Matched to me" : "All open", onclick: function () { jobsMode = m; route(); } }); }));
      var node = h("div", null, h("h1", { text: t("Jobs") }), tabsRow, h("div", { style: "height:12px" }));
      if (all) {
        var f = h("form", { class: "card", novalidate: true },
          h("input", { name: "q", type: "search", placeholder: "Search jobs (e.g. plumbing, website)", maxlength: 80, "aria-label": t("Search") }),
          h("input", { name: "location", type: "text", placeholder: "Town or village", maxlength: 120, list: "places", "aria-label": "Town or village", style: "margin-top:8px" }),
          h("datalist", { id: "places" }, PLACES.map(function (p) { return h("option", { value: p }); })),
          h("select", { name: "department", "aria-label": "Department", style: "margin-top:8px" }, h("option", { value: "", text: "Any department" }), depts.map(function (d) { return h("option", { value: d, text: d }); })),
          h("button", { class: "btn sm", type: "submit", text: t("Search") }));
        f.querySelector("[name=q]").value = jf.q; f.querySelector("[name=location]").value = jf.location; f.querySelector("[name=department]").value = jf.department;
        f.addEventListener("submit", function (ev) { ev.preventDefault(); jf = { q: val(f, "q"), location: val(f, "location"), department: val(f, "department") }; route(); });
        node.appendChild(f);
      }
      var box = h("div");
      if (!list.length) node.appendChild(empty(all ? "No open jobs match. Try fewer words or another town." : "No matches yet. Add more skills, or see all open jobs."));
      else list.forEach(function (o) { box.appendChild(oppCard(o, !all)); });
      node.appendChild(box);
      if (all && list.length === PAGE) {
        var offset = PAGE, more = h("button", { class: "btn sec", type: "button", text: t("Show more") });
        more.addEventListener("click", function () {
          busy(more, api("/me/opportunities/browse" + qs(offset))).then(function (next) {
            (next || []).forEach(function (o) { box.appendChild(oppCard(o, false)); });
            offset += PAGE; if (!next || next.length < PAGE) more.remove();
          }).catch(fail);
        });
        node.appendChild(more);
      }
      show(node);
    });
  }

  function workView() {
    return Promise.all([api("/me/assignments"), api("/me/trials")]).then(function (r) {
      var list = r[0] || [], node = h("div", null, h("h1", { text: t("My work") }));
      if (!list.length) node.appendChild(empty("Nothing yet. Apply for a job to get started."));
      list.forEach(function (a) {
        var card = h("div", { class: "card" }, h("h3", { text: a.opportunity_title }),
          h("p", { class: "m", text: [a.business_name || a.department, a.business_location].filter(Boolean).join(" · ") }),
          h("p", null, h("span", { class: "tag " + (a.status === "Accepted" || a.status === "Completed" ? "ok" : "warn"), text: statusText(a) }), h("span", { class: "tag", text: money(a.budget) })));
        var act = function (label, path, cls, ok, body) {
          var b = h("button", { class: "btn sm " + (cls || ""), type: "button", text: label });
          b.addEventListener("click", function () { busy(b, api(path, { method: "POST", body: body || {} })).then(function () { say(ok); route(); }).catch(fail); });
          card.appendChild(b);
        };
        var base = "/me/assignments/" + encodeURIComponent(a.assignment_id);
        if (a.status === "Pending" && a.opportunity_status === "Assigned") { act(t("Accept"), base + "/accept", "", "Accepted. Good luck!"); act(t("Decline"), base + "/decline", "sec", "Declined."); }
        if (a.status === "Pending" && a.opportunity_status !== "Assigned") act(t("Withdraw"), base + "/withdraw", "sec", "Application withdrawn.");
        if (a.status === "Accepted" && !a.trial_id) { act("Start work", base + "/trial", "", "Work started."); act(t("Withdraw"), base + "/withdraw", "sec", "Withdrawn."); }
        if (a.trial_id && a.trial_status === "Active") {
          card.appendChild(submitForm(a.trial_id, r[1]));
          var stop = h("button", { class: "btn sm sec", type: "button", text: "Stop this work" });
          stop.addEventListener("click", function () {
            if (!window.confirm("Stop this work? Stopping after you started lowers your reliability score.")) return;
            busy(stop, api("/me/trials/" + encodeURIComponent(a.trial_id) + "/cancel", { method: "POST", body: {} })).then(function () { say("Work stopped. You can start again."); route(); }).catch(fail);
          });
          card.appendChild(stop);
        }
        if (a.status === "Completed") card.appendChild(h("p", { class: "m" }, "Done. See Money for your payout."));
        node.appendChild(card);
      });
      var pt = patternTracker(r[1]); if (pt) node.appendChild(pt);
      show(node);
    });
  }
  function statusText(a) {
    if (a.trial_status && a.status === "Accepted") return { Active: "In progress", Submitted: "Submitted – waiting for review", "Under Review": "Being reviewed", Completed: "Completed", Cancelled: "Cancelled" }[a.trial_status] || a.trial_status;
    return { Pending: "Waiting for BSTM", Accepted: "Accepted", Declined: "Declined", Cancelled: "Withdrawn", Completed: "Completed" }[a.status] || a.status;
  }
  // ---------- the BSTM 100 Trials field card (card + exit snapshot) ----------
  var FC = {
    btype: ["retail", "salon", "food", "services", "other"], size: ["S", "M", "L"],
    entry_type: ["walk-in", "invited", "waited", "redirected"], reaction: ["friendly", "neutral", "defensive", "busy"],
    environment: ["busy", "calm", "chaotic"], interest: ["yes", "no", "neutral"], "return": ["yes", "no"]
  };
  var FC_QUESTIONS = ["How do customers usually find you?", "What time / situation is your busiest?", "What is the hardest part of running this?", "What usually causes delays or mistakes?"];
  function fcCards(trials) { return (trials || []).filter(function (x) { return x.submission && x.submission.type === "field_card"; }).map(function (x) { return x.submission; }); }
  function submitForm(trialId, trials) {
    var draftKey = "bstm-card-" + trialId, st = {}, asked = [false, false, false, false];
    try { var d0 = JSON.parse(localStorage.getItem(draftKey) || "{}"); st = d0.st || {}; asked = d0.asked || asked; } catch (e) { }
    var f = h("form", { novalidate: true, class: "fcard" });
    var save = function () { try { var o = { st: st, asked: asked }; f.querySelectorAll("input[name],textarea[name]").forEach(function (el) { o[el.name] = el.value; }); localStorage.setItem(draftKey, JSON.stringify(o)); } catch (e) { } };
    var saved = {}; try { saved = JSON.parse(localStorage.getItem(draftKey) || "{}"); } catch (e) { }
    function sec(title, note) { f.appendChild(h("h3", { text: title })); if (note) f.appendChild(h("p", { class: "m", text: note })); }
    function text(name, label, long, ph) {
      f.appendChild(h("label", { for: "fc_" + name, text: label }));
      var el = h(long ? "textarea" : "input", { id: "fc_" + name, name: name, maxlength: 400, placeholder: ph || "" }); el.value = saved[name] || ""; el.addEventListener("input", save); f.appendChild(el);
    }
    function pick(name, label) {
      f.appendChild(h("label", { text: label }));
      var row = h("div", { class: "chips", role: "group", "aria-label": label });
      FC[name].forEach(function (o) {
        var b = h("button", { type: "button", class: "chip", text: o, "aria-pressed": st[name] === o ? "true" : "false" });
        b.addEventListener("click", function () { st[name] = st[name] === o ? "" : o; row.querySelectorAll(".chip").forEach(function (c) { c.setAttribute("aria-pressed", c.textContent === st[name] ? "true" : "false"); }); save(); });
        row.appendChild(b);
      });
      f.appendChild(row);
    }
    var n = fcCards(trials).length + 1, today = new Date().toISOString().slice(0, 10);
    f.appendChild(h("h2", { text: "Field card · Trial #" + n }));
    f.appendChild(h("p", { class: "m", text: "In the field I collect. Outside the field I think. Your answers save on this phone as you type." }));
    sec("1. Identification");
    text("business", "Business name"); pick("btype", "Type"); pick("size", "Size"); text("location", "Location (village / town / area)");
    f.appendChild(h("label", { for: "fc_date", text: "Date" })); var dt = h("input", { id: "fc_date", name: "date", type: "date" }); dt.value = saved.date || today; dt.addEventListener("input", save); f.appendChild(dt);
    sec("2. Entry context"); pick("entry_type", "Entry type"); pick("reaction", "Reaction"); text("first_contact", "First contact (what happened in the first minute)");
    sec("3. Core questions", "Tick each one when you asked it.");
    FC_QUESTIONS.forEach(function (q, i) {
      var cb = h("input", { type: "checkbox", id: "q" + i, style: "width:auto;min-height:0;margin-right:8px" }); cb.checked = !!asked[i];
      cb.addEventListener("change", function () { asked[i] = cb.checked; save(); });
      f.appendChild(h("label", { for: "q" + i, style: "font-weight:400" }, cb, q));
    });
    sec("4. Raw quotes", "Exact words only. No interpretation.");
    [1, 2, 3].forEach(function (i) { text("quote" + i, "Quote " + i, false, "“…”"); });
    sec("5. Observation", "What you see, not what they say.");
    text("customer_flow", "Customer flow"); text("staff_behavior", "Staff behavior"); text("bottleneck", "Bottleneck"); pick("environment", "Environment");
    sec("Exit snapshot", "Fill this in outside, within 5 minutes of leaving.");
    text("core_problem", "Core problem (one sentence)", true); text("insight", "Insight (what it means)", true);
    text("struggle", "This business mainly struggles with…"); text("when", "…especially when this happens:");
    pick("interest", "Interest?"); pick("return", "Return?");
    f.appendChild(h("label", { text: "Scores (1–10): A, T, D" }));
    var sr = h("div", { class: "chips" });
    ["a", "t", "d"].forEach(function (k) { var el = h("input", { name: "score_" + k, type: "number", min: 1, max: 10, inputmode: "numeric", placeholder: k.toUpperCase(), "aria-label": "Score " + k.toUpperCase(), style: "width:30%" }); el.value = saved["score_" + k] || ""; el.addEventListener("input", save); sr.appendChild(el); });
    f.appendChild(sr);
    f.appendChild(h("p", { class: "m", text: "Rules: no pitching. No system mentions. No analysis inside the shop. One business = one core problem." }));
    text("link", "Link to photos or notes (optional)");
    f.appendChild(h("button", { class: "btn", type: "submit", text: "Submit trial" }));
    f.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var q = [1, 2, 3].map(function (i) { return val(f, "quote" + i); }).filter(Boolean);
      var card = {
        type: "field_card", trial_no: n, date: val(f, "date"), business: val(f, "business"), btype: st.btype || "", size: st.size || "", location: val(f, "location"),
        entry_type: st.entry_type || "", reaction: st.reaction || "", first_contact: val(f, "first_contact"), asked: asked, quotes: q,
        customer_flow: val(f, "customer_flow"), staff_behavior: val(f, "staff_behavior"), bottleneck: val(f, "bottleneck"), environment: st.environment || "",
        core_problem: val(f, "core_problem"), insight: val(f, "insight"), struggle: val(f, "struggle"), when: val(f, "when"),
        interest: st.interest || "", "return": st["return"] || "", scores: { a: val(f, "score_a"), t: val(f, "score_t"), d: val(f, "score_d") }, link: val(f, "link")
      };
      var need = [["business", "business name"], ["btype", "business type"], ["location", "location"], ["entry_type", "entry type"], ["reaction", "reaction"], ["core_problem", "core problem"], ["insight", "insight"], ["interest", "interest"], ["return", "return"]];
      for (var i = 0; i < need.length; i++) if (!card[need[i][0]]) return say("Please fill in: " + need[i][1] + ".", true);
      if (!q.length) return say("Write at least one exact quote, in their words.", true);
      busy(f.querySelector("button[type=submit]"), api("/me/trials/" + encodeURIComponent(trialId) + "/submit", { body: { submission: card } }))
        .then(function () { try { localStorage.removeItem(draftKey); } catch (e) { } say("Trial #" + n + " submitted. BSTM will review it."); route(); }).catch(fail);
    });
    return f;
  }
  // read-only view of a submitted card (youth tracker, business and staff review)
  function cardView(sub) {
    if (!sub || sub.type !== "field_card") return null;
    var rows = [["Business", [sub.business, sub.btype, sub.size && "size " + sub.size, sub.location].filter(Boolean).join(" · ")],
      ["Entry", [sub.entry_type, sub.reaction].filter(Boolean).join(" · ")], ["Core problem", sub.core_problem], ["Insight", sub.insight],
      ["Summary", sub.struggle ? "Mainly struggles with " + sub.struggle + (sub.when ? ", especially when " + sub.when : "") + "." : ""],
      ["Quotes", (sub.quotes || []).map(function (x) { return "“" + x + "”"; }).join("  ")], ["Seen", [sub.customer_flow, sub.staff_behavior, sub.bottleneck, sub.environment].filter(Boolean).join(" · ")],
      ["Interest / return", [sub.interest, sub.return].join(" / ")], ["Scores", ["a", "t", "d"].map(function (k) { return sub.scores && sub.scores[k] ? k.toUpperCase() + ": " + sub.scores[k] : ""; }).filter(Boolean).join("  ")]];
    var box = h("div", null);
    rows.forEach(function (r) { if (r[1]) box.appendChild(h("p", null, h("strong", { text: r[0] + ": " }), r[1])); });
    return box;
  }
  var STOP = "the a an and or of to in on at is it for with that this they their them are was be have has not no but as by from we you our your can very more often when what which who how".split(" ");
  function patternTracker(trials) {
    var cards = fcCards(trials).sort(function (a, b) { return (a.trial_no || 0) - (b.trial_no || 0); });
    if (!cards.length) return null;
    var box = h("div", { class: "card" }, h("h2", { text: "Pattern tracker" }), h("p", { class: "m", text: "Look for repetition, not perfection." }));
    cards.forEach(function (c) { box.appendChild(h("p", null, h("strong", { text: "#" + c.trial_no + " " }), [c.business, c.btype, c.date].filter(Boolean).join(" · "), h("br"), c.core_problem, c.insight ? h("span", { class: "m", text: " → " + c.insight }) : null)); });
    if (cards.length >= 10) {
      var types = {}, words = {};
      cards.forEach(function (c) { types[c.btype] = (types[c.btype] || 0) + 1; var seen = {}; (c.core_problem + " " + (c.struggle || "")).toLowerCase().replace(/[^a-z\s]/g, " ").split(/\s+/).forEach(function (w) { if (w.length > 3 && STOP.indexOf(w) < 0 && !seen[w]) { seen[w] = 1; words[w] = (words[w] || 0) + 1; } }); });
      var top = Object.keys(words).filter(function (w) { return words[w] >= 3; }).sort(function (a, b) { return words[b] - words[a]; }).slice(0, 3);
      var tt = Object.keys(types).sort(function (a, b) { return types[b] - types[a]; })[0];
      box.appendChild(h("h3", { text: "After 10 trials" }));
      box.appendChild(h("p", null, h("strong", { text: "Problems that repeated: " }), top.length ? top.join(", ") : "none yet"));
      box.appendChild(h("p", null, h("strong", { text: "Business type met most: " }), tt));
      box.appendChild(h("p", { class: "m", text: top.length ? "Repetition found → start thinking about solutions." : "No repetition → continue trials or refine which businesses you approach." }));
    } else box.appendChild(h("p", { class: "m", text: (10 - cards.length) + " more trials until your first analysis." }));
    return box;
  }

  var KINDS = ["Portfolio", "Screenshot", "Document", "BusinessApproval", "Assessment", "Transaction", "Other"];
  var KIND_LABEL = { BusinessApproval: "Business approval", Transaction: "Payment / transaction" };
  function proofView() {
    return Promise.all([api("/me/evidence"), api("/me/capabilities")]).then(function (r) {
      var ev = r[0] || [], caps = r[1] || [];
      var kind = h("select", { name: "kind" }, KINDS.map(function (k) { return h("option", { value: k, text: KIND_LABEL[k] || k }); }));
      var cap = h("select", { name: "capability_id" }, h("option", { value: "", text: "Skill (optional)" }), caps.map(function (c) { return h("option", { value: c.capability_id, text: c.capability_name }); }));
      var f = h("form", { class: "card", novalidate: true }, h("h2", { text: "Add proof of your work" }),
        h("label", { text: "Type" }), kind, h("label", { text: "Skill" }), cap,
        h("label", { text: "Link (optional)" }), h("input", { name: "url", type: "url", maxlength: 2000, placeholder: "https://…", inputmode: "url" }),
        h("label", { text: "Notes" }), h("textarea", { name: "notes", maxlength: 2000 }),
        h("button", { class: "btn", type: "submit", text: t("Submit") }));
      f.addEventListener("submit", function (ev) {
        ev.preventDefault();
        var url = val(f, "url"), notes = val(f, "notes");
        if (!url && !notes) return say("Add a link or some notes.", true);
        if (url && !/^https?:\/\//i.test(url)) return say("The link must start with http:// or https://", true);
        busy(f.querySelector("button"), api("/me/evidence", { body: { kind: kind.value, capability_id: cap.value || null, url: url || null, notes: notes || null } }))
          .then(function () { say("Proof saved."); route(); }).catch(fail);
      });
      var node = h("div", null, subNav("proof"), h("h1", { text: t("Proof") }), f, h("h2", { text: "Your proof" }));
      if (!ev.length) node.appendChild(empty("No proof yet. Proof helps businesses trust you."));
      ev.forEach(function (e) {
        node.appendChild(h("div", { class: "card" }, h("h3", { text: KIND_LABEL[e.kind] || e.kind }),
          e.capability_name ? h("span", { class: "tag", text: e.capability_name }) : null, e.notes ? h("p", { text: e.notes }) : null,
          e.url && /^https?:\/\//i.test(e.url) ? h("p", null, h("a", { href: e.url, target: "_blank", rel: "noopener noreferrer nofollow", text: "Open link" })) : null,
          h("p", { class: "m", text: when(e.created_at) })));
      });
      show(node);
    });
  }

  function skillsView() {
    return Promise.all([api("/me/capabilities"), loadCaps()]).then(function (r) {
      var mine = r[0] || [], all = r[1] || [], have = {};
      mine.forEach(function (c) { have[c.capability_id] = 1; });
      var node = h("div", null, subNav("skills"), h("h1", { text: t("Skills") }));
      if (!mine.length) node.appendChild(empty("You have not added any skills yet."));
      mine.forEach(function (c) { node.appendChild(h("div", { class: "card" }, h("h3", { text: c.capability_name }), h("span", { class: "tag", text: c.level }), c.verified ? h("span", { class: "tag ok", text: "Verified" }) : h("span", { class: "tag", text: "Not yet verified" }))); });
      var pick = {}, free = all.filter(function (c) { return !have[c.id]; });
      if (free.length) {
        var btn = h("button", { class: "btn", type: "button", text: t("Save") });
        btn.addEventListener("click", function () {
          var ids = Object.keys(pick); if (!ids.length) return say("Choose at least one skill.", true);
          busy(btn, Promise.all(ids.map(function (id) { return api("/me/capabilities", { body: { capability_id: id, level: "Beginner" } }); })))
            .then(function () { say("Skills added."); route(); }).catch(fail);
        });
        node.appendChild(h("div", { class: "card" }, h("h2", { text: "Add skills" }), skillPicker(free, pick), btn));
      }
      show(node);
    });
  }


  // ---------- money, profile, alerts (youth) ----------
  var PAYOUT_METHODS = [["MyZaka", "MyZaka"], ["OrangeMoney", "Orange Money"], ["BankEFT", "Bank account"], ["Other", "Other"]];
  function moneyView() {
    return Promise.all([api("/me/earnings"), api("/me/payout-account")]).then(function (r) {
      var e = r[0] || { totals: {}, payouts: [] }, acc = r[1], tt = e.totals || {};
      var node = h("div", null, h("h1", { text: t("Money") }),
        h("div", { class: "card stat" }, stat(pula(tt.awaiting_business), "Waiting for business"), stat(pula(tt.pending_payout), "Ready to send"), stat(pula(tt.paid_out), "Paid to you")),
        h("p", { class: "m", text: "You keep 70% of each job's budget. We pay you after the business has paid us." }));
      var err = h("p", { class: "err", role: "alert" });
      var method = h("select", { name: "method", "aria-label": "How do you want to be paid?" }, PAYOUT_METHODS.map(function (m) { return h("option", { value: m[0], text: m[1], selected: acc && acc.method === m[0] }); }));
      var f = h("form", { class: "card", novalidate: true }, h("h2", { text: acc ? "Where we pay you" : "Add where we should pay you" }),
        !acc ? h("p", { class: "m", text: "Needed before we can send your money." }) : null,
        h("label", { text: "How do you want to be paid?" }), method,
        field("Name on the account", "account_name", "text", { max: 120, value: acc && acc.account_name }),
        field("Phone or account number", "account_ref", "text", { max: 60, im: "numeric", value: acc && acc.account_ref }), err,
        h("button", { class: "btn", type: "submit", text: t("Save") }));
      f.addEventListener("submit", function (ev) {
        ev.preventDefault(); err.textContent = "";
        var body = { method: method.value, account_name: val(f, "account_name"), account_ref: val(f, "account_ref") };
        if (!body.account_name || body.account_ref.length < 6) return (err.textContent = "Enter the name and a phone or account number (at least 6 characters).");
        busy(f.querySelector("button"), api("/me/payout-account", { method: "PUT", body: body })).then(function () { say("Saved."); route(); }).catch(function (x) { err.textContent = x.message; });
      });
      node.appendChild(f);
      node.appendChild(h("h2", { text: "Your payouts" }));
      if (!e.payouts.length) node.appendChild(empty("No payouts yet. They appear after a business pays for your finished job."));
      e.payouts.forEach(function (p) {
        node.appendChild(h("div", { class: "card" }, h("h3", { text: pula(p.amount) + " · " + (p.opportunity_title || p.invoice_reference) }),
          h("p", null, h("span", { class: "tag " + (p.status === "Paid" ? "ok" : "warn"), text: { Pending: "Being prepared", Paid: "Paid", Failed: "Retrying" }[p.status] || p.status })),
          p.status === "Paid" ? h("p", { class: "m", text: "Sent to " + p.destination + " · ref " + p.provider_ref + " · " + when(p.paid_at) }) : (p.destination ? null : h("p", { class: "m", text: "Add your payout details above so we can pay you." }))));
      });
      show(node);
    });
  }

  function pwCard(p) {
    var err = h("p", { class: "err", role: "alert" });
    var f = h("form", { class: "card", novalidate: true }, h("h3", { text: p && p.must_change_password ? "Choose your own password" : "Change password" }),
      p && p.must_change_password ? h("p", { class: "m", text: "Someone helped you register. Choose a password only you know." }) : null,
      field("Current password", "current", "password", { ac: "current-password", max: 128 }), field("New password (8+ characters)", "newpw", "password", { ac: "new-password", max: 128 }), err,
      h("button", { class: "btn", type: "submit", text: "Save password" }));
    f.addEventListener("submit", function (ev) {
      ev.preventDefault(); err.textContent = "";
      var cur = f.querySelector("[name=current]").value, nw = f.querySelector("[name=newpw]").value;
      if (!cur || nw.length < 8) return (err.textContent = "Enter your current password and a new one of at least 8 characters.");
      busy(f.querySelector("button"), api("/me/password", { method: "PUT", body: { current: cur, "new": nw } })).then(function () { say("Password changed."); route(); }).catch(function (e) { err.textContent = e.message; });
    });
    return f;
  }
  function profileView() {
    return profile().then(function (p) {
      var err = h("p", { class: "err", role: "alert" });
      var pub = h("input", { type: "checkbox", id: "f_pub", name: "public_profile", style: "width:auto;min-height:0" }); pub.checked = !!p.public_profile;
      var f = h("form", { class: "card", novalidate: true }, h("h2", { text: "Your profile" }),
        field("Name", "name", "text", { value: p.name }),
        h("div", null, h("label", { for: "f_bio", text: "About you (what you do, what you want)" }), h("textarea", { id: "f_bio", name: "bio", maxlength: 500 })),
        field("Where do you live?", "location", "text", { max: 120, list: "places", value: p.location }),
        h("datalist", { id: "places" }, PLACES.map(function (x) { return h("option", { value: x }); })),
        field("When are you free?", "availability", "text", { max: 100, value: p.availability }),
        field("What equipment do you have?", "equipment", "text", { max: 300, value: p.equipment }),
        h("label", { for: "f_pub" }, pub, " Let businesses see my profile"),
        h("p", { class: "m", text: "Public profiles show your name, town, skills and record. Never your email, money or private answers." }), err,
        h("button", { class: "btn", type: "submit", text: t("Save") }));
      f.querySelector("[name=bio]").value = p.bio || "";
      f.querySelector("[name=name]").disabled = true;
      f.addEventListener("submit", function (ev) {
        ev.preventDefault(); err.textContent = "";
        var body = { bio: val(f, "bio") || null, location: val(f, "location"), availability: val(f, "availability") || null, equipment: val(f, "equipment") || null, passion: p.passion || null, public_profile: pub.checked };
        if (!body.location) return (err.textContent = "Please enter where you live.");
        busy(f.querySelector("button[type=submit]"), api("/me/profile", { method: "PUT", body: body })).then(function () { say("Profile saved."); route(); }).catch(function (x) { err.textContent = x.message; });
      });
      var node = h("div", null, subNav("profile"), p.must_change_password ? pwCard(p) : null, f);
      if (!p.must_change_password) node.appendChild(pwCard(p));
      var dpw = h("input", { type: "password", autocomplete: "current-password", maxlength: 128, "aria-label": "Your password", placeholder: "Your password" });
      var dErr = h("p", { class: "err", role: "alert" });
      node.appendChild(h("div", { class: "card" }, h("h3", { text: "Your data" }),
        h("p", { class: "m", text: "Download everything we hold about you, or delete your account. Deleting removes your personal details. Money records stay for the business." }),
        h("button", { class: "btn sm sec", type: "button", text: "Download my data", onclick: function () {
          api("/me/export").then(function (d) {
            var a = h("a", { href: URL.createObjectURL(new Blob([JSON.stringify(d, null, 2)], { type: "application/json" })), download: "my-bstm-data.json" });
            document.body.appendChild(a); a.click(); a.remove();
          }).catch(fail);
        } }),
        dpw, dErr,
        h("button", { class: "btn sm sec", type: "button", text: "Delete my account", onclick: function () {
          dErr.textContent = ""; if (!dpw.value) return (dErr.textContent = "Enter your password to confirm.");
          if (!window.confirm("Delete your account? This cannot be undone.")) return;
          api("/me/delete", { method: "POST", body: { password: dpw.value } }).then(function () { logout(false); say("Account deleted."); }).catch(function (e) { dErr.textContent = e.message; });
        } })));
      if (p.public_profile) {
        var link = location.origin + "/#/p/" + p.id;
        node.appendChild(h("div", { class: "card" }, h("h3", { text: "Your public link" }), h("p", { class: "m", text: link }),
          h("button", { class: "btn sm sec", type: "button", text: "Copy link", onclick: function () { try { navigator.clipboard.writeText(link).then(function () { say("Link copied."); }); } catch (x) { say("Copy the link above.", true); } } }),
          h("button", { class: "btn sm sec", type: "button", text: "Preview", onclick: function () { location.hash = "#/p/" + p.id; } })));
      }
      show(node);
    });
  }

  function publicProfileView(id) {
    show(h("div", { class: "spin", text: t("Loading…") }));
    api("/public/profiles/" + encodeURIComponent(id), { anon: true }).then(function (p) {
      var skill = function (s) { return h("span", { class: "tag " + (s.verified ? "ok" : ""), text: s.name + " · " + s.level + (s.verified ? " ✓" : "") }); };
      show(h("div", null,
        h("div", { class: "card" }, h("h1", { text: p.name }), h("p", { class: "m", text: [p.location, p.level].filter(Boolean).join(" · ") }), p.bio ? h("p", { text: p.bio }) : null,
          h("div", { class: "stat" }, stat(p.completed_jobs, "Jobs done"), stat(p.completed_trials, "Work approved"))),
        h("div", { class: "card" }, h("h2", { text: "Verified skills" }), p.verified_skills.length ? h("p", null, p.verified_skills.map(skill)) : h("p", { class: "m", text: "None verified yet." }),
          h("h2", { text: "Claimed skills" }), p.declared_skills.length ? h("p", null, p.declared_skills.map(skill)) : h("p", { class: "m", text: "None." })),
        h("p", { class: "m", text: "✓ means BSTM checked it. Claimed skills are the person's own words." }),
        h("button", { class: "btn sec", type: "button", text: t("Back"), onclick: function () { location.hash = ""; route(); } })));
    }).catch(function () {
      show(h("div", { class: "card empty" }, h("p", { text: "This profile is private or does not exist." }), h("button", { class: "btn", type: "button", text: t("Back"), onclick: function () { location.hash = ""; route(); } })));
    });
  }

  function alertsView() {
    var biz = !!S.btoken, base = biz ? "/biz" : "/me";
    return api(base + "/notifications").then(function (r) {
      var node = h("div", null, h("h1", { text: t("Alerts") }));
      if (!r.items.length) node.appendChild(empty("Nothing new. We will tell you here when something happens."));
      r.items.forEach(function (n) {
        node.appendChild(h("div", { class: "card" }, h("h3", { text: n.title }), n.body ? h("p", { text: n.body }) : null,
          h("p", { class: "m" }, when(n.created_at), n.read_at ? "" : " · ", n.read_at ? null : h("span", { class: "tag warn", text: "New" }))));
      });
      show(node);
      if (r.unread) api(base + "/notifications/read", { method: "POST", body: {} }).then(function () { bell(0); }, function () {});
    });
  }

  // ---------- business door ----------
  var SECTORS = ["Retail", "Food & catering", "Farming", "Transport", "Construction", "Beauty & salon", "Education", "Health", "Technology", "Manufacturing", "Other"];
  function businessScreen() {
    var err = h("p", { class: "err", role: "alert" }), staff = !!S.adminKey;
    var f = h("form", { class: "card", novalidate: true }, h("h1", { text: "Register your business" }),
      field("Business name", "name", "text", { max: 150 }), field("Owner name", "owner", "text", { max: 120 }),
      h("div", null, h("label", { for: "f_sector", text: "Sector" }), h("select", { id: "f_sector", name: "sector" }, SECTORS.map(function (x) { return h("option", { value: x, text: x }); }))),
      field("Where is it? (town or village)", "location", "text", { max: 120, list: "places" }),
      h("datalist", { id: "places" }, PLACES.map(function (p) { return h("option", { value: p }); })),
      h("div", null, h("label", { for: "f_problem", text: "What is your biggest problem?" }), h("textarea", { id: "f_problem", name: "main_problem", maxlength: 1000 })),
      h("h2", { text: staff ? "Account (optional)" : "Your account" }),
      field("Phone", "phone", "tel", { ac: "tel", max: 30, im: "tel" }),
      field("Email", "email", "email", { ac: "email", max: 254, im: "email" }),
      field("Password", "password", "password", { ac: "new-password", max: 128 }),
      h("p", { class: "m", text: staff ? "Leave email and password empty to register the business without an account." : "You will use your email and password to post jobs, hire, and pay. At least 8 characters." }),
      err, h("button", { class: "btn", type: "submit", text: staff ? "Register" : "Get help" }), h("button", { class: "btn sec", type: "button", text: t("Back"), onclick: staff ? route : landing }));
    f.addEventListener("submit", function (ev) {
      ev.preventDefault(); err.textContent = "";
      var body = { name: val(f, "name"), owner: val(f, "owner"), sector: val(f, "sector"), location: val(f, "location"), main_problem: val(f, "main_problem") };
      var email = val(f, "email"), pw = f.querySelector("[name=password]").value, phone = val(f, "phone");
      if (!body.name || !body.owner || !body.location || !body.main_problem) return (err.textContent = "Please fill in the business details.");
      if (phone) body.phone = phone;
      if (email || pw || !staff) {
        if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) return (err.textContent = "Enter a valid email address.");
        if (pw.length < 8) return (err.textContent = "Password must be at least 8 characters.");
        body.email = email; body.password = pw;
      }
      busy(f.querySelector("button[type=submit]"), api("/businesses", { anon: true, body: body })).then(function (r) {
        var diag = (r.diagnosis || []).map(function (d) { return h("div", { class: "card" }, h("h3", { text: d.title }), h("p", { class: "m", text: "BSTM department: " + d.department })); });
        var done = function () { if (r.access_token && !staff) { setBtoken(r.access_token); S.btab = "bjobs"; route(); } else route(); };
        show(h("div", null, h("div", { class: "card" }, h("h1", { text: "Thank you, " + body.name }),
          h("p", { text: r.access_token ? "Your account is ready. Here is where we think youth can help:" : "The business is registered. Here is where youth can help:" })), diag,
          h("button", { class: "btn", type: "button", text: r.access_token && !staff ? "Go to my jobs" : "Done", onclick: done })));
      }).catch(function (e) { err.textContent = e.message; });
    });
    show(f);
  }

  function resetScreen(type) {
    var err = h("p", { class: "err", role: "alert" });
    var f = h("form", { class: "card", novalidate: true }, h("h1", { text: "Forgot password" }),
      h("p", { class: "m", text: "Ask BSTM for a reset code (call or message us). We will check it is you and give you a code. Then enter it here." }),
      field(type === "youth" ? "Email or phone number" : "Email", "email", "text", { ac: "username", max: 254 }), field("Code from BSTM", "code", "text", { max: 20, ac: "off" }),
      field("New password (12+ characters)", "password", "password", { ac: "new-password", max: 128 }), err,
      h("button", { class: "btn", type: "submit", text: "Set new password" }), h("button", { class: "btn sec", type: "button", text: t("Back"), onclick: type === "youth" ? loginScreen : bizLoginScreen }));
    f.addEventListener("submit", function (ev) {
      ev.preventDefault(); err.textContent = "";
      busy(f.querySelector("button[type=submit]"), api("/auth/reset", { anon: true, body: { account_type: type, email: val(f, "email"), code: val(f, "code"), new_password: f.querySelector("[name=password]").value } }))
        .then(function () { say("Password changed. Please log in."); (type === "youth" ? loginScreen : bizLoginScreen)(); }).catch(function (e) { err.textContent = e.message; });
    });
    show(f);
  }
  function bizLoginScreen() {
    var err = h("p", { class: "err", role: "alert" });
    var f = h("form", { class: "card", novalidate: true }, h("h1", { text: t("Log in as business") }),
      field("Email", "email", "email", { ac: "email", max: 254, im: "email" }), field("Password", "password", "password", { ac: "current-password", max: 128 }), err,
      h("button", { class: "btn", type: "submit", text: t("Log in") }), h("button", { class: "btn sec", type: "button", text: "Forgot password?", onclick: function () { resetScreen("business"); } }), h("button", { class: "btn sec", type: "button", text: t("Back"), onclick: landing }));
    f.addEventListener("submit", function (ev) {
      ev.preventDefault(); err.textContent = "";
      busy(f.querySelector("button[type=submit]"), api("/businesses/login", { anon: true, body: { email: val(f, "email"), password: f.querySelector("[name=password]").value } }))
        .then(function (r) { setBtoken(r.access_token); S.btab = "bjobs"; route(); }).catch(function (e) { err.textContent = e.message; });
    });
    show(f);
  }

  // ---------- business portal ----------
  function bizRoute() {
    show(h("div", { class: "spin", text: t("Loading…") }));
    ({ bjobs: bJobs, bpost: bPost, binv: bInvoices, alerts: alertsView }[S.btab] || bJobs)().catch(function (e) {
      if (e && e.status === 401) return fail(e);
      show(h("div", { class: "card empty" }, h("p", { text: e.message || "Could not load." }), h("button", { class: "btn", type: "button", text: "Try again", onclick: route })));
    });
  }
  function bAct(card, label, path, body, cls, ok) {
    var b = h("button", { class: "btn sm " + (cls || ""), type: "button", text: label });
    b.addEventListener("click", function () { busy(b, api(path, { method: "POST", body: body || {} })).then(function () { say(ok || "Done."); route(); }).catch(fail); });
    card.appendChild(b);
  }
  var APPROVAL_TAG = { Pending: ["warn", "Waiting for BSTM approval"], Approved: ["ok", "Live"], Rejected: ["", "Not approved"] };
  function bJobs() {
    return Promise.all([api("/biz"), api("/biz/opportunities")]).then(function (r) {
      var me = r[0], list = r[1] || [];
      var node = h("div", null, h("h1", { text: me.name }), h("p", { class: "m", text: "Your jobs" }));
      if (!list.length) node.appendChild(empty("No jobs yet. Tap “Post a job” to ask for help."));
      list.forEach(function (o) {
        var out = h("div"), tag = APPROVAL_TAG[o.approval_status] || ["", o.approval_status];
        var card = h("div", { class: "card" }, h("h3", { text: o.title }), h("p", { class: "m", text: [o.department, money(o.budget)].filter(Boolean).join(" · ") }),
          h("p", null, h("span", { class: "tag " + tag[0], text: tag[1] }), o.approval_status === "Approved" ? h("span", { class: "tag", text: o.status }) : null, h("span", { class: "tag", text: o.people + " people" })), out);
        var show1 = h("button", { class: "btn sm sec", type: "button", text: "People on this job" });
        show1.addEventListener("click", function () { busy(show1, loadPeople(o, out)).catch(fail); });
        card.appendChild(show1);
        if (o.status === "Open") bAct(card, "Close job", "/biz/opportunities/" + o.id + "/close", {}, "sec", "Job closed.");
        node.appendChild(card);
      });
      show(node);
    });
  }
  function loadPeople(o, out) {
    return api("/biz/opportunities/" + encodeURIComponent(o.id) + "/people").then(function (people) {
      clear(out); if (!people.length) out.appendChild(h("p", { class: "m", text: "Nobody yet." }));
      people.forEach(function (p) {
        var row = h("div", { class: "card" }, h("p", null, h("strong", { text: p.name }), " ", h("span", { class: "tag", text: p.status })),
          h("p", { class: "m", text: [p.location, p.level, p.verified_skills + " verified skills"].join(" · ") }));
        if (p.status === "Pending" && p.opportunity_status === "Open") {
          bAct(row, "Choose this person", "/biz/assignments/" + p.assignment_id + "/accept", {}, "", "Chosen. They have been told.");
          bAct(row, "Not this one", "/biz/assignments/" + p.assignment_id + "/decline", {}, "sec", "Declined.");
        }
        if (p.trial_status === "Submitted" || p.trial_status === "Under Review") {
          var sub = p.submission || {};
          row.appendChild(h("p", null, h("strong", { text: "Work submitted: " }), sub.type === "field_card" ? "" : (sub.summary || ""))); var cv = cardView(sub); if (cv) row.appendChild(cv);
          row.appendChild(h("p", null, safeLink(sub.link)));
          var score = h("input", { type: "number", min: 0, max: 100, placeholder: "Score 0–100", inputmode: "numeric", "aria-label": "Score" });
          var ok = h("button", { class: "btn sm", type: "button", text: "Approve work" });
          ok.addEventListener("click", function () {
            var n = Number(score.value); if (score.value === "" || !(n >= 0 && n <= 100)) return say("Enter a score from 0 to 100.", true);
            if (!window.confirm("Approve this work? We will send you an invoice.")) return;
            busy(ok, api("/biz/trials/" + encodeURIComponent(p.trial_id) + "/approve", { method: "POST", body: { score: n } })).then(function () { say("Approved. Your invoice is ready."); route(); }).catch(fail);
          });
          row.appendChild(score); row.appendChild(ok);
        } else if (p.trial_status === "Active") row.appendChild(h("p", { class: "m", text: "Working on it now." }));
        if (p.status === "Completed") row.appendChild(h("p", { class: "m", text: "Finished. Check Invoices." }));
        out.appendChild(row);
      });
    });
  }
  function bPost() {
    return Promise.all([loadDepts(), api("/catalog/capabilities", { anon: true }).catch(function () { return []; })]).then(function (rr) {
      var depts = rr[0], caps = rr[1] || [], chosen = {};
      var skillBox = h("div", null, h("label", { text: "Skills needed (pick up to 5, optional)" }), h("p", { class: "m", text: "This helps BSTM send your job to the right young people." }));
      var chips = h("div", { class: "chips" });
      var countNote = h("p", { class: "m", text: "" });
      caps.forEach(function (c) {
        var b = h("button", { type: "button", class: "chip", "aria-pressed": "false", text: c.name });
        b.addEventListener("click", function () {
          if (chosen[c.id]) { delete chosen[c.id]; b.setAttribute("aria-pressed", "false"); }
          else if (Object.keys(chosen).length >= 5) { say("Choose at most 5 skills.", true); return; }
          else { chosen[c.id] = 1; b.setAttribute("aria-pressed", "true"); }
          countNote.textContent = Object.keys(chosen).length ? Object.keys(chosen).length + " chosen" : "";
        });
        chips.appendChild(b);
      });
      skillBox.appendChild(chips); skillBox.appendChild(countNote);
      var err = h("p", { class: "err", role: "alert" });
      var f = h("form", { class: "card", novalidate: true }, h("h1", { text: t("Post a job") }),
        field("What do you need done?", "title", "text", { max: 200, ph: "e.g. Make a poster for my shop" }),
        h("div", null, h("label", { for: "f_desc", text: "Details" }), h("textarea", { id: "f_desc", name: "description", maxlength: 4000, placeholder: "What exactly? By when? Where?" })),
        h("div", null, h("label", { for: "f_dept", text: "Type of help" }), h("select", { id: "f_dept", name: "department" }, h("option", { value: "", text: "Not sure" }), depts.map(function (d) { return h("option", { value: d, text: d }); }))),
        skillBox,
        field("Budget (Pula)", "budget", "number", { im: "numeric", ph: "0 if free" }),
        h("p", { class: "m", text: "BSTM checks every job before youth see it. You pay after the work is approved; the youth gets 70%." }), err,
        h("button", { class: "btn", type: "submit", text: t("Submit") }));
      f.addEventListener("submit", function (ev) {
        ev.preventDefault(); err.textContent = "";
        var body = { title: val(f, "title"), description: val(f, "description") || null, department: val(f, "department") || null, budget: Number(val(f, "budget")) || 0, skills: Object.keys(chosen) };
        if (!body.title) return (err.textContent = "Say what you need done.");
        if (body.budget < 0) return (err.textContent = "Budget cannot be negative.");
        busy(f.querySelector("button[type=submit]"), api("/biz/opportunities", { method: "POST", body: body })).then(function () { say("Sent. BSTM will approve it soon."); S.btab = "bjobs"; route(); }).catch(function (x) { err.textContent = x.message; });
      });
      show(f);
    });
  }
  var PAY_METHODS = [["MyZaka", "MyZaka"], ["OrangeMoney", "Orange Money"], ["BankEFT", "Bank transfer (EFT)"], ["Cash", "Cash paid to BSTM"]];
  function bInvoices() {
    return Promise.all([api("/biz"), api("/biz/invoices")]).then(function (r) {
      var me = r[0], list = r[1] || [];
      var node = h("div", null, h("h1", { text: t("Invoices") }), h("div", { class: "card" }, h("h3", { text: "How to pay" }), h("p", { text: me.payment_instructions || "" })));
      if (!list.length) node.appendChild(empty("No invoices yet. One appears when you approve finished work."));
      list.forEach(function (i) {
        var owed = Number(i.amount) - Number(i.paid_amount || 0);
        var card = h("div", { class: "card" }, h("h3", { text: i.reference + " · " + pula(i.amount) }), h("p", { class: "m", text: (i.opportunity_title || "") + " · " + when(i.created_at) }),
          h("p", null, h("span", { class: "tag " + (i.status === "Paid" ? "ok" : "warn"), text: i.status === "Paid" ? "Paid" : "Waiting for payment" }),
            Number(i.pending_payments) > 0 ? h("span", { class: "tag", text: "Payment being checked" }) : null));
        if (i.status === "Issued" && Number(i.pending_payments) === 0 && owed > 0) card.appendChild(payForm(i, owed));
        node.appendChild(card);
      });
      show(node);
    });
  }
  function payForm(i, owed) {
    var key = idem(), err = h("p", { class: "err", role: "alert" });
    var method = h("select", { name: "method", "aria-label": "Payment method" }, PAY_METHODS.map(function (m) { return h("option", { value: m[0], text: m[1] }); }));
    var f = h("form", { novalidate: true }, h("p", { class: "m", text: "After you pay " + pula(owed) + ", tell us the reference you got:" }), method,
      h("input", { name: "provider_ref", type: "text", maxlength: 80, placeholder: "Payment reference / receipt number", "aria-label": "Payment reference", style: "margin-top:8px" }), err,
      h("button", { class: "btn sm", type: "submit", text: "I have paid" }));
    f.addEventListener("submit", function (ev) {
      ev.preventDefault(); err.textContent = "";
      var ref = val(f, "provider_ref");
      if (method.value !== "Cash" && ref.length < 4) return (err.textContent = "Enter the payment reference (at least 4 characters).");
      busy(f.querySelector("button"), api("/biz/invoices/" + encodeURIComponent(i.id) + "/payments", { method: "POST", headers: { "Idempotency-Key": key }, body: { method: method.value, provider_ref: ref || null } }))
        .then(function () { say("Thank you. We will confirm your payment."); route(); }).catch(function (x) { err.textContent = x.message; });
    });
    return f;
  }

  // ---------- staff console ----------
  function staffLogin() {
    var err = h("p", { class: "err", role: "alert" });
    var f = h("form", { class: "card", novalidate: true }, h("h1", { text: "Staff sign in" }),
      field("Email", "email", "email", { ac: "email", max: 254, im: "email" }), field("Password", "password", "password", { ac: "current-password", max: 128 }), err,
      h("button", { class: "btn", type: "submit", text: t("Log in") }),
      h("button", { class: "btn sec", type: "button", text: "Create a staff account", onclick: staffSignup }),
      h("button", { class: "btn sec", type: "button", text: t("Back"), onclick: landing }));
    function keep(r) {
      try { sessionStorage.removeItem("bstm_admin"); if (r) { sessionStorage.setItem("bstm_staff", r.token); sessionStorage.setItem("bstm_srole", r.role); sessionStorage.setItem("bstm_sname", r.name); } else sessionStorage.setItem("bstm_admin", S.adminKey); } catch (e) {}
    }
    f.addEventListener("submit", function (ev) {
      ev.preventDefault(); err.textContent = "";
      var btn = f.querySelector("button[type=submit]");
      busy(btn, api("/staff/login", { anon: true, body: { email: val(f, "email"), password: f.querySelector("[name=password]").value } })).then(function (r) {
        S.staffToken = r.access_token; S.staffRole = r.role; S.staffName = r.name; S.adminKey = null; S.atab = r.role === "agent" ? "agent" : "queue";
        keep({ token: r.access_token, role: r.role, name: r.name }); route();
      }).catch(function (e) { err.textContent = e.message; });
    });
    show(f);
  }
  function staffSignup() {
    var err = h("p", { class: "err", role: "alert" });
    var f = h("form", { class: "card", novalidate: true }, h("h1", { text: "Create a staff account" }),
      h("p", { class: "m", text: "Your account stays switched off until the BSTM owner approves it and gives you a role." }),
      field("Your name", "name", "text", { max: 120 }), field("Email", "email", "email", { ac: "email", max: 254, im: "email" }),
      field("Password (12+ characters)", "password", "password", { ac: "new-password", max: 128 }), err,
      h("button", { class: "btn", type: "submit", text: "Ask for an account" }), h("button", { class: "btn sec", type: "button", text: t("Back"), onclick: staffLogin }));
    f.addEventListener("submit", function (ev) {
      ev.preventDefault(); err.textContent = "";
      busy(f.querySelector("button[type=submit]"), api("/staff/signup", { anon: true, body: { name: val(f, "name"), email: val(f, "email"), password: f.querySelector("[name=password]").value } }))
        .then(function () { say("Request sent. The owner will approve it."); staffLogin(); }).catch(function (e) { err.textContent = e.message; });
    });
    show(f);
  }
  function adminLogout() {
    S.adminKey = null; S.staffToken = null; S.staffRole = null; S.staffName = null; S.migOk = false;
    try { ["bstm_admin", "bstm_staff", "bstm_srole", "bstm_sname"].forEach(function (k) { sessionStorage.removeItem(k); }); } catch (e) {}
    route();
  }
  var A = function (path, body) { return api(path, { admin: true, method: body !== undefined ? "POST" : "GET", body: body !== undefined ? body : undefined }); };
  function aact(card, label, path, body, cls, ok) {
    var b = h("button", { class: "btn sm " + (cls || ""), type: "button", text: label });
    b.addEventListener("click", function () { busy(b, A(path, body || {})).then(function () { say(ok || "Done."); route(); }).catch(fail); });
    card.appendChild(b);
  }
  function migrateScreen(m) {
    var out = h("p", { class: "err", role: "alert" });
    var b = h("button", { class: "btn", type: "button", text: "Update database now" });
    b.addEventListener("click", function () {
      out.textContent = "";
      busy(b, A("/admin/migrations/apply", {})).then(function (r) { S.migOk = true; say("Database updated (" + r.applied_now.length + " changes)."); route(); })
        .catch(function (e) { out.textContent = e.message; });
    });
    show(h("div", { class: "card" }, h("h1", { text: "Database update needed" }),
      h("p", { text: "This version needs " + m.pending.length + " database change(s). It is safe and only adds things; your data is kept." }),
      h("ul", null, m.pending.map(function (n) { return h("li", { class: "m", text: n }); })), out, b,
      h("button", { class: "btn sec", type: "button", text: "Skip for now", onclick: function () { S.migOk = true; route(); } })));
  }
  function adminRoute() {
    if (!S.migOk && S.staffRole !== "admin" && S.staffRole !== "owner") S.migOk = true;
    if (!S.migOk) {
      show(h("div", { class: "spin", text: t("Loading…") }));
      return A("/admin/migrations").then(function (m) { if (m && m.pending && m.pending.length) return migrateScreen(m); S.migOk = true; route(); },
        function () { S.migOk = true; route(); });
    }
    show(h("div", { class: "spin", text: t("Loading…") }));
    ({ queue: aQueue, money: aMoney, biz: aBiz, jobs: aJobs, youth: aYouth, audit: aAudit, reset: aReset, team: aTeam, rep: aRep, agent: aAgent, sys: aSys, owner: aOwner }[S.atab] || (S.staffRole === "agent" ? aAgent : aQueue))().catch(function (e) {
      if (e && (e.status === 401 || e.status === 403)) return fail(e);
      show(h("div", { class: "card empty" }, h("p", { text: e.message }), h("button", { class: "btn", type: "button", text: "Try again", onclick: route })));
    });
  }
  function aReset() {
    var err = h("p", { class: "err", role: "alert" }), shown = h("div");
    var type = h("select", { "aria-label": "Account type" }, h("option", { value: "youth", text: "Youth" }), h("option", { value: "business", text: "Business" }));
    var f = h("form", { class: "card", novalidate: true }, h("h2", { text: "Password reset code" }),
      h("p", { class: "m", text: "First confirm the person is who they say (phone call or in person). Then create a code and tell it to them." }),
      type, field("Their email or phone number", "email", "text", { max: 254 }), err, h("button", { class: "btn", type: "submit", text: "Create code" }));
    f.addEventListener("submit", function (ev) {
      ev.preventDefault(); err.textContent = "";
      busy(f.querySelector("button"), A("/admin/resets", { account_type: type.value, email: val(f, "email") })).then(function (r) {
        clear(shown); shown.appendChild(h("div", { class: "card" }, h("h3", { text: "Code (shown once)" }), h("p", { style: "font-size:2rem;letter-spacing:.2em;font-weight:700", text: r.code }),
          h("p", { class: "m", text: "Valid for " + r.expires_in_hours + " hours. They open Log in, then Forgot password." })));
      }).catch(function (e) { err.textContent = e.message; });
    });
    return A("/admin/resets").then(function (list) {
      var node = h("div", null, h("h1", { text: "Resets" }), f, shown, h("h2", { text: "Open codes (" + list.length + ")" }));
      if (!list.length) node.appendChild(empty("No open codes."));
      list.forEach(function (r) { node.appendChild(h("div", { class: "card" }, h("p", { text: r.email + " (" + r.account_type + ")" }), h("p", { class: "m", text: "by " + r.created_by + " · expires " + when(r.expires_at) }))); });
      show(node);
    });
  }
  function aTeam() {
    return A("/admin/staff").then(function (list) {
      var err = h("p", { class: "err", role: "alert" });
      var role = h("select", { "aria-label": "Role" }, ["finance", "field", "support", "agent", "admin"].map(function (x) { return h("option", { value: x, text: x }); }));
      var f = h("form", { class: "card", novalidate: true }, h("h2", { text: "Add a team member" }),
        h("p", { class: "m", text: "finance: money. field: jobs, trials, audits. support: resets and viewing people. agent: registers people on their phone. admin: everything." }),
        field("Name", "name", "text", { max: 120 }), field("Email", "email", "email", { max: 254, im: "email" }), field("Password (12+ characters)", "password", "password", { ac: "new-password", max: 128 }), role, err,
        h("button", { class: "btn", type: "submit", text: "Add" }));
      f.addEventListener("submit", function (ev) {
        ev.preventDefault(); err.textContent = "";
        busy(f.querySelector("button"), A("/admin/staff", { name: val(f, "name"), email: val(f, "email"), password: f.querySelector("[name=password]").value, role: role.value }))
          .then(function () { say("Team member added."); route(); }).catch(function (e) { err.textContent = e.message; });
      });
      var node = h("div", null, h("h1", { text: "Team" }),
        h("div", { class: "card" }, h("h3", { text: "Owner (built in)" }), h("p", { class: "m", text: "Signs in with the owner email and the owner password. Cannot be removed." })), f);
      var del = function (card, m) {
        var b = h("button", { class: "btn sm sec", type: "button", text: "Delete" });
        b.addEventListener("click", function () {
          if (!window.confirm("Delete " + m.name + "? They lose access immediately.")) return;
          busy(b, api("/admin/staff/" + m.id, { admin: true, method: "DELETE" })).then(function () { say("Deleted."); route(); }).catch(fail);
        });
        card.appendChild(b);
      };
      list.forEach(function (m) {
        var card = h("div", { class: "card" }, h("h3", { text: m.name }), h("p", { class: "m", text: m.email + " · last in " + (m.last_login_at ? when(m.last_login_at) : "never") }));
        if (m.approved === false) {
          var rs = h("select", { "aria-label": "Role" }, ["support", "field", "finance", "agent", "admin"].map(function (x) { return h("option", { value: x, text: x }); }));
          card.appendChild(h("p", null, h("span", { class: "tag warn", text: "Waiting for approval" })));
          card.appendChild(rs);
          var ok = h("button", { class: "btn sm", type: "button", text: "Approve" });
          ok.addEventListener("click", function () { busy(ok, A("/admin/staff/" + m.id + "/approve", { role: rs.value })).then(function () { say("Approved."); route(); }).catch(fail); });
          card.appendChild(ok);
        } else {
          card.appendChild(h("p", null, h("span", { class: "tag", text: m.role }), h("span", { class: "tag " + (m.active ? "ok" : "warn"), text: m.active ? "Active" : "Off" })));
          var rc = h("select", { "aria-label": "Change role" }, ["support", "field", "finance", "admin"].map(function (x) { return h("option", { value: x, text: x, selected: x === m.role ? "selected" : null }); }));
          rc.value = m.role;
          var rb = h("button", { class: "btn sm", type: "button", text: "Change role" });
          rb.addEventListener("click", function () {
            if (rc.value === m.role) return say("They already have that role.", true);
            busy(rb, A("/admin/staff/" + m.id + "/role", { role: rc.value })).then(function () { say(m.name + " is now " + rc.value + "."); route(); }).catch(fail);
          });
          card.appendChild(rc); card.appendChild(rb);
          aact(card, m.active ? "Turn off" : "Turn on", "/admin/staff/" + m.id + "/active", { active: !m.active }, "sec", "Saved.");
        }
        del(card, m);
        node.appendChild(card);
      });
      show(node);
    });
  }
  function aRep() {
    var now = new Date(), opts = [];
    for (var i = 0; i < 12; i++) { var d = new Date(now.getFullYear(), now.getMonth() - i, 1); opts.push(d.getFullYear() + "-" + ("0" + (d.getMonth() + 1)).slice(-2)); }
    var month = S.rmonth || opts[0];
    return A("/admin/report?month=" + month).then(function (r) {
      var sel = h("select", { "aria-label": "Month" }, opts.map(function (o) { return h("option", { value: o, text: o, selected: o === month ? "selected" : null }); }));
      sel.addEventListener("change", function () { S.rmonth = sel.value; route(); });
      var copy = h("button", { class: "btn sm", type: "button", text: "Copy summary" });
      copy.addEventListener("click", function () { (navigator.clipboard ? navigator.clipboard.writeText(r.text) : Promise.reject()).then(function () { say("Copied."); }).catch(function () { say("Could not copy. Select the text and copy it.", true); }); });
      var tile = function (n, l) { return h("div", { class: "card" }, h("h2", { text: String(n) }), h("p", { class: "m", text: l })); };
      var pula = function (n) { return "P" + Number(n).toLocaleString("en", { minimumFractionDigits: 2, maximumFractionDigits: 2 }); };
      var node = h("div", null, h("h1", { text: "Reports" }), h("p", { class: "m", text: "Counted from live records, Africa/Gaborone time." }), sel,
        tile(r.people_joined, "New people"), tile(r.businesses_joined, "New businesses"), tile(r.jobs_posted, "Jobs posted"),
        tile(r.work_submitted + " submitted · " + r.work_approved + " approved", "Work (" + r.field_cards + " field cards)"),
        tile(pula(r.money_received), "Money received"), tile(pula(r.paid_to_youth), "Paid to young people"),
        h("h2", { text: "Where new people joined from" }));
      if (!r.places.length) node.appendChild(empty("Nobody joined this month."));
      r.places.forEach(function (p) { node.appendChild(h("p", { class: "m", text: p.location + " · " + p.people })); });
      if (r.towns && r.towns.length) { node.appendChild(h("h2", { text: "Jobs by town (where the business is)" })); r.towns.forEach(function (t2) { node.appendChild(h("p", { class: "m", text: t2.town + " · " + t2.jobs + " jobs posted · " + t2.approved + " work approved · " + pula(t2.money) + " received" })); }); }
      if (r.agents && r.agents.length) { node.appendChild(h("h2", { text: "Field agents" })); r.agents.forEach(function (a) { node.appendChild(h("p", { class: "m", text: a.name + " · registered " + a.registered + " · chose own password " + a.chose_own_password })); }); }
      node.appendChild(h("h2", { text: "All time" }));
      node.appendChild(h("p", { class: "m", text: r.total.people + " people · " + r.total.businesses + " businesses · " + r.total.verified_skills + " verified skills · " + r.total.jobs_done + " jobs done" }));
      node.appendChild(h("pre", { text: r.text, style: "white-space:pre-wrap" })); node.appendChild(copy);
      var dl = h("button", { class: "btn sm sec", type: "button", text: "Download as spreadsheet (CSV)" });
      dl.addEventListener("click", function () {
        busy(dl, fetch("/admin/report/csv?month=" + month, { headers: S.staffToken ? { Authorization: "Bearer " + S.staffToken } : { "X-API-Key": S.adminKey } }).then(function (x) { if (!x.ok) throw new Error("Could not download"); return x.blob(); }).then(function (b) {
          var a = h("a", { href: URL.createObjectURL(b), download: "bstm-report-" + month + ".csv" }); document.body.appendChild(a); a.click(); a.remove();
        })).catch(fail);
      });
      node.appendChild(dl);
      show(node);
    });
  }
  function aPerson(p) {
    var base = "/admin/agent/people/" + encodeURIComponent(p.id);
    return Promise.all([A(base + "/work"), A(base + "/jobs")]).then(function (r) {
      var work = r[0] || [], jobs = r[1] || [], err = h("p", { class: "err", role: "alert" });
      var node = h("div", null, h("button", { class: "btn sm sec", type: "button", text: "← Back", onclick: function () { S.agentPerson = null; route(); } }),
        h("h1", { text: p.name }), h("p", { class: "m", text: [p.phone, p.location].filter(Boolean).join(" · ") }), h("h2", { text: "Their work" }));
      if (!work.length) node.appendChild(empty("No applications yet."));
      work.forEach(function (a) { node.appendChild(h("div", { class: "card" }, h("h3", { text: a.opportunity_title }), h("span", { class: "tag " + (a.status === "Accepted" || a.status === "Completed" ? "ok" : "warn"), text: statusText(a) }))); });
      node.appendChild(h("h2", { text: "Jobs that fit them" }));
      if (!jobs.length) node.appendChild(empty("No matching jobs right now."));
      jobs.forEach(function (o) {
        var b = h("button", { class: "btn sm", type: "button", text: "Apply for " + p.name.split(" ")[0] });
        b.addEventListener("click", function () { busy(b, A(base + "/apply/" + encodeURIComponent(o.opportunity_id || o.id), {})).then(function () { say("Applied for them."); b.textContent = "Applied ✓"; b.disabled = true; }).catch(fail); });
        node.appendChild(h("div", { class: "card" }, h("h3", { text: o.title }), h("p", { class: "m", text: [o.business_name, o.business_location, money(o.budget)].filter(Boolean).join(" · ") }),
          o.required_skills && o.required_skills.length ? h("p", { class: "m", text: "Skills needed: " + o.required_skills.join(", ") }) : null, b));
      });
      var kind = h("select", { "aria-label": "Kind of proof" }, KINDS.map(function (k) { return h("option", { value: k, text: KIND_LABEL[k] || k }); }));
      var f = h("form", { class: "card", novalidate: true }, h("h3", { text: "Add proof of their work" }), kind,
        field("What is it?", "notes", "text", { max: 500 }), field("Link (optional)", "url", "url", { max: 500, im: "url" }), err, h("button", { class: "btn", type: "submit", text: "Save proof" }));
      f.addEventListener("submit", function (ev) {
        ev.preventDefault(); err.textContent = "";
        if (!val(f, "notes")) return (err.textContent = "Say what the proof is.");
        busy(f.querySelector("button"), A(base + "/evidence", { kind: kind.value, notes: val(f, "notes"), url: val(f, "url") || null })).then(function () { say("Proof saved."); f.reset(); }).catch(function (e) { err.textContent = e.message; });
      });
      node.appendChild(f);
      show(node);
    });
  }
  function aAgent() {
    if (S.agentPerson) return aPerson(S.agentPerson);
    return A("/admin/agent/people").then(function (people) {
      var err = h("p", { class: "err", role: "alert" }), shown = h("div");
      var cons = h("input", { type: "checkbox", id: "f_cons", style: "width:auto;min-height:0" });
      var f = h("form", { class: "card", novalidate: true }, h("h2", { text: "Register a person" }),
        h("p", { class: "m", text: "Sit with them. They give you their details and agree. You never choose their password." }),
        field("Full name", "name", "text", { max: 120 }), field("Phone number", "phone", "tel", { max: 30, im: "tel" }),
        field("Village or town", "location", "text", { max: 120, list: "places" }), h("datalist", { id: "places" }, PLACES.map(function (x) { return h("option", { value: x }); })),
        field("What work do they want? (optional)", "goal", "text", { max: 200 }),
        h("label", { for: "f_cons", style: "font-weight:400" }, cons, " They agreed to be registered and that BSTM may contact them."), err,
        h("button", { class: "btn", type: "submit", text: "Register" }));
      f.addEventListener("submit", function (ev) {
        ev.preventDefault(); err.textContent = "";
        if (!cons.checked) return (err.textContent = "Tick the box once they have agreed.");
        busy(f.querySelector("button"), A("/admin/agent/register", { name: val(f, "name"), phone: val(f, "phone"), location: val(f, "location"), goal: val(f, "goal") || null, consent: true })).then(function (r) {
          clear(shown); shown.appendChild(h("div", { class: "card" }, h("h3", { text: "Give them this password (shown once)" }),
            h("p", { style: "font-size:2rem;letter-spacing:.15em;font-weight:700", text: r.temporary_password }),
            h("p", { class: "m", text: "They log in with their phone number and this password, then choose their own. Write it down or tell them now." })));
          f.reset(); say("Registered."); window.scrollTo(0, 0);
        }).catch(function (e) { err.textContent = e.message; });
      });
      var node = h("div", null, h("h1", { text: "Register" }), shown, f, h("h2", { text: "People registered (" + people.length + ")" }));
      if (!people.length) node.appendChild(empty("Nobody yet."));
      people.forEach(function (p) {
        node.appendChild(h("div", { class: "card" }, h("h3", { text: p.name }), h("p", { class: "m", text: [p.phone, p.location, when(p.created_at)].filter(Boolean).join(" · ") }),
          h("span", { class: "tag " + (p.must_change_password ? "warn" : "ok"), text: p.must_change_password ? "Has not chosen own password yet" : "Active" }),
          h("button", { class: "btn sm", type: "button", text: "Help with jobs and proof", onclick: function () { S.agentPerson = p; route(); } })));
      });
      show(node);
    });
  }
  function aSys() {
    return A("/admin/scorecard").then(function (r) {
      var node = h("div", null, h("h1", { text: "System check" }), h("p", { class: "m", text: "Each line was measured just now." }));
      r.checks.forEach(function (c) {
        node.appendChild(h("div", { class: "card" }, h("h3", { text: c.name }), h("p", null, h("span", { class: "tag " + (c.status === "OK" ? "ok" : "warn"), text: c.status }), " " + c.detail)));
      });
      show(node);
    });
  }
  var OWNER_KINDS = [["youth", "People"], ["businesses", "Businesses"], ["jobs", "Jobs"]];
  var OWNER_FIELDS = {
    youth: [["name", "Name"], ["email", "Email"], ["location", "Location"], ["goal", "Goal"], ["passion", "Passion"], ["availability", "Availability"], ["equipment", "Equipment"], ["bio", "About"]],
    businesses: [["name", "Business name"], ["owner", "Owner"], ["email", "Email"], ["sector", "Sector"], ["location", "Location"], ["main_problem", "Main problem"]],
    jobs: [["title", "Title"], ["description", "Description"], ["department", "Department"], ["budget", "Budget (P)"], ["status", "Status"]]
  };
  function aOwner() {
    var kind = S.okind || "youth";
    return A("/admin/owner/records?kind=" + kind).then(function (rows) {
      var picked = {}, delBtn = h("button", { class: "btn sm", type: "button", text: "Delete selected (0)", disabled: true });
      function count() { var n = Object.keys(picked).length; delBtn.textContent = "Delete selected (" + n + ")"; delBtn.disabled = !n; }
      var chips = h("div", { class: "chips" }, OWNER_KINDS.map(function (k) {
        return h("button", { type: "button", class: "chip", "aria-pressed": kind === k[0] ? "true" : "false", text: k[1], onclick: function () { S.okind = k[0]; route(); } });
      }));
      var suspects = rows.filter(function (r) { return r.suggested_test && r.suggested_test.length && !Number(r.money_records); });
      var node = h("div", null, h("h1", { text: "Owner" }),
        h("p", { class: "m", text: "You can correct or remove any record. Money records are never deleted. Test-looking records are flagged; you decide what goes." }), chips,
        h("p", { class: "m", text: rows.length + " records · " + suspects.length + " look like tests" }));
      var boxes = [];
      var selBtn = h("button", { class: "btn sm sec", type: "button", text: "Tick all that look like tests", onclick: function () {
        boxes.forEach(function (b) { if (b.suspect) { b.el.checked = true; picked[b.id] = 1; } }); count();
      } });
      node.appendChild(selBtn); node.appendChild(delBtn);
      delBtn.addEventListener("click", function () {
        var ids = Object.keys(picked); if (!ids.length) return;
        var word = window.prompt("This removes " + ids.length + " record(s) for good. Type DELETE to confirm.");
        if (word !== "DELETE") return;
        busy(delBtn, A("/admin/owner/delete", { kind: kind, ids: ids, confirm: "DELETE" })).then(function (r) {
          say(r.removed.length + " removed" + (r.kept_because_of_money.length ? ", " + r.kept_because_of_money.length + " kept (money records)" : "") + "."); route();
        }).catch(fail);
      });
      rows.forEach(function (r) {
        var cb = h("input", { type: "checkbox", "aria-label": "Select " + r.name, style: "width:auto;min-height:0;margin-right:8px" });
        cb.addEventListener("change", function () { if (cb.checked) picked[r.id] = 1; else delete picked[r.id]; count(); });
        boxes.push({ el: cb, id: r.id, suspect: !!(r.suggested_test && r.suggested_test.length && !Number(r.money_records)) });
        var detail = [r.email, r.location, r.sector, r.business, r.status, r.budget != null ? "P" + r.budget : null].filter(Boolean).join(" · ");
        var card = h("div", { class: "card" }, h("h3", null, cb, r.name), h("p", { class: "m", text: detail }),
          h("p", null, (r.suggested_test || []).map(function (x) { return h("span", { class: "tag warn", text: x }); }),
            Number(r.money_records) ? h("span", { class: "tag", text: r.money_records + " money record(s): protected" }) : null));
        var editBox = h("div");
        card.appendChild(h("button", { class: "btn sm sec", type: "button", text: "Edit", onclick: function () {
          clear(editBox);
          var f = h("form", { novalidate: true }, OWNER_FIELDS[kind].map(function (fd) { return field(fd[1], fd[0], "text", { max: 2000, value: r[fd[0]] != null ? String(r[fd[0]]) : "" }); }),
            h("p", { class: "err", role: "alert" }), h("button", { class: "btn sm", type: "submit", text: "Save changes" }));
          f.addEventListener("submit", function (ev) {
            ev.preventDefault(); var body = {};
            OWNER_FIELDS[kind].forEach(function (fd) { var v = val(f, fd[0]); if (v !== "" && v !== String(r[fd[0]] != null ? r[fd[0]] : "")) body[fd[0]] = fd[0] === "budget" ? Number(v) : v; });
            if (!Object.keys(body).length) return (f.querySelector(".err").textContent = "Nothing changed.");
            busy(f.querySelector("button[type=submit]"), api("/admin/owner/" + kind + "/" + r.id, { admin: true, method: "PUT", body: body })).then(function () { say("Saved."); route(); }).catch(function (e) { f.querySelector(".err").textContent = e.message; });
          });
          editBox.appendChild(f);
        } }));
        card.appendChild(editBox); node.appendChild(card);
      });
      show(node);
    });
  }
  function safeLink(u) { return u && /^https?:\/\//i.test(u) ? h("a", { href: u, target: "_blank", rel: "noopener noreferrer nofollow", text: "Open link" }) : null; }

  function greet() { var hr = new Date().getHours(); return hr < 12 ? "Good morning" : hr < 17 ? "Good afternoon" : "Good evening"; }
  function attentionCard(a) {
    if (!a) return null;
    if (a.all_clear && !a.items.length) return h("div", { class: "card" }, h("h3", { text: "All clear ✓" }), h("p", { class: "m", text: "Nothing is stuck or waiting. The app checked itself just now." }));
    var icon = { fail: "⛔", warn: "⏳", info: "ℹ️" };
    var card = h("div", { class: "card" }, h("h3", { text: a.all_clear ? "For your attention" : "Needs attention" }), h("p", { class: "m", text: "The app checked itself just now." }));
    a.items.forEach(function (i) {
      var go = function () { S.atab = i.tab; route(); };
      card.appendChild(h("button", { type: "button", class: "chip", style: "display:block;width:100%;text-align:left;margin:6px 0;border-radius:12px;padding:10px 14px", onclick: go },
        h("b", { text: icon[i.level] + " " + i.title }), h("br"), h("span", { class: "m", text: i.detail })));
    });
    return card;
  }

  function aQueue() {
    return Promise.all([A("/admin/stats"), A("/admin/queue"), A("/admin/activity?limit=15"), A("/admin/attention").catch(function () { return null; })]).then(function (r) {
      S.attn = r[3];
      var c = (r[0] && r[0].counts) || {}, qd = r[1] || { applications: [], trials: [] }, act = r[2] || [];
      return Promise.all(qd.trials.map(function (t3) { return A("/trials/" + t3.trial_id + "/evidence").catch(function () { return []; }); })).then(function (evs) { return [c, qd, act, evs]; });
    }).then(function (r) {
      var c = r[0], qd = r[1], act = r[2], evs = r[3];
      var node = h("div", null, h("h1", { text: greet() + (S.staffName ? ", " + S.staffName : "") }), attentionCard(S.attn),
        h("div", { class: "card stat" }, Object.keys(c).slice(0, 4).map(function (k) { return stat(c[k], k.replace(/_/g, " ")); })));
      moneyQueue(node, qd);
      node.appendChild(h("h2", { text: "Applications (" + qd.applications.length + ")" }));
      if (!qd.applications.length) node.appendChild(empty("No applications waiting."));
      qd.applications.forEach(function (a) {
        var card = h("div", { class: "card" }, h("h3", { text: a.youth_name + " → " + a.opportunity_title }),
          h("p", { class: "m", text: [a.youth_location, a.level, a.business_name, money(a.budget)].filter(Boolean).join(" · ") }));
        aact(card, "Accept", "/assignments/" + a.assignment_id + "/accept", {}, "", "Applicant accepted.");
        aact(card, "Decline", "/assignments/" + a.assignment_id + "/decline", {}, "sec", "Declined.");
        node.appendChild(card);
      });
      node.appendChild(h("h2", { text: "Work to review (" + qd.trials.length + ")" }));
      if (!qd.trials.length) node.appendChild(empty("Nothing to review."));
      qd.trials.forEach(function (t2, idx) {
        var sub = t2.submission || {};
        var card = h("div", { class: "card" }, h("h3", { text: t2.youth_name + " — " + t2.opportunity_title }),
          h("span", { class: "tag warn", text: t2.status }), sub.type === "field_card" ? cardView(sub) : (sub.summary ? h("p", { text: sub.summary }) : null), h("p", null, safeLink(sub.link)),
          (evs[idx] || []).map(function (e) { return h("p", { class: "m" }, "Proof: " + e.kind + (e.notes ? " – " + e.notes : "") + " ", safeLink(e.url)); }));
        if (t2.status === "Submitted") aact(card, "Start review", "/trials/" + t2.trial_id + "/review", { review: {} }, "", "Review started.");
        else {
          var score = h("input", { type: "number", min: 0, max: 100, placeholder: "Score 0–100", inputmode: "numeric" });
          var b = h("button", { class: "btn sm", type: "button", text: "Approve & complete" });
          b.addEventListener("click", function () {
            var n = Number(score.value); if (score.value === "" || !(n >= 0 && n <= 100)) return say("Enter a score from 0 to 100.", true);
            busy(b, A("/trials/" + t2.trial_id + "/complete", { review: { score: n } })).then(function () { say("Completed."); route(); }).catch(fail);
          });
          card.appendChild(score); card.appendChild(b);
        }
        node.appendChild(card);
      });
      node.appendChild(h("h2", { text: "Recent activity" }));
      act.forEach(function (a) { node.appendChild(h("p", { class: "m", text: when(a.created_at) + " · " + String(a.event).replace(/_/g, " ") })); });
      show(node);
    });
  }

  function noteAct(card, label, path, ph, cls, ok, field_, required) {
    var inp = h("input", { type: "text", placeholder: ph, maxlength: 300, "aria-label": ph, style: "margin-top:8px" });
    var b = h("button", { class: "btn sm " + (cls || ""), type: "button", text: label });
    b.addEventListener("click", function () {
      var v = inp.value.trim(); if (required && !v) return say(ph + " is required.", true);
      var body = {}; body[field_] = v || null;
      busy(b, A(path, body)).then(function () { say(ok); route(); }).catch(fail);
    });
    card.appendChild(inp); card.appendChild(b);
  }
  function moneyQueue(node, qd) {
    var jobs = qd.jobs || [], pays = qd.payments || [], outs = qd.payouts || [], un = qd.unmatched || [];
    if (un.length) {
      node.appendChild(h("h2", { text: "Unmatched money (" + un.length + ")" }));
      un.forEach(function (u) {
        var card = h("div", { class: "card" }, h("h3", { text: (u.amount != null ? pula(u.amount) : "Amount unknown") + " · " + u.provider }),
          h("p", { class: "m", text: "Ref " + u.provider_ref + " · invoice " + (u.invoice_reference || "?") + " · " + when(u.created_at) }), h("p", { text: u.reason }));
        noteAct(card, "Mark resolved", "/unmatched-payments/" + u.id + "/resolve", "What was done (refund, matched by hand…)", "", "Resolved.", "resolution", true);
        node.appendChild(card);
      });
    }
    node.appendChild(h("h2", { text: "Payments to confirm (" + pays.length + ")" }));
    if (!pays.length) node.appendChild(empty("No payments waiting."));
    pays.forEach(function (p) {
      var card = h("div", { class: "card" }, h("h3", { text: pula(p.amount) + " · " + p.business_name }),
        h("p", { class: "m", text: p.invoice_reference + " · " + p.method + " · ref " + (p.provider_ref || "none") + " · " + when(p.created_at) }),
        h("p", { class: "m", text: "Check this money is in the account before you confirm." }));
      aact(card, "Money received", "/payments/" + p.payment_id + "/confirm", {}, "", "Payment confirmed.");
      noteAct(card, "Not received", "/payments/" + p.payment_id + "/reject", "Reason (shown to the business)", "sec", "Payment rejected.", "note", false);
      node.appendChild(card);
    });
    node.appendChild(h("h2", { text: "Payouts to send (" + outs.length + ")" }));
    if (!outs.length) node.appendChild(empty("No payouts waiting."));
    outs.forEach(function (o) {
      var card = h("div", { class: "card" }, h("h3", { text: pula(o.amount) + " → " + o.youth_name }),
        h("p", { class: "m", text: o.invoice_reference + " · " + (o.destination ? (o.method || "") + " " + o.destination : "no payout details yet") }));
      if (o.destination) noteAct(card, "Mark as paid", "/payouts/" + o.payout_id + "/paid", "Reference from your MyZaka / bank receipt", "", "Payout recorded.", "provider_ref", true);
      else card.appendChild(h("p", { class: "m", text: "The youth must add payout details first (they have been told)." }));
      noteAct(card, "Failed", "/payouts/" + o.payout_id + "/fail", "Why it failed", "sec", "Marked failed; a new payout was queued.", "note", false);
      node.appendChild(card);
    });
    node.appendChild(h("h2", { text: "Jobs to approve (" + jobs.length + ")" }));
    if (!jobs.length) node.appendChild(empty("No jobs waiting for approval."));
    jobs.forEach(function (j) { node.appendChild(approvalCard(j, j.opportunity_id)); });
  }
  function approvalCard(j, id) {
    var card = h("div", { class: "card" }, h("h3", { text: j.title }), h("p", { class: "m", text: [j.business_name, j.business_location, j.department, money(j.budget)].filter(Boolean).join(" · ") }),
      j.description ? h("p", { text: j.description }) : null,
      j.required_skills && j.required_skills.length ? h("p", { class: "m", text: "Skills needed: " + j.required_skills.join(", ") }) : null);
    var ok = h("button", { class: "btn sm", type: "button", text: "Approve" });
    ok.addEventListener("click", function () { busy(ok, A("/opportunities/" + id + "/approval", { approved: true })).then(function () { say("Job is live."); route(); }).catch(fail); });
    card.appendChild(ok);
    var inp = h("input", { type: "text", placeholder: "Reason for the business", maxlength: 300, "aria-label": "Reason", style: "margin-top:8px" });
    var no = h("button", { class: "btn sm sec", type: "button", text: "Reject" });
    no.addEventListener("click", function () { busy(no, A("/opportunities/" + id + "/approval", { approved: false, note: inp.value.trim() || null })).then(function () { say("Job rejected."); route(); }).catch(fail); });
    card.appendChild(inp); card.appendChild(no);
    return card;
  }

  function aMoney() {
    return A("/invoices?limit=100").then(function (list) {
      var node = h("div", null, h("h1", { text: "Money" }));
      var total = list.reduce(function (a, i) { return a + Number(i.amount); }, 0), paid = list.filter(function (i) { return i.status === "Paid"; }).reduce(function (a, i) { return a + Number(i.amount); }, 0);
      node.appendChild(h("div", { class: "card stat" }, stat(list.length, "Invoices"), stat(pula(total), "Billed"), stat(pula(paid), "Paid in")));
      if (!list.length) node.appendChild(empty("No invoices yet. They appear when approved work completes a paid job."));
      list.forEach(function (i) {
        var card = h("div", { class: "card" }, h("h3", { text: i.reference + " · " + pula(i.amount) + " · " + i.business_name }),
          h("p", { class: "m", text: (i.opportunity_title || "") + " · youth " + pula(i.youth_share) + " / BSTM " + pula(i.platform_share) + " · " + when(i.created_at) }),
          h("p", null, h("span", { class: "tag " + (i.status === "Paid" ? "ok" : "warn"), text: i.status }), Number(i.paid_amount) > 0 ? h("span", { class: "tag", text: pula(i.paid_amount) + " confirmed" }) : null,
            Number(i.pending_payments) > 0 ? h("span", { class: "tag warn", text: i.pending_payments + " to confirm" }) : null));
        if (i.status === "Issued" && Number(i.pending_payments) === 0) {
          var key = idem(), ref = h("input", { type: "text", placeholder: "Receipt / reference (optional for cash)", maxlength: 80, "aria-label": "Reference", style: "margin-top:8px" });
          var m = h("select", { "aria-label": "Method" }, PAY_METHODS.map(function (x) { return h("option", { value: x[0], text: x[1] }); }));
          var b = h("button", { class: "btn sm sec", type: "button", text: "Record a payment" });
          b.addEventListener("click", function () {
            busy(b, api("/invoices/" + i.id + "/payments", { admin: true, method: "POST", headers: { "Idempotency-Key": key }, body: { method: m.value, provider_ref: ref.value.trim() || null } }))
              .then(function () { say("Recorded. Confirm it in the Queue."); route(); }).catch(fail);
          });
          card.appendChild(m); card.appendChild(ref); card.appendChild(b);
        }
        if (i.status === "Issued" && Number(i.pending_payments) === 0 && Number(i.paid_amount) === 0) {
          var vb = h("button", { class: "btn sm sec", type: "button", text: "Cancel invoice" });
          vb.addEventListener("click", function () {
            var reason = window.prompt("Why is this invoice being cancelled?"); if (!reason || !reason.trim()) return;
            busy(vb, A("/invoices/" + i.id + "/void", { reason: reason.trim() })).then(function () { say("Invoice cancelled."); route(); }).catch(fail);
          });
          card.appendChild(vb);
        }
        if (i.status === "Void" && i.can_reissue) {
          var rb = h("button", { class: "btn sm", type: "button", text: "Issue corrected invoice" });
          rb.addEventListener("click", function () {
            var amt = Number(window.prompt("Correct amount in Pula for this job?")); if (!(amt > 0)) return;
            busy(rb, A("/invoices/" + i.id + "/reissue", { amount: amt })).then(function () { say("Corrected invoice issued."); route(); }).catch(fail);
          });
          card.appendChild(rb);
        }
        node.appendChild(card);
      });
      show(node);
    });
  }

  function aBiz() {
    return A("/businesses?limit=200").then(function (list) {
      var node = h("div", null, h("h1", { text: "Businesses" }), h("button", { class: "btn sec", type: "button", text: "Register a business", onclick: businessScreen }));
      if (!list.length) node.appendChild(empty("No businesses yet."));
      list.forEach(function (b) {
        var out = h("div");
        var card = h("div", { class: "card" }, h("h3", { text: b.name }), h("p", { class: "m", text: [b.owner, b.sector, b.location].join(" · ") }),
          h("p", { text: b.main_problem || "" }), h("p", null, h("span", { class: "tag", text: "Audit: " + b.audit_status }), h("span", { class: "tag", text: b.opportunities_generated + " jobs posted" })), out);
        var btn = h("button", { class: "btn sm", type: "button", text: "Suggested jobs" });
        btn.addEventListener("click", function () {
          busy(btn, A("/businesses/" + b.id + "/diagnosis")).then(function (fs) {
            clear(out);
            fs.forEach(function (f) {
              var budget = h("input", { type: "number", min: 0, placeholder: "Budget (P)", inputmode: "numeric" });
              var post = h("button", { class: "btn sm", type: "button", text: "Post job" });
              post.addEventListener("click", function () {
                busy(post, A("/opportunities", { business_id: b.id, title: f.opportunity.title, description: f.opportunity.description, department: f.opportunity.department, budget: Number(budget.value) || 0 }))
                  .then(function () { say("Job posted."); post.textContent = "Posted ✓"; post.disabled = true; }).catch(fail);
              });
              out.appendChild(h("div", { class: "card" }, h("h3", { text: f.opportunity.title }), h("p", { class: "m", text: f.department }), h("p", { text: f.opportunity.description }), budget, post));
            });
          }).catch(fail);
        });
        card.appendChild(btn);
        var st = h("select", { "aria-label": "Audit status" }, ["Pending", "InProgress", "Completed"].map(function (x) { return h("option", { value: x, text: "Audit: " + x, selected: x === b.audit_status }); }));
        st.addEventListener("change", function () { A("/businesses/" + b.id + "/audit-status", { status: st.value }).then(function () { say("Audit status updated."); }).catch(fail); });
        card.appendChild(h("div", { style: "margin-top:8px" }, st));
        node.appendChild(card);
      });
      show(node);
    });
  }

  function aJobs() {
    return A("/opportunities?limit=200").then(function (list) {
      var node = h("div", null, h("h1", { text: "Jobs" })), list_cards = [];
      if (!list.length) node.appendChild(empty("No jobs yet. Post one from Businesses."));
      list.forEach(function (o) {
        var out = h("div");
        if (o.approval_status === "Pending") { list_cards.push(approvalCard(o, o.id)); return; }
        var card = h("div", { class: "card" }, h("h3", { text: o.title }), h("p", { class: "m", text: [o.business_name, o.department, money(o.budget)].filter(Boolean).join(" · ") }), o.required_skills && o.required_skills.length ? h("p", { class: "m", text: "Skills needed: " + o.required_skills.join(", ") }) : null, h("span", { class: "tag", text: o.status }), o.approval_status === "Rejected" ? h("span", { class: "tag", text: "Rejected" }) : null, out);
        var btn = h("button", { class: "btn sm sec", type: "button", text: "People on this job" });
        btn.addEventListener("click", function () {
          busy(btn, A("/opportunities/" + o.id + "/assignments")).then(function (as) {
            clear(out); if (!as.length) out.appendChild(h("p", { class: "m", text: "No applicants yet." }));
            as.forEach(function (a) {
              var row = h("div", { class: "card" }, h("p", null, h("strong", { text: a.youth_name }), " ", h("span", { class: "tag", text: a.status })), h("p", { class: "m", text: [a.youth_location, a.youth_level].filter(Boolean).join(" · ") }));
              if (a.status === "Pending") { aact(row, "Accept", "/assignments/" + a.assignment_id + "/accept", {}, "", "Accepted."); aact(row, "Decline", "/assignments/" + a.assignment_id + "/decline", {}, "sec", "Declined."); }
              if (a.status === "Accepted") { aact(row, "Mark job complete", "/assignments/" + a.assignment_id + "/complete", {}, "", "Job completed."); aact(row, "Cancel", "/assignments/" + a.assignment_id + "/cancel", {}, "sec", "Assignment cancelled."); }
              out.appendChild(row);
            });
          }).catch(fail);
        });
        card.appendChild(btn);
        if (o.status === "Open") {
          var cbtn = h("button", { class: "btn sm sec", type: "button", text: "Suggested youth" });
          cbtn.addEventListener("click", function () {
            busy(cbtn, A("/opportunities/" + o.id + "/candidates")).then(function (cs) {
              clear(out); if (!cs.length) out.appendChild(h("p", { class: "m", text: "No matching youth yet." }));
              cs.forEach(function (c) {
                var row = h("div", { class: "card" }, h("p", null, h("strong", { text: c.name }), " ", h("span", { class: "tag ok", text: "Fit " + c.match_score + "%" }), c.verified ? h("span", { class: "tag ok", text: "Verified" }) : null),
                  h("p", { class: "m", text: [c.location, c.level, c.capability_name].filter(Boolean).join(" · ") }));
                var offer = h("button", { class: "btn sm", type: "button", text: "Offer job" });
                offer.addEventListener("click", function () {
                  busy(offer, A("/assignments", { youth_id: c.youth_id, opportunity_id: o.id })).then(function () { say("Offer sent."); route(); }).catch(fail);
                });
                row.appendChild(offer); out.appendChild(row);
              });
            }).catch(fail);
          });
          card.appendChild(cbtn);
          aact(card, "Close job", "/opportunities/" + o.id + "/close", {}, "sec", "Job closed.");
        }
        list_cards.push(card);
      });
      list_cards.forEach(function (c2) { node.appendChild(c2); });
      show(node);
    });
  }

  function aYouth() {
    return A("/youth?limit=200").then(function (list) {
      var catErr = h("p", { class: "err" });
      var catForm = h("form", { class: "card", novalidate: true }, h("h2", { text: "Add a skill to the catalogue" }), field("Skill name", "cname", "text", { max: 100 }), field("Category", "ccat", "text", { max: 60, ph: "e.g. Trades" }), catErr, h("button", { class: "btn sm", type: "submit", text: t("Save") }));
      catForm.addEventListener("submit", function (ev) {
        ev.preventDefault(); catErr.textContent = "";
        var nm = val(catForm, "cname"), ct = val(catForm, "ccat"); if (!nm || !ct) return (catErr.textContent = "Name and category are required.");
        A("/capabilities", { name: nm, category: ct }).then(function () { S.caps = null; say("Skill added."); catForm.reset(); }).catch(function (e) { catErr.textContent = e.message; });
      });
      var node = h("div", null, h("h1", { text: "Youth (" + list.length + ")" }), catForm);
      list.forEach(function (y) {
        var out = h("div");
        var card = h("div", { class: "card" }, h("h3", { text: y.name }), h("p", { class: "m", text: [y.location, y.level, y.completed_trials + " trials"].join(" · ") }), out);
        var btn = h("button", { class: "btn sm sec", type: "button", text: "Skills" });
        btn.addEventListener("click", function () {
          busy(btn, A("/youth/" + y.id + "/capabilities")).then(function (cs) {
            clear(out); if (!cs.length) out.appendChild(h("p", { class: "m", text: "No skills claimed." }));
            cs.forEach(function (c) {
              var row = h("p", null, c.capability_name + " (" + c.level + ") ", h("span", { class: "tag " + (c.verified ? "ok" : ""), text: c.verified ? "Verified" : "Unverified" }));
              if (!c.verified) { var v = h("button", { class: "btn sm", type: "button", text: "Verify" }); v.addEventListener("click", function () { busy(v, A("/youth-capabilities/" + c.id + "/verify", { verified: true })).then(function () { say("Verified."); v.remove(); }).catch(fail); }); row.appendChild(v); }
              out.appendChild(row);
            });
          }).catch(fail);
        });
        card.appendChild(btn);
        var ebtn = h("button", { class: "btn sm sec", type: "button", text: "Proof" });
        ebtn.addEventListener("click", function () {
          busy(ebtn, A("/youth/" + y.id + "/evidence")).then(function (es) {
            clear(out); if (!es.length) out.appendChild(h("p", { class: "m", text: "No proof submitted." }));
            es.forEach(function (e) { out.appendChild(h("p", { class: "m" }, e.kind + (e.capability_name ? " · " + e.capability_name : "") + (e.notes ? " – " + e.notes : "") + " ", safeLink(e.url))); });
          }).catch(fail);
        });
        card.appendChild(ebtn); node.appendChild(card);
      });
      show(node);
    });
  }

  var CHECK = ["Customer traffic", "Staff and roles", "Products or services", "Technology in use", "Marketing and branding", "Cleanliness and organisation"];
  function aAudit() {
    return Promise.all([A("/audits?limit=20"), A("/businesses?limit=200")]).then(function (r) {
      var audits = r[0] || [], biz = r[1] || [], ratings = {}, rooms = {};
      var sel = h("select", { name: "business_id" }, h("option", { value: "", text: "Business not registered yet" }), biz.map(function (b) { return h("option", { value: b.id, text: b.name + " (" + b.location + ")" }); }));
      var rate = CHECK.map(function (item) {
        var row = h("div", { class: "chips" });
        ["G", "F", "P"].forEach(function (v) {
          var b = h("button", { class: "chip", type: "button", "aria-pressed": "false", text: { G: "Good", F: "Fair", P: "Poor" }[v] });
          b.addEventListener("click", function () { ratings[item] = v; Array.prototype.forEach.call(row.children, function (c) { c.setAttribute("aria-pressed", c === b ? "true" : "false"); }); });
          row.appendChild(b);
        });
        return h("div", null, h("label", { text: item }), row);
      });
      var grid = h("div", { class: "chips" }, Array.apply(null, Array(63)).map(function (_, i) {
        var n = i + 1, b = h("button", { class: "chip", type: "button", "aria-pressed": "false", text: String(n), style: "min-width:44px;padding:0" });
        b.addEventListener("click", function () { if (rooms[n]) delete rooms[n]; else rooms[n] = 1; b.setAttribute("aria-pressed", rooms[n] ? "true" : "false"); });
        return b;
      }));
      var err = h("p", { class: "err", role: "alert" });
      var f = h("form", { class: "card", novalidate: true }, h("h2", { text: "New field audit" }), h("label", { text: "Business" }), sel,
        field("Business name", "business_name", "text", { max: 150 }), field("Location", "location", "text", { max: 120 }),
        rate, h("label", { text: "BSTM rooms (1–63)" }), grid,
        h("label", { for: "f_insight", text: "Biggest insight" }), h("textarea", { id: "f_insight", name: "insight", maxlength: 1000 }),
        field("Overall score (1–10)", "score", "number", { im: "numeric", value: "7" }), err,
        h("button", { class: "btn", type: "submit", text: t("Save") }));
      sel.addEventListener("change", function () {
        var b = biz.filter(function (x) { return x.id === sel.value; })[0];
        if (b) { f.querySelector("[name=business_name]").value = b.name; f.querySelector("[name=location]").value = b.location; }
      });
      f.addEventListener("submit", function (ev) {
        ev.preventDefault(); err.textContent = "";
        var body = { business_id: sel.value || null, business_name: val(f, "business_name"), location: val(f, "location"), ratings: ratings, rooms: Object.keys(rooms).map(Number), insight: val(f, "insight") || null, score: Number(val(f, "score")) };
        if (!body.business_name || !body.location) return (err.textContent = "Business name and location are required.");
        if (!(body.score >= 1 && body.score <= 10)) return (err.textContent = "Score must be 1 to 10.");
        busy(f.querySelector("button[type=submit]"), A("/audits", body)).then(function () { say("Audit saved."); route(); }).catch(function (e) { err.textContent = e.message; });
      });
      var node = h("div", null, h("h1", { text: "Field audit" }), f, h("h2", { text: "Recent audits" }));
      if (!audits.length) node.appendChild(empty("No audits yet."));
      audits.forEach(function (a) { node.appendChild(h("div", { class: "card" }, h("h3", { text: a.business_name }), h("p", { class: "m", text: a.location + " · score " + a.score + "/10 · " + when(a.created_at) }), a.insight ? h("p", { text: a.insight }) : null)); });
      show(node);
    });
  }

  // ---------- boot ----------
  $("outBtn").addEventListener("click", function () { if (isStaff()) adminLogout(); else logout(false); });
  $("langBtn").addEventListener("click", function () { S.lang = S.lang === "en" ? "tn" : "en"; store("bstm_lang", S.lang); document.documentElement.lang = S.lang; route(); });
  $("bellBtn").addEventListener("click", function () { if (S.btoken) S.btab = "alerts"; else S.tab = "alerts"; route(); });
  window.addEventListener("hashchange", route);
  window.addEventListener("offline", function () { say("You are offline.", true); });
  window.addEventListener("online", function () { say(""); });
  document.documentElement.lang = S.lang;
  if ("serviceWorker" in navigator) window.addEventListener("load", function () { navigator.serviceWorker.register("/sw.js").catch(function () {}); });
  route();
})();
