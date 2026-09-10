"""Tests for the rules the tool is supposed to enforce, not just for the happy path."""
from __future__ import annotations

import pathlib
import sys

import pandas as pd
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from harmonise import config, governance, ingest, linkage, mapping, normalise  # noqa: E402


@pytest.fixture(scope="module")
def cfg():
    return config.load(ROOT)


def test_all_six_cohorts_configured(cfg):
    assert len(cfg.cohorts) == 6
    assert [cfg.cohorts[c]["cohort_number"] for c in cfg.cohort_order()] == [1, 2, 3, 4, 5, 6]


def test_every_non_harmonisable_construct_states_a_reason(cfg):
    """Table B2 step 5 is a check, not a convention."""
    governance.check_declarations(cfg.constructs)  # must not raise

    bad = [dict(c, reason="") for c in cfg.constructs if c.get("declared_non_harmonisable")]
    assert bad, "expected at least one declared non-harmonisable construct in the config"
    with pytest.raises(governance.NonHarmonisableWithoutReason):
        governance.check_declarations(bad)


def test_governed_cohort_is_excluded_by_default(cfg):
    lsic = cfg.cohorts["lsic"]
    assert governance.gate(lsic, include_governed=False) is False
    assert governance.gate(lsic, include_governed=True) is True


def test_governed_wellbeing_indicators_cannot_stand_in_for_diagnosis(cfg):
    """Every status that asserts the indicator measures the construct is refused.

    The earlier version of this rule tested only for "proxy", which made it unreachable:
    the mapping engine assigns proxy solely to mechanism-role constructs while the
    forbidden list holds outcome-role ones. The test passed over dead code.
    """
    lsic = cfg.cohorts["lsic"]
    for status in ("direct", "partial", "proxy"):
        assert governance.enforce(lsic, "anx_symptoms", status) == "governed_not_proxied"
    assert governance.enforce(lsic, "anx_symptoms", "absent") == "absent"
    assert governance.enforce(lsic, "sleep_duration", "direct") == "direct"
    assert governance.enforce(cfg.cohorts["lsac"], "anx_symptoms", "proxy") == "proxy"


def test_the_governance_rule_actually_fires_in_the_pipeline(cfg):
    """The rule must be reachable from a real run, not only from a direct call."""
    spec = cfg.cohorts["lsic"]
    forbidden = (spec["governance"] or {}).get("forbid_proxy_for_constructs") or []
    assert forbidden

    # Built rather than ingested so the rule is exercised wherever the tests run,
    # including CI, which holds no dictionaries.
    wave = str(spec["waves"][0]["wave_id"])
    df = pd.DataFrame({
        "variable": ["asq2_3", "asq2_8"],
        "label": ["SDQ emotional symptoms - many worries",
                  "SDQ emotional symptoms - often unhappy"],
        "item_text": ["", ""], "instrument": ["", ""], "domain": ["Wellbeing", "Wellbeing"],
        "construct_src": ["", ""], "respondent": ["study child", "study child"],
        "confidence": ["", ""], "wave_id": [wave, wave],
    })
    df["_blob"] = df[normalise.BLOB_FIELDS].astype(str).agg(" | ".join, axis=1).str.lower()
    df = normalise.resolve_instruments(df, cfg.instruments)
    cw = mapping.crosswalk({"lsic": df}, cfg)
    hit = cw[cw["construct"].isin(forbidden)]
    assert len(hit), "expected the governed cohort to match a forbidden construct"
    assert set(hit["status"]) <= {"governed_not_proxied", "absent"}, (
        "a governed cohort's indicator was allowed to stand in for a diagnostic construct: "
        + ", ".join(sorted(set(hit["status"])))
    )


def test_era_is_derived_from_calendar_year_not_wave_index(cfg):
    assert normalise.era_for_year(2005, cfg.bands) == "Web2"
    assert normalise.era_for_year(2015, cfg.bands) == "Web3"
    assert normalise.era_for_year(2025, cfg.bands) == "Web4"
    assert normalise.era_for_year("", cfg.bands) == ""


