// On known application sites (Greenhouse, Lever, Ashby, Workday) add a small
// "Fill with Roamline" button. Nothing is filled until you press it.
"use strict";

(() => {
  if (window.top !== window || document.getElementById("roamline-autofill")) return;

  const host = document.createElement("div");
  host.id = "roamline-autofill";
  // Shadow DOM keeps the page's CSS off the button and ours off the page.
  // innerHTML here is a fixed string with no page or profile data in it.
  const root = host.attachShadow({ mode: "closed" });
  root.innerHTML = `
    <style>
      .box { position: fixed; right: 16px; bottom: 16px; z-index: 2147483647; display: flex; flex-direction: column;
             align-items: flex-end; gap: 6px; font: 14px/1.4 system-ui, sans-serif; }
      button { font: inherit; font-weight: 600; padding: 10px 16px; border: 0; border-radius: 999px;
               background: #1f6f5c; color: #fff; cursor: pointer; box-shadow: 0 2px 8px rgba(0,0,0,.25); }
      button:focus-visible { outline: 3px solid #f2b705; outline-offset: 2px; }
      .msg { background: #fff; color: #1d1d1b; padding: 8px 12px; border-radius: 8px; max-width: 260px;
             box-shadow: 0 2px 8px rgba(0,0,0,.2); }
      .msg:empty { display: none; }
    </style>
    <div class="box"><div class="msg" role="status" aria-live="polite"></div><button type="button">Fill with Roamline</button></div>`;
  const msg = root.querySelector(".msg");

  root.querySelector("button").addEventListener("click", async () => {
    const { profile } = await chrome.storage.local.get("profile");
    if (!profile) {
      msg.textContent = "Set up your profile first: right-click the Roamline icon → Options.";
      return;
    }
    const n = globalThis.roamline.fill(profile);
    msg.textContent = n
      ? `Filled ${n} field${n === 1 ? "" : "s"} (outlined in green). Check everything, then submit yourself.`
      : "Nothing to fill on this step. If the form is on another page or step, open it and press again.";
  });

  document.documentElement.append(host);
})();
