# Works field audit and fix (2026-10-13)

## Purpose

Bring every existing record in UMN Works (Watermark Faculty Success, hosted at
digitalmeasures.com) up to date on five fields, with mbarach deciding each value
through an artifact rather than navigating Works by hand. Build the folder, docs,
and catalog so the January yearly update reuses them. The CV sync is a later
design and is out of scope here.

## Scope

- Only records that already exist in Works. Nothing is added or deleted.
- All manual-entry screens that hold at least one record. Imported screens
  (Scheduled Teaching, SPA grants, PeopleSoft, Student Rating, Promotion Dates)
  are read-only in Works and skipped. Profile screens (Personal and Contact
  Information, Biography) are skipped.
- Work happens in the original view, not the new Faculty Success view. The
  original list view can show every field as a column, which is what the audit
  needs. The new view's profile page formats records as citations and hides the
  field values. Edit forms are the same in both.

## The five fields

| Field | Flag as incomplete when | Options offered |
|---|---|---|
| AACSB Classification | empty, on screens that have it | the screen's own dropdown values, plus "leave as is" |
| Start date | empty, on screens with a date range | year, month/year, or full date typed by mbarach |
| End date | never flagged; empty means ongoing | shown so a finished item can get an end date |
| Related to Teaching and Learning | cannot be told from "not applicable"; shown as a toggle on every record that has the checkbox | checked / unchecked |
| International (Scale, or the screen's equivalent) | empty, on screens that have it | the screen's own dropdown values, plus "leave as is" |

The exact field name and options differ by screen. `screens.md` records the
mapping per screen and is filled in during this audit.

## Flow

1. **Extract.** For each in-scope screen: open the list view, turn on every
   column with Select Columns, scrape all rows with JavaScript into
   `audits/2026-10-13/raw/<screen>.json`. Also save record IDs so the apply
   step can open records by URL.
2. **Audit.** A script reads the JSON and writes `audits/2026-10-13/audit.json`,
   one entry per record per incomplete field.
3. **Artifact.** A private page grouped by screen. Each entry shows the title
   and year, then only its incomplete fields as radio buttons or a date input.
   Shared database so ticks persist; Claude reads them with ArtifactData.
4. **Apply.** Per screen, per field type, a tested browser sequence (see
   CLAUDE.md). Each write is verified on the page before save and confirmed
   by the "Record has been saved" banner. Re-extract afterward and report
   before and after counts.

## Non-goals

- No cron or unattended edits. Every write follows a tick from mbarach.
- No CV comparison. The extract JSON is kept so that design can use it.
- No changes in the new Faculty Success view.

## Deliverables

- `~/repos/UMNWorks` (git): `CLAUDE.md`, `screens.md`, `scripts/`,
  `audits/2026-10-13/`, this spec.
- Skill `~/.claude/skills/umn-works-update/SKILL.md` pointing at the folder.
- Memory note reduced to a pointer at the folder.
