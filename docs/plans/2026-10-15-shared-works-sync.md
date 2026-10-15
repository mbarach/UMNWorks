# Shared Works Sync Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the one-person Works field-audit tooling into a project skill any Carlson faculty member can clone and run: resume in (any format), proposals on one artifact page, ticked changes written to Works.

**Architecture:** Python 3 scripts (standard library only) turn Works extracts and a model-written resume parse into one item schema, match them, apply guideline rules, and render one artifact page whose answers are read back and applied through in-page JavaScript helpers driven by the Claude in Chrome extension. Everything personal lives in a gitignored `local/` folder; everything shared is in git.

**Tech Stack:** Python 3.12+ standard library (`json`, `re`, `unittest`), vanilla HTML/JS artifact page with the `db` and `user` capabilities, Claude in Chrome `javascript_tool` + `computer` for the browser, git.

**Spec:** `docs/specs/2026-10-15-shared-works-sync-design.md` (read it first; it also lists the decisions that fix this plan's scope).

## Global Constraints

- Nothing is written to Works without a tick on the artifact page or an explicit instruction from the person running it. No cron, no unattended edits. Deletions are never automated.
- Carlson School only. Screens are discovered at runtime and compared with `screens.md`; a mismatch is a warning on the page, never silently ignored.
- The new Faculty Success view is the only supported view. Every browser recipe is re-tested there (Task 5) before any apply or create step is run.
- An "Add to Works" card shows every field of that screen's Add New form, in Works' order, with Works' own dropdown options; required fields are marked; a card cannot be ticked "Add" until they are filled; nothing is created with a value the person did not see on the card.
- The page opens on undecided cards only, with "Undecided (n) · Decided (m) · All" counts driven by stored answers; a decided card collapses to one line with a "change" link.
- No third-party Python packages (colleagues must not need `pip`). Tests run with `python3 -m unittest discover -s tests -v`.
- No personal data in git: no Works record ids, no names of students or colleagues, no resume content, no transcripts. `tests/test_repo_hygiene.py` enforces this. The GitHub repo starts from a fresh history (Task 12).
- Text fields in Works forms (titles, years, days, free text) only commit when typed with real keystrokes after a throwaway screenshot; comboboxes and checkboxes commit through the JS helper. Every recipe honours this.
- Scripts that read untrusted files (resume JSON written by the model, raw extracts) are run with `python3 -I`.
- Helper return strings never contain `key=value` or `?x=` text (the extension blanks such results).

## Review Focus

1. A resume item with no year (e.g. "Ad hoc reviewer: SMJ") must still validate and must land in `resume_only` with a card that asks for the date, not crash matching. Pinned in Task 2 (validation allows `year: null`) and Task 4 (null-year items match by venue only).
2. Two Works records with the same title and year (a duplicate Works flags) must each be matched or listed at most once; the second must appear under `works_only`, not be silently merged. Pinned in Task 4 (one-to-one greedy matching test).
3. A screen that exists in Works but not in `screens.md` (or vice versa) must be reported on the page's summary line, and its records must still get the field audit. Pinned in Task 3 (unknown screen → kind `other`, warning collected) and Task 8 (warnings rendered).
4. A resume parse that assigns a kind outside the schema (e.g. `"talk"`) must be rejected with a line number, not accepted as `other`. Pinned in Task 2.
5. A card ticked "Add" whose required field is empty must not reach `sync_plan.json`. Pinned in Task 9 (reader drops incomplete creates and reports them).

---

### Task 1: Repo restructure — `local/`, hygiene test, README, project skill

**Files:**
- Create: `.gitignore` (replace), `local/README.md` (tracked placeholder), `local/config.example.json`, `README.md`, `.claude/skills/umn-works/SKILL.md`, `scripts/fetch_guidelines.sh`, `tests/__init__.py`, `tests/test_repo_hygiene.py`
- Modify: `CLAUDE.md`, `screens.md`, `~/.claude/skills/umn-works-update/SKILL.md`
- Move: `audits/2026-10-13/` → `local/audits/2026-10-13/`; `docs/sessions/` → `local/sessions/`

**Interfaces:**
- Produces: `local/config.json` shape `{"name": str, "resume": str (path or URL), "website": str|"" , "international_rule": "outside_us"|"custom", "international_note": str}` read by Task 6 and Task 8. `local/audits/<date>/` as the audit directory every script takes as `AUDIT_DIR`.

- [ ] **Step 1: Write the hygiene test**

```python
# tests/test_repo_hygiene.py
import re, subprocess, unittest, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
RECORD_ID = re.compile(r"\b\d{12}\b")          # Works record ids are 12 digits
BANNED = ["<your email>", "<private path fragment>"]  # plus names from local/banned-words.txt

class RepoHygiene(unittest.TestCase):
    def tracked(self):
        out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
        skip = ("docs/specs/", "docs/plans/", "tests/test_repo_hygiene.py")
        return [ROOT / p for p in out.split("\n") if p and not p.startswith(skip)]

    def test_no_local_data_tracked(self):
        for p in self.tracked():
            rel = str(p.relative_to(ROOT))
            self.assertFalse(rel.startswith("local/") and rel not in ("local/README.md", "local/config.example.json"), f"{p} is tracked")

    def test_no_record_ids_or_names(self):
        for p in self.tracked():
            if p.suffix not in {".md", ".py", ".js", ".json", ".sh", ".txt", ".html"}:
                continue
            text = p.read_text(encoding="utf-8", errors="ignore")
            self.assertIsNone(RECORD_ID.search(text), f"record id in {p}")
            for w in BANNED:
                self.assertNotIn(w, text, f"{w!r} in {p}")

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it to see it fail** (ids and names are still in `screens.md`, `CLAUDE.md`, audits)

Run: `cd <repo> && python3 -m unittest tests.test_repo_hygiene -v`
Expected: FAIL on `test_no_record_ids_or_names` and `test_no_local_data_tracked`.

- [ ] **Step 3: Move personal data and ignore `local/`**

```bash
cd <repo>
mkdir -p local/audits local/sessions
git mv audits/2026-10-13 local/audits/2026-10-13
git mv docs/sessions local/sessions-tmp && mv local/sessions-tmp/* local/sessions/ && rmdir local/sessions-tmp
cat > .gitignore <<'EOF'
.DS_Store
local/*
!local/README.md
!local/config.example.json
__pycache__/
EOF
git rm -r --cached local/audits local/sessions
```

Write `local/README.md`:

```markdown
# local/ (not in git)

Everything about one person lives here and never enters the shared repo:

- `config.json` — copy `config.example.json` and fill it in (the skill asks on first run)
- `audits/<date>/` — one folder per run: raw extracts, records.json, resume_items.json, proposals.json, answers, after.md
- `sessions/` — transcripts and page snapshots, if you keep them
- `notes.md` — data-quality notes about your own records

Back this folder up however you like (Dropbox, a private repo); the shared repo will not.
```

Write `local/config.example.json`:

```json
{
  "name": "Your Name as it appears in Works",
  "resume": "/absolute/path/to/your/cv.pdf",
  "website": "",
  "international_rule": "outside_us",
  "international_note": "Yes only when the activity took place outside the United States; virtual events are No."
}
```

- [ ] **Step 4: Scrub `screens.md` and `CLAUDE.md`**

In `screens.md`: delete the "Data-quality notes" lines that name people and record ids (lines around 81, the swapped-name note and the travel-grant note); move them verbatim to `local/notes.md`. Replace the record-count column header "Records" with "Records (example account, 2026-10-13)" and keep the counts (they contain no ids). Delete the paragraph that lists the CV's four awards under "Manual-entry screens with no records" and replace with: "Honors and Recognition was empty on the example account; the resume-driven flow creates these."

In `CLAUDE.md`: change the first paragraph to "Tools and notes for keeping a Carlson faculty member's record in UMN **Works** current"; replace every "his"/"mbarach" with "the person running it"; replace the paths paragraph ("CV master is …") with "Personal paths live in `local/config.json` (see `local/README.md`)"; replace `audits/2026-10-13/` in the table with `local/audits/<date>/`; replace the artifact URL at the end with "The page URL for a run is recorded in `local/audits/<date>/after.md`". Delete the sentence about the Chrome extension not seeing "his own Brave tab" and write: "Open Works in a tab the extension creates; a tab the person opened themselves may not be visible to it."

- [ ] **Step 5: Write `README.md` for colleagues**

```markdown
# UMN Works sync (Carlson)

Keeps your UMN Works record (Watermark Faculty Success) in line with your resume, with you
approving every change on one page before anything is written.

## What you need

- Claude Code (the desktop app's Code tab is enough) with the Claude in Chrome extension installed.
- Chrome, Edge, or Brave signed in to Works: https://www.digitalmeasures.com/login/umn/faculty/app/activities/instruments/896?_s=0
- A claude.ai account on a paid plan (the approval page stores your answers there).
- Your resume as a file: PDF, Word, LaTeX, plain text, or a URL.

## First run

1. Clone this repo and open the folder in Claude Code.
2. Say: "Update my Works record from my resume at <path>."
3. Claude reads Works and your resume, publishes a private page, and gives you the link.
4. On the page, fix anything it misread in your resume, fill in and tick the records to add,
   answer the field questions, and decide about items that are only in Works.
5. Say "done" in chat. Claude writes only what you ticked, verifies each save, and reports.

Nothing is written to Works until you tick it. Deletions are never automated. Your data stays in
`local/` on your machine and never enters this repo.

## Once a year

Run it each January before the Annual Activity Report. Claude refreshes UMN's guidelines
(`scripts/fetch_guidelines.sh`) when they are older than 90 days.

## Questions about Works itself

worksadm@umn.edu, and the guides at https://works.umn.edu/guides-training
```

- [ ] **Step 6: Create the project skill and the personal pointer**

`.claude/skills/umn-works/SKILL.md`:

```markdown
---
name: umn-works
description: Use when the person asks to update, audit, check, or sync their UMN "Works" record (Watermark Faculty Success at digitalmeasures.com) from their resume or CV, including the yearly January activity-report update, AACSB classifications, international flags, service dates, honors, presentations, or publications. Trigger words - "Works", "Faculty Success", "Digital Measures", "activity report", "annual report".
---

# UMN Works sync

Read `CLAUDE.md` first (ground rules, browser recipes), then `screens.md` (screen catalog).
Do not work from memory of the site; the recipes there were earned through failures.

## The run (each step's details are in `docs/runbook.md`)

1. Setup: `local/config.json` exists (else ask name, resume path, international rule and write
   it); guidelines younger than 90 days (else `scripts/fetch_guidelines.sh`); a Works tab the
   extension opened, in the new Faculty Success view.
2. Read Works: discover screens from the Activities menu, extract every manual screen with all
   columns into `local/audits/<today>/raw/`, run `build_audit.py` then `normalize.py`.
3. Read the resume into `local/audits/<today>/resume_items.json` following
   `docs/item-schema.md`; run `python3 -I scripts/items.py <file>` until it validates.
4. `match.py`, `rules.py`, `build_sync_page.py`; publish the page with capabilities
   `{db: {}, user: {}}`; give the person the link and stop.
5. When they say they are done: read answers with ArtifactData, `read_sync_answers.py`,
   apply fills with `apply_record.js` and creates with `create_record.js`, one record at a time
   for a new field type, verifying every save. Re-extract, write `after.md`, commit nothing
   under `local/`.

## Hard rules

- Nothing is written without a tick. No cron, no unattended edits, no automated deletions.
- Leave the person's Works view and column settings as you found them where possible.
- Record any new recipe or quirk in `screens.md` / `CLAUDE.md` before the session ends.
```

Replace `~/.claude/skills/umn-works-update/SKILL.md` body (keep its frontmatter, update the description to add "if not already inside ~/repos/UMNWorks") with:

```markdown
# UMN Works (pointer)

The tool is the project skill in `~/repos/UMNWorks`. Change directory there (or tell the person
to open that folder in Claude Code) and follow `.claude/skills/umn-works/SKILL.md`.
```

- [ ] **Step 7: Add `scripts/fetch_guidelines.sh`**

```bash
#!/bin/sh
# Refresh UMN's Works guides (Google Docs) as text. Run from the repo root.
set -eu
cd "$(dirname "$0")/../docs/guidelines"
fetch() { curl -sSL "https://docs.google.com/document/d/$1/export?format=txt" -o "$2"; echo "fetched $2 ($(wc -c < "$2") bytes)"; }
fetch 1GClloQM_E7iKP0kmy3F8cbcgdGrmFlNI quick-start.txt
fetch 1Cuy6jY2LcwtYFNRCYvsP_xyqQsG8yUC8 publications.txt
fetch 17wLYkWTzhTUhrOWBxO04HOiKSF0ItvxG grants.txt
fetch 1cjoM6ezjncO8RtjkLUkZ_BJL8n9gkqWr reports.txt
fetch 12WomJYix3IypmRZXSbxJBRj2HnPSdTON0h8v0BPXQdU new-interface-crosswalk.txt
date -u +%Y-%m-%d > fetched-on.txt
```

Run `chmod +x scripts/fetch_guidelines.sh` and `touch tests/__init__.py`.

- [ ] **Step 8: Run the hygiene test until it passes**

Run: `python3 -m unittest tests.test_repo_hygiene -v`
Expected: both tests PASS. If a record id remains, `grep -rnE '\b[0-9]{12}\b' $(git ls-files)` finds it; move the line to `local/notes.md`.

- [ ] **Step 9: Commit**

```bash
git add -A && git commit -m "Restructure for sharing: local/ for personal data, README, project skill, hygiene test"
```

---

### Task 2: Item schema and validator (`scripts/items.py`)

**Files:**
- Create: `scripts/items.py`, `docs/item-schema.md`, `tests/test_items.py`

**Interfaces:**
- Produces: `KINDS = ("publication", "presentation", "honor", "service", "grant", "position", "education", "other")`; `validate_items(items: list) -> list[str]` (empty list = valid; each error is `"item <n> (<id>): <message>"`); `norm_text(s: str) -> str` (lowercase, ASCII letters/digits/spaces only, collapsed spaces); `tokens(s: str) -> set[str]` (norm_text split, stopwords removed); `load_items(path) -> list`. CLI: `python3 -I scripts/items.py FILE` prints errors and exits 1, or prints `ok <n> items` and exits 0.
- Item dict: `{"id": str, "kind": str, "title": str, "venue": str, "year": int|None, "month": int|None, "people": [str], "place": str, "status": str, "source": "works"|"resume", "ref": str, "source_text": str}`. For `source == "works"`, `ref` is the Works record id (12 digits) and `id` is `"w" + ref`; for resume items `ref` is the resume line or page reference and `id` is `"r" + <n>`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_items.py
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
        self.assertEqual(items.norm_text("Casting a Wider—but Less Discerning—Net: AI!"), "casting a wider but less discerning net ai")

    def test_tokens_drop_stopwords(self):
        self.assertEqual(items.tokens("The Role of AI in the Firm"), {"role", "ai", "firm"})

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m unittest tests.test_items -v`
Expected: ImportError / failures (`items` has no `validate_items`).

- [ ] **Step 3: Implement `scripts/items.py`**

```python
"""One item schema for Works records and resume entries. See docs/item-schema.md.

CLI: python3 -I scripts/items.py FILE   -> validates a JSON list of items; exit 1 on errors.
"""
import json, re, sys, unicodedata

KINDS = ("publication", "presentation", "honor", "service", "grant", "position", "education", "other")
KEYS = {"id": str, "kind": str, "title": str, "venue": str, "year": (int, type(None)), "month": (int, type(None)),
        "people": list, "place": str, "status": str, "source": str, "ref": str, "source_text": str}
STOPWORDS = {"a", "an", "the", "of", "in", "on", "and", "for", "to", "at", "by", "with", "from", "its", "vs"}

def norm_text(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c if ord(c) < 128 else " " for c in s)      # accents were split off by NFKD; other non-ASCII (em dashes) become spaces
    s = re.sub(r"[^a-z0-9]+", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()

def tokens(s):
    return {t for t in norm_text(s).split() if t not in STOPWORDS}

def validate_items(items):
    errs, seen = [], set()
    if not isinstance(items, list):
        return ["top level must be a JSON list"]
    for n, it in enumerate(items):
        tag = f"item {n} ({it.get('id', '?') if isinstance(it, dict) else '?'})"
        if not isinstance(it, dict):
            errs.append(f"{tag}: not an object"); continue
        for k, typ in KEYS.items():
            if k not in it:
                errs.append(f"{tag}: missing key {k}")
            elif not isinstance(it[k], typ) or (typ is int or isinstance(typ, tuple)) and isinstance(it[k], bool):
                errs.append(f"{tag}: {k} has wrong type")
        if it.get("kind") not in KINDS:
            errs.append(f"{tag}: kind must be one of {', '.join(KINDS)}")
        if it.get("source") not in ("works", "resume"):
            errs.append(f"{tag}: source must be works or resume")
        if it.get("source") == "works" and not re.fullmatch(r"\d{12}", str(it.get("ref", ""))):
            errs.append(f"{tag}: works ref must be the 12-digit record id")
        if isinstance(it.get("people"), list) and not all(isinstance(p, str) for p in it["people"]):
            errs.append(f"{tag}: people must be a list of strings")
        if isinstance(it.get("year"), int) and not 1950 <= it["year"] <= 2100:
            errs.append(f"{tag}: year out of range")
        if isinstance(it.get("month"), int) and not 1 <= it["month"] <= 12:
            errs.append(f"{tag}: month out of range")
        if it.get("id") in seen:
            errs.append(f"{tag}: duplicate id")
        seen.add(it.get("id"))
    return errs

def load_items(path):
    with open(path, encoding="utf-8") as f:
        items = json.load(f)
    errs = validate_items(items)
    if errs:
        raise ValueError("\n".join(errs))
    return items

if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as f:
        data = json.load(f)
    problems = validate_items(data)
    print("\n".join(problems) if problems else f"ok {len(data)} items")
    sys.exit(1 if problems else 0)
```

- [ ] **Step 4: Run tests**

Run: `python3 -m unittest tests.test_items -v`
Expected: all PASS.

- [ ] **Step 5: Write `docs/item-schema.md`** (the resume-extraction instructions Task 7 points at)

```markdown
# Item schema

Every Works record and every resume entry becomes one JSON object with exactly these keys:

| key | type | meaning |
|---|---|---|
| id | string | `r<n>` for resume items (n counts up from 1), `w<recordId>` for Works records |
| kind | string | one of publication, presentation, honor, service, grant, position, education, other |
| title | string | paper/talk/award/role title; "" when the resume gives none (common for talks) |
| venue | string | journal, conference, organization, institution, or funder |
| year | int or null | the year the resume states; null if none |
| month | int or null | 1–12 if stated |
| people | list of strings | co-authors, co-PIs; "" entries not allowed |
| place | string | city/state/country if stated; "" otherwise |
| status | string | publications: published, accepted, revise-and-resubmit, submitted, working; else "" |
| source | string | "works" or "resume" |
| ref | string | Works: the 12-digit record id. Resume: where it came from, e.g. "line 142" or "page 3" |
| source_text | string | the resume text the item was read from, verbatim, so the person can check it |

Rules for reading a resume into items (Claude does this; there is no parser):

- One item per talk, paper, award, role, grant. A resume line that lists several venues for a
  year ("2024: SRF Montreal, Wharton P&O, Dartmouth Summer Camp") becomes one item per venue,
  all with that year and the same `ref` and `source_text`.
- Working papers, papers under review, and R&Rs are `publication` with the right `status`.
- "Finalist", "Winner", "Fellowship", "Scholarship", "Award" lines are `honor`, even inside a
  publications section (a `\pawnote` under a paper). Grants with money are `grant`.
- Reviewer and editorial roles, committee work, conference organizing are `service`; the
  organization is `venue`, the role is `title`.
- Keep the resume's wording in `source_text`; do not expand abbreviations there (the alias table
  in `scripts/aliases.json` handles matching).
- Never invent a year, a place, or a co-author. Leave the field empty or null.

Validate with `python3 -I scripts/items.py local/audits/<date>/resume_items.json`.
```

- [ ] **Step 6: Commit**

```bash
git add scripts/items.py docs/item-schema.md tests/test_items.py
git commit -m "Add item schema, validator, and resume-reading rules"
```

---

### Task 3: Works records → items (`scripts/normalize.py`)

**Files:**
- Create: `scripts/normalize.py`, `scripts/screen_kinds.json`, `tests/test_normalize.py`

**Interfaces:**
- Consumes: `AUDIT_DIR/records.json` `{screenId: {name, headers, records: {id: {field: value}}}}` and `AUDIT_DIR/audit.json` `[{id, screen, screenName, title, year, context, current, flags}]` from `build_audit.py`; `items.KINDS`.
- Produces: `works_items(records: dict, audit: list, screen_kinds: dict) -> tuple[list[Item], list[str]]` (items, warnings); CLI `python3 -I scripts/normalize.py AUDIT_DIR` writes `AUDIT_DIR/works_items.json` and `AUDIT_DIR/normalize_warnings.json`. `scripts/screen_kinds.json` maps screen id → kind and is the shared catalog Task 6 reads too.

- [ ] **Step 1: Write `scripts/screen_kinds.json`**

```json
{
  "937449": {"kind": "publication", "venue_field": "Journal/Publisher/Proceedings Publisher", "status_field": "Current Status",
             "year_fields": ["Year, Date Published", "Year, Date Accepted", "Year, Date of Last/Most Recent Submission", "Year, Date of First Submission", "Year, Draft Start Date"]},
  "937611": {"kind": "presentation", "venue_field": "Conference/Meeting Name", "year_fields": ["Year, Date"], "month_field": "Month, Date"},
  "936911": {"kind": "honor", "venue_field": "Organization/Institution/Entity", "year_fields": ["Year, Date Received", "Year, Date", "Year, Start Date"]},
  "937807": {"kind": "service", "venue_field": "Organization/Committee/ Conference/Publication Name", "year_fields": ["Year, Start Date", "Year, End Date"]},
  "937757": {"kind": "service", "venue_field": "Name (e.g. committee, organization, etc.)", "year_fields": ["Year, Start Date", "Year, End Date"]},
  "937875": {"kind": "service", "venue_field": "Organization/Committee/Club", "year_fields": ["Year, Start Date", "Year, End Date"]},
  "1382407": {"kind": "grant", "venue_field": "Sponsoring Organization", "year_fields": ["Year, Start Date of Funding", "Year, Date Proposal Submitted"]},
  "936862": {"kind": "position", "venue_field": "Institution", "year_fields": ["Year, Start Date"]},
  "936967": {"kind": "education", "venue_field": "Institution", "year_fields": ["Year, Date Completed"]}
}
```

(The Honors field names are a guess until Task 5 captures the form; Task 5 step 6 corrects this file.)

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_normalize.py
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

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run to verify failure**

Run: `python3 -m unittest tests.test_normalize -v` → ImportError on `normalize`.

- [ ] **Step 4: Implement `scripts/normalize.py`**

```python
"""Turn Works extracts (records.json + audit.json) into items (docs/item-schema.md).

CLI: python3 -I scripts/normalize.py AUDIT_DIR -> AUDIT_DIR/works_items.json, normalize_warnings.json
"""
import json, pathlib, sys
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]

def _year(rec, fields):
    for f in fields:
        v = rec.get(f, "")
        if v and v.isdigit():
            return int(v)
    return None

def _month(rec, field):
    v = (rec.get(field, "") if field else "").strip().lower()
    return MONTHS.index(v) + 1 if v in MONTHS else None

def _place(rec):
    return ", ".join(rec[k] for k in ("City", "State", "Country") if rec.get(k))

def works_items(records, audit, screen_kinds):
    out, warnings, seen_unknown = [], [], set()
    for a in audit:
        sid, rid = a["screen"], a["id"]
        rec = records.get(sid, {}).get("records", {}).get(rid, {})
        sk = screen_kinds.get(sid)
        if sk is None:
            if sid not in seen_unknown:
                warnings.append(f"screen {sid} ({a.get('screenName', '?')}) is not in screen_kinds.json; its records are kind other")
                seen_unknown.add(sid)
            sk = {"kind": "other", "venue_field": "", "year_fields": []}
        year = _year(rec, sk.get("year_fields", []))
        if year is None and str(a.get("year", "")).isdigit():
            year = int(a["year"])
        people = [v for k, v in rec.items() if k.startswith("Last Name") and v]
        out.append({"id": "w" + rid, "kind": sk["kind"], "title": a.get("title", "") if a.get("title") != rid else "",
                    "venue": rec.get(sk.get("venue_field", ""), ""), "year": year, "month": _month(rec, sk.get("month_field")),
                    "people": people, "place": _place(rec), "status": rec.get(sk.get("status_field", ""), "").strip().lower(),
                    "source": "works", "ref": rid, "source_text": a.get("context", "")})
    return out, warnings

def main(audit_dir):
    d = pathlib.Path(audit_dir)
    records = json.loads((d / "records.json").read_text(encoding="utf-8"))
    audit = json.loads((d / "audit.json").read_text(encoding="utf-8"))
    kinds = json.loads((pathlib.Path(__file__).with_name("screen_kinds.json")).read_text(encoding="utf-8"))
    out, warnings = works_items(records, audit, kinds)
    (d / "works_items.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    (d / "normalize_warnings.json").write_text(json.dumps(warnings, indent=1), encoding="utf-8")
    print(f"items={len(out)} warnings={len(warnings)}")
    for w in warnings:
        print("  ", w)

if __name__ == "__main__":
    main(sys.argv[1])
```

- [ ] **Step 5: Run tests; then run on real data**

Run: `python3 -m unittest tests.test_normalize -v` → PASS.
Run: `python3 -I scripts/normalize.py local/audits/2026-10-13` → prints `items=100`, warnings list the screens not in `screen_kinds.json` (advising, media, leaves, etc.; expected). Spot-check `local/audits/2026-10-13/works_items.json`: 29 presentations with venues and years, 13 publications with statuses.

- [ ] **Step 6: Commit**

```bash
git add scripts/normalize.py scripts/screen_kinds.json tests/test_normalize.py
git commit -m "Normalize Works records into items"
```

---

### Task 4: Matching with aliases (`scripts/match.py`)

**Files:**
- Create: `scripts/match.py`, `scripts/aliases.json`, `tests/test_match.py`

**Interfaces:**
- Consumes: `items.tokens`, `items.norm_text`; `works_items.json`, `resume_items.json`.
- Produces: `expand_aliases(text: str, aliases: dict) -> str`; `similarity(a: Item, b: Item, aliases) -> float` in [0,1]; `match_items(works: list, resume: list, aliases: dict, threshold=0.5) -> dict` `{"matched": [{"works": id, "resume": id, "score": float}], "resume_only": [id], "works_only": [id]}` (only kinds in `MATCH_KINDS = {"publication","presentation","honor","service","grant"}` take part; others are omitted entirely). CLI `python3 -I scripts/match.py AUDIT_DIR` writes `matches.json`.

- [ ] **Step 1: Write `scripts/aliases.json`** (key = short form as resumes write it, value = full Works wording; matching compares normalized text)

```json
{
  "srf": "strategic research forum",
  "p&o": "wharton people and organizations",
  "people and organizations": "wharton people and organizations",
  "isc": "israel strategy conference",
  "sms": "strategic management society",
  "aom": "academy of management",
  "egos": "european group for organizational studies",
  "nber": "national bureau of economic research",
  "smj": "strategic management journal",
  "org sci": "organization science",
  "amr": "academy of management review",
  "amj": "academy of management journal",
  "asq": "administrative science quarterly",
  "mgmt sci": "management science",
  "aim": "ai in management",
  "wcrs": "west coast research symposium",
  "msom": "manufacturing and service operations management"
}
```

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_match.py
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
        w = [W("w100000000002", "publication", "Seeing Alike, Judging Apart: AI and the Diverging Logics of Diagnosis", "Org Sci", 2026, "submitted")]
        r = [R("r2", "publication", "Seeing alike, judging apart", "", 2025, "working")]
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

    def test_other_kinds_are_omitted(self):
        m = match.match_items([W("w100000000006", "other", "x")], [R("r5", "position", "Assistant Professor", "UMN", 2018)], AL)
        self.assertEqual(m, {"matched": [], "resume_only": [], "works_only": []})

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run to verify failure** → ImportError on `match`.

- [ ] **Step 4: Implement `scripts/match.py`**

```python
"""Pair Works items with resume items. CLI: python3 -I scripts/match.py AUDIT_DIR -> AUDIT_DIR/matches.json"""
import json, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import items as I

MATCH_KINDS = {"publication", "presentation", "honor", "service", "grant"}
YEAR_SLACK = {"publication": 1, "presentation": 0, "honor": 0, "service": 99, "grant": 1}
TITLE_KINDS = {"publication", "honor", "grant"}     # compare titles; others compare venues

def expand_aliases(text, aliases):
    t = I.norm_text(text)
    for short, full in sorted(aliases.items(), key=lambda kv: -len(kv[0])):
        t = re.sub(r"(?<![a-z0-9])" + re.escape(I.norm_text(short)) + r"(?![a-z0-9])", I.norm_text(full), t)
    return t

def _key_text(it, aliases):
    if it["kind"] in TITLE_KINDS and it["title"]:
        return expand_aliases(it["title"], aliases)
    return expand_aliases(it["venue"] or it["title"], aliases)

def similarity(a, b, aliases):
    ta, tb = I.tokens(_key_text(a, aliases)), I.tokens(_key_text(b, aliases))
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    return inter / min(len(ta), len(tb))      # containment: "SMS San Francisco" vs "SMS Annual Conference San Francisco"

def _year_ok(a, b):
    if a["year"] is None or b["year"] is None:
        return True
    return abs(a["year"] - b["year"]) <= YEAR_SLACK[a["kind"]]

def match_items(works, resume, aliases, threshold=0.5):
    works = [w for w in works if w["kind"] in MATCH_KINDS]
    resume = [r for r in resume if r["kind"] in MATCH_KINDS]
    pairs = []
    for w in works:
        for r in resume:
            if w["kind"] != r["kind"] or not _year_ok(w, r):
                continue
            s = similarity(w, r, aliases)
            if s >= threshold:
                pairs.append((s, w["id"], r["id"]))
    pairs.sort(key=lambda p: (-p[0], p[1], p[2]))
    used_w, used_r, matched = set(), set(), []
    for s, wid, rid in pairs:
        if wid in used_w or rid in used_r:
            continue
        used_w.add(wid); used_r.add(rid)
        matched.append({"works": wid, "resume": rid, "score": round(s, 3)})
    return {"matched": matched,
            "resume_only": [r["id"] for r in resume if r["id"] not in used_r],
            "works_only": [w["id"] for w in works if w["id"] not in used_w]}

def main(audit_dir):
    d = pathlib.Path(audit_dir)
    aliases = json.loads(pathlib.Path(__file__).with_name("aliases.json").read_text(encoding="utf-8"))
    works = I.load_items(d / "works_items.json"); resume = I.load_items(d / "resume_items.json")
    m = match_items(works, resume, aliases)
    (d / "matches.json").write_text(json.dumps(m, indent=1), encoding="utf-8")
    print(f"matched={len(m['matched'])} resume_only={len(m['resume_only'])} works_only={len(m['works_only'])}")

if __name__ == "__main__":
    main(sys.argv[1])
```

- [ ] **Step 5: Run tests** → `python3 -m unittest tests.test_match -v` PASS. Review Focus items 1 and 2 are the `null_year` and `one_to_one` tests.

- [ ] **Step 6: Commit**

```bash
git add scripts/match.py scripts/aliases.json tests/test_match.py
git commit -m "Match Works and resume items with venue aliases"
```

---

### Task 5: Re-verify the browser recipes in the new view; capture Add New forms (`screens/forms.json`)

Needs the person at the keyboard with Works logged in. No unit tests; the evidence is the list view and the saved files.

**Files:**
- Create: `screens/forms.json`, `scripts/capture_form.js`
- Modify: `CLAUDE.md` (view notes, recipe differences), `screens.md`, `scripts/scrape_list.js` if selectors changed, `scripts/apply_record.js` if ids changed, `scripts/screen_kinds.json` (Honors fields)

**Interfaces:**
- Produces: `screens/forms.json` `{screenId: {"name": str, "add_url": str, "fields": [{"name": str, "prefix": str, "type": "text"|"textarea"|"combo"|"date"|"checkbox", "options": [str], "required": bool}]}}` for 937611, 937449, 936911, 937807, 937757, 937875. `prefix` is the input id up to the per-page UUID (e.g. `_scope-`); date fields carry the base (e.g. `date`, `start`, `end`) so helpers build `_dtm_<base>-`, `_dtd_<base>-`, `_dty_<base>-`.

- [ ] **Step 1: Open Works in the new view.** Load the Chrome tools in one ToolSearch call (`tabs_context_mcp, tabs_create_mcp, navigate, computer, javascript_tool, read_page, browser_batch`). Create a tab, navigate to `https://www.digitalmeasures.com/login/umn/faculty/app/home/instruments/896?fxp=true&_s=0`. Note in `CLAUDE.md` whether the "Go back to the original view" banner still exists; from now on do not flip back.

- [ ] **Step 2: Re-run the list extraction on Presentations** with the recipe in `CLAUDE.md` ("Reading data"). If `Select Columns`, `[role=row][data-dm-id]`, or `[role=gridcell]` differ, fix `scripts/scrape_list.js` and the recipe text. Confirm one row's parsed text matches `local/audits/2026-10-13/raw/extract_part1.txt` for the same record.

- [ ] **Step 3: Re-run `apply_record.js` on one presentation with a no-op write** (set `intl` to the value it already has). Expected: helper returns `SAVED _international- No` and the list view is unchanged. If any input prefix differs, update `FIELDS` in the helper and the id list in `CLAUDE.md`.

- [ ] **Step 4: Re-verify text typing** on the same record: change the day of the date to its current value plus nothing (type the same year), Save, confirm "Record has been saved". Record whether the throwaway-screenshot rule still holds.

- [ ] **Step 5: Write `scripts/capture_form.js`** and run it on each screen's Add New page (the "+ Add New" button on the list; note the URL pattern, expected `.../screens/<screenId>/records/new?_s=0`):

```javascript
// Run on an Add New form. Returns an array of "name | prefix | type | required | options" strings (one per field).
(() => {
  const rows = [];
  const labelOf = el => { const l = el.closest("[class*=field], .form-group, wm-field, div")?.querySelector("label, [class*=label]"); return (l?.innerText || el.getAttribute("aria-label") || "").trim().replace(/\s+/g, " "); };
  for (const el of document.querySelectorAll("input, textarea, select")) {
    if (!el.id || el.type === "hidden") continue;
    const prefix = el.id.replace(/[0-9a-f]{8}-[0-9a-f-]{27,}$/i, "");
    let type = el.tagName === "TEXTAREA" ? "textarea" : el.type === "checkbox" ? "checkbox" : el.getAttribute("role") === "combobox" || el.getAttribute("aria-expanded") !== null ? "combo" : "text";
    if (/^_dt[mdy]_/.test(prefix)) type = "date";
    const req = !!(el.required || el.getAttribute("aria-required") === "true" || /\*/.test(labelOf(el)));
    rows.push([labelOf(el), prefix, type, req ? "required" : "", ""].join(" | "));
  }
  return rows;
})()
```

For each combo, open it (dispatch pointer/mouse events as `setCombo` does) and read `[role=option]` texts into `options`. Assemble `screens/forms.json` by hand from the arrays. Avoid `=` characters in returned strings.

- [ ] **Step 6: Fix `scripts/screen_kinds.json` for Honors** with the real field names from the captured form (venue field, year field), then run `python3 -m unittest discover -s tests -v` to confirm nothing broke.

- [ ] **Step 7: Document and commit**

Update `CLAUDE.md` "Original view vs new view" to "New view (verified <date>)" with any differences found; add the Add New URL pattern under URLs. In `screens.md` add a "Add New forms" section pointing at `screens/forms.json`.

```bash
git add CLAUDE.md screens.md screens/forms.json scripts/capture_form.js scripts/screen_kinds.json scripts/scrape_list.js scripts/apply_record.js
git commit -m "Verify recipes in the new Faculty Success view; capture Add New forms"
```

---

### Task 6: Guideline rules → proposals (`scripts/rules.py`)

**Files:**
- Create: `scripts/rules.py`, `scripts/field_map.json`, `tests/test_rules.py`

**Interfaces:**
- Consumes: `matches.json`, `works_items.json`, `resume_items.json`, `screens/forms.json`, `local/config.json`, `scripts/screen_kinds.json`.
- Produces: `propose(matches, works, resume, forms, field_map, screen_kinds, config) -> list[Proposal]`. Create proposal: `{"id": "a<n>", "action": "create", "kind", "screen", "screenName", "resume_id", "title_line": str, "fields": [{"name", "prefix", "type", "options", "required", "value": str|bool|null, "note": str}]}`. Review proposal: `{"id": "v<n>", "action": "review", "works_id", "kind", "title_line": str}`. CLI `python3 -I scripts/rules.py AUDIT_DIR` writes `proposals.json`.

- [ ] **Step 1: Write `scripts/field_map.json`** (which item key feeds which form field; `date` entries name the date base; `const` entries are fixed defaults with the guide line that justifies them)

```json
{
  "937611": {"Presentation Title": {"from": "title"}, "Conference/Meeting Name": {"from": "venue"},
             "Date": {"date": "date", "note": "Single event: Works wants the date as the end/only date (Quick Start Guide, dates)"},
             "City": {"from": "place"}, "Was/is this an international activity?": {"intl": true},
             "AACSB Classification": {"const": "Basic or Discovery Scholarship", "note": "Default for research talks; change if applied or teaching"},
             "Presentation Type": {"const": "Presentation/Talk"}},
  "937449": {"Title of Contribution": {"from": "title"}, "Journal/Publisher/Proceedings Publisher": {"from": "venue"},
             "Current Status": {"status": true, "note": "Required to save (Publications guide)"},
             "Contribution Type": {"const": "Journal Article", "note": "Required to save (Publications guide)"},
             "AACSB Classification": {"const": "Basic or Discovery Scholarship"},
             "Annotation": {"const": "", "note": "Multi-author paper: describe your contribution here (Publications guide, annotations)"}},
  "936911": {"__title__": {"from": "title"}, "__venue__": {"from": "venue"}, "__date__": {"date": "date", "note": "Single event: end/only date"}},
  "937807": {"Position/Role": {"from": "title"}, "Organization/Committee/ Conference/Publication Name": {"from": "venue"},
             "Start Date": {"date": "start", "note": "Start only = ongoing (Quick Start Guide)"}, "End Date": {"date": "end"},
             "Was/is this an international activity?": {"intl": true}, "AACSB": {"const": "Basic or Discovery Scholarship"}}
}
```

(Task 5 replaces the `__title__`/`__venue__`/`__date__` placeholders for Honors with the real field names; the test below uses its own map.)

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_rules.py
import unittest, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import rules

FORMS = {"937611": {"name": "Presentations", "add_url": "x", "fields": [
    {"name": "Presentation Title", "prefix": "_title-", "type": "text", "options": [], "required": True},
    {"name": "Conference/Meeting Name", "prefix": "_conf-", "type": "text", "options": [], "required": False},
    {"name": "Date", "prefix": "date", "type": "date", "options": [], "required": True},
    {"name": "Was/is this an international activity?", "prefix": "_international-", "type": "combo", "options": ["Yes", "No"], "required": False},
    {"name": "AACSB Classification", "prefix": "_classification-", "type": "combo", "options": ["Basic or Discovery Scholarship", "Applied or Integration/Application Scholarship", "Teaching and Learning Scholarship"], "required": False},
    {"name": "Scale", "prefix": "_scope-", "type": "combo", "options": ["International", "National"], "required": False}]}}
FMAP = {"937611": {"Presentation Title": {"from": "title"}, "Conference/Meeting Name": {"from": "venue"}, "Date": {"date": "date", "note": "single event"},
                   "Was/is this an international activity?": {"intl": True}, "AACSB Classification": {"const": "Basic or Discovery Scholarship", "note": "default"}}}
KINDS = {"937611": {"kind": "presentation"}}
CONFIG = {"international_rule": "outside_us"}
def R(id, kind, title="", venue="", year=None, month=None, place=""):
    return {"id": id, "kind": kind, "title": title, "venue": venue, "year": year, "month": month, "people": [], "place": place,
            "status": "", "source": "resume", "ref": "line 1", "source_text": venue}

class Rules(unittest.TestCase):
    def propose(self, resume, matches=None, works=None):
        matches = matches or {"matched": [], "resume_only": [r["id"] for r in resume], "works_only": []}
        return rules.propose(matches, works or [], resume, FORMS, FMAP, KINDS, CONFIG)

    def test_create_card_has_every_form_field_in_order(self):
        p = self.propose([R("r1", "presentation", "", "SRF Montreal", 2024, place="Montreal, Canada")])[0]
        self.assertEqual(p["action"], "create"); self.assertEqual(p["screen"], "937611")
        self.assertEqual([f["name"] for f in p["fields"]], [f["name"] for f in FORMS["937611"]["fields"]])

    def test_prefill_and_defaults(self):
        p = self.propose([R("r1", "presentation", "", "SRF Montreal", 2024, 6, "Montreal, Canada")])[0]
        by = {f["name"]: f for f in p["fields"]}
        self.assertEqual(by["Conference/Meeting Name"]["value"], "SRF Montreal")
        self.assertEqual(by["Presentation Title"]["value"], "")                     # resume had no title; person fills it
        self.assertEqual(by["Date"]["value"], "Jun 2024"); self.assertIn("single event", by["Date"]["note"])
        self.assertEqual(by["Was/is this an international activity?"]["value"], "Yes")   # Canada
        self.assertEqual(by["AACSB Classification"]["value"], "Basic or Discovery Scholarship")
        self.assertIsNone(by["Scale"]["value"])                                     # no rule: left for the person

    def test_intl_unknown_place_is_blank(self):
        p = self.propose([R("r1", "presentation", "", "Dartmouth Summer Camp", 2023)])[0]
        self.assertIsNone({f["name"]: f for f in p["fields"]}["Was/is this an international activity?"]["value"])

    def test_us_place_is_no(self):
        p = self.propose([R("r1", "presentation", "", "SMS", 2025, place="San Francisco, CA")])[0]
        self.assertEqual({f["name"]: f for f in p["fields"]}["Was/is this an international activity?"]["value"], "No")

    def test_review_for_works_only(self):
        w = [dict(R("w100000000001", "presentation", "Old talk", "Some Conf", 2016), source="works", ref="100000000001")]
        out = rules.propose({"matched": [], "resume_only": [], "works_only": ["w100000000001"]}, w, [], FORMS, FMAP, KINDS, CONFIG)
        self.assertEqual(out[0]["action"], "review"); self.assertIn("Some Conf", out[0]["title_line"])

    def test_kind_without_form_is_skipped_with_note(self):
        out = self.propose([R("r9", "grant", "Travel Grant", "Dean", 2023)])
        self.assertEqual(out, [])

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run to verify failure** → ImportError on `rules`.

- [ ] **Step 4: Implement `scripts/rules.py`**

```python
"""Apply the Works guideline rules to matched/unmatched items -> proposals.json (create and review cards).
Fill cards for matched records come from audit.json (build_audit.py) and are not produced here.
CLI: python3 -I scripts/rules.py AUDIT_DIR
"""
import json, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import items as I

MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
US = re.compile(r"\b(usa|u s a|united states|us)\b|\b(al|ak|az|ar|ca|co|ct|de|fl|ga|hi|id|il|in|ia|ks|ky|la|me|md|ma|mi|mn|ms|mo|mt|ne|nv|nh|nj|nm|ny|nc|nd|oh|ok|or|pa|ri|sc|sd|tn|tx|ut|vt|va|wa|wv|wi|wy|dc)\b"
                r"|\b(california|minnesota|massachusetts|pennsylvania|new york|texas|utah|michigan|illinois|washington|new hampshire|ohio|georgia)\b")

def intl_from_place(place, config):
    """Yes/No/None by the person's rule. Default rule: outside the US = Yes; unknown place = None (ask)."""
    p = I.norm_text(place)
    if not p:
        return None
    if config.get("international_rule", "outside_us") != "outside_us":
        return None
    return "No" if US.search(p) else "Yes"

def date_text(it):
    if it["year"] is None:
        return ""
    return f"{MONTH_ABBR[it['month'] - 1]} {it['year']}" if it["month"] else str(it["year"])

def screen_for(kind, screen_kinds, forms):
    for sid, sk in screen_kinds.items():
        if sk["kind"] == kind and sid in forms:
            return sid
    return None

def title_line(it):
    return " · ".join(x for x in [str(it["year"] or ""), it["title"], it["venue"]] if x)

