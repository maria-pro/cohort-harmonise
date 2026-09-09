"""Checks the application's own assertions against the dictionaries.

This is the part that de-risks the application rather than illustrating it. Each claim
records where it appears in the submitted text, what it asserts, and what the dictionaries
say. Verdicts are PASS, MISMATCH or UNVERIFIABLE, and UNVERIFIABLE is a real answer: it
marks a claim that no held dictionary can settle either way.
"""
from __future__ import annotations

import pandas as pd

from .mapping import match_construct


def _instrument_rows(df: pd.DataFrame, instrument_id) -> pd.DataFrame:
    """instrument_id is a ';'-joined multi-label field; accept one id or a list."""
    ids = [instrument_id] if isinstance(instrument_id, str) else list(instrument_id)
    have = df["instrument_id"].astype(str).str.split(";")
    keep = have.map(lambda lst: any(i in lst for i in ids))
    return df[keep]


def _tiers(cfg, cohorts):
    return {c: cfg.cohorts[c]["evidence_tier"] for c in cohorts}


def _tier_aware(cfg, failing) -> tuple[str, str]:
    """Absence of evidence is not evidence of absence.

    A cohort read from a custodian dictionary can genuinely contradict a claim. A cohort
    inventoried from publications can only fail to confirm it, so the verdict there is
    UNVERIFIABLE and the note says which cohorts and why.
    """
    HARD = {"official_dictionary", "custodian_documentation"}
    hard = [c for c in failing if cfg.cohorts[c]["evidence_tier"] in HARD]
    soft = [c for c in failing if c not in hard]
    if hard:
        return "MISMATCH", ""
    if soft:
        return "UNVERIFIABLE", (
            "not confirmed for " + ", ".join(f"{c} ({cfg.cohorts[c]['evidence_tier']})" for c in soft)
            + " — no custodian dictionary held, so absence here is unproven")
    return "PASS", ""


def _sorted_waves(spec, waves):
    order = {str(w["wave_id"]): i for i, w in enumerate(spec.get("waves", []))}
    return sorted({str(w) for w in waves}, key=lambda w: order.get(w, 999))


