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


def test_governed_wellbeing_indicators_cannot_become_a_proxy_for_diagnosis(cfg):
    lsic = cfg.cohorts["lsic"]
    assert governance.enforce(lsic, "anx_symptoms", "proxy") == "governed_not_proxied"
    assert governance.enforce(lsic, "anx_symptoms", "direct") == "direct"
    assert governance.enforce(cfg.cohorts["lsac"], "anx_symptoms", "proxy") == "proxy"


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


def test_config_notes_do_not_resolve_instruments(cfg):
    """An editorial note quoting a claim must not become evidence for that claim.

    The AStRA inventory records that the application names the SDQ while the located
    sources do not. That note must not cause the tool to resolve the SDQ for AStRA.
    """
    spec = cfg.cohorts["astra"]
    df = normalise.build(ingest.ingest_cohort(spec, cfg.resolve), spec,
                         cfg.bands, cfg.instruments)
    resolved = {i for cell in df["instrument_id"] for i in str(cell).split(";") if i}
    assert "sdq" not in resolved and "sdq_emotional" not in resolved
    assert (df["item_text"].astype(str) == "").all()


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
