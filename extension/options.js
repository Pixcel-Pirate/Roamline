"use strict";

const form = document.getElementById("profile");
const msg = (t) => (document.getElementById("msg").textContent = t);
const MAX_RESUME = 5 * 1024 * 1024;
const RESUME_TYPES = ["application/pdf", "application/msword",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document"];
let resume = null; // {name, type, data: dataURL}

function showResume() {
  document.getElementById("resume-name").textContent = resume ? `Saved: ${resume.name}` : "No resume saved.";
}

async function load() {
  const { profile } = await chrome.storage.local.get("profile");
  if (!profile) return showResume();
  for (const el of form.elements) {
    if (el.name && typeof profile[el.name] === "string") el.value = profile[el.name];
  }
  resume = profile.resume || null;
  showResume();
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!form.reportValidity()) return;
  const profile = { resume };
  for (const el of form.elements) {
    if (el.name) profile[el.name] = el.value.trim();
  }
  await chrome.storage.local.set({ profile });
  msg("Saved in this browser.");
});

document.getElementById("resume").addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (!file) return;
  if (file.size > MAX_RESUME) return msg("That file is over 5 MB. Please pick a smaller one.");
  if (!RESUME_TYPES.includes(file.type)) return msg("Please pick a PDF or Word file.");
  const reader = new FileReader();
  reader.onload = () => {
    resume = { name: file.name.slice(0, 120), type: file.type, data: reader.result };
    showResume();
    msg("Resume ready. Press Save profile to keep it.");
  };
  reader.onerror = () => msg("Couldn't read that file.");
  reader.readAsDataURL(file);
});

document.getElementById("remove-resume").addEventListener("click", () => {
  resume = null;
  document.getElementById("resume").value = "";
  showResume();
  msg("Resume removed. Press Save profile to keep this change.");
});

document.getElementById("export").addEventListener("click", async () => {
  const { profile } = await chrome.storage.local.get("profile");
  if (!profile) return msg("Nothing saved yet.");
  const url = URL.createObjectURL(new Blob([JSON.stringify(profile, null, 2)], { type: "application/json" }));
  const a = Object.assign(document.createElement("a"), { href: url, download: "roamline-profile.json" });
  a.click();
  URL.revokeObjectURL(url);
});

document.getElementById("delete").addEventListener("click", async () => {
  if (!confirm("Delete your saved profile and resume from this browser?")) return;
  await chrome.storage.local.clear();
  form.reset();
  resume = null;
  showResume();
  msg("Deleted. Nothing is stored anymore.");
});

load();
