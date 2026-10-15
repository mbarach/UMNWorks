# UMNWorks

Tools and notes for keeping a Carlson faculty member's record in UMN **Works** current. Works is
the University of Minnesota's name for Watermark's **Faculty Success** product, hosted at
`digitalmeasures.com` (Digital Measures is the vendor's old name, still in the URL). Updated at
least once a year, in January, for the annual activity report. The skill that drives a run is
`.claude/skills/umn-works/SKILL.md`; the step-by-step procedure is `docs/runbook.md`.

## Ground rules

- **Nothing is written to Works without an explicit tick on the review page or an instruction
  from the person running it.** Read first, present choices (an artifact page), then apply only
  what they chose. No cron, no unattended edits, no automated deletions.
- Everything about one person (config, audits, answers, transcripts, notes) lives in `local/`,
  which git ignores. Keep every run under `local/audits/YYYY-MM-DD/` so years can be compared.
- Open Works in a tab the extension creates; a tab the person opened themselves may not be
  visible to it. The URLs are below.
- This folder is a git repo shared with colleagues. Commit code and docs after each session;
  never anything under `local/`.

## Where things are

| Path | What |
|---|---|
| `screens.md` | Catalog of every Works screen: id, which audited fields it has, option values |
| `screens/forms.json` | Field list, input id prefixes, and options of each Add New form (captured in the browser) |
| `scripts/build_audit.py` | Parses `local/audits/<date>/raw/extract_*.txt` into `records.json` and `audit.json` |
| `scripts/normalize.py`, `match.py`, `rules.py` | Works records → items, matching against the resume, guideline rules → proposals |
| `scripts/build_sync_page.py` | Renders the review page (`sync_page.html`); `build_page.py` is the older field-audit-only page |
| `scripts/read_sync_answers.py` | Reads the page's answers into `sync_plan.json` |
| `scripts/apply_record.js`, `create_record.js` | In-page helpers for editing and creating records |
| `scripts/scrape_list.js` | The in-page list scraper (reference copy) |
| `scripts/fetch_guidelines.sh` | Refreshes `docs/guidelines/*.txt` from UMN's Google Docs |
| `docs/item-schema.md` | The one item schema and the rules for reading a resume into it |
| `docs/specs/`, `docs/plans/` | Design specs and implementation plans |
| `local/` | Personal data (see `local/README.md`); `local/config.json` names the person, resume, and rules |

## URLs

- Activities menu: `https://www.digitalmeasures.com/login/umn/faculty/app/activities/instruments/896?_s=0`
- A screen's list: `.../activities/instruments/896/screens/<screenId>?_s=0`
- A record's edit form: `.../activities/instruments/896/screens/<screenId>/records/<recordId>?_s=0`
- New view home: `.../app/home/instruments/896?fxp=true&_s=0`. The new Faculty Success view is
  the only supported view (UMN's full rollout was Fall 2026).

## Works conventions (from UMN's guides)

Guides index: https://works.umn.edu/guides-training. The Quick Start Guide (Google Doc
1GClloQM_E7iKP0kmy3F8cbcgdGrmFlNI) sets the date convention:

- start date only = ongoing or current
- end date only = a single event (do not enter the same date twice)
- both dates = an activity that spanned a period

It also says every record needs a title and a date, and asks that international and
outreach/extension/public-engagement activities be flagged. It does not mention the AACSB
classification or the "Related to Teaching and Learning" checkbox.

In-form help texts (Presentations form, read 2026-10-13):

- **Related to Teaching and Learning?** "This record will print to the Annual Activity Report and
  other aggregate reports. Do you also want to include this record on your Teaching and Learning
  Portfolio?" So the box is a portfolio-inclusion flag, not a content classification.
- **AACSB Classification.** Basic or Discovery: new knowledge or methods, intended to impact theory
  or knowledge of business. Applied or Integration/Application: synthesizes or applies existing
  knowledge or technology, intended to impact practice. Teaching and Learning: develops teaching
  content and methods, intended to impact the teaching of business.
- **Was/is this an international activity?** has no help text and no UMN definition was found
  (works.umn.edu, web search 2026-10-13). The International Engagement Summary screen asks "In what
  countries did these activities take place?", which reads as location-based. Default rule (set
  per person in `local/config.json`): Yes only when the activity took place outside the US;
  virtual events are No.

