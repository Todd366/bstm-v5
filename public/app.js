(function () {
  "use strict";

  var $ = function (id) { return document.getElementById(id); };
  var app = $("app"), tabs = $("tabs"), banner = $("banner");
  var S = { atab: "queue", adminKey: null, token: null, lang: "en", tab: "home", profile: null, caps: null };

  try { S.adminKey = sessionStorage.getItem("bstm_admin"); } catch (e) {}
  try { S.token = localStorage.getItem("bstm_token"); S.lang = localStorage.getItem("bstm_lang") || "en"; } catch (e) {}
  function store(k, v) { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch (e) {} }

  // ---------- language ----------
  var TS = {
    "Home": "Gae", "Jobs": "Ditiro", "My work": "Tiro ya me", "Proof": "Bopaki", "Skills": "Dikgono",
    "Log in": "Tsena", "Log out": "Tswa", "Create account": "Ikwadisa", "Email": "Imeile", "Password": "Password",
    "Next": "Latelang", "Back": "Boela morago", "Name": "Leina", "Apply": "Kopa tiro", "Accept": "Amogela",
    "Decline": "Gana", "Withdraw": "Ikgogele morago", "Submit": "Romela", "Save": "Boloka",
    "Where do you live?": "O nna kae?", "Loading…": "Go a tsenngwa…", "Setswana": "English"
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
    if (opt.admin) headers["X-API-Key"] = S.adminKey;
    else if (S.token && !opt.anon) headers.Authorization = "Bearer " + S.token;
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
    if (S.adminKey && e && (e.status === 401 || e.status === 403)) { adminLogout(); say("Staff key was not accepted.", true); return; }
    if (e && e.status === 401 && S.token) { logout(true); return; }
    say(e && e.message || "Something went wrong.", true);
  }
  function busy(btn, p) {
    btn.disabled = true;
    return p.then(function (x) { btn.disabled = false; return x; }, function (e) { btn.disabled = false; throw e; });
  }

  // ---------- session ----------
  function logout(expired) {
    S.token = null; S.profile = null; store("bstm_token", null);
    if (expired) say("Your session ended. Please log in again.", true);
    route();
  }
  function setToken(tok) { S.token = tok; store("bstm_token", tok); }

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
        h("button", { class: "btn", type: "button", text: "Register my business", onclick: businessScreen })),
      h("div", { class: "card" }, h("h2", { text: "BSTM staff" }),
        h("button", { class: "btn sec", type: "button", text: "Staff sign in", onclick: staffLogin }))));
  }

  function loginScreen() {
    var err = h("p", { class: "err", role: "alert" });
    var form = h("form", { class: "card", novalidate: true },
      h("h1", { text: t("Log in") }),
      field("Email", "email", "email", { ac: "email", max: 254, im: "email" }),
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
          field("Email", "email", "email", { ac: "email", max: 254, im: "email", value: d.email }),
          field("Password", "password", "password", { ac: "new-password", max: 128 }),
          h("p", { class: "m", text: "At least 8 characters." }), err, nav());
        body.addEventListener("submit", function (ev) {
          ev.preventDefault();
          d.name = val(body, "name"); d.email = val(body, "email"); d.password = body.querySelector("[name=password]").value;
          if (!d.name) return problem("Please enter your name.");
          if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(d.email)) return problem("Enter a valid email address.");
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
              name: d.name, email: d.email, password: d.password, location: d.location, goal: d.aspiration,
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
  var TABS = [["home", "🏠", "Home"], ["jobs", "🔎", "Jobs"], ["work", "💼", "My work"], ["proof", "📎", "Proof"], ["skills", "⭐", "Skills"]];
  var ATABS = [["queue", "📋", "Queue"], ["biz", "🏪", "Businesses"], ["jobs", "💼", "Jobs"], ["youth", "👥", "Youth"], ["audit", "📝", "Audit"]];
  function drawTabs() {
    clear(tabs); tabs.hidden = !S.token && !S.adminKey;
    if (S.adminKey) {
      ATABS.forEach(function (x) {
        tabs.appendChild(h("button", { type: "button", "aria-current": S.atab === x[0] ? "page" : null, onclick: function () { S.atab = x[0]; route(); } }, h("i", { text: x[1] }), x[2]));
      });
      return;
    }
    if (!S.token) return;
    TABS.forEach(function (x) {
      tabs.appendChild(h("button", { type: "button", "aria-current": S.tab === x[0] ? "page" : null, onclick: function () { S.tab = x[0]; route(); } }, h("i", { text: x[1] }), t(x[2])));
    });
  }
  var VIEWS = { home: homeView, jobs: jobsView, work: workView, proof: proofView, skills: skillsView };

  function route() {
    $("outBtn").hidden = !S.token && !S.adminKey; $("outBtn").textContent = t("Log out"); $("langBtn").textContent = t("Setswana");
    drawTabs();
    if (S.adminKey) { $("who").textContent = "Staff"; $("outBtn").hidden = false; return adminRoute(); }
    if (!S.token) { $("who").textContent = ""; return landing(); }
    show(h("div", { class: "spin", text: t("Loading…") }));
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
        h("h1", { text: (S.lang === "tn" ? "Dumela, " : "Hello, ") + p.name.split(" ")[0] }),
        h("div", { class: "card" }, h("h3", { text: "Your level" }), h("p", { text: p.level || "Beginner" }),
          h("div", { class: "stat" },
            stat(p.completed_trials, "Trials done"), stat(p.completed_opportunities, "Jobs done"), stat(Math.round(p.reputation_score || 0), "Reputation"), stat("P" + Number(p.revenue || 0).toLocaleString("en"), "Earned"))));
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
        (o.reasons || []).map(function (r) { return h("span", { class: "tag", text: r }); })));
    var b = h("button", { class: "btn", type: "button", text: t("Apply") });
    b.addEventListener("click", function () {
      busy(b, api("/me/opportunities/" + encodeURIComponent(o.opportunity_id || o.id) + "/apply", { method: "POST", body: {} })).then(function () {
        say("Application sent. We will tell you when it is accepted."); b.textContent = "Applied ✓"; b.disabled = true;
      }).catch(fail);
    });
    card.appendChild(b); return card;
  }
  var jobsMode = "match";
  function jobsView() {
    var path = jobsMode === "match" ? "/me/opportunities" : "/me/opportunities/browse";
    return api(path).then(function (list) {
      var tabsRow = h("div", { class: "chips" },
        ["match", "all"].map(function (m) { return h("button", { class: "chip", type: "button", "aria-pressed": jobsMode === m ? "true" : "false", text: m === "match" ? "Matched to me" : "All open", onclick: function () { jobsMode = m; route(); } }); }));
      var node = h("div", null, h("h1", { text: t("Jobs") }), tabsRow, h("div", { style: "height:12px" }));
      if (!list || !list.length) node.appendChild(empty(jobsMode === "match" ? "No matches yet. Add more skills, or see all open jobs." : "No open jobs right now. Check back soon."));
      else list.forEach(function (o) { node.appendChild(oppCard(o, jobsMode === "match")); });
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
        if (a.trial_id && a.trial_status === "Active") card.appendChild(submitForm(a.trial_id));
        node.appendChild(card);
      });
      show(node);
    });
  }
  function statusText(a) {
    if (a.trial_status && a.status === "Accepted") return { Active: "In progress", Submitted: "Submitted – waiting for review", "Under Review": "Being reviewed", Completed: "Completed", Cancelled: "Cancelled" }[a.trial_status] || a.trial_status;
    return { Pending: "Waiting for BSTM", Accepted: "Accepted", Declined: "Declined", Cancelled: "Withdrawn", Completed: "Completed" }[a.status] || a.status;
  }
  function submitForm(trialId) {
    var f = h("form", { novalidate: true }, h("label", { text: "What did you do? Add a link to your work if you have one." }),
      h("textarea", { name: "summary", maxlength: 1500 }), h("input", { name: "link", type: "url", placeholder: "https://… (optional)", maxlength: 500, inputmode: "url" }),
      h("button", { class: "btn", type: "submit", text: "Submit my work" }));
    f.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var summary = val(f, "summary"), link = val(f, "link");
      if (!summary) return say("Please describe what you did.", true);
      if (link && !/^https?:\/\//i.test(link)) return say("The link must start with http:// or https://", true);
      busy(f.querySelector("button"), api("/me/trials/" + encodeURIComponent(trialId) + "/submit", { body: { submission: { summary: summary, link: link || null } } }))
        .then(function () { say("Submitted! BSTM will review it."); route(); }).catch(fail);
    });
    return f;
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
      var node = h("div", null, h("h1", { text: t("Proof") }), f, h("h2", { text: "Your proof" }));
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
      var node = h("div", null, h("h1", { text: t("Skills") }));
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


  // ---------- business door ----------
  var SECTORS = ["Retail", "Food & catering", "Farming", "Transport", "Construction", "Beauty & salon", "Education", "Health", "Technology", "Manufacturing", "Other"];
  function businessScreen() {
    var err = h("p", { class: "err", role: "alert" });
    var f = h("form", { class: "card", novalidate: true }, h("h1", { text: "Register your business" }),
      field("Business name", "name", "text", { max: 150 }), field("Owner name", "owner", "text", { max: 120 }),
      h("div", null, h("label", { for: "f_sector", text: "Sector" }), h("select", { id: "f_sector", name: "sector" }, SECTORS.map(function (x) { return h("option", { value: x, text: x }); }))),
      field("Where is it? (town or village)", "location", "text", { max: 120, list: "places" }),
      h("datalist", { id: "places" }, PLACES.map(function (p) { return h("option", { value: p }); })),
      h("div", null, h("label", { for: "f_problem", text: "What is your biggest problem?" }), h("textarea", { id: "f_problem", name: "main_problem", maxlength: 1000 })),
      err, h("button", { class: "btn", type: "submit", text: "Get help" }), h("button", { class: "btn sec", type: "button", text: t("Back"), onclick: landing }));
    f.addEventListener("submit", function (ev) {
      ev.preventDefault(); err.textContent = "";
      var body = { name: val(f, "name"), owner: val(f, "owner"), sector: val(f, "sector"), location: val(f, "location"), main_problem: val(f, "main_problem") };
      if (!body.name || !body.owner || !body.location || !body.main_problem) return (err.textContent = "Please fill in every field.");
      busy(f.querySelector("button[type=submit]"), api("/businesses", { anon: true, body: body })).then(function (r) {
        show(h("div", null, h("div", { class: "card" }, h("h1", { text: "Thank you, " + body.name }), h("p", { text: "We received your business. A BSTM team member will visit or call you. Here is where we think youth can help:" })),
          (r.diagnosis || []).map(function (d) { return h("div", { class: "card" }, h("h3", { text: d.title }), h("p", { class: "m", text: "BSTM department: " + d.department })); }),
          h("button", { class: "btn", type: "button", text: "Done", onclick: landing })));
      }).catch(function (e) { err.textContent = e.message; });
    });
    show(f);
  }

  // ---------- staff console ----------
  function staffLogin() {
    var err = h("p", { class: "err", role: "alert" });
    var f = h("form", { class: "card", novalidate: true }, h("h1", { text: "Staff sign in" }),
      field("Staff key", "key", "password", { ac: "off", max: 200 }), err,
      h("button", { class: "btn", type: "submit", text: t("Log in") }), h("button", { class: "btn sec", type: "button", text: t("Back"), onclick: landing }));
    f.addEventListener("submit", function (ev) {
      ev.preventDefault(); S.adminKey = f.querySelector("[name=key]").value.trim();
      busy(f.querySelector("button[type=submit]"), api("/admin/stats", { admin: true })).then(function () {
        try { sessionStorage.setItem("bstm_admin", S.adminKey); } catch (e) {}
        route();
      }).catch(function (e) { S.adminKey = null; err.textContent = e.status === 401 || e.status === 403 ? "That key was not accepted." : e.message; });
    });
    show(f);
  }
  function adminLogout() { S.adminKey = null; try { sessionStorage.removeItem("bstm_admin"); } catch (e) {} route(); }
  var A = function (path, body) { return api(path, { admin: true, method: body !== undefined ? "POST" : "GET", body: body !== undefined ? body : undefined }); };
  function aact(card, label, path, body, cls, ok) {
    var b = h("button", { class: "btn sm " + (cls || ""), type: "button", text: label });
    b.addEventListener("click", function () { busy(b, A(path, body || {})).then(function () { say(ok || "Done."); route(); }).catch(fail); });
    card.appendChild(b);
  }
  function adminRoute() {
    show(h("div", { class: "spin", text: t("Loading…") }));
    ({ queue: aQueue, biz: aBiz, jobs: aJobs, youth: aYouth, audit: aAudit }[S.atab] || aQueue)().catch(function (e) {
      if (e && (e.status === 401 || e.status === 403)) return fail(e);
      show(h("div", { class: "card empty" }, h("p", { text: e.message }), h("button", { class: "btn", type: "button", text: "Try again", onclick: route })));
    });
  }
  function safeLink(u) { return u && /^https?:\/\//i.test(u) ? h("a", { href: u, target: "_blank", rel: "noopener noreferrer nofollow", text: "Open link" }) : null; }

  function aQueue() {
    return Promise.all([A("/admin/stats"), A("/admin/queue"), A("/admin/activity?limit=15")]).then(function (r) {
      var c = (r[0] && r[0].counts) || {}, qd = r[1] || { applications: [], trials: [] }, act = r[2] || [];
      return Promise.all(qd.trials.map(function (t3) { return A("/trials/" + t3.trial_id + "/evidence").catch(function () { return []; }); })).then(function (evs) { return [c, qd, act, evs]; });
    }).then(function (r) {
      var c = r[0], qd = r[1], act = r[2], evs = r[3];
      var node = h("div", null, h("h1", { text: "Queue" }),
        h("div", { class: "card stat" }, Object.keys(c).slice(0, 4).map(function (k) { return stat(c[k], k.replace(/_/g, " ")); })),
        h("h2", { text: "Applications (" + qd.applications.length + ")" }));
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
          h("span", { class: "tag warn", text: t2.status }), sub.summary ? h("p", { text: sub.summary }) : null, h("p", null, safeLink(sub.link)),
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
      var node = h("div", null, h("h1", { text: "Jobs" }));
      if (!list.length) node.appendChild(empty("No jobs yet. Post one from Businesses."));
      list.forEach(function (o) {
        var out = h("div");
        var card = h("div", { class: "card" }, h("h3", { text: o.title }), h("p", { class: "m", text: [o.business_name, o.department, money(o.budget)].filter(Boolean).join(" · ") }), h("span", { class: "tag", text: o.status }), out);
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
        node.appendChild(card);
      });
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
  $("outBtn").addEventListener("click", function () { if (S.adminKey) adminLogout(); else logout(false); });
  $("langBtn").addEventListener("click", function () { S.lang = S.lang === "en" ? "tn" : "en"; store("bstm_lang", S.lang); document.documentElement.lang = S.lang; route(); });
  window.addEventListener("offline", function () { say("You are offline.", true); });
  window.addEventListener("online", function () { say(""); });
  document.documentElement.lang = S.lang;
  if ("serviceWorker" in navigator) window.addEventListener("load", function () { navigator.serviceWorker.register("/sw.js").catch(function () {}); });
  route();
})();
