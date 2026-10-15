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
| status | string | publications: published, accepted, revise-and-resubmit, submitted, working, in-preparation; else "" |
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

## Known differences by format (checked 2026-10-15)

- **LaTeX source**: `ref` is the line number; one `\yritem` line yields several items; `\pawnote`
  lines under a paper are honors or notes, not publications.
- **Compiled PDF of the same CV**: `ref` is the page number; the gray bullet lines under a paper
  are the `\pawnote` notes; a venue list wrapped across lines is still one year's list; the
  "2019/20/21" row gives no per-venue year, so those items carry `year: null`.
- Resting projects and references are not items.
