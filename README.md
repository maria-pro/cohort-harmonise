# cohort-harmonise

Dictionary-first harmonisation across six longitudinal youth-development cohorts, and an
audit of published methodological claims against those cohorts' own data dictionaries.

It reads **variable-level metadata only**. No participant data is read, produced or
redistributed, and no dictionary file is committed to this repository.

**[Read the generated report](https://maria-pro.github.io/cohort-harmonise/)** — the coverage
matrix, claim audit, non-harmonisable register and step-3 verdicts on one page, regenerated
from the dictionaries on every run.

The tool answers four questions a reader of a harmonisation protocol will actually ask:

1. **Which constructs does each cohort really hold, at which wave, from which informant?**
   → `outputs/coverage_matrix.html`
2. **Where the protocol asserts something checkable, is it true?**
   → `outputs/claim_audit.csv`
3. **Can the constructs that cannot be aligned be named, with reasons, rather than quietly
   dropped?** → `outputs/non_harmonisable_register.csv`
4. **Is pooled latent modelling actually available for a given pair of cohorts, or does the
   inference have to be harmonised instead of the scale?** → `outputs/step3_linkage.csv`

## Cohorts

| # | Cohort | Country | Tier | Evidence |
|---|---|---|---|---|
| 1 | LSAC — Growing Up in Australia | AUS | 1 | custodian dictionary (Release 10.1) |
| 2 | ABCD — Adolescent Brain Cognitive Development | USA | 1 | custodian dictionary (7.0) |
| 3 | TESS — Trondheim Early Secure Study | NOR | 1 | published cohort profile |
| 4 | Ten to Men — Australian Longitudinal Study on Male Health | AUS | 2 | custodian dictionary (Wave 5) |
| 5 | AStRA — Athena Studies of Resilient Adaptation | GRC | 2 | reconstructed from publications |
| 6 | LSIC — Footprints in Time | AUS | governed | custodian dictionary (Release 14.0), **sign-off required** |

Adding a cohort is a new YAML file in `configs/cohorts/` and nothing else. There is no
cohort-specific logic in `src/`.

## Quick start

```bash
uv venv && uv pip install -e .
harmonise run --data-root /path/to/your/dictionaries
```

The dictionaries are not in this repository. `docs/data_sources.md` lists the expected
relative paths and where to obtain each file. Cohort 6 is excluded unless you pass
`--include-governed`; see **Governance** below.

```
harmonise run       ingest, map, audit and report in one pass
harmonise ingest    read the dictionaries only, and report what did not map
harmonise audit     check the documented claims and print the verdicts
      --strict           exit non-zero if any claim mismatches (usable in CI)
      --include-governed include cohort 6; requires documented sign-off
      --no-publish-docs  do not refresh docs/index.html for GitHub Pages
```

`harmonise run` writes the report to both `outputs/coverage_matrix.html` and `docs/index.html`.
GitHub Pages can be pointed at either the repository root or `/docs`; the root `index.html`
redirects to `docs/`, so the published link works under both settings.

A full run over all six cohorts reads roughly 545,000 cohort-wave-variable rows (ABCD alone
contributes about 430,000 across 32 sessions) and takes a few minutes. `harmonise ingest` is
quick and is the right command when you only want to check that a dictionary parses.

## Method, and where each step lives

The harmonisation pathway this implements is a six-step protocol. Each step maps to a module,
so a reader checking feasibility can see the correspondence rather than take it on trust.

| Step | Purpose | Module |
|---|---|---|
| 0 · Data dictionary | Record instrument, reporter, item wording, response range, scoring rules, published cut-offs and age at assessment | `ingest.py`, `normalise.py` |
| 1 · Within-instrument standardisation | Identify what can be z-scored within instrument and age band | `mapping.py` |
| 2 · Caseness and transition status | Apply published, instrument-specific thresholds | `mapping.py` + `configs/constructs.yaml` (`thresholds`) |
| 3 · Latent severity | Decide whether genuine common items exist to anchor a multi-group model | `linkage.py` |
| 4 · Reporter, age and era alignment | Carry informant, age and digital era as first-class fields | `normalise.py` |
| 5 · Declared non-harmonisable | Name the construct, state why, analyse within cohort only | `governance.py`, `mapping.py` |

Three schema fields carry more weight than they look:

- **`respondent`** — a parent report at 10 years must never be silently treated as a youth
  self-report at 14, so the informant is a field, not a footnote. ABCD's informant is derived
  from its table-naming convention; LSAC's and LSIC's are read from the dictionary; Ten to
  Men has no informant column, so it is set from the study design and *recorded as such*.
- **`wave_year`** and **`digital_era`** — two hours of screen use in 2010 is not the same
  ecological exposure as two hours in 2025, so calendar year travels separately from wave
  index and the era is derived from it. Each wave's year carries a `year_source` of
  `published`, `derived` or `unconfirmed`; nothing is presented as cited when it was inferred.
- **`source_file` / `source_sheet` / `source_row`** — any mapping traces back to a cell.

## Evidence tiers

Two of the six cohorts have no custodian dictionary. Rather than show blank columns or
pretend otherwise, every row records the tier of evidence it rests on, and the coverage
matrix displays it:

| Tier | Meaning |
|---|---|
| `official_dictionary` | Read from the custodian's dictionary file |
| `published_profile` | Built from a published cohort profile or instrument paper, citation on the row |
| `reconstructed` | Assembled from published methods and results, because no codebook exists |

This distinction is load-bearing in the audit. A cohort read from a custodian dictionary can
genuinely **contradict** a claim, so a failure there is a `MISMATCH`. A cohort inventoried
from publications can only **fail to confirm** it, so a failure there is `UNVERIFIABLE`.
Absence of evidence is not treated as evidence of absence.

For each such cohort the tool writes `outputs/custodian_template_<cohort>.csv`: a pre-filled
inventory of what we have assumed, with its source and our confidence, and blank columns for
corrections. The ask to a study lead becomes *confirm or correct these rows*, not *please
produce documentation*.

## Governance

Cohort 6 (LSIC, Footprints in Time) is analysed only under First Nations leadership and data
governance, following the CARE Principles for Indigenous Data Governance and the Maiam nayri
Wingara Indigenous Data Sovereignty Principles. Two consequences are enforced in code, not
described in prose:

- The cohort is **excluded by default**. `--include-governed` is required, and should only be
  used where sign-off is documented.
- Its culturally grounded wellbeing indicators **cannot be mapped as a proxy** for a
  diagnostic anxiety construct. The mapping engine returns `governed_not_proxied` instead of
  `proxy`, so the refusal appears in the output rather than depending on an analyst's care.

Separately, a construct declared non-harmonisable **without a stated reason raises an error**
rather than being written. Step 5 is a check, not a convention.

## What is and is not in this repository

Committed: the code, the cohort configs, the claim set, and the aggregate reports a reader
needs — coverage matrix, claim audit, non-harmonisable register, step-3 linkage verdicts,
custodian templates, and `provenance.json`.

Not committed: the dictionary files themselves, the full normalised table and the full
crosswalk, since those reproduce dictionary content in bulk. `provenance.json` records the
SHA-256 of every file actually read, so a third party can confirm they ran the tool against
the same releases without those files being redistributed here.

## Licence and citation

Code is MIT (`LICENSE`). Documentation and generated reports are CC-BY-4.0. Cite the tool via
`CITATION.cff`, or the archived release DOI once one is minted.
