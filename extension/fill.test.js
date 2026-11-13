// Run: node --test extension/
"use strict";
const test = require("node:test");
const assert = require("node:assert");
const { keyFor, answerClass, optionMatches, textValue } = require("./fill.js");

test("questions map to profile keys", () => {
  const cases = {
    "First Name *": "firstName", "Last name": "lastName", "Email address": "email", "Phone": "phone",
    "LinkedIn Profile": "linkedin", "Website": "website", "Resume/CV": "resume", "Name": "fullName",
    "Are you legally authorized to work in the United States?": "authorized",
    "Will you now or in the future require sponsorship for employment visa status (e.g., H-1B)?": "sponsorship",
    "Are you a U.S. citizen?": "citizen", "Veteran Status": "veteran", "Disability Status": "disability",
    "Gender": "gender", "Are you Hispanic/Latino?": "hispanic", "Race": "race",
    "Why do you want to work here?": "",
  };
  for (const [q, want] of Object.entries(cases)) assert.strictEqual(keyFor(q), want, q);
});

test("answer options sort into yes / no / decline", () => {
  const cases = {
    "Yes": "yes", "No": "no",
    "I am a protected veteran": "yes", "I identify as one or more of the classifications of protected veteran": "yes",
    "I am not a protected veteran": "no", "I don't wish to answer": "decline", "Decline to self identify": "decline",
    "Yes, I have a disability (or previously had a disability)": "yes",
    "No, I do not have a disability and have not had one in the past": "no",
    "I do not want to answer": "decline", "Do not answer": "decline", "N/A": "", "Prefer not to say": "decline",
  };
  for (const [t, want] of Object.entries(cases)) assert.strictEqual(answerClass(t), want, t);
});

test("gender and race options match without false hits", () => {
  assert.ok(optionMatches("gender", "male", "Male"));
  assert.ok(!optionMatches("gender", "male", "Female"));
  assert.ok(optionMatches("gender", "female", "Woman"));
  assert.ok(optionMatches("gender", "non binary", "Non-binary"));
  assert.ok(optionMatches("gender", "decline", "Decline to self-identify"));
  assert.ok(optionMatches("race", "black", "Black or African American (United States of America)"));
  assert.ok(!optionMatches("race", "white", "Asian"));
  assert.ok(!optionMatches("veteran", "", "Yes"));
});

test("text values come only from strings", () => {
  assert.strictEqual(textValue({ firstName: "Ada", lastName: "Lovelace" }, "fullName"), "Ada Lovelace");
  assert.strictEqual(textValue({ email: 42 }, "email"), "");
});
