# Shared Works sync skill (design)

Status: **for mbarach's review.** Written 2026-10-15. Supersedes
`2026-10-13-cv-sync-design-draft.md` (kept for the record; its open questions are answered here).

Decisions taken in conversation on 2026-10-15:

- Carlson School only. Other colleges may have different Works screens; out of scope.
- The new Faculty Success view is the only view from now on. Every browser recipe is re-tested
  there before January; the original view is not supported.
- Distribution is this GitHub repo. A colleague clones it, opens it in Claude Code, and the
  project skill loads. A plugin marketplace is not needed now; if colleagues want "install once,
  update from anywhere", a `.claude-plugin/marketplace.json` can be added to this same repo
  later without changing anything else.
- It runs on the machine of whoever is driving it, against whatever Works account is logged in
  to the browser. Who that is (the faculty member, or someone running it for them with a valid
  login) is not the tool's concern; the page always names the Works account it read.
- Scope for the first shared version: publications, presentations, honors, service, plus the
  field audit built on 2026-10-13 (AACSB, dates, international, scale, portfolio flag).

## Purpose

A Carlson faculty member hands Claude their resume in whatever form they keep it, and Claude
brings their Works record into line with it under UMN's Works guidelines: it proposes new records,
fills gaps on existing ones, flags Works items the resume does not mention, and audits the fields
the college wants set. Every change is shown on one artifact page with ticks, dates, and
dropdowns, and nothing is written to Works until the person ticks it.

## Who uses it and what they need

- A Carlson faculty member with Claude Code (desktop app's Code tab is enough; no terminal
  needed), the Claude in Chrome extension, and a browser signed in to Works. Chrome, Edge, or
  Brave all work with Claude Code per its docs.
- A claude.ai account on a paid plan so the artifact page can store their answers. Fallback if
  the page cannot store answers: the page offers a "Download answers" file that the skill reads.
- Their resume as a file (PDF, Word, LaTeX, text, or a URL). No required format.

## Layout of the shared repo

```
UMNWorks/
  .claude/skills/umn-works/SKILL.md     the skill (loads for anyone who clones)
  CLAUDE.md                             ground rules for Claude (generic, no personal data)
  README.md                             for colleagues: what it does, what you need, first run
  screens.md                            Carlson screen catalog: ids, fields, option values
  docs/guidelines/                      UMN guides as text + digest; refresh script
  docs/specs/                           design docs
  scripts/                              extraction, matching, rules, page builder, apply helper
  local/                                GITIGNORED: everything about one person (see below)
```

`local/` holds `config.json` (name, resume path, website path if any, international rule),
`audits/<date>/` (raw extracts, records, proposals, answers, after-report), and `sessions/`
(transcripts). It never enters git. mbarach's existing `audits/2026-10-13/` and `docs/sessions/`
move there. The current repo history contains that data, so the GitHub repo is started from a
fresh history (a new `git init` on the cleaned tree); the current `.git` is kept locally as
`UMNWorks-private-history` for reference.

`screens.md` is scrubbed of record ids and names; data-quality notes about a person's own records
go to `local/notes.md`.

