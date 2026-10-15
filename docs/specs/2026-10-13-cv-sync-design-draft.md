# Works ⇄ CV sync (draft for review)

Status: **draft, not approved.** Written 2026-10-13 after the first field audit so the January
update can start from a design rather than a blank page. mbarach reviews and edits this before any
code is written; open questions are at the end.

## Purpose

Each January, take mbarach's own documents (the CV first; later the website and other sources) and
bring Works into line with them under UMN's published guidelines, with every change ticked by
mbarach before it is written. Also flag anything in Works that the documents do not mention, so he
can decide whether it belongs on the CV, stays only in Works, or is wrong.

## Inputs

| Source | Path | Role |
|---|---|---|
| CV (LaTeX) | `<the CV .tex file>` | Master document. Structured by `\section{}` and `\yritem{year}{text}` / `\pawnote{}` macros |
| Website | `<the website folder>` | Secondary; mostly the same content as the CV |
| Works | `audits/<date>/records.json` from the extraction in `CLAUDE.md` | Current state |
| Guidelines | `docs/guidelines/*.txt` and `README.md` | Rules for how an item should be entered |
| Other documents (later) | research statement, annual report drafts, award letters | Optional inputs that can fill fields the CV lacks (amounts, roles, dates) |

## Shape of the problem

The CV and Works disagree in granularity, not just content:

- CV presentations are one line per year listing venues; Works has one record per talk with a
  title, a place, a date. Matching is venue + year, not title.
- CV publications list journal, year, co-authors; Works adds status, dates submitted and accepted,
  DOI, AACSB class, peer-review flag.
- CV service is terse ("Ad hoc reviewer: SMJ, Org Sci"); Works wants start/end years and hours.
- Works has things that never go on a CV (consulting, media, teaching portfolio flags, international
  flags). The CV has things Works lacks today (honors: ISC best-paper finalist 2017 and 2022, AIM
  best-paper finalist 2026, Maekyung award 2026).

So the sync is a three-way reconciliation, with mbarach as the judge, not a one-way copy.

## Proposed pipeline

1. **Normalize both sides into one schema.** `scripts/normalize.py` turns `records.json` and a
   parse of `cv.tex` into lists of `Item`s:
   `{kind, title, venue, year, month?, people?, place?, status?, source: "works"|"cv", ref}`
   where `kind` ∈ publication, working-paper, presentation, grant, honor, service, teaching,
   advising, position, education. The CV parser is macro-aware (`\yritem`, `\pawnote`,
   `\section`) and splits comma-separated venue lists into one item per venue.
2. **Match.** Within a kind and year (±1 for publications), score pairs by normalized title or
   venue similarity (token set ratio), with alias tables for venues the CV abbreviates
   (SRF = Strategic Research Forum, P&O = Wharton People and Organizations, ISC = Israel Strategy
   Conference, EGOS, SMS, AOM, NBER). Output three buckets: matched, CV-only, Works-only.
3. **Apply guideline rules** to every CV-only item and every matched item with gaps:
   which screen, which required fields, date convention (single event = end date only), flags
   (international by location), AACSB class defaults by kind (presentations and research service
   = Basic or Discovery; teaching grants = Teaching and Learning), annotation suggestions for
   multi-author papers. Encoded as a small rules table in `rules.py`, each rule citing the guide
   line it comes from.
4. **Artifact page**, same pattern as the field audit: one card per proposed action. Types of
   action: *create* in Works (CV-only), *fill* a field on a matched record, *review* a Works-only
   item (keep / add to CV / delete). Each with the field values prefilled from the CV and the rule
   that produced them, and a tick. The `db` store holds the answers.
5. **Apply** with `scripts/apply_record.js` for fills; creating records needs a new recipe
   (the "Add New" form per screen) tested one record at a time. Deletions are never automated;
   the page lists them for him to do by hand.
6. **Report** before/after and a list of CV edits he may want (the reverse direction is a text
   diff he applies in `cv.tex` himself, or asks Claude to draft).

## What exists already

- Extraction, parsing, audit page, answers store, apply helper, verification: all in this repo
  and documented in `CLAUDE.md` and `screens.md`.
- Screen catalog with which fields each screen has.
- Guidelines downloaded and digested in `docs/guidelines/README.md`.

## What has to be built

- `scripts/parse_cv.py` (LaTeX macros → items) and `scripts/normalize.py` (Works records → items).
- `scripts/match.py` with the alias table and a reviewable `matches.json`.
- `scripts/rules.py` and a `proposals.json` builder.
- A second page template (`build_sync_page.py`) with create/fill/review cards.
- A tested "Add New" recipe per screen that gets new records (Honors first, since it is empty and
  the CV lists four).
- Optional: Works' own "CV - Standard University of Minnesota" report as a cross-check output.

## Open questions for mbarach

1. Is `cv.tex` the single master, or should the website ever win? (Proposal: CV wins; website is
   generated from it.)
2. Which kinds should the first version cover? (Proposal: publications, presentations, honors,
   service. Teaching and advising come from UMN imports and should not be synced from the CV.)
3. For CV-only presentations that lack a title (the CV lists venues only), should Works records be
   created with the venue as title, or should the page ask for titles one by one?
4. Should the tool ever propose CV edits (Works-only items that look CV-worthy), or stay one-way?
5. Do you want the Annual Activity Report run and saved into the audit folder as the final
   artifact of each January update?

---
Superseded 2026-10-15 by `2026-10-15-shared-works-sync-design.md`, which answers the open
questions above.
