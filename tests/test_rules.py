import unittest, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import rules

FORMS = {"937611": {"name": "Presentations", "add": "drawer", "fields": [
    {"name": "Presentation Title", "prefix": "_title-", "type": "text", "options": [], "required": True},
    {"name": "Conference/Meeting Name", "prefix": "_conf-", "type": "text", "options": [], "required": False},
    {"name": "Presenters/Authors", "prefix": "__people__", "type": "note", "options": [], "required": False},
    {"name": "Date", "prefix": "date", "type": "date", "options": [], "required": True},
    {"name": "Was/is this an international activity?", "prefix": "_international-", "type": "combo", "options": ["Yes", "No"], "required": False},
    {"name": "AACSB Classification", "prefix": "_classification-", "type": "combo", "options": ["Basic or Discovery Scholarship", "Applied or Integration/Application Scholarship", "Teaching and Learning Scholarship"], "required": False},
    {"name": "Scale", "prefix": "_scope-", "type": "combo", "options": ["International", "National"], "required": False}]},
  "937807": {"name": "Service", "add": "drawer", "fields": [
    {"name": "Position/Role", "prefix": "_role-", "type": "combo", "options": ["Ad Hoc Reviewer", "Member"], "required": False},
    {"name": "Org", "prefix": "_org-", "type": "text", "options": [], "required": False}]},
  "937449": {"name": "Publications", "add": "drawer", "fields": [
    {"name": "Title of Contribution", "prefix": "_title-", "type": "text", "options": [], "required": True},
    {"name": "Current Status", "prefix": "_status-", "type": "combo", "options": ["Published", "Submitted", "Working Paper"], "required": True},
    {"name": "Date Published", "prefix": "pub", "type": "date", "options": [], "required": False},
    {"name": "Date of Last/Most Recent Submission", "prefix": "sub", "type": "date", "options": [], "required": False}]}}
FMAP = {"937611": {"Presentation Title": {"from": "title"}, "Conference/Meeting Name": {"from": "venue"}, "Presenters/Authors": {"people": True},
                   "Date": {"date": "date", "note": "single event"},
                   "Was/is this an international activity?": {"intl": True}, "AACSB Classification": {"const": "Basic or Discovery Scholarship", "note": "default"}},
        "937807": {"Position/Role": {"from": "title"}, "Org": {"from": "venue"}},
        "937449": {"Title of Contribution": {"from": "title"}, "Current Status": {"status": True},
                   "Date Published": {"date": "pub", "if_status": ["published"]}, "Date of Last/Most Recent Submission": {"date": "sub", "if_status": ["submitted"]}}}
KINDS = {"937611": {"kind": "presentation"}, "937807": {"kind": "service"}, "937449": {"kind": "publication"}}
CONFIG = {"international_rule": "outside_us"}
def R(id, kind, title="", venue="", year=None, month=None, place="", status="", people=None):
    return {"id": id, "kind": kind, "title": title, "venue": venue, "year": year, "month": month, "people": people or [], "place": place,
            "status": status, "source": "resume", "ref": "line 1", "source_text": venue}