def test_compound_construct_requires_both_terms(cfg):
    """Late-night device use must not match a bedtime item or a screen item alone."""
    rule = cfg.construct("late_night_device_use")["match"]
    blob = pd.Series([
        "what time do you usually go to bed",
        "hours per day of screen time",
        "uses phone in bed after lights out",
    ])
    assert list(mapping.match_construct(blob, rule)) == [False, False, True]


def test_documented_rule_only_applies_to_publication_based_cohorts(cfg):
    con = cfg.construct("sleep_duration")
    blob = pd.Series(["sleep", "sleep"])
    official = pd.Series([False, False])
    documented = pd.Series([False, True])
    strict = mapping.match_construct(blob, con["match"], official, con.get("documented_match"))
    loose = mapping.match_construct(blob, con["match"], documented, con.get("documented_match"))
    assert list(strict) == [False, False]
    assert list(loose) == [False, True]


def test_documented_cohorts_ingest_without_any_dictionary_file(cfg):
    """TESS and AStRA must work with no data directory present at all."""
    for cid in ("tess", "astra"):
        spec = cfg.cohorts[cid]
        df = normalise.build(ingest.ingest_cohort(spec, cfg.resolve), spec,
                             cfg.bands, cfg.instruments)
        assert len(df) > 0
        assert (df["digital_era"].astype(str) != "").all()
        assert (df["citation"].astype(str) != "").all()


def test_step3_falls_back_when_item_wording_is_unavailable(cfg):
    """A cohort documented at domain level cannot anchor a multi-group model."""
    frames = {}
    for cid in ("tess", "astra"):
        spec = cfg.cohorts[cid]
        frames[cid] = normalise.build(ingest.ingest_cohort(spec, cfg.resolve), spec,
                                      cfg.bands, cfg.instruments)
    verdicts, _ = linkage.assess(frames, cfg, tiers=())
    assert len(verdicts)
    assert set(verdicts["step3_verdict"]) == {"inference_harmonisation_only"}
    assert verdicts["fallback"].str.contains("harmonise the inference").all()


def test_every_threshold_carries_a_citation(cfg):
    """A threshold without a citation is a defect, not a default."""
    for t in cfg.thresholds:
        assert t.get("citation"), f"threshold for {t['cohort']} has no citation"
        if t.get("status") == "citation_missing":
            raise AssertionError(f"threshold for {t['cohort']} still needs a citation")


def test_secondary_citations_declare_the_unresolved_primary_source(cfg):
    """Citing usage rather than validation is allowed, but it must say so.

    The LSAC CAS-8 cut-offs are applied in published analyses whose own citations do not
    check out, so the threshold is recorded as cited_secondary and must carry the reason.
    """
    secondary = [t for t in cfg.thresholds if t.get("status") == "cited_secondary"]
    assert secondary, "expected at least one threshold cited from applied usage"
    for t in secondary:
        assert t.get("primary_source_unresolved"), (
            f"{t['cohort']} threshold cites usage but does not say why the primary "
            "source is unresolved")


def test_sex_specific_thresholds_are_recorded_as_such(cfg):
    """LSAC's CAS-8 cut is sex-specific, which makes its caseness outcome
    inherently sex-differentiated rather than sex-adjusted afterwards."""
    lsac = [t for t in cfg.thresholds if t["cohort"] == "lsac" and t["construct"] == "anx_caseness"]
    assert lsac and lsac[0].get("sex_specific") == {"male": 13, "female": 16}


def test_scale_name_overlap_is_not_an_anchor(cfg):
    """Two variables both labelled "SDQ Emotional Symptoms" are one scale reported twice."""
    import pandas as pd
    names = linkage.instrument_name_tokens(cfg.instruments)
    a = pd.DataFrame({"variable": ["caemot"], "item_text": [""],
                      "label": ["SDQ Emotional Symptoms score"]})
    b = pd.DataFrame({"variable": ["asqemot"], "item_text": [""],
                      "label": ["SDQ Emotional Symptoms subscale"]})
    assert linkage.anchor_candidates(a, b, names).empty

    # Genuine item wording in common does anchor.
    a2 = pd.DataFrame({"variable": ["i1"], "item_text": ["I worry that something awful will happen"],
                       "label": ["SDQ item"]})
    b2 = pd.DataFrame({"variable": ["i2"], "item_text": ["I worry something awful might happen to me"],
                       "label": ["SDQ item"]})
    assert not linkage.anchor_candidates(a2, b2, names).empty


