# Runbook

The skill (`.claude/skills/umn-works/SKILL.md`) names the steps; this file has the details.
Browser recipes are in `CLAUDE.md`; screen fields in `screens.md` and `screens/forms.json`.

## 1. Setup
- `local/config.json` exists (copy `local/config.example.json`; ask for name, resume path,
  international rule). Never ask for passwords; the person signs in to Works themselves.
- `docs/guidelines/fetched-on.txt` is within 90 days, else run `scripts/fetch_guidelines.sh`.
- One ToolSearch call loads: tabs_context_mcp, tabs_create_mcp, navigate, computer,
  javascript_tool, read_page, browser_batch, find.
- Create a tab; navigate to the Activities menu URL in `CLAUDE.md`. If it lands on the UMN sign-in
  page, ask the person to sign in (with Duo) in that tab and wait. Confirm the header shows the
  name in `config.json`; stop if not.

## 2. Read Works
- Discover screens: on the Activities page, collect every screen link `(name, screenId)`; diff
  against `screens.md`; save the list as `local/audits/<date>/screens_seen.json`. Unknown screens
  go to the page's "Check:" line.
- Extract each manual screen with the list recipe in `CLAUDE.md` into `raw/extract_*.txt`.
- `python3 -I scripts/build_audit.py local/audits/<date>` then
  `python3 -I scripts/normalize.py local/audits/<date>`.

## 3. Read the resume
- Open the file from `config.json` with the Read tool (PDF pages in ranges of 20; a .docx via
  `textutil -convert txt` on macOS or `pandoc`; a .tex as text; a URL via WebFetch). Read the
  whole document before writing anything.
- Write `local/audits/<date>/resume_items.json` following `docs/item-schema.md`, section by
  section: publications, working papers, presentations, honors and grants, service, positions,
  education. Keep `source_text` verbatim and `ref` as the line or page.
- If `config.json` names a website, read it too and add only items the resume lacks (`ref` =
  the page URL).
- `python3 -I scripts/items.py local/audits/<date>/resume_items.json`; fix until `ok`.
- Print a count per kind in chat so the person can sanity-check before the page is built.

## 4. Match, rule, page
- `python3 -I scripts/match.py local/audits/<date>`; `python3 -I scripts/rules.py local/audits/<date>`;
  `python3 -I scripts/build_sync_page.py local/audits/<date>`.
- Publish `sync_page.html` with capabilities `{db: {}, user: {}, downloads: true}` (load
  `artifact-capabilities` first); `downloads` powers the "Download answers" fallback. Record the URL in `local/audits/<date>/after.md`. After publishing, give the person the
  link and stop; do not read answers until they say they are done.

## 5. Apply
- Load ArtifactData; `list` collection `answers` with `out_dir local/audits/<date>/answers`.
- `python3 -I scripts/read_sync_answers.py local/audits/<date>`; tell the person about any
  `incomplete_creates` (ticked Add with a required field still blank) and stop if they want to
  fix them first.
- Fills: install `scripts/apply_record.js` once, then one record per `javascript_tool` call after
  `navigate` + 3 s, batches of 4 (`CLAUDE.md`, "Writing data").
- Creates: the drawer recipe in `CLAUDE.md` ("Creating records"), one record per `browser_batch`,
  fields typed into script-focused inputs, values read back before `finishCreate()`. Verify each new
  row on the list view before the next.
- Reviews: list `delete_by_hand` items in `after.md` for the person; never delete. Also list the
  `add_to_resume` items and the step-1 edits (`parse.edited`) under "Resume edits you may want".
- Re-extract, rerun `build_audit.py`, write `after.md` with before/after counts and the page URL.
