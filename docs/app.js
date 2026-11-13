// Everything is rendered with textContent, never innerHTML, so job text from
// the APIs can't inject markup or scripts.
"use strict";

const $ = (id) => document.getElementById(id);
const SAVED_KEY = "roamline-saved";
const LIMIT = 200; // ponytail: render cap, add paging if people scroll past 200

let jobs = [];
let saved = loadSaved();

function loadSaved() {
  try {
    return new Set(JSON.parse(localStorage.getItem(SAVED_KEY)) || []);
  } catch {
    return new Set(); // private mode or corrupt value
  }
}

function storeSaved() {
  try {
    localStorage.setItem(SAVED_KEY, JSON.stringify([...saved]));
  } catch {
    /* storage blocked: saving just won't persist */
  }
}

function daysAgo(iso) {
  const d = Math.floor((Date.now() - new Date(iso)) / 86400000);
  return d <= 0 ? "today" : d === 1 ? "1 day ago" : `${d} days ago`;
}

function render() {
  const q = $("q").value.trim().toLowerCase();
  const source = $("source").value;
  const maxAge = Number($("age").value) * 86400000;
  const paidOnly = $("paid").checked;
  const savedOnly = $("saved").checked;
  const now = Date.now();

  const hits = jobs.filter((j) =>
    (!source || j.source === source) &&
    now - j.time <= maxAge &&
    (!paidOnly || j.salary) &&
    (!savedOnly || saved.has(j.url)) &&
    (!q || `${j.title} ${j.company} ${j.tags.join(" ")}`.toLowerCase().includes(q))
  );

  const list = $("jobs");
  const tpl = $("card");
  list.replaceChildren(...hits.slice(0, LIMIT).map((j) => {
    const li = tpl.content.firstElementChild.cloneNode(true);
    const a = li.querySelector(".title");
    a.textContent = j.title;
    a.href = j.url; // fetcher already dropped anything that isn't https://
    li.querySelector(".meta").textContent =
      [j.company, j.location, j.salary, `${j.source}, ${daysAgo(j.posted)}`].filter(Boolean).join(" · ");
    li.querySelector(".tags").textContent = j.tags.join(", ");
    const btn = li.querySelector(".save");
    btn.dataset.url = j.url;
    btn.setAttribute("aria-label", `Save ${j.title} at ${j.company || "unknown company"}`);
    paintSave(btn);
    return li;
  }));

  $("status").textContent = hits.length
    ? `${hits.length} jobs${hits.length > LIMIT ? `, showing the newest ${LIMIT}` : ""}`
    : "No jobs match. Try a broader search.";
}

function paintSave(btn) {
  const on = saved.has(btn.dataset.url);
  btn.textContent = on ? "Saved" : "Save";
  btn.setAttribute("aria-pressed", String(on));
}

$("jobs").addEventListener("click", (e) => {
  const btn = e.target.closest(".save");
  if (!btn) return;
  const url = btn.dataset.url;
  saved.has(url) ? saved.delete(url) : saved.add(url);
  storeSaved();
  // Update just this button so keyboard focus stays put; a full re-render
  // is only needed when "Saved only" would hide the card.
  $("saved").checked ? render() : paintSave(btn);
});
$("filters").addEventListener("input", render);
$("filters").addEventListener("submit", (e) => e.preventDefault());

fetch("jobs.json", { cache: "no-cache" })
  .then((r) => {
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  })
  .then((data) => {
    jobs = (Array.isArray(data.jobs) ? data.jobs : [])
      .map((j) => ({ ...j, time: Date.parse(j.posted) }))
      .filter((j) => j.url && !Number.isNaN(j.time));
    for (const s of [...new Set(jobs.map((j) => j.source))].sort()) {
      $("source").append(new Option(s, s));
    }
    render();
    $("status").textContent += ` · updated ${daysAgo(data.updated)}`;
  })
  .catch((err) => {
    $("status").textContent = `Couldn't load jobs (${err.message}). Try again later.`;
  });