def test_a_construct_name_is_not_an_instrument(cfg):
    """Neither an editorial note nor a domain label may resolve an instrument.

    Two ways this went wrong. A config note quoting the claim under audit made the tool
    agree with its own commentary. And "emotional symptoms" — the name of a construct, and
    of the SDQ subscale, and of any inventory's domain heading — was an alias, so a
    reconstructed inventory looked like it had a named instrument.
    """
    spec = cfg.cohorts["astra"]
    df = normalise.build(ingest.ingest_cohort(spec, cfg.resolve), spec,
                         cfg.bands, cfg.instruments)
    resolved = {i for cell in df["instrument_id"] for i in str(cell).split(";") if i}
    assert "sdq" not in resolved and "sdq_emotional" not in resolved
    assert (df["item_text"].astype(str) == "").all()

    labels = pd.Series(["Emotional symptoms", "emotional symptoms | psychological wellbeing"])
    probe = pd.DataFrame({"variable": ["x", "y"], "label": labels, "item_text": ["", ""],
                          "instrument": ["", ""], "domain": ["", ""], "construct_src": ["", ""]})
    probe["_blob"] = probe[normalise.BLOB_FIELDS].astype(str).agg(" | ".join, axis=1).str.lower()
    out = normalise.resolve_instruments(probe, cfg.instruments)
    assert all(v == "" for v in out["instrument_id"]), \
        "a bare construct name resolved to an instrument"


def test_full_pipeline_runs_with_no_dictionaries_at_all(tmp_path):
    """The path CI takes, and the one that broke.

    With no dictionary files present only the publication-documented cohorts ingest, so
    every claim about a cohort that did not load must report UNVERIFIABLE rather than
    raising. An audit has to run on whatever subset of dictionaries the operator holds.
    """
    from harmonise import cli

    rc = cli.main(["run", "--root", str(ROOT), "--outdir", str(tmp_path),
                   "--no-publish-docs"])
    assert rc == 0
    for name in ("coverage_matrix.html", "claim_audit.csv", "provenance.json",
                 "non_harmonisable_register.csv", "custodian_template_tess.csv"):
        assert (tmp_path / name).exists(), f"{name} not written"

    audit = pd.read_csv(tmp_path / "claim_audit.csv")
    not_ingested = audit[audit["evidence"].astype(str).str.contains("was not ingested")]
    assert len(not_ingested), "expected claims about absent cohorts to be reported"
    assert (not_ingested["verdict"] == "UNVERIFIABLE").all()


def test_no_cohort_is_credited_with_more_waves_than_it_has(cfg):
    """A dictionary lists every session a study ever ran, not its waves.

    ABCD's dictionary covers 32 sessions — 8 annual assessments plus mid-year check-ins,
    a screener and four substudies — so counting sessions as waves credited it with 31
    waves against the 8 it actually has.
    """
    for cid, spec in cfg.cohorts.items():
        declared = spec.get("waves_per_participant")
        assert declared, f"{cid} does not declare waves_per_participant"
        primary = [w for w in spec["waves"] if w.get("wave_kind") == "primary"]
        assert primary, f"{cid} has no primary waves"
        assert all(w.get("wave_kind") for w in spec["waves"]), \
            f"{cid} has a wave with no wave_kind"
        if cid != "astra":  # three parallel cohorts, three waves each
            assert len(primary) == declared, (
                f"{cid}: {len(primary)} primary waves but declares {declared} per participant")


def test_abcd_has_eight_waves_not_thirty_two(cfg):
    spec = cfg.cohorts["abcd"]
    kinds = {}
    for w in spec["waves"]:
        kinds.setdefault(w["wave_kind"], []).append(w["wave_id"])
    assert len(kinds["primary"]) == 8
    assert spec["waves_per_participant"] == 8
    assert len(spec["waves"]) == 32
    assert set(kinds) == {"primary", "mid_year", "screener", "substudy"}