def _value(spec, it, config):
    if "from" in spec:
        v = it.get(spec["from"], "")
        return v if isinstance(v, str) else ""
    if "const" in spec:
        return spec["const"]
    if "date" in spec:
        return date_text(it)
    if spec.get("intl"):
        return intl_from_place(it["place"], config)
    if spec.get("status"):
        return {"published": "Published", "accepted": "Accepted", "revise-and-resubmit": "Revising to Resubmit",
                "submitted": "Submitted", "working": "Working Paper"}.get(it["status"], None)
    return None

def propose(matches, works, resume, forms, field_map, screen_kinds, config):
    by_r = {r["id"]: r for r in resume}; by_w = {w["id"]: w for w in works}
    out, n = [], 0
    for rid in matches["resume_only"]:
        it = by_r[rid]; sid = screen_for(it["kind"], screen_kinds, forms)
        if sid is None:
            continue
        fmap = field_map.get(sid, {}); fields = []
        for f in forms[sid]["fields"]:
            spec = fmap.get(f["name"], {})
            v = _value(spec, it, config) if spec else None
            if f["type"] == "combo" and v is not None and v not in f["options"]:
                v = None
            fields.append({"name": f["name"], "prefix": f["prefix"], "type": f["type"], "options": f["options"],
                           "required": f["required"], "value": v, "note": spec.get("note", "")})
        n += 1
        out.append({"id": f"a{n}", "action": "create", "kind": it["kind"], "screen": sid, "screenName": forms[sid]["name"],
                    "resume_id": rid, "title_line": title_line(it), "fields": fields})
    for wid in matches["works_only"]:
        w = by_w[wid]; n += 1
        out.append({"id": f"v{n}", "action": "review", "works_id": wid, "kind": w["kind"], "title_line": title_line(w)})
    return out

