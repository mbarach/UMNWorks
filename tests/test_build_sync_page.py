import unittest, sys, pathlib, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import build_sync_page as B

RES = [{"id": "r1", "kind": "presentation", "title": "", "venue": "SRF Montreal", "year": 2024, "month": None, "people": [], "place": "",
        "status": "", "source": "resume", "ref": "line 143", "source_text": "SRF Montreal"}]
PROPS = [{"id": "a1", "action": "create", "kind": "presentation", "screen": "937611", "screenName": "Presentations", "resume_id": "r1",
          "title_line": "2024 · SRF Montreal", "fields": [
            {"name": "Presentation Title", "prefix": "_title-", "type": "text", "options": [], "required": True, "value": "", "note": ""},
            {"name": "Scale", "prefix": "_scope-", "type": "combo", "options": ["International", "National"], "required": False, "value": None, "note": ""},
            {"name": "Date", "prefix": "date", "type": "date", "options": [], "required": True, "value": "2024", "note": "single event"}]},
         {"id": "v2", "action": "review", "works_id": "w100000000009", "kind": "presentation", "title_line": "2016 · Old talk · Some Conf"}]
AUDIT = [{"id": "100000000001", "screen": "937611", "screenName": "Presentations", "title": "Net", "year": "2025", "context": "SMS",
          "current": {"intl": "", "teaching": "False"}, "flags": {"intl": {"ask": True, "suggest": "No"}}}]

class Page(unittest.TestCase):
    def setUp(self):
        self.html = B.render(RES, PROPS, AUDIT, ["screen 999 unknown"], {"name": "Test Person"})

    def test_four_sections_and_filter_bar(self):
        for s in ("Check the resume parse", "Add to Works", "Fill gaps", "Only in Works"):
            self.assertIn(s, self.html)
        for s in ('id="flt-undecided"', 'id="flt-decided"', 'id="flt-all"'):
            self.assertIn(s, self.html)

    def test_data_embedded_and_escaped(self):
        self.assertIn('"a1"', self.html); self.assertIn("SRF Montreal", self.html)
        html2 = B.render([dict(RES[0], source_text="</script><b>x")], [], [], [], {})
        self.assertNotIn("</script><b>x", html2); self.assertIn("<\\/script><b>x", html2)

    def test_warning_rendered(self):
        self.assertIn("screen 999 unknown", self.html)

    def test_account_name_shown(self):
        self.assertIn("Test Person", self.html)

    def test_no_personal_leftovers_in_template(self):
        self.assertNotIn("mbarach", B.TEMPLATE)

    def test_css_is_shared_with_audit_page(self):
        self.assertIn("--accent: #7a0019", self.html)

if __name__ == "__main__":
    unittest.main()

class Navigation(unittest.TestCase):
    def test_subsections_by_kind_and_jump_nav(self):
        html = B.render(RES, PROPS, AUDIT, [], {})
        for s in ('id="jump"', 'sec.id = "sec-" + key', 'id="sub-${key}-${g.slug}"', 'function groupCards', 'KIND_LABELS', 'data-subcount'):
            self.assertIn(s, html)

    def test_download_answers_target_screen_and_parse_drop(self):
        html = B.render(RES, PROPS, AUDIT, [], {}, {"937611": {"name": "Presentations", "fields": PROPS[0]["fields"]}})
        for s in ('id="download"', 'data-screen', 'dropped in step 1', '"forms":', 'parse-" + c.p.resume_id'):
            self.assertIn(s, html)
