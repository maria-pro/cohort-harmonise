"""Dictionary-first harmonisation across six youth-development cohorts.

Module map to the application's Table B2:
  ingest      step 0  data dictionary
  normalise   step 0  common schema, reporter, era
  mapping     steps 1, 2, 4  construct crosswalk, caseness readiness, reporter/age/era alignment
  linkage     step 3  anchor-item feasibility for pooled latent modelling
  governance  step 5  declared non-harmonisable, plus cohort 6 governance gate
  audit               checks the application's own assertions against the dictionaries
"""

__version__ = "0.2.0"

SCHEMA = [
    "cohort", "cohort_number", "tier", "release", "evidence_tier",
    "wave_id", "wave_year", "year_source", "digital_era", "age_range",
    "variable", "label", "item_text", "instrument", "instrument_id",
    "domain", "construct_src", "respondent", "coding", "population",
    "subcohort", "confidence", "governance_required",
    "source_file", "source_sheet", "source_row",
]
