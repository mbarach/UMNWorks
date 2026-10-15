# Works screen catalog

Instrument 896 (University of Minnesota, Carlson School account). Record counts and field availability as seen on the example account, 2026-10-13.
Full column lists for every screen with records are in `local/audits/<date>/raw/extract_*.txt`
(the `H` lines). "Audited fields" are the five from the 2026-10-13 spec.

Column names that carry the audited fields:

| Field | Column name(s) in Works |
|---|---|
| AACSB | `AACSB Classification` (Presentations, Publications); `AACSB: If this activity contributes to professional practice standards or public policy, provide a classification` (service, consulting) |
| Teaching | `Related to Teaching and Learning?` (checkbox) |
| International | `Was/is this an international activity?` (Yes/No). Presentations and Other Instructional also have `Scale` (International / National / Regional / State / Local, to confirm on first edit) |
| Start | `Start Date` (Month/Day/Year parts), `Date Advising Began`, `Start Date of Funding` |
| End | `End Date`, `Date Advising Ended`, `End Date of Funding`. Convention (Quick Start Guide): start only = ongoing, end only = single event, both = span |

`Record Start Date` and `Record End Date` are derived by Works (filled from whichever date exists)
and are not the user-entered fields.

## Manual-entry screens with records

| Screen id | Name | AACSB | Teaching | Intl | Scale | Start/End |
|---|---|---|---|---|---|---|
| 937611 | Presentations | yes | yes | yes | yes | single `Date` only |
| 937449 | Publications and Other Intellectual Contributions | yes | yes | no | no | draft/submission/accept/publish dates |
| 937807 | Discipline/Profession/Interdisciplinary Areas (service) | yes | yes | yes | no | Start/End |
| 937757 | University/Department (service) | yes | yes | yes | no | Start/End |
| 937875 | Public/External/Community (service) | yes | yes | yes | no | Start/End |
| 936938 | Consulting and Outside Professional Commitments | yes | no | yes | no | Start/End |
| 937014 | Professional Development and Mentoring Received | no | yes | no | no | Start/End |
| 1382407 | Other Grants, Contracts, Gifts, or Earnings (manual) | no | yes | yes | no | Start/End of Funding, Proposal Submitted |
| 937176 | Other Instructional Activity | no | no | yes | yes | Start/End, Term and Year |
| 1783268 | Leaves and Sabbaticals | no | no | yes | no | Start/End |
| 1331951 | My Advisees | no | no | no | no | Date Advising Began/Ended |
| 1943801 | Committee Advising | no | no | no | no | Date Advising Began/Ended (5 imported from PeopleSoft) |
| 937119 | Other Student Advising | no | no | yes | no | Start/End |
| 1888336 | Doctoral and Postdoctoral Placement | no | no | no | no | Degree Completion, Year Started |
| 937067 | Media Appearances and Interviews | no | no | no | no | single `Date` |
| 936967 | Education | no | no | no | no | Date Completed |
| 936862 | Current Position and Employment History | no | no | no | no | Start/End |

## Manual-entry screens with no records (2026-10-13)

1742158 Narrative/Goals/Supplementary Upload · 937259 Creative and Artistic Practice · 937675
Collaboration and Research in Progress · 937562 Patents · 1783301 Scholarly Reviews of My Work ·
1384802 Curriculum Development · 937113 Advising Totals · 1956833 Post Doc/Trainee Supervision ·
1793811 Mentoring/Career Advising · 2041082 International Engagement Summary · 2039173 Outreach
Summary · 936911 Honors and Recognition · 1324321 Graduate/Post-Professional Training ·
Administrative Appointments · Licensures and Certifications · Professional Memberships ·
Teaching and Learning Portfolio.

Honors and Recognition was empty on the example account; the resume-driven flow creates these.

## Imported, read-only screens

937212 Scheduled Teaching · 2147630 Student Rating of Teaching · Academic Advising (imported) ·
1407640/1410717/1410762 Proposals/Awards/Projects SPA · PeopleSoft HR and AACSB Qualification Data ·
UMN Professorial Promotion Dates. Profile pages: 936599 Personal and Contact Information,
1823840 Biography and Expertise.

## Field-type edit recipes

All via `scripts/apply_record.js` (see CLAUDE.md "Writing data") unless noted.

| Type | Example | Recipe | Status |
|---|---|---|---|
| Combobox dropdown | AACSB Classification, Was/is this an international activity?, Scale, Month parts | helper `setCombo(prefix, optionText)`: dispatch pointer/mouse events on the input, click the `[role=option]` by exact text, verify shown value | tested on 50+ records 2026-10-13 |
| Checkbox | Related to Teaching and Learning? | helper `setCheckbox(prefix, bool)`: `.click()` and verify `checked` | tested on 5 records 2026-10-13 |
| Text date parts | Year / Day of Start, End, Date Advising Ended | **script-set values are dropped on Save.** Type for real: throwaway screenshot, click the field, `type`, Tab, Save | tested 2026-10-13 (advisee end year) |
| Free text | titles, organizations | same as text date parts; untested | untested |
| Add New record | any screen | drawer on the list page; fields in `screens/forms.json`; recipe `scripts/create_record.js` | forms captured 2026-10-15; creation verified on Honors (2 records) 2026-10-15 |

Option orders seen: international Yes, No · Scale International, National, Regional, State, Local ·
AACSB Basic or Discovery Scholarship, Applied or Integration/Application Scholarship, Teaching and
Learning Scholarship.

## Data quality notes

Notes about a person's own records go in `local/notes.md` (not in git). Works itself flags possible
duplicate publications in its notifications; the tool never deletes them.

## Add New forms (captured 2026-10-15, new view)

`screens/forms.json` lists, per screen, every field of the Add Activity drawer in form order with
its input id prefix, type (text, textarea, combo, checkbox, date, checkgroup, note), options, and
whether Works marks it required. Captured for Presentations, Publications, Honors and Recognition,
and the three service screens. Presenter/author rows were not captured (a `note` field stands in
for them); the Country combobox options were not captured (opening it from script hangs the page).