def main(audit_dir):
    d = pathlib.Path(audit_dir); here = pathlib.Path(__file__).resolve().parent; root = here.parent
    load = lambda p: json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
    out = propose(load(d / "matches.json"), I.load_items(d / "works_items.json"), I.load_items(d / "resume_items.json"),
                  load(root / "screens" / "forms.json"), load(here / "field_map.json"), load(here / "screen_kinds.json"),
                  load(root / "local" / "config.json"))
    (d / "proposals.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"create={sum(p['action'] == 'create' for p in out)} review={sum(p['action'] == 'review' for p in out)}")

if __name__ == "__main__":
    main(sys.argv[1])
```

- [ ] **Step 5: Run tests** → `python3 -m unittest tests.test_rules -v` PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/rules.py scripts/field_map.json tests/test_rules.py
git commit -m "Propose create and review cards from guideline rules"
```

---

### Task 7: Resume reading (model-driven) and the runbook

**Files:**
- Create: `docs/runbook.md`
- Produce (not committed): `local/audits/<date>/resume_items.json` from the person's resume

**Interfaces:**
- Consumes: `docs/item-schema.md`, `scripts/items.py` CLI.
- Produces: a validated `resume_items.json`; `docs/runbook.md` with the exact reading procedure the skill step 3 refers to.

- [ ] **Step 1: Write `docs/runbook.md`** (the per-step detail the skill points at; this step covers the resume part, Tasks 8 and 9 append theirs)

```markdown
# Runbook

## 1. Setup
- `local/config.json` exists (copy `local/config.example.json`; ask for name, resume path, international rule).
- `docs/guidelines/fetched-on.txt` is within 90 days, else run `scripts/fetch_guidelines.sh`.
- One ToolSearch call loads: tabs_context_mcp, tabs_create_mcp, navigate, computer, javascript_tool, read_page, browser_batch.
- Create a tab; navigate to the Activities menu URL in `CLAUDE.md`. Confirm the page shows the person named in `config.json` (the account name is in the header); stop if not.

## 2. Read Works
- Discover screens: on the Activities page, collect every screen link `(name, screenId)`; diff against `screens.md`; keep the list in `local/audits/<date>/screens_seen.json`.
- Extract each manual screen with the list recipe in `CLAUDE.md` into `raw/extract_*.txt`.
- `python3 -I scripts/build_audit.py local/audits/<date>` then `python3 -I scripts/normalize.py local/audits/<date>`.

## 3. Read the resume
- Open the file from `config.json` with the Read tool (PDF pages in ranges of 20; a .docx via `textutil -convert txt` on macOS or `pandoc`; a .tex as text; a URL via WebFetch). Read the whole document before writing anything.
- Write `local/audits/<date>/resume_items.json` following `docs/item-schema.md`, section by section: publications, working papers, presentations, honors and grants, service, positions, education. Keep `source_text` verbatim and `ref` as the line or page.
- If `config.json` names a website, read it too and add only items the resume lacks (`ref` = the page URL).
- `python3 -I scripts/items.py local/audits/<date>/resume_items.json`; fix until `ok`.
- Print a count per kind in chat so the person can sanity-check before the page is built.

## 4. Match, rule, page
- `python3 -I scripts/match.py local/audits/<date>`; `python3 -I scripts/rules.py local/audits/<date>`; `python3 -I scripts/build_sync_page.py local/audits/<date>`.
- Publish `sync_page.html` with capabilities `{db: {}, user: {}}` (load `artifact-capabilities` first). Record the URL in `local/audits/<date>/after.md`. Give the link and stop.

## 5. Apply
- See Task 9/10 sections appended below.
```

- [ ] **Step 2: Run the procedure on the LaTeX CV** named in `local/config.json`. Write `local/audits/2026-10-13/resume_items.json` (reuse that audit folder as the development fixture). Validate: `python3 -I scripts/items.py local/audits/2026-10-13/resume_items.json` → `ok <n> items`. Expected counts to report in chat: ~13 publications/working papers, ~60 presentations (one per venue per year), ~15 honors/grants, service items, 2 positions, education.

- [ ] **Step 3: Run it again on the compiled PDF** (`site/cv.pdf` in the website repo) into a scratch file under `local/audits/2026-10-13/resume_items_pdf.json`. Compare counts per kind with the LaTeX result; they should agree within one or two items per kind. Note any systematic difference (e.g. PDF loses line refs) in `docs/item-schema.md` under a "Known differences by format" heading.

- [ ] **Step 4: Run the pipeline end to end on the fixture**

```bash
python3 -I scripts/match.py local/audits/2026-10-13
python3 -I scripts/rules.py local/audits/2026-10-13
```

Expected: most 2016–2025 presentations match (check `matches.json`); the four honors are `resume_only`; a handful of Works-only presentations (talks not on the CV) are listed. If obvious pairs are missed, add aliases to `scripts/aliases.json` and rerun; do not lower the threshold below 0.5.

- [ ] **Step 5: Commit** (docs only; `local/` stays out)

```bash
git add docs/runbook.md docs/item-schema.md scripts/aliases.json
git commit -m "Runbook and resume-reading procedure, verified on LaTeX and PDF"
```

---

### Task 8: The sync page (`scripts/build_sync_page.py`)

**Files:**
- Create: `scripts/build_sync_page.py`, `scripts/page_style.css`, `tests/test_build_sync_page.py`
- Modify: `scripts/build_page.py` (read its CSS from `page_style.css`)

**Interfaces:**
- Consumes: `resume_items.json`, `proposals.json`, `audit.json`, `normalize_warnings.json`, `local/config.json`.
- Produces: `AUDIT_DIR/sync_page.html`. Answer documents in db collection `answers`, doc id = card id: `p<n>`-style ids are `parse-r<n>` → `{"keep": bool, "title": str, "venue": str, "year": str}`; `add-a<n>` → `{"decision": "add"|"skip", "values": {fieldName: value}}`; `fill-<recordId>` → same shape as today's `{intl, scale, aacsb, start, teaching, end}`; `review-v<n>` → `{"decision": "keep"|"add_to_resume"|"delete_by_hand"}`. Every doc also carries `updatedAt`.
- `render(resume_items, proposals, audit, warnings, config) -> str` for tests; CLI `python3 -I scripts/build_sync_page.py AUDIT_DIR`.

- [ ] **Step 1: Move the CSS out of `build_page.py`.** Cut everything between `<style>` and `</style>` in `TEMPLATE` into `scripts/page_style.css`, and in `build_page.py` replace that block with `<style>__CSS__</style>` plus, in `main`, `.replace("__CSS__", (pathlib.Path(__file__).with_name("page_style.css")).read_text(encoding="utf-8"))`. Run `python3 -I scripts/build_page.py local/audits/2026-10-13` and diff the output with the committed `audit_page.html` in that folder: identical apart from whitespace.

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_build_sync_page.py
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

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run to verify failure** → ImportError.

- [ ] **Step 4: Implement `scripts/build_sync_page.py`**

```python
"""Render the sync page: resume parse check, Add cards, Fill cards, Works-only review. One artifact, db-backed answers.
CLI: python3 -I scripts/build_sync_page.py AUDIT_DIR -> AUDIT_DIR/sync_page.html
Publish with capabilities {db: {}, user: {}}. Answers live at answers/<cardId> (see docstring of read_sync_answers.py).
"""
import json, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
TEMPLATE = r"""<title>Works Sync Review</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,500;6..72,600&family=Public+Sans:wght@400;500;600&display=swap">
<style>__CSS__
.flt { display: inline-flex; border: 1px solid var(--line); border-radius: 6px; overflow: hidden; }
.flt button { border: 0; border-radius: 0; padding: 5px 10px; }
.flt button[aria-pressed=true] { background: var(--accent); color: #fff; }
.card { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 12px 14px; margin-bottom: 8px; }
.card.done { border-color: var(--ok); }
.card.done .body { display: none; }
.card .oneline { display: none; color: var(--muted); font-size: .9rem; }
.card.done .oneline { display: flex; gap: 10px; align-items: baseline; }
.card .oneline a { color: var(--accent); cursor: pointer; margin-left: auto; }
.fields { display: grid; grid-template-columns: minmax(0, 14em) minmax(0, 1fr); gap: 6px 12px; align-items: center; margin-top: 8px; }
.fields .fname { font-size: .85rem; color: var(--muted); }
.fields .req::after { content: " *"; color: var(--accent); }
.fields input[type=text], .fields select, .fields textarea { font: inherit; font-size: .9rem; padding: 4px 8px; border: 1px solid var(--line); border-radius: 6px; background: var(--bg); color: var(--fg); width: 100%; box-sizing: border-box; }
.fields .fnote { grid-column: 2; font-size: .8rem; color: var(--muted); }
.src { font-size: .85rem; color: var(--muted); font-style: italic; }
.actions { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; }
.actions label { display: inline-flex; align-items: center; gap: 4px; padding: 3px 9px; border: 1px solid var(--line); border-radius: 6px; cursor: pointer; font-size: .9rem; }
.actions label:has(input:checked) { border-color: var(--accent); background: var(--accent-soft); }
@media (max-width: 640px) { .fields { grid-template-columns: 1fr; } .fields .fnote { grid-column: 1; } }
</style>
<div class="wrap">
  <h1>Works Sync Review</h1>
  <p class="lede">Works account: <b id="acct">__NAME__</b>. Four steps, top to bottom. Everything saves as you go; nothing is written to Works until you say "done" in chat, and only what you ticked.</p>
  <div class="topbar">
    <div class="progress"><div class="status" id="status">Loading…</div><div class="bar"><i id="barfill"></i></div></div>
    <div class="flt" role="group" aria-label="Show"><button type="button" id="flt-undecided" aria-pressed="true">Undecided</button><button type="button" id="flt-decided" aria-pressed="false">Decided</button><button type="button" id="flt-all" aria-pressed="false">All</button></div>
  </div>
  <div class="alert" id="dbwarn" hidden>Answers can't be saved in this view (not signed in, or no data access). Open the page from your own Claude account.</div>
  <div class="note" id="warnings" hidden></div>
  <div id="sections"></div>
  <p class="foot">Dates: start only = ongoing, end only = a single event, both = a span (Works Quick Start Guide). Fields marked * are required by Works before a record can be saved. "I will delete by hand" is noted for you; the tool never deletes.</p>
</div>
<script>
const DATA = __DATA_JSON__;
const answers = {}; let db = null; let filter = "undecided";
const $ = (s, el=document) => el.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const SCALE_OPTS = ["International","National","Regional","State","Local"];

// ---- card model: every card has id, section, render(), isDone(), oneLine()
const cards = [];
for (const r of DATA.resume) cards.push({id: "parse-" + r.id, section: "parse", r});
for (const p of DATA.proposals) cards.push({id: (p.action === "create" ? "add-" : "review-") + p.id, section: p.action === "create" ? "add" : "review", p});
for (const a of DATA.audit) if (Object.values(a.flags).some(f => f.ask || f.toggle || f.ongoing)) cards.push({id: "fill-" + a.id, section: "fill", a});
const SECTIONS = [["parse", "1. Check the resume parse", "Fix anything misread. Untick an item that is not real."],
                  ["add", "2. Add to Works", "Each card is the Works form for that screen. Fill the blanks, then tick Add or Skip."],
                  ["fill", "3. Fill gaps", "Existing Works records missing a field."],
                  ["review", "4. Only in Works", "Items your resume does not mention."]];

function isDone(c) {
  const a = answers[c.id];
  if (!a) return false;
  if (c.section === "parse") return a.keep !== undefined;
  if (c.section === "add") return a.decision === "skip" || (a.decision === "add" && c.p.fields.every(f => !f.required || (a.values?.[f.name] ?? "") !== ""));
  if (c.section === "review") return !!a.decision;
  return Object.entries(c.a.flags).filter(([k, f]) => f.ask).every(([k]) => a[k] !== undefined && a[k] !== "");
}
function oneLine(c) {
  const a = answers[c.id] || {};
  if (c.section === "parse") return a.keep ? "kept" : "dropped";
  if (c.section === "add") return a.decision === "add" ? "will be added" : "skipped";
  if (c.section === "review") return {keep: "keep in Works", add_to_resume: "add to resume", delete_by_hand: "delete by hand"}[a.decision];
  return Object.entries(a).filter(([k]) => k !== "updatedAt").map(([k, v]) => `${k}: ${v === "__leave" ? "leave blank" : v}`).join(", ");
}
function fieldInput(cid, f, val) {
  const id = `${cid}__${f.name}`;
  if (f.type === "combo") return `<select data-field="${esc(f.name)}"><option value="">—</option>${f.options.map(o => `<option ${val===o?'selected':''}>${esc(o)}</option>`).join("")}</select>`;
  if (f.type === "checkbox") return `<input type="checkbox" data-field="${esc(f.name)}" ${val?'checked':''}>`;
  if (f.type === "textarea") return `<textarea data-field="${esc(f.name)}" rows="2">${esc(val)}</textarea>`;
  return `<input type="text" data-field="${esc(f.name)}" value="${esc(val)}" placeholder="${f.type==='date'?'2024, Jun 2024, or 6/15/2024':''}">`;
}
function renderCard(c) {
  const a = answers[c.id] || {}; let head = "", body = "";
  if (c.section === "parse") {
    const r = c.r;
    head = `<span class="year">${esc(r.year ?? "")}</span>${esc(r.kind)}: ${esc(r.title || r.venue)}`;
    body = `<div class="src">from the resume (${esc(r.ref)}): “${esc(r.source_text)}”</div>
      <div class="fields"><span class="fname">Title</span><input type="text" data-k="title" value="${esc(a.title ?? r.title)}">
      <span class="fname">Venue</span><input type="text" data-k="venue" value="${esc(a.venue ?? r.venue)}">
      <span class="fname">Year</span><input type="text" data-k="year" value="${esc(a.year ?? r.year ?? "")}"></div>
      <div class="actions"><label><input type="radio" name="${c.id}-keep" value="1" ${a.keep===true?'checked':''}>Correct, keep</label><label><input type="radio" name="${c.id}-keep" value="0" ${a.keep===false?'checked':''}>Not a real item, drop</label></div>`;
  } else if (c.section === "add") {
    const p = c.p, vals = a.values || {};
    head = `Add a ${esc(p.kind)} to ${esc(p.screenName)}: ${esc(p.title_line)}`;
    body = `<div class="fields">${p.fields.map(f => `<span class="fname ${f.required?'req':''}">${esc(f.name)}</span>${fieldInput(c.id, f, vals[f.name] ?? f.value ?? "")}${f.note?`<span class="fnote">${esc(f.note)}</span>`:""}`).join("")}</div>
      <div class="actions"><label><input type="radio" name="${c.id}-d" value="add" ${a.decision==='add'?'checked':''}>Add to Works</label><label><input type="radio" name="${c.id}-d" value="skip" ${a.decision==='skip'?'checked':''}>Skip</label><span class="hint" id="${c.id}-req"></span></div>`;
  } else if (c.section === "review") {
    head = esc(c.p.title_line);
    body = `<div class="actions">${[["keep","Keep in Works"],["add_to_resume","Add to my resume"],["delete_by_hand","I will delete it by hand"]].map(([v,l]) => `<label><input type="radio" name="${c.id}-d" value="${v}" ${a.decision===v?'checked':''}>${l}</label>`).join("")}</div>`;
  } else {
    const r = c.a, f = r.flags, qs = [];
    const radio = (field, opts, cur, sug) => opts.map(o => `<label class="${o===sug?'sug':''}"><input type="radio" name="${c.id}-${field}" value="${esc(o)}" ${cur===o?'checked':''}>${esc(o)}</label>`).join("") + `<label><input type="radio" name="${c.id}-${field}" value="__leave" ${cur==='__leave'?'checked':''}>Leave blank</label>`;
    if (f.intl?.ask) qs.push(`<div class="q" data-f="intl"><span class="lbl">International activity?</span>${radio("intl",["Yes","No"],a.intl,f.intl.suggest)}</div>`);
    if (f.scale?.ask) qs.push(`<div class="q" data-f="scale"><span class="lbl">Scale</span>${radio("scale",SCALE_OPTS,a.scale,"")}</div>`);
    if (f.aacsb?.ask) qs.push(`<div class="q" data-f="aacsb"><span class="lbl">AACSB classification</span>${radio("aacsb",["Basic or Discovery Scholarship","Applied or Integration/Application Scholarship","Teaching and Learning Scholarship"],a.aacsb,"Basic or Discovery Scholarship")}</div>`);
    if (f.start?.ask) qs.push(`<div class="q" data-f="start"><span class="lbl">End date only (single event)</span><label class="sug"><input type="checkbox" data-k="start-leave" ${a.start==='__leave'?'checked':''}>Single event, keep as is</label><span class="hint">or it spanned a period, starting</span><input type="text" data-k="start" placeholder="2023, Sep 2023, or 9/15/2023" value="${esc(a.start && a.start!=='__leave' ? a.start : '')}"></div>`);
    if (f.teaching?.toggle) qs.push(`<div class="q" data-f="teaching"><label><input type="checkbox" data-k="teaching" ${(a.teaching ?? (r.current.teaching==='True'))?'checked':''}>Also include in Teaching and Learning Portfolio</label><span class="cur">Works now: ${esc(r.current.teaching||'unset')}</span></div>`);
    if (f.end?.ongoing) qs.push(`<div class="q" data-f="end"><span class="ongoing">No end date (ongoing).</span><input type="text" data-k="end" placeholder="End date, if it ended" value="${esc(a.end||'')}"></div>`);
    head = `<span class="year">${esc(r.year)}</span>${esc(r.title)} <span class="ctx">${esc(r.context)}</span>`;
    body = `<div class="qs">${qs.join("")}</div>`;
  }
  return `<div class="card ${isDone(c)?'done':''}" id="card-${c.id}" data-id="${c.id}"><div class="title">${head}</div><div class="oneline"><span>${esc(oneLine(c))}</span><a data-change>change</a></div><div class="body">${body}</div></div>`;
}
function render() {
  const host = $("#sections"); host.innerHTML = "";
  for (const [key, title, lede] of SECTIONS) {
    const cs = cards.filter(c => c.section === key); if (!cs.length) continue;
    const sec = document.createElement("section"); sec.dataset.section = key;
    sec.innerHTML = `<div class="sec-head"><h2>${title}</h2><span class="count" data-count></span></div><p class="lede">${lede}</p>` + cs.map(renderCard).join("");
    host.appendChild(sec);
  }
  if (DATA.warnings.length) { const w = $("#warnings"); w.hidden = false; w.textContent = "Check: " + DATA.warnings.join(" · "); }
  updateStatus();
}
function updateStatus() {
  const done = cards.filter(isDone).length;
  $("#status").textContent = `${done} decided · ${cards.length - done} undecided`;
  $("#barfill").style.width = (cards.length ? 100*done/cards.length : 0) + "%";
  $("#flt-undecided").textContent = `Undecided (${cards.length - done})`; $("#flt-decided").textContent = `Decided (${done})`; $("#flt-all").textContent = "All";
  for (const c of cards) { const el = document.getElementById("card-" + c.id); if (!el) continue; const d = isDone(c); el.classList.toggle("done", d && !el.dataset.open); el.hidden = filter === "undecided" ? d : filter === "decided" ? !d : false; }
  for (const sec of document.querySelectorAll("section")) { const vis = [...sec.querySelectorAll(".card")].filter(e => !e.hidden); sec.hidden = vis.length === 0; sec.querySelector("[data-count]").textContent = `${vis.length} shown`; }
  for (const c of cards.filter(c => c.section === "add")) { const el = document.getElementById(c.id + "-req"); if (!el) continue; const a = answers[c.id] || {}; const missing = c.p.fields.filter(f => f.required && (a.values?.[f.name] ?? "") === "").map(f => f.name); el.textContent = a.decision === "add" && missing.length ? "Still needed: " + missing.join(", ") : ""; }
}
const pending = {};
function save(cid, patch) {
  answers[cid] = Object.assign(answers[cid] || {}, patch); updateStatus();
  if (!db) return;
  const body = Object.assign({}, answers[cid], {updatedAt: new Date().toISOString()});
  pending[cid] = (pending[cid] || Promise.resolve()).then(() => db.doc("answers/" + cid).set(body)).catch(e => { console.log("save failed", cid, e.code, e.message); $("#dbwarn").hidden = false; });
}
document.addEventListener("change", ev => {
  const card = ev.target.closest(".card"); if (!card) return; const cid = card.dataset.id; const c = cards.find(x => x.id === cid); const t = ev.target;
  if (c.section === "parse") { if (t.name === cid + "-keep") save(cid, {keep: t.value === "1"}); else if (t.dataset.k) save(cid, {[t.dataset.k]: t.value.trim()}); }
  else if (c.section === "add") { if (t.name === cid + "-d") save(cid, {decision: t.value}); else if (t.dataset.field) { const values = Object.assign({}, answers[cid]?.values || {}); for (const el of card.querySelectorAll("[data-field]")) values[el.dataset.field] = el.type === "checkbox" ? el.checked : el.value.trim(); save(cid, {values}); } }
  else if (c.section === "review") { if (t.name === cid + "-d") save(cid, {decision: t.value}); }
  else { const q = t.closest(".q"); const f = q?.dataset.f; if (!f) return;
    if (f === "intl" || f === "scale" || f === "aacsb") save(cid, {[f]: t.value});
    else if (f === "start") { const leave = card.querySelector('[data-k="start-leave"]').checked; const v = card.querySelector('[data-k="start"]').value.trim(); save(cid, {start: leave ? "__leave" : v}); }
    else if (f === "teaching") save(cid, {teaching: t.checked});
    else if (f === "end") save(cid, {end: t.value.trim()}); }
});
document.addEventListener("click", ev => {
  const a = ev.target.closest("[data-change]"); if (a) { const card = a.closest(".card"); card.dataset.open = "1"; card.classList.remove("done"); return; }
  const b = ev.target.closest(".flt button"); if (b) { filter = b.id.replace("flt-", ""); for (const x of document.querySelectorAll(".flt button")) x.setAttribute("aria-pressed", String(x === b)); updateStatus(); }
});
render();
(async () => {
  db = await (window.claude?.use ? claude.use("db") : Promise.resolve(null));
  if (!db) { $("#dbwarn").hidden = false; return; }
  try { const snap = await db.collection("answers").get(); snap.docs.forEach(d => { const {updatedAt, ...rest} = d.data() || {}; answers[d.id] = rest; }); render(); }
  catch (e) { console.log("load failed", e.code, e.message); $("#dbwarn").hidden = false; }
})();
</script>
"""

def render(resume_items, proposals, audit, warnings, config):
    slim_audit = [{k: r[k] for k in ("id", "screen", "screenName", "title", "year", "context", "current", "flags")} for r in audit]
    data = {"resume": resume_items, "proposals": proposals, "audit": slim_audit, "warnings": warnings}
    css = (HERE / "page_style.css").read_text(encoding="utf-8")
    return (TEMPLATE.replace("__CSS__", css).replace("__NAME__", str(config.get("name", "")).replace("<", "&lt;"))
            .replace("__DATA_JSON__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/")))

def main(audit_dir):
    d = pathlib.Path(audit_dir); root = HERE.parent
    load = lambda p, default=None: json.loads(p.read_text(encoding="utf-8")) if p.exists() else default
    page = render(load(d / "resume_items.json", []), load(d / "proposals.json", []), load(d / "audit.json", []),
                  load(d / "normalize_warnings.json", []), load(root / "local" / "config.json", {}))
    (d / "sync_page.html").write_text(page, encoding="utf-8")
    print("wrote", d / "sync_page.html", len(page), "bytes")

if __name__ == "__main__":
    main(sys.argv[1])
```

- [ ] **Step 5: Run tests** → `python3 -m unittest tests.test_build_sync_page -v` PASS. (The escaping test asserts no raw `</script>` inside the DATA block.)

- [ ] **Step 6: Build and publish the fixture page; check it by eye**

`python3 -I scripts/build_sync_page.py local/audits/2026-10-13`, then publish with the Artifact tool, capabilities `{db: {}, user: {}}`, icon "checklist". Open it: the filter bar shows counts; ticking a parse card makes it collapse to one line and the counts move; "change" reopens it; an Add card with an empty required field and "Add" ticked shows "Still needed: …" and stays undecided; reload keeps every answer. Record the artifact URL in `local/audits/2026-10-13/after.md`.

- [ ] **Step 7: Append to `docs/runbook.md`** under "## 4." the sentence: "After publishing, give the person the link and stop; do not read answers until they say they are done."

- [ ] **Step 8: Commit**

```bash
git add scripts/build_sync_page.py scripts/page_style.css scripts/build_page.py tests/test_build_sync_page.py docs/runbook.md
git commit -m "Sync review page: parse check, Add cards as full forms, fills, Works-only review, decided filter"
```

---

### Task 9: Read answers into a plan (`scripts/read_sync_answers.py`)

**Files:**
- Create: `scripts/read_sync_answers.py`, `tests/test_read_sync_answers.py`
- Modify: `scripts/build_plan.py` (wrap the top-level code in `fill_plan(audit, decisions) -> list` and a `main`)

**Interfaces:**
- Consumes: `AUDIT_DIR/answers/answers/<cardId>.json` (ArtifactData `list` output saved with `out_dir`), `proposals.json`, `audit.json`, `resume_items.json`.
- Produces: `sync_plan.json` `{"fills": [{id, screen, screenName, title, writes: {field: value}}], "creates": [{"proposal_id", "screen", "screenName", "values": {fieldName: value}, "fields": [...the proposal's field specs...]}], "reviews": [{"works_id", "decision"}], "parse": {"kept": n, "dropped": n, "edited": [resume ids]}, "incomplete_creates": [proposal ids]}`. `build_plan.fill_plan(audit: list, decisions: {recordId: {"answers": {...}}}) -> list` keeps today's semantics (`__leave` and unchanged values dropped).

- [ ] **Step 1: Refactor `build_plan.py`** so the loop body sits in `def fill_plan(audit, dec):` returning `plan`, with `main(audit_dir)` doing the file I/O. Run `python3 -I scripts/build_plan.py local/audits/2026-10-13` and confirm the printed summary still says 44 records / 58 writes.

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_read_sync_answers.py
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
       "fill-100000000001": {"intl": "No", "scale": "National"},
       "parse-r1": {"keep": True, "title": "Edited"}, "parse-r2": {"keep": False}}

