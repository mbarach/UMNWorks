import unittest, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import items

GOOD = {"id": "r1", "kind": "presentation", "title": "", "venue": "SMS Annual Conference", "year": 2025,
        "month": 10, "people": [], "place": "San Francisco, CA", "status": "", "source": "resume",
        "ref": "line 142", "source_text": "SMS San Francisco"}

class Validate(unittest.TestCase):
    def test_good_item_passes(self):
        self.assertEqual(items.validate_items([GOOD]), [])

    def test_null_year_allowed(self):
        self.assertEqual(items.validate_items([dict(GOOD, year=None, month=None)]), [])

    def test_bad_kind_reports_index_and_id(self):
        errs = items.validate_items([dict(GOOD, kind="talk")])
        self.assertEqual(len(errs), 1)
        self.assertIn("item 0 (r1)", errs[0]); self.assertIn("kind", errs[0])

    def test_missing_key_and_wrong_types(self):
        bad = dict(GOOD); del bad["venue"]; bad["year"] = "2025"; bad["people"] = "A, B"
        errs = items.validate_items([bad])
        self.assertTrue(any("venue" in e for e in errs))
        self.assertTrue(any("year" in e for e in errs))
        self.assertTrue(any("people" in e for e in errs))

    def test_duplicate_ids_rejected(self):
        errs = items.validate_items([GOOD, dict(GOOD)])
        self.assertTrue(any("duplicate id" in e for e in errs))

    def test_source_ref_shape(self):
        errs = items.validate_items([dict(GOOD, source="works", id="w1", ref="12")])
        self.assertTrue(any("ref" in e for e in errs))

class Text(unittest.TestCase):
    def test_norm_text(self):
        self.assertEqual(items.norm_text("Rivers—but Not Lakes—Flow: Yes!"), "rivers but not lakes flow yes")

    def test_tokens_drop_stopwords(self):
        self.assertEqual(items.tokens("The Role of AI in the Firm"), {"role", "ai", "firm"})

if __name__ == "__main__":
    unittest.main()
