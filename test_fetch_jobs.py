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
        self.assertEqual(fj.safe_url("http://x.com"), "https://x.com")
        self.assertEqual(fj.safe_url(" https://x.com"), "")
        self.assertEqual(fj.safe_url(None), "")


    def test_garbage_fields_do_not_crash(self):
        data = [{"position": 123, "company": None, "tags": "python", "salary_min": "lots",
                 "salary_max": True, "url": "https://x.com", "epoch": 10**20}]
        out = fj.from_remoteok(data)[0]
        self.assertEqual((out["title"], out["tags"], out["salary"], out["posted"]), ("", [], "", None))

    def test_long_title_capped(self):
        out = fj.job("S", "x" * 5000, "C", "", [], "", "https://x.com", None)
        self.assertEqual(len(out["title"]), 200)


class NewSources(unittest.TestCase):
    def test_jobicy_hourly_salary(self):
        data = {"jobs": [{"jobTitle": "PT", "companyName": "Kins", "jobGeo": "USA", "jobIndustry": ["Health"],
                          "pubDate": "2026-11-12T15:48:21+00:00", "salaryMin": 45, "salaryMax": 45,
                          "salaryCurrency": "USD", "salaryPeriod": "hourly", "url": "https://jobicy.com/jobs/1"}]}
        self.assertEqual(fj.from_jobicy(data)[0]["salary"], "USD 45/hr")

    def test_wwr_rss(self):
        xml = b"""<rss><channel><item><title>Acme: Backend Dev</title><region>Anywhere in the World</region>
            <category>Programming</category><pubDate>Fri, 13 Nov 2026 03:41:36 +0000</pubDate>
            <link>https://weworkremotely.com/remote-jobs/acme-backend</link></item></channel></rss>"""
        j = fj.from_wwr(xml)[0]
        self.assertEqual((j["company"], j["title"], j["posted"][:10]), ("Acme", "Backend Dev", "2026-11-13"))

    def test_adzuna_coords_and_hybrid(self):
        data = {"results": [{"title": "Analyst (Hybrid)", "company": {"display_name": "X"},
                             "location": {"display_name": "Austin, TX"}, "latitude": 30.27, "longitude": -97.74,
                             "redirect_url": "https://www.adzuna.com/land/ad/1", "created": "2026-11-12T10:00:00Z"},
                            {"title": "Bad coords", "company": {}, "location": {}, "latitude": 999, "longitude": "x",
                             "redirect_url": "https://www.adzuna.com/land/ad/2", "created": "2026-11-12T10:00:00Z"}]}
        a, b = fj.from_adzuna(data, "remote")
        self.assertEqual((a["type"], a["lat"], a["lon"]), ("hybrid", 30.27, -97.74))
        self.assertNotIn("lat", b)
        self.assertEqual(b["type"], "remote")

    def test_usajobs(self):
        data = {"SearchResult": {"SearchResultItems": [{"MatchedObjectDescriptor": {
            "PositionTitle": "IT Specialist", "OrganizationName": "VA", "PositionURI": "https://www.usajobs.gov/job/1",
            "PositionLocation": [{"LocationName": "Anywhere in the U.S. (remote job)"}],
            "PublicationStartDate": "2026-11-01T00:00:00.0000",
            "PositionRemuneration": [{"MinimumRange": "80000.0", "MaximumRange": "104000.0"}]}}]}}
        j = fj.from_usajobs(data)[0]
        self.assertEqual((j["title"], j["salary"]), ("IT Specialist", "$80,000-104,000"))

    def test_company_boards_skip_onsite(self):
        gh = {"jobs": [{"title": "SRE", "location": {"name": "Remote, United States"}, "company_name": "GitLab",
                        "absolute_url": "https://job-boards.greenhouse.io/gitlab/1", "first_published": "2026-11-01T00:00:00-04:00"},
                       {"title": "Chef", "location": {"name": "San Francisco"},
                        "absolute_url": "https://job-boards.greenhouse.io/gitlab/2", "first_published": "2026-11-01T00:00:00-04:00"}]}
        self.assertEqual([j["title"] for j in fj.from_greenhouse("gitlab", gh)], ["SRE"])
        lever = [{"text": "AE", "hostedUrl": "https://jobs.lever.co/spotify/1", "workplaceType": "hybrid",
                  "categories": {"location": "New York, NY", "team": "Sales"}, "createdAt": 1792767640768}]
        j = fj.from_lever("spotify", lever)[0]
        self.assertEqual((j["type"], j["company"], j["posted"][:4]), ("hybrid", "Spotify", "2026"))
        ashby = {"jobs": [{"title": "Eng", "location": "NYC", "isRemote": True, "workplaceType": "Remote",
                           "jobUrl": "https://jobs.ashbyhq.com/ramp/1", "publishedAt": "2026-11-01T00:00:00Z"}]}
        self.assertEqual(fj.from_ashby("ramp", ashby)[0]["type"], "remote")

    def test_working_nomads(self):
        data = [{"url": "https://www.workingnomads.com/job/go/1/", "title": "Senior React Dev", "company_name": "Lemon",
                 "category_name": "Development", "tags": "react,python", "location": "Europe",
                 "pub_date": "2026-11-12T06:47:52-05:00"}]
        j = fj.from_working_nomads(data)[0]
        self.assertEqual((j["tags"], j["level"]), (["react", "python", "Development"], "senior"))
        self.assertEqual(fj.from_working_nomads({"not": "a list"}), [])

    def test_levels(self):
        cases = {
            "Senior Software Engineer": "senior", "Sr. Data Analyst": "senior", "Data Engineer III": "senior",
            "Staff Engineer": "lead", "Director of Sales": "lead", "Head of Design": "lead", "Team Lead": "lead",
            "Junior Developer": "entry", "Marketing Intern": "entry", "Engineer I": "entry",
            "Software Engineer II": "mid", "Mid-level QA": "mid",
            "Account Executive": "", "Lead Generation Specialist": "", "Staff Accountant": "",
            "Customer Support Rep": "",
        }
        for title, want in cases.items():
            self.assertEqual(fj.level_of(title), want, title)
        self.assertEqual(fj.level_of("Designer", ["Entry-level"]), "entry")
        self.assertEqual(fj.level_of("Designer", ["Executive"]), "lead")
        self.assertEqual(fj.level_of("Designer", "not a list"), "")

    def test_settings_validates_zips_and_radius(self):
        self.assertEqual(fj.settings({"SEARCH_ZIPS": "10001, 9410, abcde,94103;x", "SEARCH_RADIUS_MILES": "500"}),
                         (["10001"], 100))
        self.assertEqual(fj.settings({"SEARCH_ZIPS": "10001,94103", "SEARCH_RADIUS_MILES": "nope"}),
                         (["10001", "94103"], 30))


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
            saved = fj.OUT, fj.get_json, fj.fetch, fj.PAUSE
            fj.OUT, fj.PAUSE = out, 0
            fj.get_json = lambda url, headers=None: {}  # every JSON source answers, no jobs
            fj.fetch = lambda url, headers=None: b"<rss><channel></channel></rss>"
            try:
                with self.assertRaises(SystemExit):
                    fj.main()
            finally:
                fj.OUT, fj.get_json, fj.fetch, fj.PAUSE = saved
            with open(out) as f:
                self.assertEqual(f.read(), "OLD")


if __name__ == "__main__":
    unittest.main()
