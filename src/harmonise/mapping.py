"""Table B2 steps 1, 2 and 4 — the construct crosswalk and the coverage matrix.

Mapping status per construct x cohort x wave:
  direct                measured with an instrument the application names for this construct
  partial               the construct is measured, but not with a named instrument
  proxy                 only a nearby indicator is available
  non_harmonisable      declared under step 5, with a mandatory reason
  governed_not_proxied  a governed cohort's indicator that must not stand in for a diagnosis
  absent                nothing in the dictionary matches
"""
from __future__ import annotations

import re

import pandas as pd

from . import governance

STATUS_ORDER = ["direct", "partial", "proxy", "governed_not_proxied", "non_harmonisable", "absent"]


def _compile_any(patterns) -> re.Pattern:
    # Config patterns use plain groups for readability; make them non-capturing so the
    # combined alternation does not look like an extraction pattern to pandas.
    safe = [re.sub(r"\((?!\?)", "(?:", p) for p in patterns]
    return re.compile("|".join(safe), re.I)


def _rule_hit(blob: pd.Series, rule: dict) -> pd.Series:
    if "all_of_groups" in rule:
        hit = pd.Series(True, index=blob.index)
        for group in rule["all_of_groups"]:
            hit &= blob.str.contains(_compile_any(group), regex=True, na=False)
    else:
        hit = blob.str.contains(_compile_any(rule["any_of"]), regex=True, na=False)

    for ex in rule.get("exclude", []) or []:
        hit &= ~blob.str.contains(re.compile(re.escape(ex), re.I), regex=True, na=False)
    return hit


def match_construct(blob: pd.Series, rule: dict, documented: pd.Series | None = None,
                    doc_rule: dict | None = None) -> pd.Series:
    """A construct's match rule.

    `all_of_groups` requires one hit from every group, which is how a compound construct
    such as late-night device use is expressed: a night term AND a device term.

    Cohorts with no custodian dictionary are inventoried at domain level, so item-wording
    patterns cannot match them. `documented_match` is the coarser rule applied to those
    rows only, which keeps precision on real dictionaries without silently scoring a
    domain-level cohort as absent.
    """
    if not rule:
        return pd.Series(False, index=blob.index)
    hit = _rule_hit(blob, rule)
    if doc_rule is not None and documented is not None and documented.any():
        hit = hit | (_rule_hit(blob, doc_rule) & documented)
    return hit


def crosswalk(frames: dict, cfg, progress=None) -> pd.DataFrame:
    """One row per (construct, cohort, wave) with a status and traceable examples."""
    governance.check_declarations(cfg.constructs)
    rows = []

    for n_done, con in enumerate(cfg.constructs, 1):
        if progress:
            progress(f"  [{n_done}/{len(cfg.constructs)}] {con['id']}")
        cid = con["id"]
        preferred = set(con.get("preferred_instruments", []) or [])
        declared_nh = bool(con.get("declared_non_harmonisable"))

        for cohort_id, df in frames.items():
            spec = cfg.cohorts[cohort_id]
            documented = pd.Series(spec["evidence_tier"] != "official_dictionary", index=df.index)
            hit = match_construct(df["_blob"], con.get("match"),
                                  documented, con.get("documented_match"))
            sub = df.loc[hit]

            declared_waves = [str(w["wave_id"]) for w in spec.get("waves", [])]
            wave_key = sub["wave_id"].astype(str)
            seen = set(wave_key.unique())
            # One pass over the matched rows rather than one filter per declared wave:
            # ABCD alone has 32 sessions against 430,000 rows.
            groups = {w: g for w, g in sub.groupby(wave_key, sort=False)}
            empty = sub.iloc[0:0]

            for wave in declared_waves:
                wsub = groups.get(wave, empty)
                n = len(wsub)
                inst_ids = sorted({i for cell in wsub["instrument_id"].unique()
                                   for i in str(cell).split(";") if i})

                if declared_nh:
                    status = "non_harmonisable"
                elif n == 0:
                    status = "absent"
                elif preferred and (preferred & set(inst_ids)):
                    status = "direct"
                elif con.get("role") in ("mechanism",):
                    status = "proxy"
                elif preferred:
                    status = "partial"
                else:
                    status = "direct" if n >= 3 else "partial"

                status = governance.enforce(spec, cid, status)

                wmeta = next((w for w in spec.get("waves", []) if str(w["wave_id"]) == wave), {})
                examples = wsub["variable"].astype(str).head(3).tolist()
                # Labels are carried for the internal view only. The published payload
                # omits them, because bulk variable labels reproduce dictionary content
                # that ABCD's NDA and the AIFS terms do not let us redistribute.
                example_labels = wsub["label"].astype(str).str.slice(0, 140).head(3).tolist()
                rows.append({
                    "construct": cid,
                    "construct_label": con["label"],
                    "role": con.get("role", ""),
                    "core": bool(con.get("core", False)),
                    "cohort": cohort_id,
                    "cohort_number": spec["cohort_number"],
                    "tier": str(spec["tier"]),
                    "evidence_tier": spec["evidence_tier"],
                    "wave_id": wave,
                    "wave_kind": wmeta.get("wave_kind", ""),
                    "wave_year": wmeta.get("wave_year", ""),
                    "year_source": wmeta.get("year_source", ""),
                    "digital_era": wmeta.get("digital_era", ""),
                    "status": status,
                    "n_variables": n,
                    "instruments_matched": "; ".join(inst_ids),
                    "respondents": "; ".join(sorted({r for r in wsub["respondent"].unique() if r})[:4]),
                    "example_variables": "; ".join(examples),
                    "example_labels": " | ".join(example_labels),
                    "reason": con.get("reason", "").strip() if declared_nh else "",
                    "governance_required": bool((spec.get("governance") or {}).get("restricted", False)),
                })
            unknown = seen - set(declared_waves)
            if unknown:
                n_undeclared = int(sum(len(groups[w]) for w in unknown))
                rows.append({
                    "construct": cid, "construct_label": con["label"], "role": con.get("role", ""),
                    "core": bool(con.get("core", False)), "cohort": cohort_id,
                    "cohort_number": spec["cohort_number"], "tier": str(spec["tier"]),
                    "evidence_tier": spec["evidence_tier"],
                    "wave_id": "UNDECLARED:" + ",".join(sorted(unknown)[:6]),
                    "wave_kind": "", "wave_year": "", "year_source": "", "digital_era": "",
                    "status": "undeclared_wave", "n_variables": n_undeclared,
                    "instruments_matched": "", "respondents": "", "example_variables": "",
                    "example_labels": "",
                    "reason": "", "governance_required": False,
                })
    return pd.DataFrame(rows)


