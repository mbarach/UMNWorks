import unittest, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import match

AL = {"sms": "strategic management society", "isc": "israel strategy conference"}
def W(id, kind, title="", venue="", year=None, status=""):
    return {"id": id, "kind": kind, "title": title, "venue": venue, "year": year, "month": None, "people": [], "place": "",
            "status": status, "source": "works", "ref": id[1:], "source_text": ""}
def R(id, kind, title="", venue="", year=None, status=""):
    return dict(W(id, kind, title, venue, year, status), source="resume", ref="line 1")

class Match(unittest.TestCase):
    def test_alias_expansion(self):
        self.assertEqual(match.expand_aliases("SMS San Francisco", AL), "strategic management society san francisco")

    def test_presentation_matches_by_venue_and_year(self):
        w = [W("w100000000001", "presentation", "Net", "SMS Annual Conference San Francisco", 2025)]
        r = [R("r1", "presentation", "", "SMS San Francisco", 2025)]
        m = match.match_items(w, r, AL)
        self.assertEqual(m["matched"][0]["works"], "w100000000001"); self.assertEqual(m["resume_only"], []); self.assertEqual(m["works_only"], [])

    def test_wrong_year_does_not_match_presentation(self):
        w = [W("w100000000001", "presentation", "", "SMS Annual Conference", 2024)]
        r = [R("r1", "presentation", "", "SMS", 2025)]
        m = match.match_items(w, r, AL)
        self.assertEqual(m["matched"], []); self.assertEqual(m["resume_only"], ["r1"]); self.assertEqual(m["works_only"], ["w100000000001"])

    def test_publication_matches_by_title_within_one_year(self):
        w = [W("w100000000002", "publication", "Mapping Rivers, Counting Stars: Imaginary Flows in a Made-up Market", "Org Sci", 2026, "submitted")]
        r = [R("r2", "publication", "Mapping rivers, counting stars", "", 2025, "working")]
        self.assertEqual(match.match_items(w, r, AL)["matched"][0]["resume"], "r2")

    def test_null_year_matches_by_venue_only(self):
        w = [W("w100000000003", "service", "Ad Hoc Reviewer", "Strategic Management Journal", 2019)]
        r = [R("r3", "service", "Ad hoc reviewer", "SMJ", None)]
        self.assertEqual(match.match_items(w, r, {"smj": "strategic management journal"})["matched"][0]["works"], "w100000000003")

    def test_one_to_one_duplicates_stay_works_only(self):
        w = [W("w100000000004", "presentation", "", "Wharton People and Organizations", 2023),
             W("w100000000005", "presentation", "", "Wharton People and Organizations", 2023)]
        r = [R("r4", "presentation", "", "Wharton People and Organizations", 2023)]
        m = match.match_items(w, r, AL)
        self.assertEqual(len(m["matched"]), 1); self.assertEqual(len(m["works_only"]), 1)

    def test_similar_journal_names_do_not_match_service(self):
        w = [W("w100000000007", "service", "Reviewer", "Journal of Strategy and Management", 2020)]
        r = [R("r6", "service", "Reviewer", "SMJ", None)]
        m = match.match_items(w, r, {"smj": "strategic management journal"})
        self.assertEqual(m["matched"], [])

    def test_grant_titles_need_most_words_in_common(self):
        w = [W("w100000000008", "grant", "Dean's Small Grant", "Carlson", 2022)]
        r = [R("r7", "grant", "Dean's Research Travel Grant", "Carlson", 2023)]
        self.assertEqual(match.match_items(w, r, {})["matched"], [])

    def test_null_year_item_does_not_steal_the_exact_year_match(self):
        w = [W("w100000000010", "presentation", "", "SMS Annual Conference", 2025)]
        r = [R("r10", "presentation", "", "SMS", None), R("r9", "presentation", "", "SMS", 2025)]
        m = match.match_items(w, r, AL)
        self.assertEqual(m["matched"][0]["resume"], "r9"); self.assertEqual(m["resume_only"], ["r10"])

    def test_service_role_breaks_ties_between_same_venue(self):
        w = [W("w100000000011", "service", "Ad Hoc Reviewer", "Strategic Management Journal", 2019)]
        r = [R("r11", "service", "Editorial Board Member", "SMJ", 2024), R("r12", "service", "Ad hoc reviewer", "SMJ", None)]
        m = match.match_items(w, r, {"smj": "strategic management journal"})
        self.assertEqual(m["matched"][0]["resume"], "r12"); self.assertEqual(m["resume_only"], ["r11"])

    def test_other_kinds_are_omitted(self):
        m = match.match_items([W("w100000000006", "other", "x")], [R("r5", "position", "Assistant Professor", "UMN", 2018)], AL)
        self.assertEqual(m, {"matched": [], "resume_only": [], "works_only": []})

if __name__ == "__main__":
    unittest.main()
