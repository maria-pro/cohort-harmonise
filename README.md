# cohort-harmonise

Dictionary-first harmonisation across five longitudinal youth-development cohorts, and an
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
| 3 | TESS — Trondheim Early Secure Study | NOR | 1 | published cohort profile (custodian documentation held locally, not published) |
| 4 | Ten to Men — Australian Longitudinal Study on Male Health | AUS | 2 | custodian dictionary (Wave 5) |
| 6 | LSIC — Footprints in Time | AUS | governed | custodian dictionary (Release 14.0), **sign-off required** |

Cohort numbers follow Table B1 and are not reindexed when a cohort is removed, so the gap at 5 is deliberate. Adding a cohort is a new YAML file in `configs/cohorts/` and nothing else — no
cohort-specific branch in `src/` exists for any of the six. Two general conventions are
built in rather than configured: a subcohort wave id ending `W<n>` groups parallel cohorts,
and the step 3 assessment defaults to the anxiety constructs unless told otherwise.

### A cohort that was assessed and removed

A sixth cohort, AStRA (Athena Studies of Resilient Adaptation, Greece), was carried through
version 0.1 and removed in 0.2. The tool found it held none of the three primary predictors the
analysis depends on — late-night device use, sleep, and the fearful subtype of social withdrawal —
and no anxiety caseness measure, and that no public codebook existed against which any of this
could be confirmed. Six of the nine claims the audit could not check were about that one cohort.

It is recorded here rather than quietly dropped, because the reason is the point: the tool was
built to make a harmonisation claim checkable, and a cohort that cannot be checked and cannot
contribute to the primary analysis is a weaker claim, not a larger one. Restoring it needs a
custodian codebook and a new `configs/cohorts/astra.yaml`; the earlier version is in the git
history at tag `v0.1.0`.

## Quick start

```bash
uv venv && uv pip install -e .
harmonise run --data-root /path/to/your/dictionaries
```

The dictionaries are not in this repository. `docs/data_sources.md` lists the expected
relative paths and where to obtain each file. Cohort 6 is excluded unless you pass
`--include-governed`; see **Governance** below. **The published artefacts in this repository
are generated with `--public` and without `--include-governed`**, so the governed cohort
appears as excluded rather than mapped, and the committed configuration carries only what
published sources support.

```
harmonise run       ingest, map, audit and report in one pass
harmonise ingest    read the dictionaries only and report row counts per cohort
harmonise audit     check the documented claims and print the verdicts
      --strict           exit non-zero if any claim mismatches (usable in CI)
      --include-governed include cohort 6; requires documented sign-off
      --no-publish-docs  do not refresh docs/index.html for GitHub Pages
      --public           ignore local overlays when generating committed artefacts
```

`harmonise run` writes the interactive report to `outputs/explore.html` and `docs/index.html`,
and a static plain-HTML version of the same run to `outputs/coverage_matrix.html` and
`docs/static.html`.
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
| `custodian_documentation` | Supplied by the study custodian but not public. Counts as hard evidence, and lives in a `configs/cohorts/local/` overlay that is never committed |
| `published_profile` | Built from a published cohort profile or instrument paper, citation on the row |
| `reconstructed` | Assembled from published methods and results, because no codebook exists |

This distinction is load-bearing in the audit. A cohort read from a custodian dictionary or
custodian documentation can genuinely **contradict** a claim, so a failure there is a
`MISMATCH`. A cohort inventoried from publications can only **fail to confirm** it, so a
failure there is `UNVERIFIABLE`, and a declared absence is only reported as confirmed for
those cohorts where a dictionary exists to confirm it in. Absence of evidence is not
treated as evidence of absence.

Where a custodian supplies documentation that cannot be published, the committed config
carries only what public sources support and the rest is merged in at load time from
`configs/cohorts/local/<cohort>.yaml`, which is gitignored. Runs inside the study team see
the full picture; the published artefacts do not reproduce material we have no right to
redistribute.

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
crosswalk, since those reproduce dictionary content in bulk. `provenance.json` records a
SHA-256 over each file actually read (hashing the first 1 GiB, which covers every dictionary
held), so a third party can confirm they ran the tool against the same releases without
those files being redistributed here.

## Licence and citation

Code is MIT (`LICENSE`). Documentation and generated reports are CC-BY-4.0. Cite the tool via
`CITATION.cff`, or the archived release DOI once one is minted.