def run(frames: dict, cw: pd.DataFrame, link: pd.DataFrame, cfg) -> pd.DataFrame:
    rows = []
    for claim in cfg.claims_doc["claims"]:
        chk = claim["check"]
        t = chk["type"]
        verdict, evidence = "UNVERIFIABLE", ""

        # A claim about a cohort whose dictionary was not read in this run cannot be
        # checked in this run. Say so, rather than crashing or scoring it on absence:
        # the audit must run on whatever subset of dictionaries the operator holds.
        target = chk.get("cohort")
        if target and target not in frames:
            rows.append({
                "claim_id": claim["id"],
                "source": claim["source"],
                "assertion": " ".join(str(claim["assertion"]).split()),
                "verdict": "UNVERIFIABLE",
                "evidence": (f"cohort '{target}' was not ingested in this run, so the claim "
                             "was not checked. Supply its dictionary, or --include-governed "
                             "for a governed cohort, and run again."),
                "note": " ".join(str(claim.get("known_risk", "")).split()),
            })
            continue

        if t == "manual":
            verdict = chk.get("verdict", "UNVERIFIABLE")
            evidence = " ".join(str(chk.get("note", "")).split())

        elif t == "instrument_in_cohort":
            c = chk["cohort"]
            if c not in frames:
                evidence = f"cohort {c} not ingested"
            else:
                tier = cfg.cohorts[c]["evidence_tier"]
                sub = _instrument_rows(frames[c], chk["instrument"])
                # An inventory entry we ourselves marked unverified cannot confirm a claim:
                # that would be the audit agreeing with its own reconstruction.
                conf = sub["confidence"].astype(str)
                unverified = sub[conf == "unverified"]
                sub = sub[conf != "unverified"]
                n = len(sub)
                if n >= chk.get("min_vars", 1):
                    verdict = "PASS"
                elif tier in ("official_dictionary", "custodian_documentation"):
                    verdict = "MISMATCH"
                else:
                    verdict = "UNVERIFIABLE"
                waves = _sorted_waves(cfg.cohorts[c], sub["wave_id"].unique())
                evidence = (f"{n} variables resolve to instrument '{chk['instrument']}' in "
                            f"{c} ({tier})")
                if waves:
                    evidence += f"; waves {', '.join(waves[:14])}"
                if n:
                    evidence += f"; e.g. {', '.join(sub['variable'].astype(str).head(3))}"
                if len(unverified):
                    evidence += (f"; {len(unverified)} inventory entr(ies) mention it but are"
                                 " marked unverified and are excluded from the verdict")
                if verdict == "UNVERIFIABLE":
                    evidence += (". No custodian dictionary is held for this cohort, so the"
                                 " instrument can be neither confirmed nor ruled out here")

        elif t == "instrument_in_cohort_before_wave":
            c = chk["cohort"]
            spec = cfg.cohorts[c]
            order = [str(w["wave_id"]) for w in spec.get("waves", [])]
            cut = order.index(str(chk["before_wave"])) if str(chk["before_wave"]) in order else len(order)
            earlier = set(order[:cut])
            want = chk.get("instruments") or [chk["instrument"]]
            sub = _instrument_rows(frames[c], want)
            sub = sub[sub["wave_id"].astype(str).isin(earlier)]
            verdict = "PASS" if len(sub) >= chk.get("min_vars", 1) else "MISMATCH"
            named = sorted({n for n in sub["instrument"].astype(str).unique() if n.strip()})
            evidence = (f"{len(sub)} variables for {'/'.join(want)} in {c} before wave "
                        f"{chk['before_wave']}; waves "
                        f"{', '.join(_sorted_waves(spec, sub['wave_id'].unique())) or '(none)'}")
            if named:
                evidence += "; instruments named in the dictionary: " + "; ".join(n[:60] for n in named[:3])

        elif t == "instrument_first_wave":
            c = chk["cohort"]
            spec = cfg.cohorts[c]
            sub = _instrument_rows(frames[c], chk["instrument"])
            waves = _sorted_waves(spec, sub["wave_id"].unique())
            first = waves[0] if waves else None
            exp = str(chk["expected_first_wave"])
            verdict = ("PASS" if first == exp
                       else "MISMATCH" if first
                       else "UNVERIFIABLE")
            evidence = (f"'{chk['instrument']}' appears in {c} at waves "
                        f"{', '.join(waves) if waves else '(none)'}; application says from wave {exp}"
                        + (f"; first observed wave {first}" if first else ""))

        elif t == "construct_in_all_cohorts":
            wanted = chk["constructs"]
            missing = []
            detail = []
            for c in cfg.cohort_order():
                if c not in frames:
                    continue
                sub = cw[(cw["cohort"] == c) & (cw["construct"].isin(wanted))]
                n = int(sub["n_variables"].sum())
                detail.append(f"{c}={n}")
                if n == 0:
                    missing.append(c)
            verdict, note = _tier_aware(cfg, missing)
            evidence = "variables matched: " + ", ".join(detail)
            if missing:
                evidence += f"; nothing matched in {', '.join(missing)}"
            if note:
                evidence += f". {note}"

        elif t == "core_completeness":
            core = [c["id"] for c in cfg.constructs if c.get("core")]
            gaps = []
            for c in cfg.cohort_order():
                if c not in frames:
                    continue
                for cid in core:
                    n = int(cw[(cw["cohort"] == c) & (cw["construct"] == cid)]["n_variables"].sum())
                    if n == 0:
                        gaps.append(f"{c}:{cid}")
            failing = sorted({g.split(":")[0] for g in gaps})
            verdict, note = _tier_aware(cfg, failing)
            evidence = ("every core construct is held by every ingested cohort"
                        if not gaps else "core construct not found for " + ", ".join(gaps))
            if note:
                evidence += f". {note}"

        elif t == "construct_absent":
            HARD = {"official_dictionary", "custodian_documentation"}
            found, checked, unchecked = [], [], []
            for c in chk["cohorts"]:
                if c not in frames:
                    unchecked.append(f"{c} (not ingested)")
                    continue
                if cfg.cohorts[c]["evidence_tier"] not in HARD:
                    unchecked.append(f"{c} ({cfg.cohorts[c]['evidence_tier']})")
                    continue
                checked.append(c)
                for cid in chk["constructs"]:
                    n = int(cw[(cw["cohort"] == c) & (cw["construct"] == cid)]["n_variables"].sum())
                    if n:
                        found.append(f"{c}:{cid}({n})")
            if found:
                verdict = "MISMATCH"
                evidence = "candidate matches found for " + ", ".join(found[:12])
            elif not checked:
                verdict = "UNVERIFIABLE"
                evidence = "no cohort in this claim has a dictionary that could confirm absence"
            else:
                # An absence is only "confirmed empirically" where a dictionary exists to
                # confirm it in. A publication-based inventory lists domains someone chose
                # to describe, so silence in it is not evidence.
                verdict = "PASS" if not unchecked else "UNVERIFIABLE"
                evidence = ("absence confirmed against the dictionaries of "
                            + ", ".join(checked))
                if unchecked:
                    evidence += ("; NOT confirmable for " + ", ".join(unchecked)
                                 + ", where no dictionary exists, so silence is not evidence")

        elif t == "construct_present_in_any":
            cid = chk["construct"]
            found = {}
            for c in chk["cohorts"]:
                if c not in frames:
                    continue
                n = int(cw[(cw["cohort"] == c) & (cw["construct"] == cid)]["n_variables"].sum())
                if n:
                    found[c] = n
            ingested = [c for c in chk["cohorts"] if c in frames]
            if not ingested:
                rows.append({
                    "claim_id": claim["id"], "source": claim["source"],
                    "assertion": " ".join(str(claim["assertion"]).split()),
                    "verdict": "UNVERIFIABLE",
                    "evidence": "none of the listed cohorts were ingested in this run",
                    "note": " ".join(str(claim.get("known_risk", "")).split()),
                })
                continue
            expect_present = chk.get("expect", "present") == "present"
            verdict = "MISMATCH" if bool(found) == expect_present else "PASS"
            if found:
                ex = []
                for c in found:
                    row = cw[(cw["cohort"] == c) & (cw["construct"] == cid) &
                             (cw["example_variables"].astype(str) != "")]
                    if len(row):
                        ex.append(f"{c}: {row.iloc[0]['example_variables']}")
                evidence = ("the construct IS measured in "
                            + ", ".join(f"{c} ({n} variables)" for c, n in found.items())
                            + (". Examples — " + "; ".join(ex[:3]) if ex else ""))
            else:
                evidence = "no cohort holds this construct"

        elif t == "respondent_recorded":
            # Judged on rows matched to a target construct. Identifier and administrative
            # variables legitimately have no informant, and counting them would manufacture
            # a failure out of a dictionary doing the right thing.
            matched = set(cw.loc[cw["status"].isin(["direct", "partial", "proxy"]), "cohort"])
            empty, single = [], []
            for c, df in frames.items():
                if c not in matched:
                    continue
                keep = pd.Series(False, index=df.index)
                for con in cfg.constructs:
                    if con.get("declared_non_harmonisable"):
                        continue
                    keep = keep | match_construct(
                        df["_blob"], con.get("match"),
                        pd.Series(cfg.cohorts[c]["evidence_tier"] != "official_dictionary",
                                  index=df.index),
                        con.get("documented_match"))
                d = df.loc[keep, "respondent"].astype(str).str.strip()
                blank = int((d == "").sum())
                nd = d[d != ""].nunique()
                if blank:
                    empty.append(f"{c}:{blank} rows")
                if nd < chk.get("min_distinct", 2):
                    single.append(c)
            verdict = "PASS" if not empty else "MISMATCH"
            evidence = ("the informant is populated on every construct-matched row in every cohort"
                        if not empty else "informant missing on construct-matched rows: " + ", ".join(empty))
            if single:
                evidence += (f". Single-informant by design in {', '.join(single)}: the dictionary "
                             "carries no informant column, so it is set from the study design and "
                             "recorded as such rather than read from a cell")

        elif t == "field_complete":
            f = chk["field"]
            bad = {}
            for c, df in frames.items():
                v = df[f].astype(str).str.strip()
                n = int((v == "").sum())
                if n:
                    bad[c] = n
            verdict = "PASS" if not bad else "MISMATCH"
            evidence = (f"'{f}' is populated on every row"
                        if not bad else f"'{f}' empty on " + ", ".join(f"{k}:{v} rows" for k, v in bad.items()))

        elif t == "linkage_reported":
            want_tier = str(chk.get("tier", "") or "")
            sub = link if not want_tier else link[(link["tier_a"] == want_tier) &
                                                  (link["tier_b"] == want_tier)]
            feasible = sub[sub["step3_verdict"] == "anchor_candidates_found"]
            verdict = "PASS" if len(sub) else "UNVERIFIABLE"
            evidence = (f"{len(sub)} cohort pairs assessed; "
                        f"{len(feasible)} with anchor candidates; "
                        f"{len(sub) - len(feasible)} fall back to harmonising the inference")
            if len(feasible):
                evidence += ". Feasible: " + "; ".join(
                    f"{r.cohort_a}-{r.cohort_b} on {r.usable_instruments} ({r.n_anchor_candidates} candidates)"
                    for r in feasible.itertuples())

        elif t == "linkage_pair":
            a, b = chk["cohort_a"], chk["cohort_b"]
            sub = link[(link["construct"] == chk["construct"]) &
                       (((link["cohort_a"] == a) & (link["cohort_b"] == b)) |
                        ((link["cohort_a"] == b) & (link["cohort_b"] == a)))]
            if sub.empty:
                verdict, evidence = "UNVERIFIABLE", f"pair {a}-{b} was not assessed"
            else:
                r = sub.iloc[0]
                verdict = "PASS" if r["step3_verdict"] == "anchor_candidates_found" else "MISMATCH"
                evidence = (f"shared instruments: {r['shared_instruments'] or 'none'}"
                            f"; items per shared instrument: {r['items_per_shared_instrument'] or 'n/a'}"
                            f"; verdict {r['step3_verdict']}")
                if r["why_not"]:
                    evidence += f"; {r['why_not']}"
                best = link[(link["step3_verdict"] == "anchor_candidates_found")]
                if len(best):
                    evidence += (". Pairs that DO share an anchorable item bank: "
                                 + "; ".join(f"{x.cohort_a}-{x.cohort_b} on {x.usable_instruments}"
                                             f" ({x.n_anchor_candidates} candidates)"
                                             for x in best.itertuples()))

        elif t == "thresholds_cited":
            miss = [f"{th['cohort']}/{th.get('instrument')}" for th in cfg.thresholds
                    if th.get("status") == "citation_missing"]
            verdict = "PASS" if not miss else "MISMATCH"
            evidence = ("every threshold carries a citation"
                        if not miss else f"{len(miss)} thresholds lack a citation: " + ", ".join(miss))

        rows.append({
            "claim_id": claim["id"],
            "source": claim["source"],
            "assertion": " ".join(str(claim["assertion"]).split()),
            "verdict": verdict,
            "evidence": evidence,
            "note": " ".join(str(claim.get("known_risk", "")).split()),
        })

    order = {"MISMATCH": 0, "UNVERIFIABLE": 1, "PASS": 2}
    return (pd.DataFrame(rows)
            .assign(_o=lambda d: d["verdict"].map(order).fillna(9))
            .sort_values(["_o", "claim_id"]).drop(columns="_o").reset_index(drop=True))
