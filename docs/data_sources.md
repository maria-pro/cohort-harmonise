# Data sources

This repository contains **no participant data and no cohort dictionary files**. It reads
dictionaries you obtain yourself, under each study's own terms, and writes variable-level
metadata only.

Place the files below under `data/dictionaries/` (or point `--data-root` at wherever you
keep them) with these relative paths. `provenance.json` records the SHA-256 of every file
actually read, so a third party can confirm they ran the tool against the same releases.

| Cohort | Expected relative path | Where to obtain it |
|---|---|---|
| LSAC (1) | `LSAC Dictionary/LSAC-Data-Dictionary-Release-10.1.xlsx` | AIFS Growing Up in Australia data documentation; dictionary is a published AIFS document, data access under AIFS/DSS terms |
| ABCD (2) | `ABCD Data for Custom GPT/ABCD_7.0_dictionary_with_waves.xlsx`, `ABCD_7.0_events.csv`, `ABCD_7.0_response_levels.csv` | Dictionary metadata is public at docs.abcdstudy.org; participant data require an NDA Data Use Certification |
| TESS (3) | — no custodian dictionary held | Study custodians at NTNU. The inventory in `configs/cohorts/tess.yaml` is built from published sources: the cohort profile, the study's wave list, the anxiety-course paper, the actigraphy papers and the social-withdrawal paper. Further documentation held by the study team is merged from a local overlay that is not committed |
| Ten to Men (4) | `2510-Wave-5-Data-Dictionary.xlsx` | AIFS Ten to Men data documentation |
| AStRA (5) | — no custodian dictionary held, and no public codebook exists | Study lead. The inventory in `configs/cohorts/astra.yaml` is reconstructed from published methods and results |
| LSIC (6) | `LSIC Dictionary/2. Data Dictionary - LSIC Release 14.0.xlsx` | AIFS Footprints in Time documentation. **Use requires First Nations governance sign-off**; the tool excludes this cohort unless `--include-governed` is passed |

The Ten to Men file is distributed with a release prefix (for example
`2510-Wave-5-Data-Dictionary (1).xlsx`). Either rename it to the path above or set the
`source.path` in `configs/cohorts/ttm.yaml` to the name you have.

## Evidence tiers

Every row carries the tier of evidence it rests on, and the coverage matrix shows it:

| Tier | Meaning |
|---|---|
| `official_dictionary` | Read from the custodian's own dictionary file |
| `published_profile` | Built from a published cohort profile or instrument paper, with the citation on the row |
| `reconstructed` | Assembled from published methods and results sections, because no codebook exists |

`published_profile` and `reconstructed` rows are provisional. `outputs/custodian_template_*.csv`
is generated for each such cohort: a pre-filled inventory that asks the study lead to confirm
or correct what we have assumed, rather than asking them to produce documentation from scratch.
