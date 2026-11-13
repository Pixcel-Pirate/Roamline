# Roamline Autofill (browser extension)

Fills job applications from a profile you save once: name, contact, links, resume,
work authorization, sponsorship, citizenship, and the voluntary questions
(gender, Hispanic/Latino, race, veteran, disability). You always review and press
Submit yourself — it never submits.

## Install (free, about 1 minute)
Works in Chrome, Edge, Brave and other Chromium browsers.
1. On GitHub, open the Roamline repo → **Code → Download ZIP**, and unzip it.
2. Go to `chrome://extensions` (Edge: `edge://extensions`) and turn on **Developer mode**.
3. Click **Load unpacked** and pick the `extension` folder.
4. Click the puzzle icon → pin **Roamline Autofill** → right-click it → **Options**, fill in your profile and press **Save profile**.

## Use it
- On Greenhouse, Lever, Ashby and Workday application pages a **Fill with Roamline** button appears at the bottom right.
- On any other site, click the Roamline icon → **Fill this page**.
- Filled fields get a green outline. Fields that already have something in them, essay questions and anything it can't recognise are left for you.
- Multi-step forms (Workday): press the button again on each step.

## Privacy
- Your profile and resume are stored only in this browser (`chrome.storage.local`). The extension makes no network requests at all.
- It can only read a page when you press its button (`activeTab`), plus the five job-application sites above for the floating button.
- **Delete everything** in Options wipes it; **Export** saves a copy as JSON.
- Like your browser's own autofill, the data is not encrypted on disk, so use it on your own computer only.

## Limits
Some sites use custom drop-downs instead of normal form fields; those may need a click from you. Publishing to the Chrome Web Store is optional and costs a one-time $5 developer fee.

## Test
`node --test extension/fill.test.js`
