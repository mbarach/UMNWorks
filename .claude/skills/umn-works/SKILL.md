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
