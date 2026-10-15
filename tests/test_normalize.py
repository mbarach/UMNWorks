import unittest, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import normalize, items

KINDS = {"937611": {"kind": "presentation", "venue_field": "Conference/Meeting Name", "year_fields": ["Year, Date"], "month_field": "Month, Date"},
         "937449": {"kind": "publication", "venue_field": "Journal/Publisher/Proceedings Publisher", "status_field": "Current Status",
                    "year_fields": ["Year, Date Published", "Year, Date of First Submission"]}}
RECORDS = {
  "937611": {"name": "Presentations", "headers": [], "records": {
      "100000000001": {"Presentation Title": "Net", "Conference/Meeting Name": "SMS Annual Conference", "Year, Date": "2025", "Month, Date": "October",
                       "City": "San Francisco", "State": "California", "Country": "United States", "Last Name, Presenters/Authors": "Doe"}}},
  "937449": {"name": "Publications", "headers": [], "records": {
      "100000000002": {"Title of Contribution": "Seeing Alike", "Journal/Publisher/Proceedings Publisher": "Org Sci", "Current Status": "Submitted",
                       "Year, Date of First Submission": "2026"}}},
  "999999": {"name": "Mystery Screen", "headers": [], "records": {"100000000003": {"Title": "x"}}}}
AUDIT = [{"id": "100000000001", "screen": "937611", "screenName": "Presentations", "title": "Net", "year": "2025", "context": "", "current": {}, "flags": {}},
         {"id": "100000000002", "screen": "937449", "screenName": "Publications", "title": "Seeing Alike", "year": "2026", "context": "", "current": {}, "flags": {}},
         {"id": "100000000003", "screen": "999999", "screenName": "Mystery Screen", "title": "x", "year": "", "context": "", "current": {}, "flags": {}}]

class Normalize(unittest.TestCase):
    def setUp(self):
        self.out, self.warn = normalize.works_items(RECORDS, AUDIT, KINDS)
        self.by = {i["id"]: i for i in self.out}

    def test_valid_items(self):
        self.assertEqual(items.validate_items(self.out), [])

    def test_presentation_fields(self):
        p = self.by["w100000000001"]
        self.assertEqual((p["kind"], p["venue"], p["year"], p["month"]), ("presentation", "SMS Annual Conference", 2025, 10))
        self.assertEqual(p["place"], "San Francisco, California, United States")
        self.assertEqual(p["ref"], "100000000001")

    def test_publication_status_and_year_fallback(self):
        q = self.by["w100000000002"]
        self.assertEqual((q["status"], q["year"]), ("submitted", 2026))

    def test_unknown_screen_is_other_with_warning(self):
        self.assertEqual(self.by["w100000000003"]["kind"], "other")
        self.assertTrue(any("999999" in w for w in self.warn))

class ScreenDiff(unittest.TestCase):
    def test_both_directions_reported(self):
        seen = [{"id": "937611", "name": "Presentations"}, {"id": "555555", "name": "Brand New Screen"}]
        catalog = {"937611": "Presentations", "936911": "Honors and Recognition"}
        w = normalize.screen_diff_warnings(seen, catalog)
        self.assertTrue(any("555555" in x and "Brand New Screen" in x for x in w))
        self.assertTrue(any("936911" in x for x in w))
        self.assertFalse(any("937611" in x for x in w))

    def test_service_title_is_the_role(self):
        kinds = {"937807": {"kind": "service", "venue_field": "Org", "role_field": "Position/Role", "year_fields": []}}
        recs = {"937807": {"name": "S", "headers": [], "records": {"100000000007": {"Org": "SMJ", "Position/Role": "Ad Hoc Reviewer"}}}}
        audit = [{"id": "100000000007", "screen": "937807", "screenName": "S", "title": "SMJ", "year": "", "context": "", "current": {}, "flags": {}}]
        out, _ = normalize.works_items(recs, audit, kinds)
        self.assertEqual((out[0]["title"], out[0]["venue"]), ("Ad Hoc Reviewer", "SMJ"))

if __name__ == "__main__":
    unittest.main()
