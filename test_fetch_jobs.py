"""Run: python3 -m unittest -v"""

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

    def test_bad_date_dropped(self):
        bad = fj.job("S", "X", "C", "", [], "", "https://x.com", "not a date")
        self.assertEqual(fj.clean([bad], NOW), [])


if __name__ == "__main__":
    unittest.main()