class Reader(unittest.TestCase):
    def test_plan(self):
        p = R.build_sync_plan(ANS, PROPS, AUDIT)
        self.assertEqual(p["creates"][0]["values"], {"Title": "Best Paper Finalist", "Date": "Jun 2026"})
        self.assertEqual(p["incomplete_creates"], ["a2"])
        self.assertEqual(p["reviews"], [{"works_id": "w100000000009", "decision": "delete_by_hand"}])
        self.assertEqual(p["fills"][0]["writes"], {"intl": "No"})          # scale unchanged → dropped
        self.assertEqual(p["parse"], {"kept": 1, "dropped": 1, "edited": ["r1"]})

    def test_loads_answer_files(self):
        with tempfile.TemporaryDirectory() as t:
            d = pathlib.Path(t) / "answers" / "answers"; d.mkdir(parents=True)
            (d / "add-a1.json").write_text(json.dumps({"data": {"decision": "skip", "updatedAt": "now"}}))
            self.assertEqual(R.load_answers(pathlib.Path(t)), {"add-a1": {"decision": "skip"}})

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run to verify failure** → ImportError.

- [ ] **Step 4: Implement `scripts/read_sync_answers.py`**

```python
"""Turn the page's saved answers into sync_plan.json. CLI: python3 -I scripts/read_sync_answers.py AUDIT_DIR
Answer files: AUDIT_DIR/answers/answers/<cardId>.json as saved by ArtifactData list with out_dir.
"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build_plan

def load_answers(audit_dir):
    out = {}
    for p in (pathlib.Path(audit_dir) / "answers" / "answers").glob("*.json"):
        doc = json.loads(p.read_text(encoding="utf-8")); data = dict(doc.get("data", doc)); data.pop("updatedAt", None)
        out[p.stem] = data
    return out

def build_sync_plan(answers, proposals, audit):
    creates, incomplete, reviews = [], [], []
    for p in proposals:
        a = answers.get(("add-" if p["action"] == "create" else "review-") + p["id"])
        if not a:
            continue
        if p["action"] == "create" and a.get("decision") == "add":
            values = a.get("values", {})
            if any(f["required"] and str(values.get(f["name"], "") or "") == "" for f in p["fields"]):
                incomplete.append(p["id"]); continue
            creates.append({"proposal_id": p["id"], "screen": p["screen"], "screenName": p["screenName"], "values": values, "fields": p["fields"]})
        elif p["action"] == "review" and a.get("decision"):
            reviews.append({"works_id": p["works_id"], "decision": a["decision"]})
    decisions = {k[5:]: {"answers": v} for k, v in answers.items() if k.startswith("fill-")}
    fills = build_plan.fill_plan(audit, decisions)
    parse = [(k[6:], v) for k, v in answers.items() if k.startswith("parse-")]
    edited = sorted(rid for rid, v in parse if v.get("keep") and any(x in v for x in ("title", "venue", "year")))
    return {"fills": fills, "creates": creates, "reviews": reviews, "incomplete_creates": incomplete,
            "parse": {"kept": sum(1 for _, v in parse if v.get("keep") is True), "dropped": sum(1 for _, v in parse if v.get("keep") is False), "edited": edited}}

def main(audit_dir):
    d = pathlib.Path(audit_dir); load = lambda n: json.loads((d / n).read_text(encoding="utf-8"))
    plan = build_sync_plan(load_answers(d), load("proposals.json"), load("audit.json"))
    (d / "sync_plan.json").write_text(json.dumps(plan, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"fills={len(plan['fills'])} creates={len(plan['creates'])} incomplete={plan['incomplete_creates']} reviews={len(plan['reviews'])} parse={plan['parse']}")

if __name__ == "__main__":
    main(sys.argv[1])
```

