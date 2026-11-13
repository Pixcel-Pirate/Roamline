// Everything is rendered with textContent, never innerHTML, so job text from
// the APIs can't inject markup or scripts.
"use strict";

const $ = (id) => document.getElementById(id);
const SAVED_KEY = "roamline-saved";
const AREA_KEY = "roamline-area";
const SEARCH_KEY = "roamline-search";
const VISIT_KEY = "roamline-last-visit";
const FILTERS = ["q", "type", "level", "source", "age", "paid", "fresh"]; // what "my search" remembers
const LEVEL_NAME = { entry: "Entry", mid: "Mid", senior: "Senior", lead: "Lead" };
const LIMIT = 200; // ponytail: render cap, add paging if people scroll past 200
const SOURCE_HOME = {
  "Remote OK": "https://remoteok.com",
  Remotive: "https://remotive.com",
  Himalayas: "https://himalayas.app",
  Arbeitnow: "https://www.arbeitnow.com",
  Jobicy: "https://jobicy.com",
  "We Work Remotely": "https://weworkremotely.com",
  "Working Nomads": "https://www.workingnomads.com",
  Adzuna: "https://www.adzuna.com",
  USAJOBS: "https://www.usajobs.gov",
};

let jobs = [];
let saved = loadSaved();
let area = loadArea(); // {zip, lat, lon, city, state} or null
const lastVisit = startVisit(); // jobs posted after this are "new"

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

function readJSON(key) {
  try {
    return JSON.parse(localStorage.getItem(key));
  } catch {
    return null; // private mode or corrupt value
  }
}

function writeJSON(key, value) {
  try {
    value === null ? localStorage.removeItem(key) : localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* storage blocked: it just won't persist */
  }
}

// Returns when the previous visit started (0 on a first visit). Reloads within
// an hour count as the same visit, so "new" jobs don't vanish on refresh.
function startVisit() {
  const v = readJSON(VISIT_KEY);
  const prev = Number(v && v.prev) || 0;
  const current = Number(v && v.current) || 0;
  const now = Date.now();
  if (now - current < 3600e3) return prev;
  writeJSON(VISIT_KEY, { prev: current, current: now });
  return current;
}

function getFilters() {
  return Object.fromEntries(FILTERS.map((id) => [id, $(id).type === "checkbox" ? $(id).checked : $(id).value]));
}

function setFilters(f) {
  for (const id of FILTERS) {
    if (!(id in f)) continue;
    if ($(id).type === "checkbox") $(id).checked = f[id] === true;
    else if (typeof f[id] === "string") $(id).value = f[id];
  }
}

function loadArea() {
  try {
    const a = JSON.parse(localStorage.getItem(AREA_KEY));
    return a && Number.isFinite(a.lat) && Number.isFinite(a.lon) &&
      typeof a.city === "string" && typeof a.state === "string" ? a : null;
  } catch {
    return null;
  }
}

function storeArea() {
  try {
    area ? localStorage.setItem(AREA_KEY, JSON.stringify(area)) : localStorage.removeItem(AREA_KEY);
  } catch {
    /* storage blocked */
  }
}

// Great-circle distance in miles.
function miles(lat1, lon1, lat2, lon2) {
  const r = Math.PI / 180;
  const a = Math.sin(((lat2 - lat1) * r) / 2) ** 2 +
    Math.cos(lat1 * r) * Math.cos(lat2 * r) * Math.sin(((lon2 - lon1) * r) / 2) ** 2;
  return 7918 * Math.asin(Math.sqrt(a));
}

// Hybrid jobs count as "near" when their coordinates are inside the radius,
// or, for sources without coordinates, when the location names the same
// city and state as the ZIP code.
function isNear(j, radius) {
  if (Number.isFinite(j.lat) && Number.isFinite(j.lon)) {
    return miles(area.lat, area.lon, j.lat, j.lon) <= radius;
  }
  const loc = j.location.toLowerCase();
  return loc.includes(area.city.toLowerCase()) && loc.split(/[^a-z]+/).includes(area.state.toLowerCase());
}

function daysAgo(iso) {
  const d = Math.floor((Date.now() - new Date(iso)) / 86400000);
  return d <= 0 ? "today" : d === 1 ? "1 day ago" : `${d} days ago`;
}

