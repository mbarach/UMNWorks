import re, subprocess, unittest, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
RECORD_ID = re.compile(r"\b(?!1000000000)\d{12}\b")   # Works record ids are 12 digits; 1000000000xx are test fixtures
BANNED = ["Dropbox/resume", "/Users/"]            # plus one word per line in local/banned-words.txt (names, emails), if present
_extra = ROOT / "local" / "banned-words.txt"
if _extra.exists():
    BANNED += [w.strip() for w in _extra.read_text(encoding="utf-8").splitlines() if w.strip()]

class RepoHygiene(unittest.TestCase):
    def tracked(self):
        out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
        skip = ("tests/test_repo_hygiene.py",)
        return [ROOT / p for p in out.split("\n") if p and not p.startswith(skip)]

    def test_no_local_data_tracked(self):
        for p in self.tracked():
            rel = str(p.relative_to(ROOT))
            self.assertFalse(rel.startswith("local/") and rel not in ("local/README.md", "local/config.example.json"), f"{p} is tracked")

    def test_no_record_ids_or_names(self):
        for p in self.tracked():
            if p.suffix in {".png", ".jpg", ".pdf", ".gif"}:
                continue
            text = p.read_text(encoding="utf-8", errors="ignore")
            if not str(p.relative_to(ROOT)).startswith("tests/"):      # test fixtures use obviously fake ids
                self.assertIsNone(RECORD_ID.search(text), f"record id in {p}")
            for w in BANNED:
                self.assertFalse(w in text, f"{w!r} in {p}")

if __name__ == "__main__":
    unittest.main()
