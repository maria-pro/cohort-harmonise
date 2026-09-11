# v0.1.0

First release. **Superseded by v0.2.0**, which removed one cohort; see
[`release-notes-v0.2.0.md`](release-notes-v0.2.0.md). Kept because the `v0.1.0` tag still points
at this state, and it is where the six-cohort configuration can be recovered from.

- Dictionary-first harmonisation across six longitudinal youth cohorts: LSAC, ABCD, TESS,
  Ten to Men, AStRA and LSIC. Cohorts are configuration, not code.
- Four adapter kinds cover the four dictionary shapes held (long, wide-wave, wave-code list,
  and publication-documented inventories for cohorts with no custodian dictionary).
- Common schema carrying instrument, item wording, informant, response coding, age,
  calendar year, digital era and full cell-level provenance.
- Construct coverage matrix as a single self-contained HTML page.
- Claim audit: checks the methodological assertions in the accompanying protocol against the
  cohorts' own dictionaries, with evidence-tier-aware verdicts, so a cohort documented only
  from publications returns UNVERIFIABLE rather than a false contradiction.
- Step-3 feasibility assessment: whether genuine common items exist to anchor a multi-group
  latent model for a given cohort pair, or whether the inference must be harmonised instead.
- Register of constructs declared non-harmonisable, with a mandatory reason and empirical
  confirmation of absence.
- Governance enforced in code: the governed cohort is excluded by default, and its culturally
  grounded wellbeing indicators cannot be mapped as a proxy for a diagnostic construct.
- Pre-filled custodian templates for the two cohorts awaiting documentation.
