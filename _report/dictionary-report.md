*Team note · 11 September 2026*

# What the Dictionaries Told Us

We built the alignment application that Component B's Feasibility paragraph
promises, ran it against every cohort dictionary we hold, and had it check the application's own
claims. Fourteen held. Nine did not. Two independent review rounds then found that several of our
own findings were wrong, which is recorded below alongside the rest.

  **6** cohorts · **516,344** cohort–wave–variable rows · **20** constructs ·
**32** claims checked · **14** verified · **9** corrections · **9** not checkable

## Where this sits in the pathway

Table B2 is a six-step pathway, and WP1 is one of three work packages running
M1–15. Step 0 is complete across all six cohorts; steps 2 to 5 have been assessed for
feasibility and their constraints documented. That is the scope, stated precisely so the rest of
this note can be read against it.


    **Step 0.**
    Data dictionary

  Instrument, reporter, item wording, response range, scoring rules, cut-offs, age — all six cohorts
     — **complete**


    **Step 1.**
    Within-instrument standardisation

  Requires participant data. None has been touched.
     — **not started**


    **Step 2.**
    Caseness and transition status

  Thresholds located and cited; one has no verifiable primary source
     — **assessed only**


    **Step 3.**
    Latent severity across cohorts

  All 20 cohort pairs tested for shared item banks. One is anchorable.
     — **assessed only**


    **Step 4.**
    Reporter, age and era alignment

  Informant carried on every row and now compared across cohorts
     — **assessed only**


    **Step 5.**
    Declared non-harmonisable

  Register produced, with absence confirmed only where a dictionary exists to confirm it
     — **assessed only**


What is not yet done, so nobody reads more into this than it
carries: no model has been fitted, WP2 and WP3 are untouched, and the tool reads what dictionaries
*say* rather than what the data contain — data access itself has not begun.

> **What it retires.** WP1's replication design rests entirely on the six cohorts being harmonisable. Had the dictionaries not lined up, no amount of WP2 would have rescued it — and it is the one risk that could not be retired later by working harder. It is now largely retired, and the constraints on the rest of the pathway are documented rather than assumed.

## Fourteen claims verified

Each of these is now checkable by a reviewer against a cohort's own dictionary,
rather than taken on trust.

  | Claim | Evidence |


    | LSAC measures the SCAS short form in adolescence | CAS-8 items at 12/13, 14/15 and 16/17, both cohorts |

    | ABCD measures K-SADS anxiety and CBCL internalising | 61,176 K-SADS and 1,472 CBCL variables |

    | TESS uses PAPA and CAPA interviews | PAPA at 4 and 6, CAPA from 8, per the six-wave anxiety paper |

    | Ten to Men measures GAD-7 from Wave 3 | 50 variables, waves 3, 4, 4.1 and 5; absent from 1–2 |

    | Ten to Men holds earlier distress measures | PHQ-9 and PHQ-9M, 13 variables each at waves 1 and 2 |

    | All six collect education and functioning, and social context | Matched in every ingested cohort |

    | Digital era enters the model | Web 1–4 populated on all 516,344 rows |

    | Intolerance of uncertainty and AI interaction are absent | Zero matches in every dictionary held |

    | TESS runs objective actigraphy at seven waves | Hip-mounted ActiGraph GT3X, ages 6–18, n = 880 |

    | The five-wave / seven-wave figures do not conflict | Two different papers, each correctly cited in its own component |



## Nine corrections to the text

Ordered by how much work each one saves later. All nine are edits to Components A
and B, not to the science.

  **[correct]**`B1-note-objective-sleep`— Methods · Table B1 note

### TESS holds the longest objective sleep series in the project, and the note omits it


Table B1 says objective wearable sleep exists in cohorts 1 and 2 only — CheckPoint at
  ~12 y and the ABCD Fitbit substudy. TESS runs hip-mounted ActiGraph GT3X for seven nights at
  **seven waves, ages 6 to 18** (n = 880 analytic). That is the longest series we have,
  in the cohort with the diagnostic phenotype, so objective sleep and clinical caseness sit in the
  same participants across twelve years.


