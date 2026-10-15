# UMN Works guidelines

The guide texts are UMN's documents and are not committed here; `scripts/fetch_guidelines.sh`
downloads them into this folder (git ignores the `.txt` files) from the Google Docs linked at
https://works.umn.edu/guides-training
(`curl -L "https://docs.google.com/document/d/<id>/export?format=txt"`). Re-download before each
January update; the Quick Start and Reports guides were "Updated October, 2026 to support the new
Works experience".

| File | Source doc id | What it covers |
|---|---|---|
| `quick-start.txt` | 1GClloQM_E7iKP0kmy3F8cbcgdGrmFlNI | Entering activities, the date convention, international/outreach flags, annotations, running the Annual Activity Report |
| `publications.txt` | 1Cuy6jY2LcwtYFNRCYvsP_xyqQsG8yUC8 | Importing citations (Scopus, ORCID, BibTeX), manual entry of unpublished work, author-contribution annotations, required fields, duplicates |
| `grants.txt` | 17wLYkWTzhTUhrOWBxO04HOiKSF0ItvxG | SPA-imported grants vs manual entry, override fields, suppressing project records |
| `reports.txt` | 1cjoM6ezjncO8RtjkLUkZ_BJL8n9gkqWr | Running reports, Rapid Reports, file formats |
| `new-interface-crosswalk.txt` | 12WomJYix3IypmRZXSbxJBRj2HnPSdTON0h8v0BPXQdU | Mostly screenshots (not in the text export). New interface preview 2026-06-01, launch Fall 2026 |

Not yet fetched: the Carlson-specific guide, if one exists (the guides page lists college guides for
other units but none for Carlson), and the Annual Activity Report template Carlson asks for.

## Rules that matter for automation (extracted)

**Dates** (Quick Start). Every record needs a title and a date.
- start only = ongoing or current
- end only = single event
- both = a date range, to be included on reports for that range
So a conference talk, a panel, a one-day workshop: end date only. A reviewer role with no end:
start only. The Annual Activity Report selects by date range, so a missing date hides a record.

**Flags** (Quick Start). Mark activities that were international or had an outreach/extension/
public-engagement component. No definition of "international" is given; the International
Engagement Summary screen asks in what countries activities took place. The tool's default rule: Yes only
when the activity took place outside the US; virtual events are No.

**Publications** (Publications guide).
- Required to save: Contribution Type, Current Status, and at least one date.
- Unpublished work is entered manually with a status (submitted, revising to resubmit, etc.).
- Multi-author papers: describe your contribution in the Annotation field (corresponding author,
  conceptualization, data, analysis, supervision). Annotations print under the record on reports.
- Imports (ORCID, Scopus, BibTeX) can create duplicates; Works flags them and they are deleted from
  the list view. Limit re-imports to the last 12 months.
- "My Record?" on the author row bolds the name on reports.

**Grants** (Grants guide). SPA is the system of record for sponsored grants; internal grants and
grants from other institutions go on the manual-entry screen with Internal/External set. Funding
amounts are never imported and must be typed. Use "Also print to CV?" to hide duplicate project
rows.

**In-form help** (read in the Presentations form): the "Related to Teaching and Learning?" box only
adds the record to the Teaching and Learning Portfolio; AACSB classification definitions are in
`../../CLAUDE.md`.

**Annual report** (Reports guide). Run "Annual Activity Report" with the review period dates;
departments may require a college-specific report. CV reports are also generated from Works
("CV - Standard University of Minnesota"), which is one way to compare Works to the real CV.
