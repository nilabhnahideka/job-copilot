// The side panel's behaviour: which view is shown, and what each button does.
//
// Safety rule: everything from a job page or from the AI is inserted with
// `textContent` (plain text), never `innerHTML`, so a web page can't inject
// code into the extension.

import * as api from "./api.js";
import { extractJobFromPage } from "./extract.js";

const $ = (id) => document.getElementById(id);

// The agent's steps, in order, with plain-English names (same as the website).
const STEPS = [
  ["parse_job", "Reading the job post"],
  ["match_resume", "Checking each requirement against your resume"],
  ["tailor_bullets", "Rewriting your resume points"],
  ["check_grounding", "Fact-checking the rewrites"],
  ["draft_cover_letter", "Writing the cover letter"],
  ["draft_outreach", "Writing a recruiter message"],
];

const VERDICTS = { strong_fit: "Strong fit", good_fit: "Good fit", stretch: "Stretch", poor_fit: "Poor fit" };

let current = { view: "loading", application: null, tab: "cover_letter", jobUrl: "" };

// ---------------------------------------------------------------------------
// Views
// ---------------------------------------------------------------------------
function show(view) {
  for (const el of document.querySelectorAll(".view")) el.hidden = el.id !== `view-${view}`;
  if (view !== "settings") current.view = view;
}

function setError(id, message) {
  const el = $(id);
  el.textContent = message || "";
  el.hidden = !message;
}

async function start() {
  const session = await api.getSession();
  const { webUrl } = await api.getSettings();
  $("who").textContent = session ? session.email : "";
  $("logout-btn").hidden = !session;
  if (webUrl) {
    $("signup-link").hidden = false;
    $("signup-link").querySelector("a").href = `${webUrl}/signup`;
  }
  if (!session) return show("login");
  show("job");
  checkProfile();
}

/** Warn early if the profile has no resume, since analysing needs one. */
async function checkProfile() {
  try {
    const profile = await api.getProfile();
    const warn = $("profile-warning");
    warn.hidden = !!profile.active_resume;
    warn.textContent = profile.active_resume
      ? ""
      : "Upload your resume on the Job Copilot website first. The analysis compares the job with it.";
  } catch (e) {
    if (e.status === 401) return start(); // logged out
    // Not fatal: the API may be waking up. The analyse step will report real problems.
  }
}

// ---------------------------------------------------------------------------
// Log in / settings
// ---------------------------------------------------------------------------
$("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  setError("login-error", "");
  const btn = e.submitter;
  btn.disabled = true;
  btn.textContent = "Logging in…";
  try {
    await api.login($("login-email").value, $("login-password").value);
    $("login-password").value = "";
    await start();
  } catch (err) {
    setError("login-error", err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Log in";
  }
});

$("settings-btn").addEventListener("click", async () => {
  const s = await api.getSettings();
  $("set-api").value = s.apiUrl;
  $("set-web").value = s.webUrl;
  show("settings");
});

$("settings-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  await api.saveSettings({ apiUrl: $("set-api").value, webUrl: $("set-web").value });
  await start();
});

$("settings-cancel").addEventListener("click", () => show(current.view));

$("logout-btn").addEventListener("click", async () => {
  await api.logout();
  await start();
});

// ---------------------------------------------------------------------------
// Read the job from the page
// ---------------------------------------------------------------------------
$("read-btn").addEventListener("click", async () => {
  setError("job-error", "");
  const info = $("read-info");
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.id) throw new Error("Open a job page in this window first.");
    const [{ result }] = await chrome.scripting.executeScript({ target: { tabId: tab.id }, func: extractJobFromPage });
    $("job-text").value = result.text;
    current.jobUrl = result.url;
    info.textContent =
      `Read ${result.text.length.toLocaleString()} characters from ${result.source}` +
      (result.truncated ? " (shortened to fit)." : ".") +
      " Check it below.";
    info.hidden = false;
  } catch (err) {
    // Chrome's own pages (chrome://, the Web Store) can't be read by any extension.
    setError(
      "job-error",
      /Cannot access|cannot be scripted|chrome:\/\//i.test(err.message)
        ? "This page can't be read. Open the job page itself, or copy the description and paste it below."
        : err.message,
    );
  }
});