One qualification, also published: **duration is the only derived sleep variable**
  in any TESS actigraphy paper, and Ranum et al. (2021) says so outright in its limitations —
  "sleep quality, timing, night-to-night variability in sleep duration, sleep architecture, and sleep
  problems were not accounted for". Timing and irregularity, both named in WP1's predictor list, are
  therefore *derivable* rather than held: per-night bedtime and rise time were manually set by
  inspecting each measurement (Ranum et al. 2020). Say derivable, not held. Every figure in this
  section rests on published papers, not on correspondence.

  **[correct]**`B2-S3-worked-example`— Methods · Table B2 step 3

### The worked example describes a linkage that cannot exist


> LSAC SCAS items and ABCD K-SADS and CBCL anxiety indicators enter one multi-group model, yielding Anxiety_latent for joint analysis.


**LSAC has no CBCL variable at all** — zero in 81,919 rows. Across all 20
  cohort pairs the only anchorable one is **LSAC ↔ Ten to Men on the SCAS**, item
  level on both sides: LSAC's `gse16b4` "Worry bad things will happen" and Ten to Men's
  `awdscas22u` "SCAS(22) — Bad things will happen" are the same item. That is also
  the Tier 1 ↔ Tier 2 sex-asymmetry bridge cohort 4 exists to test.


**Independent review cut this down, and it is worth stating precisely.** An earlier
  version of this note said all eight CAS-8 items could be aligned by item number. They cannot.
  LSAC's variables and labels carry no SCAS item numbers, so alignment is wording-only; and Ten to
  Men administers a **12-item subset at waves 1 and 2 only** which omits three of
  LSAC's eight — "Feel nervous", "Wake feeling scared" and "Feel scared for no reason".
  **Five items can anchor, not eight**, and two of the five are asked of 15–17s
  only, which shrinks the linking sample further. Still the only anchorable pair in the set, but
  thin enough that the step 3 text should say so.

  **[correct]**`B2-S3-tess-data-egress`— Methods · Table B2 step 3

### TESS item-level data cannot be pooled centrally


Item-level CBCL, K-SADS and SCID responses are retrievable — and no individual TESS data
  may leave the secure server it is stored on. A multi-group model including cohort 3 has to be
  fitted on the NTNU server or federated, exchanging model quantities rather than records. Step 3
  should say which. Answered well, this is a strength: the harmonisation works without centralising
  participant data.

  **[correct]**`B2-S5-support-seeking-partial`— Methods · Table B2 step 5

### Digital help seeking is measured, in three cohorts


Reassurance seeking and avoidance through a digital channel are genuinely absent from all six.
  Help seeking is not: LSAC asks at 14/15 and 16/17 whether help was sought from the internet or a
  phone help line (`hhs55l`, `ihs55l`), Ten to Men asks comparably, and LSIC
  holds two such items. The word "largely" is carrying the whole exception, and naming it turns a
  soft spot into the WP1→WP3 bridge — the closest slow-clock analogue to the WP3 exposure
  that exists in our data. Keep it secondary.


**Correction, and a caution about counts.** An earlier version of this note said 42
  variables across three cohorts. The real figure is 32 matched rows, and review showed the content
  matters more than the count: **eight of LSAC's eighteen are "seek help next 4 weeks"**
  — intention rather than help sought — four of Ten to Men's fourteen matched a free-text
  field name rather than a digital channel, and one is sexual-health advice rather than mental
  health. LSIC's two are real but sit outside the published run because the governance gate excludes
  that cohort. The harmonisable core is therefore a handful of items, not dozens. It still supports
  the bridge; it does not support a strong quantitative claim.

  **[correct]**`B2-S5-rumination-in-tess`— Methods · WP1 note

### A Tier 1 cohort already tracks rumination longitudinally