- [ ] **Step 5: Run all tests** → `python3 -m unittest discover -s tests -v` PASS (Review Focus item 5 is `incomplete_creates`).

- [ ] **Step 6: Append to `docs/runbook.md`** under "## 5. Apply":

```markdown
- Load ArtifactData; `list` collection `answers` with `out_dir local/audits/<date>/answers`.
- `python3 -I scripts/read_sync_answers.py local/audits/<date>`; tell the person about any `incomplete_creates` and stop if they want to fix them first.
- Fills: install `scripts/apply_record.js` once, then one record per `javascript_tool` call after `navigate` + 3 s, batches of 4 (`CLAUDE.md`, "Writing data").
- Creates: `scripts/create_record.js` recipe (below). One record at a time for the first of each screen; verify on the list view.
- Reviews: list `delete_by_hand` items in `after.md` for the person; never delete.
- Re-extract, rerun `build_audit.py`, write `after.md` with before/after counts and the page URL.
```

- [ ] **Step 7: Commit**

```bash
git add scripts/read_sync_answers.py scripts/build_plan.py tests/test_read_sync_answers.py docs/runbook.md
git commit -m "Read sync page answers into a plan; drop incomplete creates"
```

---

### Task 10: The create recipe (`scripts/create_record.js`), Honors first

