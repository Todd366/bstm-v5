(function () {
  "use strict";

  var $ = function (id) { return document.getElementById(id); };
  var app = $("app"), tabs = $("tabs"), banner = $("banner");
  var S = { token: null, lang: "en", tab: "home", profile: null, caps: null };

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
    if (S.token && !opt.anon) headers.Authorization = "Bearer " + S.token;
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
        h("button", { class: "btn sec", type: "button", text: t("Create account"), onclick: registerScreen }))));
  }

  var PLACES = ["Gaborone", "Francistown", "Maun", "Kasane", "Serowe", "Palapye", "Molepolole", "Mochudi", "Lobatse", "Selebi-Phikwe", "Kanye", "Mahalapye", "Ghanzi", "Jwaneng", "Orapa", "Tsabong", "Shakawe", "Tonota", "Letlhakane", "Mmadinare"];
  var GOALS = ["Get a job", "Start my own business", "Earn money from my skills", "Learn new skills", "Build experience"];

  function registerScreen() {
    var d = { skills: {} }, step = 0;
    function render() {
      var err = h("p", { class: "err", role: "alert" });
      var bar = h("div", { class: "steps" }, [0, 1, 2].map(function (i) { return h("span", { class: i <= step ? "on" : "" }); }));
      var body;
      if (step === 0) {
        body = h("form", { novalidate: true }, h("h1", { text: "Create your account" }),
          field("Name", "name", "text", { ac: "name", max: 120, value: d.name }),
          field("Email", "email", "email", { ac: "email", max: 254, im: "email", value: d.email }),
          field("Password", "password", "password", { ac: "new-password", max: 128 }),
          h("p", { class: "m", text: "At least 8 characters." }), err,
          h("button", { class: "btn", type: "submit", text: t("Next") }));
        body.addEventListener("submit", function (ev) {
          ev.preventDefault();
          d.name = val(body, "name"); d.email = val(body, "email"); d.password = body.querySelector("[name=password]").value;
          if (!d.name) return (err.textContent = "Please enter your name.");
          if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(d.email)) return (err.textContent = "Enter a valid email address.");
          if (d.password.length < 8) return (err.textContent = "Password must be at least 8 characters.");
          step = 1; render();
        });
      } else if (step === 1) {
        var dl = h("datalist", { id: "places" }, PLACES.map(function (p) { return h("option", { value: p }); }));
        var gl = h("datalist", { id: "goals" }, GOALS.map(function (p) { return h("option", { value: p }); }));
        body = h("form", { novalidate: true }, h("h1", { text: "About you" }), dl, gl,
          field("Where do you live?", "location", "text", { ac: "address-level2", max: 120, list: "places", value: d.location }),
          field("What is your goal?", "goal", "text", { max: 200, list: "goals", value: d.goal }),
          field("What are you passionate about? (optional)", "passion", "text", { max: 300, value: d.passion }),
          field("When can you work? (optional)", "availability", "text", { max: 100, ph: "e.g. Weekdays after 2pm", value: d.availability }),
          field("Equipment you have (optional)", "equipment", "text", { max: 300, ph: "e.g. Smartphone, laptop", value: d.equipment }), err,
          h("button", { class: "btn", type: "submit", text: t("Next") }),
          h("button", { class: "btn sec", type: "button", text: t("Back"), onclick: function () { step = 0; render(); } }));
        body.addEventListener("submit", function (ev) {
          ev.preventDefault();
          ["location", "goal", "passion", "availability", "equipment"].forEach(function (k) { d[k] = val(body, k); });
          if (!d.location || !d.goal) return (err.textContent = "Location and goal are required.");
          step = 2; render();
        });
      } else {
        var holder = h("div", { class: "spin", text: t("Loading…") });
        body = h("div", null, h("h1", { text: "Pick your skills" }), h("p", { class: "m", text: "Choose what you can do. You can change this later." }), holder, err,
          h("button", { class: "btn", type: "button", text: t("Create account"), onclick: function (ev) {
            err.textContent = "";
            var caps = Object.keys(d.skills).map(function (id) { return { capability_id: id, level: "Beginner" }; });
            var payload = { name: d.name, email: d.email, password: d.password, location: d.location, goal: d.goal, passion: d.passion || null, availability: d.availability || null, equipment: d.equipment || null, capabilities: caps };
            busy(ev.target, api("/youth", { anon: true, body: payload }))
              .then(function (r) { setToken(r.access_token); say("Welcome to BSTM!"); S.tab = "home"; route(); })
              .catch(function (e) { err.textContent = e.message; });
          } }),
          h("button", { class: "btn sec", type: "button", text: t("Back"), onclick: function () { step = 1; render(); } }));
        loadCaps().then(function (caps) { clear(holder); holder.className = ""; holder.appendChild(skillPicker(caps, d.skills)); }).catch(function (e) { holder.className = "err"; holder.textContent = e.message; });
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
    Object.keys(cats).sort().forEach(function (cat) {
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
  function drawTabs() {
    clear(tabs); tabs.hidden = !S.token;
    if (!S.token) return;
    TABS.forEach(function (x) {
      tabs.appendChild(h("button", { type: "button", "aria-current": S.tab === x[0] ? "page" : null, onclick: function () { S.tab = x[0]; route(); } }, h("i", { text: x[1] }), t(x[2])));
    });
  }
  var VIEWS = { home: homeView, jobs: jobsView, work: workView, proof: proofView, skills: skillsView };

  function route() {
    $("outBtn").hidden = !S.token; $("outBtn").textContent = t("Log out"); $("langBtn").textContent = t("Setswana");
    drawTabs();
    if (!S.token) { $("who").textContent = ""; return loginScreen(); }
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
    return Promise.all([profile(), api("/me/assignments"), api("/me/opportunities")]).then(function (r) {
      var p = r[0], as = r[1] || [], ms = r[2] || [];
      var active = as.filter(function (a) { return a.status === "Accepted"; });
      var pending = as.filter(function (a) { return a.status === "Pending"; });
      var node = h("div", null,
        h("h1", { text: (S.lang === "tn" ? "Dumela, " : "Hello, ") + p.name.split(" ")[0] }),
        h("div", { class: "card" }, h("h3", { text: "Your level" }), h("p", { text: p.level || "Beginner" }),
          h("div", { class: "stat" },
            stat(p.completed_trials, "Trials done"), stat(p.completed_opportunities, "Jobs done"), stat(Math.round(p.reputation_score || 0), "Reputation"))));
      if (!ms.length && !as.length) node.appendChild(h("div", { class: "card" }, h("h3", { text: "Next step" }), h("p", { text: "Add your skills so we can match you to work." }), h("button", { class: "btn", type: "button", text: "Add skills", onclick: function () { S.tab = "skills"; route(); } })));
      if (active.length) node.appendChild(h("div", { class: "card" }, h("h3", { text: "Active work (" + active.length + ")" }), h("button", { class: "btn sm", type: "button", text: "Open my work", onclick: function () { S.tab = "work"; route(); } })));
      if (pending.length) node.appendChild(h("div", { class: "card" }, h("p", { text: pending.length + " application(s)/offer(s) waiting." })));
      if (ms.length) node.appendChild(h("div", { class: "card" }, h("h3", { text: ms.length + " job(s) match your skills" }), h("button", { class: "btn sm", type: "button", text: "See jobs", onclick: function () { S.tab = "jobs"; route(); } })));
      show(node);
    });
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
        if (a.status === "Pending") { act(t("Accept"), base + "/accept", "", "Accepted. Good luck!"); act(t("Decline"), base + "/decline", "sec", "Declined."); act(t("Withdraw"), base + "/withdraw", "sec", "Withdrawn."); }
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

  // ---------- boot ----------
  $("outBtn").addEventListener("click", function () { logout(false); });
  $("langBtn").addEventListener("click", function () { S.lang = S.lang === "en" ? "tn" : "en"; store("bstm_lang", S.lang); document.documentElement.lang = S.lang; route(); });
  window.addEventListener("offline", function () { say("You are offline.", true); });
  window.addEventListener("online", function () { say(""); });
  document.documentElement.lang = S.lang;
  route();
})();