The personal skill at `~/.claude/skills/umn-works-update/` becomes a two-line pointer ("cd to the
repo; the project skill does the work") so it keeps triggering when mbarach is elsewhere.

## The January flow (what the skill does)

1. **Setup check.** Confirm the repo, the extension, a Works tab in the new view, and
   `local/config.json`. On first run, ask for name, resume path, and whether international means
   "took place outside the US" (the default) or something else. Download the guidelines if older
   than 90 days (`scripts/fetch_guidelines.sh`).
2. **Read Works.** Discover the screens from the Activities menu at runtime, compare with
   `screens.md`, and warn if they differ. Extract every manual-entry screen with all columns
   (existing recipe, re-verified in the new view). Save under `local/audits/<date>/raw/`, build
   `records.json`.
3. **Read the resume.** Claude reads the file and writes `local/audits/<date>/resume_items.json`
   in the shared item schema: `{kind, title, venue, year, month?, people?, place?, status?,
   source_text}` with `kind` in publication, working-paper, presentation, honor, service, grant,
   position, education. There is no format-specific parser; the model is the parser and the page
   is the check. Each item keeps the resume line it came from so the person can verify it.
4. **Normalize and match** (`scripts/normalize.py`, `scripts/match.py`). Works records become the
   same schema. Within a kind and year (±1 for publications), pair by normalized title or venue
   similarity, with an alias table for venues resumes abbreviate (SRF, P&O, ISC, EGOS, SMS, AOM,
   NBER, SMJ, Org Sci, ...). Buckets: matched, resume-only, Works-only. Output `matches.json`.
5. **Apply the rules** (`scripts/rules.py`, each rule citing its guide line) to produce
   `proposals.json`: which screen a resume-only item goes to, its required fields, the date
   convention (single event = end date only), the international flag by place, AACSB default by
   kind (research presentations and publications = Basic or Discovery), author annotation
   reminders for multi-author papers, and the field-audit gaps on matched records.
6. **The page** (`scripts/build_sync_page.py`), one artifact with four sections and a progress
   count: *Check the resume parse* (edit or drop items), *Add to Works*, *Fill gaps* (matched
   records; the 2026-10-13 audit cards), *Only in Works* (keep / add to resume / I will delete by
   hand). Same tick-and-store pattern as today; answers stored per item.

   **Decided vs undecided.** The page opens showing only undecided cards, with a filter bar
   "Undecided (n) · Decided (m) · All" and the counts updating as ticks land. A decided card
   collapses to one line (what was chosen, with a "change" link) so the person can see at a
   glance what is done. Counts and filtering are driven by the stored answers, not by page
   state, so they survive a reload.

   **The card is the approval, and it is the whole form.** An *Add to Works* card says what it
   proposes ("Add a presentation", "Add a journal article", "Add an honor") and shows every field
   that screen's Add New form has, in the same order, with the same dropdown options Works
   offers (taken from `screens.md`). Values the resume supplied are prefilled; everything else is
   blank for the person to fill, dates included, with the date convention printed beside the
   date fields. Required fields are marked, and the card cannot be ticked "Add" until they are
   filled. The person can also change the target screen, edit any prefilled value, or tick
   "Skip". Nothing is created from a card that is not ticked, and nothing is created with a
   field value the person did not see on the card.
7. **Apply ticked answers only.** Fills through `apply_record.js` (new-view version). Creates
   through an "Add New" recipe per screen that fills exactly the card's values, tested one record
   at a time starting with Honors. Deletions are never automated. Verify every save on the list
   view and show the person the new record's values on the after-report.
8. **Report.** `local/audits/<date>/after.md` with before and after counts, and a list of resume
   edits the person may want (text, applied by hand).

## Answers to the draft's open questions

1. The resume is the master. A website is an optional extra input, not a source of truth.
2. First version: publications, presentations, honors, service, plus the field audit. Teaching
   and SPA grants come from UMN imports and are not synced. Advising is mixed: Committee
   Advising is partly imported from PeopleSoft, while My Advisees and Other Student Advising
   are manual. Advising records get the field audit (dates, flags) but are not created from the
   resume in the first version. **Open question:** whether to add resume-driven creation of
   advising records later.
3. Presentations without titles in the resume: the page asks for a title per item, with the
   venue prefilled as the default.
4. One-way. Works-only items are listed for the person; resume edits are suggested as text.
5. Yes: the skill ends by running the Annual Activity Report for the year and saving it under
   `local/audits/<date>/`.
6. (new) Multi-user: per-person data in gitignored `local/`; shared code and catalog in git;
   fresh history before the first push.

## Work to do, in order

1. Scrub and restructure the repo: `local/`, `.gitignore`, move personal data, scrub
   `screens.md`, write `README.md`, generic `CLAUDE.md`, move the skill into `.claude/skills/`.
   Fresh git history; push to GitHub.
2. Re-verify in the new view: list extraction, the edit-form helper, text-field typing, Save.
   Record differences in `screens.md`.
3. `fetch_guidelines.sh`, `normalize.py`, `match.py`, `rules.py` with tests on mbarach's data.
4. Resume reading: schema, prompt text in the skill, worked example on `cv.tex` and on the PDF.
5. `build_sync_page.py` and the answers reader.
6. "Add New" recipe, Honors first (mbarach's four awards are the test).
7. End-to-end run on mbarach's record as the January 2027 update. Then one colleague's first run
   with mbarach present, to catch what the docs could not: Cowork vs Code tab, screen differences.

## Where it runs

Claude Code is required: the desktop app's Code tab (a window, no terminal) or the CLI. The
scripts run locally in Python and the browser is driven through the Claude in Chrome extension.
claude.ai in a browser alone cannot run it. The desktop app's Cowork tab is untested for this
(official docs confirm skills and the Chrome extension there, but not a skill driving the
extension); it is the first thing to try on a colleague's first run.

## Out of scope

Other colleges; running for someone else; automated deletions; the original view; cron.