// ---------------------------------------------------------------------------
// Analyse
// ---------------------------------------------------------------------------
$("analyse-btn").addEventListener("click", async () => {
  const jobText = $("job-text").value.trim();
  setError("job-error", "");
  if (jobText.length < 50) return setError("job-error", "That's too short to be a job description.");

  const done = new Set();
  renderSteps(done);
  show("progress");
  try {
    let finished = false;
    await api.analyseJob({ jobText, jobUrl: current.jobUrl }, (ev) => {
      if (ev.type === "node") {
        done.add(ev.node);
        renderSteps(done);
      } else if (ev.type === "error") {
        throw new Error(ev.detail);
      } else if (ev.type === "done") {
        finished = true;
        current.application = ev.application;
        renderResult();
      }
    });
    if (!finished) throw new Error("The analysis stopped before finishing. Try again.");
  } catch (err) {
    if (err.status === 401) return start();
    show("job");
    setError("job-error", err.message);
  }
});

function renderSteps(done) {
  const list = $("steps");
  list.replaceChildren(
    ...STEPS.map(([node, label], i) => {
      const li = document.createElement("li");
      li.dataset.n = String(i + 1);
      li.textContent = label;
      if (done.has(node)) li.classList.add("done");
      return li;
    }),
  );
}

// ---------------------------------------------------------------------------
// Results
// ---------------------------------------------------------------------------
async function renderResult() {
  const app = current.application;
  const match = app.agent.match || {};
  $("score").textContent = match.fit_score ?? "–";
  $("verdict").textContent = VERDICTS[match.verdict] || "";
  $("role").textContent = [app.title, app.company].filter(Boolean).join(" at ");

  // Requirement strip
  const strip = $("strip");
  const matches = match.matches || [];
  strip.replaceChildren(
    ...matches.map((m) => {
      const seg = document.createElement("i");
      seg.className = m.level;
      seg.style.flexGrow = m.importance === "must_have" ? "2" : "1";
      seg.title = `${m.requirement} (${m.level})`;
      return seg;
    }),
  );
  const count = (l) => matches.filter((m) => m.level === l).length;
  strip.setAttribute(
    "aria-label",
    `${count("strong")} covered, ${count("partial")} partly covered, ${count("missing")} missing`,
  );

  fillList($("gaps"), match.gaps || []);
  fillList($("suggestions"), match.suggestions || []);
  const kw = match.missing_keywords || [];
  $("keywords").textContent = kw.length ? `Keywords missing from your resume: ${kw.join(", ")}` : "";

  const { webUrl } = await api.getSettings();
  const open = $("open-web");
  open.hidden = !webUrl;
  if (webUrl) open.href = `${webUrl}/applications/${app.id}`;

  selectTab("cover_letter");
  show("result");
}

function fillList(ul, items) {
  ul.replaceChildren(
    ...items.map((t) => {
      const li = document.createElement("li");
      li.textContent = t;
      return li;
    }),
  );
}

function selectTab(tab) {
  current.tab = tab;
  for (const b of document.querySelectorAll(".tabs button")) {
    b.setAttribute("aria-selected", String(b.dataset.tab === tab));
  }
  const agent = current.application.agent;
  const body = $("tab-body");

  if (tab === "bullets") {
    const bullets = agent.bullets || [];
    if (!bullets.length) return body.replaceChildren(para("No resume points were rewritten for this job."));
    const ol = document.createElement("ol");
    for (const b of bullets) {
      const li = document.createElement("li");
      li.append(document.createTextNode(b.rewritten));
      const was = document.createElement("span");
      was.className = "was";
      was.textContent = b.original;
      li.append(was);
      ol.append(li);
    }
    return body.replaceChildren(ol);
  }

  const text = (tab === "cover_letter" ? agent.cover_letter : agent.outreach) || "";
  body.replaceChildren(...(text ? text.split(/\n{2,}/).map(para) : [para("Nothing drafted.")]));
}

function para(text) {
  const p = document.createElement("p");
  p.textContent = text;
  return p;
}

for (const b of document.querySelectorAll(".tabs button")) {
  b.addEventListener("click", () => selectTab(b.dataset.tab));
}

$("copy-btn").addEventListener("click", async () => {
  const agent = current.application.agent;
  const text =
    current.tab === "bullets"
      ? (agent.bullets || []).map((b) => `• ${b.rewritten}`).join("\n")
      : (current.tab === "cover_letter" ? agent.cover_letter : agent.outreach) || "";
  await navigator.clipboard.writeText(text);
  const btn = $("copy-btn");
  btn.textContent = "Copied";
  setTimeout(() => (btn.textContent = "Copy"), 1500);
});

$("again-btn").addEventListener("click", () => {
  $("job-text").value = "";
  $("read-info").hidden = true;
  current.jobUrl = "";
  show("job");
});

start();
