# GT Transfer Equivalencies

A searchable mirror of Georgia Tech's transfer equivalency table. Find out which courses at other colleges transfer in as a specific GT course — filter by US state or limit to community colleges only.

> GT's official table lets you look up one school at a time. This site flips that around: pick a GT course and see **every** school whose course transfers in, or search across thousands of schools at once.

## Using the site

Open the site and you'll see one search box and two filters.

### Search box
Matches against GT course code, external course code, course title, or school name — whichever you type.

| If you type… | You get… |
|---|---|
| `APPH 1040` | Every external course that transfers in as GT's APPH 1040. |
| `CS 1332` | Every external course equivalent to GT's Data Structures. |
| `De Anza` | Every transferable course at De Anza College. |
| `calculus` | Every course with "calculus" in the title. |
| `BIOL 10` | That specific external course (paired with whatever GT course it becomes). |

Search is case-insensitive and matches anywhere in the text. Results update as you type.

### State filter
Pick a US state from the dropdown to restrict to schools in that state. "Any" turns it off.

### Community colleges only
Check this box to exclude 4-year schools. "Community college" here means a school whose predominantly-awarded degree is the associate's (the standard US Dept. of Ed. definition).

### Combining filters
All three work together. Typical workflow:

> "I'm home in California this summer and want to knock out APPH 1040 at a local community college."
>
> → search `APPH 1040`, state `CA`, check community colleges. You'll get the list of CA community colleges with a matching course.

### Results table
Each row is one external-course → GT-course equivalency:

| Column | Meaning |
|---|---|
| School | The external institution. |
| State | 2-letter code. Blank if the school couldn't be matched against Dept. of Ed. data. |
| External Course | Course code at that school. |
| Course Title | Title at that school. |
| GT Course | What it transfers in as. |
| Credits | Credit hours awarded at GT. |

Results are capped at 500 rows at a time — if you see a "narrow your search" notice, add more filters or a more specific query.

### Data freshness
The footer shows when the data was last refreshed. The scraper runs nightly, so equivalencies added by GT's registrar show up within 24 hours.

## Caveats

- **Always verify with the registrar before relying on it.** GT can and does update equivalencies; this is a snapshot.
- **Blank state column** means the school's name didn't match any record in the federal Dept. of Education dataset (often minor name differences or non-US schools). The row is still searchable by name and course.
- **No guarantees about currency of an individual course.** A course that appears in the table was transferable at some point. GT may stop accepting it later.

## Advanced: using the data directly

The full dataset is a single JSON file published alongside the site at `data.json`. Shape:

```json
{
  "generated_at": "2026-04-15T04:07:12Z",
  "schools": [
    {
      "code": "001569",
      "name": "De Anza College",
      "state": "CA",
      "is_community_college": true,
      "courses": [
        {"ext_subj":"BIOL","ext_num":"10","ext_title":"Intro Biology",
         "gt_subj":"BIOL","gt_num":"1510","gt_credits":"3"}
      ]
    }
  ]
}
```

Fetch it, filter it however you like — it's public.

## Advanced: CLI

For one-off queries without a browser:

```bash
pip install -r scraper/requirements.txt
python -m scraper.reverse_transfer APPH 1040 --state CA --community-college
```

The `--state` and `--community-college` flags require a free [College Scorecard API key](https://api.data.gov/signup/) in `COLLEGE_SCORECARD_API_KEY`. Without filters, no key is needed.

## Contributing / running your own copy

See [`docs/SETUP.md`](docs/SETUP.md) (or the workflow files in `.github/workflows/`) for how the nightly scrape and deploy are wired up.