Needs the person at the keyboard. No unit tests; evidence is the new record on the list view.

**Files:**
- Create: `scripts/create_record.js`
- Modify: `CLAUDE.md` ("Creating records" section), `screens.md`, `docs/runbook.md`

**Interfaces:**
- Consumes: `sync_plan.json` `creates[]` entries (`screen`, `values`, `fields`), `screens/forms.json` `add_url`.
- Produces: in-page `prepareCreate(FIELDS, VALUES)` that sets every combo and checkbox and returns the list of text/date-text fields still to type as `"<prefix> <value>"` lines; `finishCreate()` clicks Save, waits, and returns `SAVED <newRecordId>` (read from the URL or the list's newest `data-dm-id`) or `NOT SAVED`.

- [ ] **Step 1: Write `scripts/create_record.js`**

```javascript
// Create one Works record on an Add New form. Install like apply_record.js:
//   run this file, then localStorage.__worksCreate = JSON.stringify({p: prepareCreate.toString(), f: finishCreate.toString()})
// Per record: navigate to the screen's add_url, wait 3 s, run prepareCreate(FIELDS, VALUES) -> it sets combos/checkboxes/month
// comboboxes and returns the text fields left to TYPE (titles, years, days, free text), as "prefix value" lines. Type each one
// (throwaway screenshot, click the input whose id starts with prefix, type, Tab), then run finishCreate().
async function prepareCreate(FIELDS, VALUES) {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"];
  const fire = (el, types) => types.forEach(t => el.dispatchEvent(new MouseEvent(t, {bubbles: true, cancelable: true, view: window})));
  const shown = i => i.parentElement.parentElement.innerText.trim();
  async function setCombo(prefix, text) {
    const i = document.querySelector(`input[id^="${prefix}"]`); if (!i) throw new Error("no input " + prefix);
    i.scrollIntoView({block: "center"}); i.focus(); fire(i, ["pointerdown","mousedown","pointerup","mouseup","click"]); await sleep(400);
    const opt = [...document.querySelectorAll("[role=option]")].find(o => o.textContent.trim() === text);
    if (!opt) throw new Error(`option '${text}' not found for ${prefix}`);
    opt.click(); await sleep(400);
    if (!shown(i).split("\n").includes(text)) throw new Error(`${prefix} shows '${shown(i)}', wanted '${text}'`);
    return `${prefix} ${text}`;
  }
  const toType = [], done = [];
  for (const f of FIELDS) {
    const v = VALUES[f.name]; if (v === undefined || v === null || v === "") continue;
    if (f.type === "combo") done.push(await setCombo(f.prefix, v));
    else if (f.type === "checkbox") { const c = document.querySelector(`input[id^="${f.prefix}"]`); if (c.checked !== !!v) c.click(); done.push(`${f.prefix} ${!!v}`); }
    else if (f.type === "date") {
      const m = String(v).match(/^(?:([A-Za-z]+)\.?\s+)?(?:(\d{1,2}),?\s+)?(\d{4})$/) || String(v).match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
      if (!m) throw new Error("date not understood: " + v);
      let month = null, day = null, year;
      if (String(v).includes("/")) { month = MONTHS[+m[1]-1]; day = m[2]; year = m[3]; } else { year = m[3]; day = m[2] || null; if (m[1]) month = MONTHS.find(x => x.toLowerCase().startsWith(m[1].toLowerCase().slice(0,3))); }
      if (month) done.push(await setCombo(`_dtm_${f.prefix}-`, month));
      toType.push(`_dty_${f.prefix}- ${year}`); if (day) toType.push(`_dtd_${f.prefix}- ${+day}`);
    } else toType.push(`${f.prefix} ${v}`);
  }
  return ["SET " + done.join(" ; "), ...toType.map(t => "TYPE " + t)];
}
async function finishCreate() {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const save = [...document.querySelectorAll("button")].find(b => /^save$/i.test(b.textContent.trim())); if (!save) throw new Error("no Save button");
  save.click(); await sleep(3500);
  if (!document.body.innerText.includes("Record has been saved")) return "NOT SAVED";
  const rows = [...document.querySelectorAll("[role=row][data-dm-id]")].map(r => r.getAttribute("data-dm-id"));
  return "SAVED newest " + (rows[0] || "unknown");
}
```

- [ ] **Step 2: Dry run on Honors with the first award from `sync_plan.json`** (after Tasks 7–9 produced it from the person's ticks): navigate to the Honors `add_url`, wait 3 s, run `prepareCreate(FIELDS, VALUES)`. Expected: a `SET …` line listing combos and the month, and `TYPE …` lines for the title and year. For each TYPE line: throwaway screenshot (scale 0.1), `find`/JS to locate `input[id^="<prefix>"]`, `scrollIntoView`, `left_click`, `type` the value, `key` Tab. Then `finishCreate()` → `SAVED newest <id>`.

- [ ] **Step 3: Verify on the list view** with all columns: the new record shows the title, organization, and date exactly as on the card. If a typed field is blank, the typing was dropped: repeat with a fresh throwaway screenshot before each click. Record what worked in `CLAUDE.md` under a new "Creating records" section (URL pattern, the SET/TYPE split, which fields had to be typed).

- [ ] **Step 4: Create the remaining ticked honors**, one per `browser_batch`, verifying each. Then one presentation and one service record if any are ticked, to prove the other forms. Any new quirk goes into `screens.md`'s field-type table.

- [ ] **Step 5: Append the create recipe to `docs/runbook.md`** under "## 5. Apply" (the SET/TYPE sequence from Step 2 in five lines).

- [ ] **Step 6: Commit**

```bash
git add scripts/create_record.js CLAUDE.md screens.md docs/runbook.md
git commit -m "Create recipe for Add New forms, verified on Honors"
```

---

### Task 11: End-to-end run on the maintainer's record (this becomes the January update)

**Files:**
- Modify: `docs/runbook.md`, `CLAUDE.md`, `screens.md` as findings dictate
- Produce (not committed): `local/audits/<date>/` full set, `after.md`, saved Annual Activity Report

- [ ] **Step 0: Persistence and screen checks.** Tick three cards, reload the page, and confirm the ticks and the Undecided/Decided counts survive. Confirm `screens_seen.json` was written and the page's "Check:" line lists only screens the catalog lacks.
- [ ] **Step 1: Run the skill from a fresh session**: open `~/repos/UMNWorks` in Claude Code, say "Update my Works record from my resume." Follow `docs/runbook.md` exactly; where it is wrong or missing, fix the runbook before continuing (that is the point of this task).
- [ ] **Step 2: Decide on the page**, including at least one of each: a dropped parse item, an Add with a filled-in title, a Skip, a fill, and a Works-only review of each kind.
- [ ] **Step 3: Apply and verify** per the runbook. Re-extract. Write `after.md` with the before/after table in the style of `local/audits/2026-10-13/after.md`, the page URL, the `delete_by_hand` list, and resume edits suggested from `add_to_resume` reviews.
- [ ] **Step 4: Run the Annual Activity Report** for the year (Reports guide: Run Reports → Annual Activity Report, date range Jan 1–Dec 31) and save the file under `local/audits/<date>/annual-activity-report.<ext>`; add the recipe to `docs/runbook.md` "## 6. Report".
- [ ] **Step 5: Run all tests and commit the doc fixes**

```bash
python3 -m unittest discover -s tests -v
git add docs CLAUDE.md screens.md scripts && git commit -m "Runbook fixes from the first end-to-end run"
```

---

### Task 12: Fresh history and GitHub push

- [ ] **Step 1: Confirm nothing personal is tracked**: `python3 -m unittest tests.test_repo_hygiene -v` PASS, and `git ls-files | grep -c '^local/'` prints `2` (README and example config only).
- [ ] **Step 2: Keep the old history aside and start fresh**

```bash
cd <repo>
mv .git ../UMNWorks-private-history.git
git init -b main
git add -A
git commit -m "UMN Works sync skill for Carlson faculty"
```

- [ ] **Step 3: Create the GitHub repo and push** (the person chooses public or private; both are fine because `local/` is excluded):

```bash
gh repo create UMNWorks --source . --private --push
```

- [ ] **Step 4: Verify from a clean clone** in the scratchpad: `git clone <url> /tmp-scratch/UMNWorks-check`, open it in Claude Code, confirm the `umn-works` skill is listed, run `python3 -m unittest discover -s tests -v` → PASS, and confirm `local/` holds only the two tracked files.

---

### Task 13: First colleague run (with the maintainer present)

- [ ] **Step 1: Before the session**: colleague has Claude Code (desktop Code tab is enough) and the Chrome extension, is signed in to Works, and has their resume file. Try the desktop app's Cowork tab first for ten minutes; if the skill cannot drive the extension there, switch to the Code tab and note the result in `README.md`.
- [ ] **Step 2: Watch the setup and Works-read steps.** The page's "Check:" line must be empty or list only screens the colleague genuinely lacks; otherwise fix `screens.md`/`screen_kinds.json`.
- [ ] **Step 3: Let the colleague drive the page alone** and note every point where they ask what a card means; those become copy changes in `build_sync_page.py`.
- [ ] **Step 4: Apply with the colleague watching**, one record per screen type first.
- [ ] **Step 5: Commit the fixes and push**

```bash
python3 -m unittest discover -s tests -v
git add -A && git commit -m "Fixes from the first colleague run" && git push
```
