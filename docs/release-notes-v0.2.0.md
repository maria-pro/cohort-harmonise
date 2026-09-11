# v0.2.0

Removes a cohort, and with it the largest source of claims the audit could not check.

## AStRA removed

Cohort 5, the Athena Studies of Resilient Adaptation, is no longer part of the set. The tool
established that it holds none of the three primary predictors the analysis depends on — late-night
device use, sleep, and the fearful subtype of social withdrawal — nor any anxiety caseness measure,
and that no public codebook exists against which those absences could be confirmed rather than
merely observed. Six of the nine unverifiable claims in v0.1.0 concerned that one cohort.

Restoring it requires a custodian codebook. The v0.1.0 configuration is in the git history.

The `reconstructed` evidence tier remains in the code and is now unused. It stays because the
distinction it encodes — a cohort documented only from publications can fail to confirm a claim but
cannot contradict one — is a property of the method rather than of any particular cohort.

## Also in this release

Two rounds of independent review, and the fixes they produced: an audit check that reported PASS
beside evidence contradicting it; an informant classifier that read a parent report about a child as
a child self-report; a display truncation that was deciding audit verdicts; alias matching that let
"panic" match "Hispanic" and "k10" match "k100"; a governance rule that could never fire; and
declared absences reported as empirically confirmed using cohorts that hold no dictionary.

Social withdrawal is split into its fearful and unsociable subtypes, because the instrument that
measures it separates them and only one is anxiety-relevant. Informant agreement across cohorts is
now checked rather than merely recorded.

Material supplied privately by a custodian is held in an uncommitted overlay, and
`tools/check_private.sh` gates commits against it.
