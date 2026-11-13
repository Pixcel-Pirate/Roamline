"""Run: python3 -m unittest -v"""

import os
import tempfile
import unittest
from datetime import datetime, timezone

import fetch_jobs as fj

NOW = datetime(2026, 11, 13, tzinfo=timezone.utc)
RECENT = int(datetime(2026, 11, 10, tzinfo=timezone.utc).timestamp())
OLD = int(datetime(2026, 9, 1, tzinfo=timezone.utc).timestamp())


class Parsers(unittest.TestCase):
    def test_remoteok_skips_legal_notice(self):
        data = [{"legal": "x", "last_updated": 1},
                {"position": "Dev", "company": "A", "tags": ["py"], "salary_min": 50000,
                 "salary_max": 0, "url": "https://remoteok.com/1", "epoch": RECENT}]
        out = fj.from_remoteok(data)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["salary"], "$50,000")
        self.assertEqual(out[0]["location"], "Anywhere")

    def test_arbeitnow_keeps_only_remote(self):
        data = {"data": [
            {"title": "A", "company_name": "X", "remote": True, "url": "https://a.com", "created_at": RECENT},
            {"title": "B", "company_name": "Y", "remote": False, "url": "https://b.com", "created_at": RECENT}]}
        self.assertEqual([j["title"] for j in fj.from_arbeitnow(data)], ["A"])

    def test_himalayas_null_salary(self):
        data = {"jobs": [{"title": "T", "companyName": "C", "minSalary": None, "maxSalary": None,
                          "currency": None, "applicationLink": "https://h.app/1", "pubDate": RECENT}]}
        self.assertEqual(fj.from_himalayas(data)[0]["salary"], "")

    def test_non_https_url_blanked(self):
        self.assertEqual(fj.safe_url("javascript:alert(1)"), "")
        self.assertEqual(fj.safe_url("http://x.com"), "")
        self.assertEqual(fj.safe_url(None), "")


    def test_garbage_fields_do_not_crash(self):
        data = [{"position": 123, "company": None, "tags": "python", "salary_min": "lots",
                 "salary_max": True, "url": "https://x.com", "epoch": 10**20}]
        out = fj.from_remoteok(data)[0]
        self.assertEqual((out["title"], out["tags"], out["salary"], out["posted"]), ("", [], "", None))

    def test_long_title_capped(self):
        out = fj.job("S", "x" * 5000, "C", "", [], "", "https://x.com", None)
        self.assertEqual(len(out["title"]), 200)


class Clean(unittest.TestCase):
    def row(self, title, company="Co", posted=RECENT, url="https://x.com"):
        return fj.job("S", title, company, "", [], "", url, fj.iso(posted))

    def test_dedupe_old_and_broken(self):
        rows = [self.row("Dev"), self.row("dev", "co"), self.row("Old", posted=OLD),
                self.row("NoUrl", url="ftp://x"), self.row("")]
        self.assertEqual([j["title"] for j in fj.clean(rows, NOW)], ["Dev"])

    def test_naive_remotive_date_and_sort(self):
        a = fj.job("Remotive", "A", "C", "", [], "", "https://r.com/a", "2026-11-11T08:00:00")
        b = self.row("B")
        out = fj.clean([b, a], NOW)
        self.assertEqual([j["title"] for j in out], ["A", "B"])
        self.assertTrue(out[0]["posted"].endswith("+00:00"))

    def test_remotive_24h_delay(self):
        fresh = fj.job("Remotive", "New", "C", "", [], "", "https://r.com/n", "2026-11-12T18:00:00")
        self.assertEqual(fj.clean([fresh], NOW), [])

    def test_non_string_date_dropped(self):
        row = self.row("X")
        row["posted"] = 12345
        self.assertEqual(fj.clean([row], NOW), [])

    def test_bad_date_dropped(self):
        bad = fj.job("S", "X", "C", "", [], "", "https://x.com", "not a date")
        self.assertEqual(fj.clean([bad], NOW), [])


class KeepsOldFile(unittest.TestCase):
    def test_old_jobs_json_untouched_when_nothing_usable(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "jobs.json")
            with open(out, "w") as f:
                f.write("OLD")
            orig_out, orig_get = fj.OUT, fj.get_json
            fj.OUT, fj.get_json = out, lambda url: {}  # every source answers, no jobs
            try:
                with self.assertRaises(SystemExit):
                    fj.main()
            finally:
                fj.OUT, fj.get_json = orig_out, orig_get
            with open(out) as f:
                self.assertEqual(f.read(), "OLD")


if __name__ == "__main__":
    unittest.main()