def test_short_patterns_do_not_match_inside_longer_words(cfg):
    """"panic" matched "Hispanic", tagging ABCD ethnicity items as anxiety caseness."""
    import pandas as pd
    blob = pd.Series(["hispanic origin of participant",
                      "diagnosis of panic disorder",
                      "worried about a related matter",
                      "uses phone late at night in bed"])
    for cid in ("anx_symptoms", "anx_caseness"):
        hits = list(mapping.match_construct(blob, cfg.construct(cid)["match"]))
        assert hits[0] is False, f"{cid} matched 'Hispanic'"
        assert hits[1] is True, f"{cid} missed 'panic disorder'"

    late = cfg.construct("late_night_device_use")["match"]
    assert list(mapping.match_construct(blob, late)) == [False, False, False, True]


def test_contraceptive_withdrawal_is_not_social_withdrawal(cfg):
    import pandas as pd
    blob = pd.Series(["Method used to prevent pregnancy - Withdrawal",
                      "Child is socially withdrawn from peers"])
    rule = cfg.construct("withdrawal_behavioural")["match"]
    assert list(mapping.match_construct(blob, rule)) == [False, True]


def test_withdrawal_subtypes_are_kept_apart(cfg):
    """The CSPS separates fearful shyness from unsociability; only the first is
    anxiety-relevant, and pooling them is the false equivalence step 5 refuses."""
    import pandas as pd
    fearful = cfg.construct("withdrawal_fearful")
    unsociable = cfg.construct("withdrawal_unsociable")

    assert "withdrawal_unsociable" in fearful["not_interchangeable_with"]
    assert fearful.get("not_interchangeable_reason")
    assert fearful["core"] and not unsociable["core"]

    blob = pd.Series([
        "The child declines social initiatives from other children because he/she is shy",
        "The child prefers to be alone rather than play with others",
    ])
    assert list(mapping.match_construct(blob, fearful["match"])) == [True, False]
    assert list(mapping.match_construct(blob, unsociable["match"])) == [False, True]


def test_conflicted_shyness_resolves_to_its_subscale(cfg):
    ids = {i["id"] for i in cfg.instruments}
    assert {"csps_conflicted_shyness", "csps_unsociability"} <= ids
    df = pd.DataFrame({
        "variable": ["a", "b"],
        "label": ["Conflicted shyness subscale score", "Unsociability subscale score"],
        "item_text": ["", ""], "instrument": ["", ""], "domain": ["", ""],
        "construct_src": ["", ""],
    })
    df["_blob"] = df[normalise.BLOB_FIELDS].astype(str).agg(" | ".join, axis=1).str.lower()
    out = normalise.resolve_instruments(df, cfg.instruments)
    assert "csps_conflicted_shyness" in out.loc[0, "instrument_id"]
    assert "csps_unsociability" in out.loc[1, "instrument_id"]


def test_instrument_override_resolves_an_unnamed_instrument(cfg):
    """LSAC administers the CAS-8 but names it only on the derived total."""
    spec = cfg.cohorts["lsac"]
    rules = spec["source"].get("instrument_overrides")
    assert rules, "LSAC must declare the CAS-8 item override"
    df = pd.DataFrame({"variable": ["gse16b1", "hse16b8", "gspenceanx", "hhs55l"],
                       "instrument_id": ["", "", "scas_cas8", ""],
                       "wave_id": ["5", "6", "5", "6"]})
    out = normalise.apply_instrument_overrides(df, spec)
    got = [set(v.split(";")) - {""} for v in out["instrument_id"]]
    assert "scas_cas8" in got[0] and "scas_cas8" in got[1], "CAS-8 items not resolved"
    assert got[2] == {"scas_cas8"}, "existing resolution must not be duplicated"
    assert got[3] == set(), "unrelated variables must not be tagged"


def test_public_mode_ignores_local_overlays():
    """The committed artefacts must not be derived from unpublished custodian material."""
    local = ROOT / "configs" / "cohorts" / "local"
    if not any(local.glob("*.yaml")):
        pytest.skip("no local overlay present to test against")
    with_local = config.load(ROOT, use_local=True)
    public = config.load(ROOT, use_local=False)
    overlaid = [c for c, s in with_local.cohorts.items() if s.get("_local_overlay")]
    assert overlaid, "expected at least one cohort to carry an overlay"
    for cid in overlaid:
        assert not public.cohorts[cid].get("_local_overlay")
        assert public.cohorts[cid]["source"]["entries"] != \
            with_local.cohorts[cid]["source"]["entries"], \
            f"{cid}: --public did not fall back to the published inventory"