class Rules(unittest.TestCase):
    def propose(self, resume, matches=None, works=None):
        matches = matches or {"matched": [], "resume_only": [r["id"] for r in resume], "works_only": []}
        return rules.propose(matches, works or [], resume, FORMS, FMAP, KINDS, CONFIG)

    def test_create_card_has_every_form_field_in_order(self):
        p = self.propose([R("r1", "presentation", "", "SRF Montreal", 2024, place="Montreal, Canada")])[0]
        self.assertEqual(p["action"], "create"); self.assertEqual(p["screen"], "937611")
        self.assertEqual([f["name"] for f in p["fields"]], [f["name"] for f in FORMS["937611"]["fields"]])

    def test_prefill_and_defaults(self):
        p = self.propose([R("r1", "presentation", "", "SRF Montreal", 2024, 6, "Montreal, Canada", people=["A", "B"])])[0]
        by = {f["name"]: f for f in p["fields"]}
        self.assertEqual(by["Conference/Meeting Name"]["value"], "SRF Montreal")
        self.assertEqual(by["Presentation Title"]["value"], "")                     # resume had no title; person fills it
        self.assertEqual(by["Date"]["value"], "Jun 2024"); self.assertIn("single event", by["Date"]["note"])
        self.assertEqual(by["Was/is this an international activity?"]["value"], "Yes")   # Canada
        self.assertEqual(by["AACSB Classification"]["value"], "Basic or Discovery Scholarship")
        self.assertIsNone(by["Scale"]["value"])                                     # no rule: left for the person
        self.assertEqual(by["Presenters/Authors"]["value"], "A, B")

    def test_intl_unknown_place_is_blank(self):
        p = self.propose([R("r1", "presentation", "", "Dartmouth Summer Camp", 2023)])[0]
        self.assertIsNone({f["name"]: f for f in p["fields"]}["Was/is this an international activity?"]["value"])

    def test_us_place_is_no(self):
        p = self.propose([R("r1", "presentation", "", "SMS", 2025, place="San Francisco, CA")])[0]
        self.assertEqual({f["name"]: f for f in p["fields"]}["Was/is this an international activity?"]["value"], "No")

    def test_combo_prefill_matches_option_case_insensitively(self):
        p = self.propose([R("r7", "service", "ad hoc reviewer", "SMJ", 2021)])[0]
        self.assertEqual({f["name"]: f for f in p["fields"]}["Position/Role"]["value"], "Ad Hoc Reviewer")

    def test_publication_date_follows_status(self):
        p = self.propose([R("r8", "publication", "Paper", "Org Sci", 2025, 3, status="submitted")])[0]
        by = {f["name"]: f for f in p["fields"]}
        self.assertEqual(by["Current Status"]["value"], "Submitted")
        self.assertEqual(by["Date of Last/Most Recent Submission"]["value"], "Mar 2025")
        self.assertIsNone(by["Date Published"]["value"])

    def test_intl_rule_on_foreign_and_us_places(self):
        cases = {"Rio de Janeiro, Brazil": "Yes", "Paris, Ile-de-France, France": "Yes", "La Paz, Bolivia": "Yes", "Santiago de Chile": "Yes",
                 "Israel": "Yes", "Montreal, Canada": "Yes", "Minneapolis, MN": "No", "San Francisco, CA": "No", "Boston, Massachusetts": "No",
                 "Washington, DC": "No", "Remote": None, "": None}
        for place, want in cases.items():
            self.assertEqual(rules.intl_from_place(place, CONFIG), want, place)
        self.assertNotEqual(rules.intl_from_place("Toronto, ON, CA", CONFIG), "No")

    def test_card_ids_are_stable_resume_and_works_ids(self):
        p = self.propose([R("r42", "presentation", "", "SRF Montreal", 2024)])[0]
        self.assertEqual(p["id"], "r42")
        w = [dict(R("w100000000001", "presentation", "Old talk", "Some Conf", 2016), source="works", ref="100000000001")]
        out = rules.propose({"matched": [], "resume_only": [], "works_only": ["w100000000001"]}, w, [], FORMS, FMAP, KINDS, CONFIG)
        self.assertEqual(out[0]["id"], "w100000000001")

    def test_review_for_works_only(self):
        w = [dict(R("w100000000001", "presentation", "Old talk", "Some Conf", 2016), source="works", ref="100000000001")]
        out = rules.propose({"matched": [], "resume_only": [], "works_only": ["w100000000001"]}, w, [], FORMS, FMAP, KINDS, CONFIG)
        self.assertEqual(out[0]["action"], "review"); self.assertIn("Some Conf", out[0]["title_line"])

    def test_kind_without_form_is_skipped(self):
        out = self.propose([R("r9", "grant", "Travel Grant", "Dean", 2023)])
        self.assertEqual(out, [])

if __name__ == "__main__":
    unittest.main()