Component B lists rumination among the mechanisms historical cohorts cannot observe. TESS
  measures it repeatedly from age 12. The reframe is stronger than the original: *same mechanisms,
  two clocks*. WP1 shows a mechanism moving across years; WP2 asks whether it moves inside a
  person across days. That is a timescale argument, which is what the project is about, rather than a
  data-availability argument the dictionaries contradict.

  **[correct]**`B2-S4-informant-agreement-withdrawal`— Methods · Table B2 step 4

### Social withdrawal is the weakest of the three WP1 predictors


**No informant type is shared.** ABCD is parent and self-report, TESS is
  teacher-rated (Child Social Preference Scale, Conflicted Shyness, seven items, ages 6–14,
  α .76–.87; Stenseng et al. 2022). Step 4 already forbids treating one cohort's
  informant as another's, and it needs stating for withdrawal as it already is for anxiety.


**Correction.** An earlier version said withdrawal was absent from Ten to Men.
  That holds only for the narrow *temperamental* construct — shyness, behavioural
  inhibition — and review found Ten to Men in fact holds SCAS Social Phobia subscale scores,
  items such as "Afraid appear foolish" and "Afraid talk in class", and lifetime **social
  anxiety disorder diagnosis at waves 4, 4.1 and 5**. So cohort 4 is better covered for
  social anxiety than we said; what it lacks is the temperamental shyness measure.


**Suggestion:** use the broad form for cross-cohort replication, present in every
  ingested cohort, and treat the fearful subtype as a secondary analysis in TESS and ABCD where it is
  properly measured. Sleep and late-night device use remain the robust two.

  **[correct]**`B2-S2-thresholds`— Methods · Table B2 step 2

### Two threshold problems, one substantive


**CBCL is on the wrong scale.** B says "CBCL internalising T at or above 65". T
  ≥ 65 and ≥ 70 are the ASEBA cut-points for the *narrowband* syndrome and DSM-oriented
  scales. The *broadband* Internalising scale is T 60–63 borderline,
  **T ≥ 64 clinical**.


**CAS-8 is citable but its derivation is not.** Both published LSAC analyses cite
  Spence, March & Donovan (2019), *Internet Interventions* 18:100268, which states the
  ≥13 male / ≥16 female rule verbatim. That paper attributes the norms to Spence et al. (2014),
  *IJERPH* 11:5113–5132 — which uses the 8-item scale and publishes no norms,
  percentiles or cut-offs. Cite the 2019 paper as the literature does and note the underlying norms
  are unpublished. Also: K-SADS yields a diagnosis, not a threshold, so "diagnostic status" should
  read "meets diagnostic criteria".

  **[correct]**`B1-C3-N · B2-S0-reporter-recorded`— Methods · Table B1, Table B2 step 0

### Two small ones


**TESS N.** Both figures across A and B are right and describe different stages:
  1,250 drawn, 997 at wave 1. Label the stage and the apparent contradiction disappears. The 3,456
  birth-cohort figure sits in the profile's Figure 1, not its running text.


**Step 0's reporter claim.** As written it is falsifiable: 2,159 LSAC
  construct-matched variables carry `Person Label = "Not applicable"`, and Ten to Men's
  dictionary has no informant column at all. Scope it to measures entering the crosswalk, and say
  that where a dictionary carries no informant column the reporter comes from the study design.

## What needs to be added to the grant application

Four assets the dictionaries and the literature turned up that the application does
not yet claim. Each is additive — none requires anything to be taken out.

  - **[asset]** **ABCD and TESS share CBCL and K-SADS.** The first Tier 1 ↔ Tier 1 instrument overlap in the set — the pairing WP1's replication design actually wants. Not anchorable from documentation alone, but item-level responses exist.
  - **[asset]** **TESS is the most digitally instrumented cohort we hold**, not a supporting one: app-level phone use from 16, plus social media, gaming and cyberbullying measures across the adolescent waves, alongside diagnostic interviews.
  - **[asset]** **Conflicted shyness sharpens a predictor.** Coplan's scale separates fearfully inhibited social approach from a non-fearful preference for solitude; only the first is anxiety-relevant, and it is the dimension TESS holds. "Spends time alone" becomes "fearfully inhibited social approach".
  - **[asset]** **A better feasibility citation for WP1's method.** Stenseng et al. (2022) models bidirectional within-person effects between social withdrawal and academic achievement, ages 6–14, in TESS, co-authored by LW — a named WP1 predictor against a named core construct, in a Tier 1 cohort.

