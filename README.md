# UMN Works sync (Carlson School)

A Claude Code skill that keeps your UMN **Works** record (Watermark Faculty Success, the system
behind the annual activity report) in line with your resume. You hand it your CV in any format,
it reads your Works record, and it puts every proposed change on one private web page: records to
add (shown as the actual Works form, prefilled), fields to fill on existing records, and items
that are only in Works. You tick what you want. Nothing is written to Works until you do, and
deletions are never automated.

Built for Carlson School faculty. Other colleges have different Works screens; the tool warns
when it meets a screen it does not know, but it has only been run against Carlson accounts.

## What you need

- [Claude Code](https://claude.com/claude-code). The desktop app's Code tab is enough; no
  terminal skills required.
- The [Claude in Chrome](https://claude.com/chrome) extension, in Chrome, Edge, or Brave, signed
  in to Works: https://www.digitalmeasures.com/login/umn/faculty/app/activities/instruments/896?_s=0
- A claude.ai account on a paid plan (the review page stores your ticks there).
- Python 3.10 or newer (macOS has it). No packages to install.
- Your resume as a file: PDF, Word, LaTeX, plain text, or a URL.

## First run

1. Clone this repository and open the folder in Claude Code:
   ```
   git clone https://github.com/mbarach/UMNWorks.git
   cd UMNWorks && claude
   ```
2. Say: *Update my Works record from my resume at /path/to/cv.pdf.*
3. Claude asks for your name and a couple of settings once, saves them in `local/config.json`,
   and asks you to sign in to Works in the browser tab it opens.
4. It reads Works and your resume, publishes a private review page, and gives you the link.
5. On the page: fix anything it misread in your resume, fill in and tick the records to add,
   answer the field questions, and decide what to do with items that are only in Works. The
   page keeps count and lets you show only what is still undecided.
6. Say *done* in chat. Claude writes only what you ticked, verifies every save on the Works list
   view, and leaves a report in `local/audits/<date>/after.md`.

Plan an hour the first time. Later runs are quicker because only new items come up.

## Each January

Run it again before the Annual Activity Report. Claude refreshes UMN's Works guides
(`scripts/fetch_guidelines.sh`) when they are older than 90 days, and the page shows which
rules it applied (for example "end date only = a single event", from the Works Quick Start Guide).

## What stays private

Everything about you lives in `local/`, which git ignores: your config, every audit, the page's
answers, transcripts. The shared repository holds only code, the screen catalog, and UMN's public
guides. A test (`tests/test_repo_hygiene.py`) fails if a Works record id or personal path ends up
in a tracked file.

## How it works

| Step | Script | Output |
|---|---|---|
| Read Works through the list view with all columns | `scripts/build_audit.py`, `scripts/normalize.py` | `records.json`, `works_items.json` |
| Read the resume (Claude does this; there is no parser) | rules in `docs/item-schema.md`, validator `scripts/items.py` | `resume_items.json` |
| Match the two | `scripts/match.py` with `scripts/aliases.json` | `matches.json` |
| Apply UMN's guideline rules to unmatched and incomplete items | `scripts/rules.py`, `scripts/field_map.json`, `screens/forms.json` | `proposals.json` |
| Build the review page | `scripts/build_sync_page.py` | `sync_page.html` (published as a private artifact) |
| Read the ticks back | `scripts/read_sync_answers.py` | `sync_plan.json` |
| Write to Works through the browser | `scripts/apply_record.js`, `scripts/create_record.js` | verified on the list view |

The browser recipes in `CLAUDE.md` are the hard-won part: which clicks Works drops, which fields
must be typed for real, how to tell that a save happened in the new Faculty Success view.
Claude reads `CLAUDE.md`, `docs/runbook.md`, and `screens.md` at the start of every run.

## Tests

```
python3 -m unittest discover -s tests -v
```

## Contributing

Fixes to the screen catalog (`screens.md`, `screens/forms.json`, `scripts/screen_kinds.json`)
and the venue alias table (`scripts/aliases.json`) are the most useful contributions. If Works
changes its interface, the recipes in `CLAUDE.md` are where to look first. Please never commit
anything from `local/`.

## Questions about Works itself

Email worksadm@umn.edu, or see the guides at https://works.umn.edu/guides-training.

## License

MIT. See `LICENSE`.
