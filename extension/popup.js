"use strict";

const msg = document.getElementById("msg");

document.getElementById("fill").addEventListener("click", async () => {
  const { profile } = await chrome.storage.local.get("profile");
  if (!profile) {
    msg.textContent = "Set up your profile first.";
    chrome.runtime.openOptionsPage();
    return;
  }
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  try {
    // activeTab lets us touch only the tab you clicked on, only now.
    await chrome.scripting.executeScript({ target: { tabId: tab.id, allFrames: true }, files: ["fill.js"] });
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id, allFrames: true },
      func: (p) => globalThis.roamline.fill(p),
      args: [profile],
    });
    const n = results.reduce((sum, r) => sum + (Number(r.result) || 0), 0);
    msg.textContent = n
      ? `Filled ${n} field${n === 1 ? "" : "s"}. Check everything, then submit yourself.`
      : "Found nothing to fill on this page.";
  } catch (e) {
    msg.textContent = `Can't fill this page (${e.message}).`;
  }
});
