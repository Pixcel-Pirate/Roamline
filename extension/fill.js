// Roamline Autofill: fills the job application form on the current page from
// the profile saved in this browser. It never submits, and it never touches a
// field that already has a value. The matching rules are plain functions so
// `node --test extension/` can check them without a browser.
"use strict";

(() => {
  const DECLINE = /decline|prefer not|don.?t wish|do not wish|choose not|not to (answer|disclose|say|self.?identify)|rather not|(wish|want) to (answer|disclose|identify)|not (to )?answer/;
  const NO = /^\s*no\b|\bnot\b|don.?t have|do not have|\bnone\b|i am not/;
  const YES = /^\s*yes\b|\bi am\b|\bi have\b|\bidentify as\b|\bi do\b/;

  // Question text -> profile key. Order matters: the first match wins.
  const QUESTIONS = [
    ["sponsorship", /(require|need|now or in the future).*sponsor|sponsorship/],
    ["authorized", /authori[sz]ed to work|eligible to work|right to work|legally (able|permitted) to work/],
    ["citizen", /citizen/],
    ["veteran", /veteran/],
    ["disability", /disabilit/],
    ["hispanic", /hispanic|latin[oax]/],
    ["race", /\brace\b|ethnicit/],
    ["gender", /\bgender\b|\bsex\b/],
    ["resume", /resume|résumé|\bcv\b/],
    ["linkedin", /linkedin/],
    ["website", /website|portfolio|github|personal (site|url)/],
    ["firstName", /first.?name|given.?name|preferred.?name|fname/],
    ["lastName", /last.?name|family.?name|surname|lname/],
    ["email", /e-?mail/],
    ["phone", /phone|mobile|\btel\b/],
    ["location", /\blocation\b|\bcity\b|where (are you|do you) (based|live)|current address/],
    ["fullName", /^\s*(full.?)?name\b|your name|legal name/],
  ];

  const CHOICE_KEYS = new Set(["sponsorship", "authorized", "citizen", "veteran", "disability", "hispanic"]);

  function clean(s) {
    return String(s || "").toLowerCase().replace(/\s+/g, " ").trim();
  }

  function keyFor(question) {
    const q = clean(question);
    if (!q) return "";
    for (const [key, re] of QUESTIONS) if (re.test(q)) return key;
    return "";
  }

  // Sort an answer option ("Yes, I have a disability", "I don't wish to answer") into yes / no / decline.
  function answerClass(optionText) {
    const t = clean(optionText);
    if (DECLINE.test(t)) return "decline";
    if (NO.test(t)) return "no";
    if (YES.test(t)) return "yes";
    return "";
  }

  function optionMatches(key, answer, optionText) {
    const t = clean(optionText);
    if (!answer || !t) return false;
    if (CHOICE_KEYS.has(key)) return answerClass(t) === answer;
    if (answer === "decline") return DECLINE.test(t);
    if (key === "gender") return new RegExp(`\\b${answer}\\b`).test(t.replace(/-/g, " ").replace("nonbinary", "non binary")
      .replace(/\bman\b/, "male").replace(/\bwoman\b/, "female"));
    if (key === "race") return t.includes(answer);
    return false;
  }

  function textValue(profile, key) {
    if (key === "fullName") return [profile.firstName, profile.lastName].filter(Boolean).join(" ");
    const v = profile[key];
    return typeof v === "string" ? v : "";
  }

  // ---------- DOM part (browser only) ----------

  function labelText(el) {
    const doc = el.ownerDocument;
    const parts = [];
    if (el.id) {
      const l = doc.querySelector(`label[for="${CSS.escape(el.id)}"]`);
      if (l) parts.push(l.textContent);
    }
    parts.push(el.getAttribute("aria-label"));
    for (const id of (el.getAttribute("aria-labelledby") || "").split(/\s+/).filter(Boolean)) {
      parts.push(doc.getElementById(id)?.textContent);
    }
    parts.push(el.closest("label")?.textContent, el.getAttribute("placeholder"), el.name, el.id);
    return parts.filter(Boolean).join(" ");
  }

  // The question for a radio group: fieldset legend, a labelled group, or the
  // label-ish text in the nearest wrapper.
  function groupQuestion(radio) {
    const fs = radio.closest("fieldset");
    if (fs?.querySelector("legend")) return fs.querySelector("legend").textContent;
    const group = radio.closest('[role="radiogroup"],[role="group"]');
    if (group) {
      const by = group.getAttribute("aria-labelledby");
      const t = group.getAttribute("aria-label") || (by && radio.ownerDocument.getElementById(by)?.textContent);
      if (t) return t;
    }
    let node = radio.parentElement;
    for (let i = 0; i < 5 && node; i++, node = node.parentElement) {
      const q = node.querySelector(":scope > label, :scope > .text, :scope > .application-label, :scope > p, :scope > div > label");
      if (q && !q.contains(radio)) return q.textContent;
    }
    return radio.name;
  }

  function optionLabel(input) {
    const doc = input.ownerDocument;
    if (input.id) {
      const l = doc.querySelector(`label[for="${CSS.escape(input.id)}"]`);
      if (l) return l.textContent;
    }
    return input.closest("label")?.textContent || input.value;
  }

  // React/Vue keep their own copy of the value, so use the native setter and fire events.
  function setValue(el, value) {
    const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype
      : el instanceof HTMLSelectElement ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(proto, "value").set.call(el, value);
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function mark(el) {
    el.style.outline = "2px solid #1f6f5c";
    el.style.outlineOffset = "2px";
  }

  function fileFromDataUrl(resume) {
    const [head, b64] = String(resume.data).split(",");
    const type = (head.match(/^data:([^;]+);base64$/) || [])[1];
    if (!type || !b64) return null;
    const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
    return new File([bytes], resume.name || "resume.pdf", { type });
  }

  function fill(profile, doc = document) {
    let filled = 0;
    const p = profile || {};

    for (const el of doc.querySelectorAll("input, textarea")) {
      const type = (el.getAttribute("type") || "text").toLowerCase();
      if (el.disabled || el.readOnly || ["hidden", "radio", "checkbox", "submit", "button", "file", "password"].includes(type)) continue;
      if (el.value) continue;
      const key = keyFor(labelText(el));
      const value = key && !CHOICE_KEYS.has(key) ? textValue(p, key) : "";
      if (!value) continue;
      setValue(el, value);
      mark(el);
      filled++;
    }

    for (const sel of doc.querySelectorAll("select")) {
      if (sel.disabled || (sel.selectedIndex > 0 && sel.value)) continue;
      const key = keyFor(labelText(sel));
      const answer = p[key];
      if (!key || typeof answer !== "string" || !answer) continue;
      const opt = [...sel.options].find((o) => o.value && optionMatches(key, answer, o.textContent));
      if (!opt) continue;
      setValue(sel, opt.value);
      mark(sel);
      filled++;
    }

    const groups = new Map();
    for (const r of doc.querySelectorAll('input[type="radio"]')) {
      const id = r.name || r.closest("fieldset,[role=radiogroup]") || r;
      if (!groups.has(id)) groups.set(id, []);
      groups.get(id).push(r);
    }
    for (const radios of groups.values()) {
      if (radios.some((r) => r.checked)) continue;
      const key = keyFor(groupQuestion(radios[0]));
      const answer = p[key];
      if (!key || typeof answer !== "string" || !answer) continue;
      const hit = radios.find((r) => !r.disabled && optionMatches(key, answer, optionLabel(r)));
      if (!hit) continue;
      hit.click();
      mark(hit.closest("label") || hit);
      filled++;
    }

    if (p.resume && p.resume.data) {
      for (const el of doc.querySelectorAll('input[type="file"]')) {
        if (el.files?.length || keyFor(labelText(el)) !== "resume") continue;
        const file = fileFromDataUrl(p.resume);
        if (!file) break;
        const dt = new DataTransfer();
        dt.items.add(file);
        el.files = dt.files;
        el.dispatchEvent(new Event("change", { bubbles: true }));
        mark(el);
        filled++;
        break; // one resume upload is enough
      }
    }
    return filled;
  }

  const api = { keyFor, answerClass, optionMatches, textValue, fill };
  if (typeof module !== "undefined") module.exports = api;
  else globalThis.roamline = api;
})();