function render() {
  const terms = $("q").value.toLowerCase().split(",").map((t) => t.trim()).filter(Boolean);
  const level = $("level").value;
  const freshOnly = $("fresh").checked;
  const source = $("source").value;
  const maxAge = Number($("age").value) * 86400000;
  const paidOnly = $("paid").checked;
  const savedOnly = $("saved").checked;
  const type = $("type").value;
  const radius = Number($("radius").value);
  const now = Date.now();

  const hits = jobs.filter((j) =>
    (!source || j.source === source) &&
    (!type || j.type === type) &&
    (!level || j.level === level) &&
    (!freshOnly || j.time > lastVisit) &&
    (!area || j.type === "remote" || isNear(j, radius)) &&
    now - j.time <= maxAge &&
    (!paidOnly || j.salary) &&
    (!savedOnly || saved.has(j.url)) &&
    (!terms.length || terms.some((t) => j.haystack.includes(t)))
  );

  const list = $("jobs");
  const tpl = $("card");
  list.replaceChildren(...hits.slice(0, LIMIT).map((j) => {
    const li = tpl.content.firstElementChild.cloneNode(true);
    const a = li.querySelector(".title");
    a.textContent = j.title;
    a.href = j.url; // fetcher already dropped anything that isn't https://
    li.querySelector(".new").hidden = !(lastVisit && j.time > lastVisit);
    li.querySelector(".lvl").textContent = LEVEL_NAME[j.level] || "";
    li.querySelector(".kind").textContent = j.type === "hybrid" ? "Hybrid" : "Remote";
    li.querySelector(".kind").dataset.type = j.type;
    const meta = li.querySelector(".meta");
    meta.textContent = [j.company, j.location, j.salary].filter(Boolean).concat("").join(" · ");
    const home = SOURCE_HOME[j.source];
    const src = document.createElement(home ? "a" : "span");
    src.textContent = j.source;
    if (home) {
      src.href = home;
      src.className = j.source === "Adzuna" ? "src adzuna" : "src";
    }
    meta.append(src, `, ${daysAgo(j.posted)}`);
    li.querySelector(".tags").textContent = j.tags.join(", ");
    const btn = li.querySelector(".save");
    btn.dataset.url = j.url;
    btn.setAttribute("aria-label", `Save ${j.title} at ${j.company || "unknown company"}`);
    paintSave(btn);
    return li;
  }));

  const fresh = lastVisit ? hits.filter((j) => j.time > lastVisit).length : 0;
  const where = (fresh ? ` · ${fresh} new since your last visit` : "") + (area ? ` · hybrid within ${radius} mi of ${area.city}, ${area.state}` : "");
  $("status").textContent = (hits.length
    ? `${hits.length} ${hits.length === 1 ? "job" : "jobs"}${hits.length > LIMIT ? `, showing the newest ${LIMIT}` : ""}`
    : "No jobs match. Try a broader search.") + where;
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

$("near").addEventListener("submit", async (e) => {
  e.preventDefault();
  const zip = $("zip").value.trim();
  if (!/^\d{5}$/.test(zip)) {
    $("zip-msg").textContent = "Enter a 5-digit US ZIP code.";
    return;
  }
  $("zip-msg").textContent = "Looking up ZIP code…";
  try {
    const r = await fetch(`https://api.zippopotam.us/us/${zip}`);
    if (!r.ok) throw new Error(r.status === 404 ? "ZIP code not found" : `HTTP ${r.status}`);
    const place = (await r.json()).places?.[0];
    const lat = Number(place?.latitude);
    const lon = Number(place?.longitude);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) throw new Error("ZIP code not found");
    area = { zip, lat, lon, city: String(place["place name"]), state: String(place["state abbreviation"]) };
    storeArea();
    $("zip-msg").textContent = `Showing remote jobs plus hybrid jobs near ${area.city}, ${area.state}.`;
    render();
  } catch (err) {
    $("zip-msg").textContent = `Couldn't look up that ZIP code (${err.message}).`;
  }
});

$("save-search").addEventListener("click", () => {
  writeJSON(SEARCH_KEY, getFilters());
  $("mine-msg").textContent = "Saved. Roamline will open with this search next time.";
});

$("forget-search").addEventListener("click", () => {
  writeJSON(SEARCH_KEY, null);
  $("mine-msg").textContent = "Forgot your saved search.";
});

$("clear-zip").addEventListener("click", () => {
  area = null;
  storeArea();
  $("zip").value = "";
  $("zip-msg").textContent = "";
  render();
});
$("radius").addEventListener("change", () => area && render());

if (area) {
  $("zip").value = area.zip;
  $("zip-msg").textContent = `Showing remote jobs plus hybrid jobs near ${area.city}, ${area.state}.`;
}

fetch("jobs.json", { cache: "no-cache" })
  .then((r) => {
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  })
  .then((data) => {
    jobs = (Array.isArray(data.jobs) ? data.jobs : [])
      .map((j) => ({
        ...j,
        time: Date.parse(j.posted),
        haystack: `${j.title} ${j.company} ${(j.tags || []).join(" ")}`.toLowerCase(),
      }))
      .filter((j) => j.url && !Number.isNaN(j.time));
    for (const s of [...new Set(jobs.map((j) => j.source))].sort()) {
      $("source").append(new Option(s, s));
    }
    const mine = readJSON(SEARCH_KEY);
    if (mine && typeof mine === "object") {
      setFilters(mine);
      $("mine-msg").textContent = "Showing your saved search.";
    }
    render();
    $("status").textContent += ` · updated ${daysAgo(data.updated)}`;
  })
  .catch((err) => {
    $("status").textContent = `Couldn't load jobs (${err.message}). Try again later.`;
  });