def test_alias_boundaries_admit_suffixes_but_not_collisions(cfg):
    """Short aliases are acronyms; long ones are phrases or stems. Both must work."""
    df = pd.DataFrame({
        "variable": ["a", "b", "c", "d", "e"],
        "label": ["Unsociability subscale score",       # stem must reach the suffix
                  "SDQ emotional symptoms subscale",     # phrase must reach the plural
                  "CBC Literacy environment (acbclite)", # must NOT resolve to CBCL
                  "Self-Description Questionnaire SDQ-I",# must NOT resolve to the SDQ
                  "K10 score"],                          # acronym plus a following word
        "item_text": [""] * 5, "instrument": [""] * 5,
        "domain": [""] * 5, "construct_src": [""] * 5,
    })
    df["_blob"] = df[normalise.BLOB_FIELDS].astype(str).agg(" | ".join, axis=1).str.lower()
    out = normalise.resolve_instruments(df, cfg.instruments)
    got = [set(v.split(";")) - {""} for v in out["instrument_id"]]
    assert "csps_unsociability" in got[0]
    assert "sdq_emotional" in got[1]
    assert "cbcl" not in got[2], "matched CBCL inside 'acbclite'"
    assert "sdq" not in got[3], "matched the SDQ inside 'SDQ-I'"
    assert "k10" in got[4]


def test_informant_families_never_collapse_a_parent_report_into_self_report(cfg):
    """The elif chain read "primary carer report about study child" as self-report,
    which is the substitution Table B2 step 4 exists to forbid."""
    f = normalise.informant_families
    assert f({"primary carer report about study child"}) == {"parent", "self"}
    assert f({"parent interview; child interview"}) == {"parent", "self"}
    assert f({"teacher rating"}) == {"teacher"}
    assert f({"peer sociometric nominations"}) == {"peer"}
    assert f({"not stated in dictionary"}) == {"unclassified"}
    assert f(set()) == set()
    assert f({"hip-worn actigraphy"}) == {"objective"}


def test_digit_ending_acronyms_do_not_absorb_another_digit(cfg):
    df = pd.DataFrame({
        "variable": ["a", "b", "c", "d"],
        "label": ["K10 score", "k100 arbitrary variable", "GAD7 total", "gad78 nonsense"],
        "item_text": [""] * 4, "instrument": [""] * 4,
        "domain": [""] * 4, "construct_src": [""] * 4,
    })
    df["_blob"] = df[normalise.BLOB_FIELDS].astype(str).agg(" | ".join, axis=1).str.lower()
    got = [set(v.split(";")) - {""}
           for v in normalise.resolve_instruments(df, cfg.instruments)["instrument_id"]]
    assert "k10" in got[0] and "k10" not in got[1], "k10 absorbed a following digit"
    assert "gad7" in got[2] and "gad7" not in got[3], "gad7 absorbed a following digit"


def test_self_description_questionnaire_is_not_the_sdq(cfg):
    df = pd.DataFrame({
        "variable": ["a", "b"],
        "label": ["Self-esteem measured with SDQ-I and SDQ-II", "SDQ-25 total difficulties"],
        "item_text": ["", ""], "instrument": ["", ""], "domain": ["", ""], "construct_src": ["", ""],
    })
    df["_blob"] = df[normalise.BLOB_FIELDS].astype(str).agg(" | ".join, axis=1).str.lower()
    got = [set(v.split(";")) - {""}
           for v in normalise.resolve_instruments(df, cfg.instruments)["instrument_id"]]
    assert "sdq" not in got[0], "Self-Description Questionnaire resolved as the SDQ"
    assert "sdq" in got[1]


def test_a_claim_cannot_pass_while_its_own_evidence_contradicts_it(cfg):
    """construct_not_pooled had a hard-coded PASS. An auditor that reports green beside
    contradicting evidence is worse than no auditor."""
    src = (ROOT / "src" / "harmonise" / "audit.py").read_text()
    block = src[src.index('elif t == "construct_not_pooled"'):src.index('elif t == "respondent_recorded"')]
    assert 'verdict = "PASS"\n' not in block, "verdict is unconditional again"
    assert "only_a or only_b" in block