## The new Faculty Success view (verified 2026-10-15)

- Screen ids, record ids, record URLs, input id prefixes, and the list grid are the same as in the
  original view. The list recipe and the edit helper below work unchanged.
- **Save** on an edit form returns to the screen list within a second and shows no "Record has
  been saved" banner. The helper treats leaving the `/records/<id>` URL as saved; confirm on the
  list where the row's "Last Saved" cell shows today's date.
- **Add New** opens an "Add Activity" drawer on the list page (no new URL). After it opens, make
  one real click inside it (the heading, via the `computer` tool); until then script-dispatched
  pointer events do not open its comboboxes. Opening the Country combobox from script hangs the
  renderer for a long time; skip it.
- Field lists and options for each Add New form are in `screens/forms.json`, captured with
  `scripts/capture_form.js`.

## Reading data: the list view with all columns

1. Open the screen's list URL. Click **Select Columns**, then **Select All**, then **Update**.
   Column choices persist per screen for the account. These are custom elements (`WM-BUTTON`,
   `SPAN`), not `<button>`, so find them by text over `document.querySelectorAll('*')` leaf nodes.
2. Rows are `[role=row][data-dm-id]`; cells are `[role=gridcell]` whose text is
   `"<value>, <Column Name>, , column N of M, row R of T"`. Blank cells say `Empty`. Match the
   column name against the `[role=columnheader]` texts (longest first; some names contain commas).
3. The extension's `javascript_tool` truncates a string result at about 1 KB but returns an
   **array** of up to roughly 100 items nearly untruncated. Return one string per row, keep each
   under about 1,200 characters (skip author sub-columns, abstracts, audit-trail columns, and
   `Day,` parts; shorten long headers), and use `Field: value ; Field: value` separators. Avoid
   `key=value&`-looking text and any `?...=` in results, or the tool blanks the item as
   "Cookie/query string data".
4. Paste the arrays into `local/audits/<date>/raw/extract_*.txt` in the documented format, then run
   `python3 -I scripts/build_audit.py local/audits/<date>`.

## Writing data: the edit form

