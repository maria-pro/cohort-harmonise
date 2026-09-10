# Team reports

Snapshots written for the investigator team, not part of the tool.

| File | What it is |
|---|---|
| [`dictionary-report.md`](dictionary-report.md) | Team note, 11 September 2026. What the six cohort dictionaries turned out to contain, which claims in the application they support, which they correct, and what two rounds of independent review overturned in our own findings. |
| `index.html` | The same note, styled for reading in a browser. Served at `/_report/` if GitHub Pages is enabled for this repository. |

## These are snapshots, not live output

The tool's own reports regenerate on every run and live in `outputs/` and `docs/`. The files here
were written at a point in time and do not update themselves. Figures in them were current at the
date on the note; re-run `harmonise run --public` and check `outputs/claim_audit.csv` for the present
state.

## One caveat that travels with the numbers

The variable counts in these reports are keyword-match counts, not curated tallies. Independent
review found real false positives inside them. Read a count as *where to look*, not as *how much is
there*; the mapping status, the instrument resolution and the informant are more reliable than the
number beside them.
