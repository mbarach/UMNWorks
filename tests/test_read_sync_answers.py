import unittest, sys, pathlib, json, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import read_sync_answers as R

PROPS = [{"id": "a1", "action": "create", "kind": "honor", "screen": "936911", "screenName": "Honors", "resume_id": "r1", "title_line": "x",
          "fields": [{"name": "Title", "prefix": "_t-", "type": "text", "options": [], "required": True, "value": "", "note": ""},
                     {"name": "Date", "prefix": "date", "type": "date", "options": [], "required": True, "value": "2026", "note": ""}]},
         {"id": "a2", "action": "create", "kind": "honor", "screen": "936911", "screenName": "Honors", "resume_id": "r2", "title_line": "y", "fields": [
             {"name": "Title", "prefix": "_t-", "type": "text", "options": [], "required": True, "value": "", "note": ""}]},
         {"id": "v3", "action": "review", "works_id": "w100000000009", "kind": "presentation", "title_line": "z"}]
AUDIT = [{"id": "100000000001", "screen": "937611", "screenName": "Presentations", "title": "Net", "year": "2025", "context": "",
          "current": {"intl": "", "scale": "National"}, "flags": {"intl": {"ask": True}}}]
ANS = {"add-a1": {"decision": "add", "values": {"Title": "Best Paper Finalist", "Date": "Jun 2026"}},
       "add-a2": {"decision": "add", "values": {"Title": ""}},
       "review-v3": {"decision": "delete_by_hand"},
       "parse-r2": {"keep": True},
       "fill-100000000001": {"intl": "No", "scale": "National"},
       "parse-r1": {"keep": True, "title": "Edited"}}

class Reader(unittest.TestCase):
    def test_plan(self):
        p = R.build_sync_plan(ANS, PROPS, AUDIT)
        self.assertEqual(p["creates"][0]["values"], {"Title": "Best Paper Finalist", "Date": "Jun 2026"})
        self.assertEqual(p["incomplete_creates"], ["a2"])
        self.assertEqual(p["reviews"], [{"works_id": "w100000000009", "decision": "delete_by_hand"}])
        self.assertEqual(p["fills"][0]["writes"], {"intl": "No"})          # scale unchanged → dropped
        self.assertEqual(p["parse"], {"kept": 2, "dropped": 0, "edited": ["r1"]})

    def test_dropped_parse_item_is_not_created(self):
        ans = dict(ANS); ans["parse-r1"] = {"keep": False}
        p = R.build_sync_plan(ans, PROPS, AUDIT)
        self.assertEqual(p["creates"], []); self.assertEqual(p["dropped_creates"], ["a1"])

    def test_changed_target_screen_uses_that_forms_required_fields(self):
        forms = {"936911": {"name": "Honors", "fields": PROPS[0]["fields"]},
                 "937611": {"name": "Presentations", "fields": [{"name": "Presentation Title", "prefix": "_title-", "type": "text", "options": [], "required": True}]}}
        ans = dict(ANS); ans["add-a1"] = {"decision": "add", "screen": "937611", "values": {"Title": "x"}}
        p = R.build_sync_plan(ans, PROPS, AUDIT, forms)
        self.assertEqual(p["incomplete_creates"], ["a1", "a2"])
        ans["add-a1"]["values"] = {"Presentation Title": "Talk"}
        p = R.build_sync_plan(ans, PROPS, AUDIT, forms)
        self.assertEqual(p["creates"][0]["screen"], "937611"); self.assertEqual(p["creates"][0]["fields"][0]["name"], "Presentation Title")

    def test_require_one_of_dates(self):
        forms = {"936911": {"name": "Honors", "fields": [{"name": "Title", "prefix": "_t-", "type": "text", "options": [], "required": True},
                 {"name": "Date A", "prefix": "a", "type": "date", "options": [], "required": False}, {"name": "Date B", "prefix": "b", "type": "date", "options": [], "required": False}],
                 "require_one_of": ["Date A", "Date B"]}}
        props = [{"id": "a7", "action": "create", "kind": "honor", "screen": "936911", "screenName": "Honors", "resume_id": "r7", "title_line": "x", "fields": forms["936911"]["fields"]}]
        p = R.build_sync_plan({"add-a7": {"decision": "add", "values": {"Title": "T"}}}, props, [], forms)
        self.assertEqual(p["incomplete_creates"], ["a7"])
        p = R.build_sync_plan({"add-a7": {"decision": "add", "values": {"Title": "T", "Date B": "2024"}}}, props, [], forms)
        self.assertEqual(len(p["creates"]), 1)

    def test_loads_downloaded_answers_file(self):
        with tempfile.TemporaryDirectory() as t:
            d = pathlib.Path(t) / "answers"; d.mkdir(parents=True)
            (d / "answers.json").write_text(json.dumps({"review-v3": {"decision": "keep", "updatedAt": "now"}}))
            self.assertEqual(R.load_answers(pathlib.Path(t)), {"review-v3": {"decision": "keep"}})

    def test_loads_answer_files(self):
        with tempfile.TemporaryDirectory() as t:
            d = pathlib.Path(t) / "answers" / "answers"; d.mkdir(parents=True)
            (d / "add-a1.json").write_text(json.dumps({"data": {"decision": "skip", "updatedAt": "now"}}))
            self.assertEqual(R.load_answers(pathlib.Path(t)), {"add-a1": {"decision": "skip"}})

if __name__ == "__main__":
    unittest.main()