## Nine claims we cannot check

Reported as unverifiable rather than false. Absence of evidence is not evidence of
absence, and the tool now refuses to pretend otherwise.

  | Why | Claims | What would close it |


    | **[AStRA]** | 5
      | No codebook exists. Sleep, activity, digital exposure, anxiety caseness and the SDQ cell are unverifiable, not contradicted. If nothing arrives, narrow cohort 5's role to what the published record documents: depressive symptoms, self-esteem, self-efficacy, school adaptation, peer acceptance. |

    | **[Governance]** | 2
      | LSIC is excluded from the published run by design, so its claims cannot be checked there. A governed run under documented First Nations sign-off would close them. |

    | **[CheckPoint]** | 1
      | Child Health CheckPoint is a separate sub-study, so its actigraphy is not in the LSAC survey dictionary. Add the CheckPoint dictionary as its own source. |



## How much to trust these numbers

The tool has been through two rounds of independent review — eight reviewers with
no knowledge of how it was built, tasked with falsifying its findings. They were productive, and not
in a comfortable way.

What they overturned in our own results: the anchor set (eight items became five), the
digital help-seeking count (42 became 32, most of it not what it looked like), the claim that
withdrawal was absent from Ten to Men, and the size of Ten to Men's SCAS. All four are corrected
above.

What they found in the tool: a check reporting **PASS beside evidence that contradicted
it**; an informant classifier that read "primary carer report about study child" as
self-report, the exact substitution step 4 forbids; a display truncation that was silently deciding
audit verdicts; `panic` matching **Hispanic** across 117 ABCD rows; a
governance rule that could never fire, with a passing test over it; and a declared absence reported
as "confirmed empirically" using cohorts that hold no dictionary to confirm it in. All fixed, each
with a regression test — 29 now.

> **One caveat to carry into any use of the matrix.** The variable counts are keyword-match counts, not curated tallies. Review found real false positives inside them: a CBCL Thought Problems item matched on "Nervous", ABCD administrative metadata matched as social context, and ABCD's longitudinal variable variants counted twice. Read the counts as *where to look*, not as *how much is there*. The status, the instrument resolution and the informant are more reliable than the number beside them.

## Where it lives

Code and reports: [github.com/maria-pro/cohort-harmonise](https://github.com/maria-pro/cohort-harmonise).
Browsable report, filterable, with every cell traceable to its wave, informant and instrument:
[maria-pro.github.io/cohort-harmonise](https://maria-pro.github.io/cohort-harmonise/).

Cohorts and constructs are configuration rather than code, so this generalises past anxiety and
past these six cohorts — adding either is a YAML file. Before submission the gate to run is
`harmonise audit --strict --require-cohorts lsac,abcd,ttm,lsic`, which fails on any
mismatch and refuses to report at all if a dictionary is missing. Make the nine edits, re-run it,
commit the output, then tag the release, so the published audit and the submitted text agree.

---

*No participant data was read, produced or redistributed at any point: the tool operates on variable-level metadata only, and no dictionary file is committed. Provenance records a SHA-256 over every file read, so a third party can confirm they ran against the same releases. Cohort 6 is excluded from published output unless First Nations sign-off is documented, and its culturally grounded wellbeing indicators cannot be mapped as a proxy for a diagnostic construct — the engine refuses it. Unpublished documentation supplied by a custodian is held outside the repository pending consent.*