**Preferred recipe (2026-10-13, 44 records across 10 screens):** `scripts/apply_record.js`.
Install it once per browser profile by running the file's text in the page and then
`localStorage.__worksApply = applyRecord.toString()` (localStorage persists across navigations
on digitalmeasures.com). Then per record, in one `browser_batch`:
`navigate` to the record URL → `wait` 3 s → `javascript_tool` with
`const f=new Function("return "+localStorage.__worksApply)(); "<id> " + await f({intl:"No", scale:"International", teaching:true})`.
The helper opens each combobox by dispatching pointer/mouse events on the input, clicks the
`[role=option]` whose text matches exactly, verifies the shown value, clicks Save, waits 3.5 s and
reports `SAVED`/`NOT SAVED`. It throws before Save if any field does not show the requested value.
Keep batches to **4 records**: 8 records finished but the tool's response timed out.
Avoid `key=value` text in anything returned to the tool (it blanks the result as "query string
data"); the helper returns `prefix value` pairs for that reason.

Input id prefixes (the suffix is a per-page UUID): `_international-` (Yes/No), `_scope-` (Scale:
International/National/Regional/State/Local), `_classification-` (AACSB), `_related_teaching-`
(checkbox), dates `_dtm_start-`/`_dtd_start-`/`_dty_start-` and `_dtm_end-`/`_dtd_end-`/`_dty_end-`
(month combobox, day text, year text; the same ids serve "Date Advising Began/Ended"), single
`_dtm_date-`/`_dtd_date-`/`_dty_date-` on Presentations and Media.

**Text fields (year, day, titles) do not commit from script.** Setting `.value` through the native
setter plus input/change events shows the value but Works drops it on Save unless a combobox on
the same form changes afterwards. Type them for real: `navigate`, `wait`, JS `scrollIntoView`,
**throwaway screenshot (scale 0.1)**, `left_click` on the field, `type`, `key` Tab, then Save.
Without the throwaway screenshot the first click or key after a navigation is dropped.

Keyboard path (kept for reference): JS `focus()` on the combobox input, throwaway screenshot,
`key` ArrowDown (opens the list, first option highlighted), `key` Return; clicking the field
instead pre-highlights the first option, so ArrowDown then goes one too far. `form_input` and
`computer type` do not commit a value into these comboboxes.

Save: click the button whose text is "Save"; in the new view the page returns to the list (see above). Field types met so far and how to set them: `screens.md`. Always test one
record of a new field type and verify on the list view before bulk runs.

## Creating records: the Add Activity drawer (recipe established 2026-10-15)

`scripts/create_record.js` holds `prepareCreate(FIELDS, VALUES)` and `finishCreate()`; install both into
`localStorage` as its header says. Per record:

1. `navigate` to the screen's list URL, `wait` 3 s; from script click the leaf element whose text is
   "Add New"; `wait` 3.5 s (the drawer opens on the same URL).
2. **Wake the drawer**: throwaway `screenshot` (scale 0.1), then one real `left_click` on the
   "Add Activity" heading (about x 406, y 34 at 1291 px wide). Without it the drawer's comboboxes
   ignore script events; sometimes a second click is needed, so check the first combobox opened.
3. `javascript_tool`: `prepareCreate(FIELDS, VALUES)` with the proposal's `fields` and the card's
   `values`. It sets comboboxes, checkboxes and month comboboxes and returns `SET …` plus one
   `TYPE <prefix> <value>` line per text field (titles, organizations, years, days).
4. For each TYPE line, **do not click by coordinates** (the drawer scrolls between measuring and
   clicking, and the text lands in the wrong field). Instead: `javascript_tool` to `scrollIntoView`
   and `focus()` the input whose id starts with the prefix, then `computer` `type` the value, then
   `key` Tab. A throwaway screenshot once before the first keystroke is enough.
5. `javascript_tool`: read every typed input's `.value` back and compare before saving.
6. `computer` `key` Escape (closes any open dropdown list; it does not close the drawer), then
   `javascript_tool`: `finishCreate()` clicks the drawer's Save, waits for the drawer to close, and
   returns `SAVED newest <recordId>` (the new row's id on the list) or `NOT SAVED …` with the Save
   button's coordinates; in that case `left_click` Save for real and re-check the list. Never
   close a list or blur a field from script in the drawer: it hung the renderer for 45 s.
7. Confirm the row's values on the list view with all columns (Select Columns → Select All →
   Update persists per screen). Cell text is `<value> , <Column>, …`; split on `" , "` with the
   column name, not on the first comma, because values contain commas.

Lesson from the first create (2026-10-15): text typed into the wrong field cannot be cleared by
select-all + Backspace alone; Works keeps the earlier text unless a combobox on the same form
changes afterwards (toggle one and set it back), then Save.

Required fields show a red asterisk on the drawer that the id capture does not always detect;
`screens/forms.json` is corrected by hand when one is seen (Honors: name, organization,
Awarded/Nominated, UMN award yes/no, year).

## The review page

`build_sync_page.py` makes a page with the `db`, `user`, and `downloads` capabilities. Each decision is stored at
`answers/<cardId>`; card ids are `parse-<resumeId>`, `add-<proposalId>`, `fill-<recordId>`,
`review-<proposalId>`; `"__leave"` means the person chose to leave a field blank. Read them back
with `ArtifactData` (`list` on collection `answers`, saved under `local/audits/<date>/answers/`).
The page URL for a run is recorded in that run's `after.md`.