def cohort_construct_summary(cw: pd.DataFrame) -> pd.DataFrame:
    """Collapse waves: the best status a cohort achieves for each construct.

    Wave counts are over PRIMARY waves only. A cohort's dictionary lists every session
    it ever ran — ABCD's includes mid-year check-ins, a screener and four substudies —
    and counting those as waves would credit ABCD with 31 where it has 8, making a
    cross-cohort comparison meaningless. Supplementary sessions are counted separately
    rather than discarded.
    """
    rank = {s: i for i, s in enumerate(STATUS_ORDER)}
    d = cw[~cw["wave_id"].astype(str).str.startswith("UNDECLARED")].copy()
    d["_rank"] = d["status"].map(rank).fillna(99)
    idx = d.groupby(["construct", "cohort"])["_rank"].idxmin()
    best = d.loc[idx, ["construct", "construct_label", "core", "role", "cohort",
                       "cohort_number", "status", "n_variables", "instruments_matched",
                       "evidence_tier", "reason"]]

    has_data = d[d["status"].isin(["direct", "partial", "proxy"])]
    primary = (has_data[has_data["wave_kind"] == "primary"]
               .groupby(["construct", "cohort"])["wave_id"].nunique()
               .rename("waves_with_data").reset_index())
    supp = (has_data[has_data["wave_kind"].isin(
                ["mid_year", "substudy", "screener", "mailout", "topup", "covid_split"])]
            .groupby(["construct", "cohort"])["wave_id"].nunique()
            .rename("supplementary_sessions_with_data").reset_index())
    out = (best.merge(primary, on=["construct", "cohort"], how="left")
                .merge(supp, on=["construct", "cohort"], how="left"))
    return out.fillna({"waves_with_data": 0, "supplementary_sessions_with_data": 0})


def non_harmonisable_register(cw: pd.DataFrame, cfg) -> pd.DataFrame:
    """Table B2 step 5 as data: named construct, reason, cohorts affected, and whether
    the dictionaries confirm the absence rather than the claim asserting it."""
    rows = []
    for con in cfg.constructs:
        if not con.get("declared_non_harmonisable"):
            continue
        sub = cw[cw["construct"] == con["id"]]
        by_cohort = sub.groupby("cohort")["n_variables"].sum()
        confirmed = [c for c, n in by_cohort.items() if n == 0]
        contradicted = {c: int(n) for c, n in by_cohort.items() if n > 0}
        rows.append({
            "construct": con["id"],
            "construct_label": con["label"],
            "reason": con["reason"].strip(),
            "cohorts_declared": "; ".join(con.get("affects_cohorts", [])),
            "absence_confirmed_in": "; ".join(sorted(confirmed)),
            "possible_partial_coverage": "; ".join(f"{k}({v})" for k, v in sorted(contradicted.items())),
            "captured_instead_by": "WP2 / WP3",
        })
    return pd.DataFrame(rows)
