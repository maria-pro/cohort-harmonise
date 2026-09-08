"""Table B2 step 3 — is pooled latent modelling actually available for this pair?

The application writes step 3 as a conditional: it "is used only where genuine common
items and adequate linking information exist; otherwise the inference is harmonised
rather than the scale". That conditional is computable from dictionaries, so this module
evaluates it instead of assuming it.

A pair is reported feasible only when the two cohorts share a canonical instrument, both
sides carry enough items, and item wording is present on both sides to anchor on.
"""
from __future__ import annotations

import collections
import itertools
import re

import pandas as pd

STOP = set("""a an and are as at be been by can do does for from had has have how i if in is it
its of on or that the their they this to was were what when where which who will with you your
your not no did been about please during last week weeks month months year years day days times
sc study child parent mother father respondent""".split())

MIN_ITEMS = 3
MIN_JACCARD = 0.34


def _tokens(text: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", str(text).lower()) if len(t) > 2 and t not in STOP}


def _item_text_series(df: pd.DataFrame) -> pd.Series:
    """Prefer question wording; fall back to the variable label."""
    it = df["item_text"].astype(str).str.strip()
    lb = df["label"].astype(str).str.strip()
    return it.where(it.str.len() > 8, lb)


MAX_ITEMS = 4000
COMMON_TOKEN_SHARE = 0.25


def anchor_candidates(a: pd.DataFrame, b: pd.DataFrame, limit: int = 25) -> pd.DataFrame:
    """Item pairs whose wording overlaps enough to be worth testing as anchors.

    Instrument banks run to thousands of items, so the comparison uses an inverted token
    index rather than a full cross product: only items sharing at least one distinctive
    term are scored. Terms appearing in more than a quarter of one side's items carry no
    discriminating information and are dropped from the index.
    """
    ta = [(v, s) for v, s in
          ((v, _tokens(t)) for v, t in zip(a["variable"], _item_text_series(a)))
          if len(s) >= 3][:MAX_ITEMS]
    tb = [(v, s) for v, s in
          ((v, _tokens(t)) for v, t in zip(b["variable"], _item_text_series(b)))
          if len(s) >= 3][:MAX_ITEMS]
    if not ta or not tb:
        return pd.DataFrame()

    df_count = collections.Counter(t for _, s in tb for t in s)
    ceiling = max(2, int(len(tb) * COMMON_TOKEN_SHARE))
    index = collections.defaultdict(list)
    for j, (_, s) in enumerate(tb):
        for t in s:
            if df_count[t] <= ceiling:
                index[t].append(j)

    out = []
    for va, sa in ta:
        shared_counts = collections.Counter()
        for t in sa:
            for j in index.get(t, ()):
                shared_counts[j] += 1
        for j, n_shared in shared_counts.items():
            vb, sb = tb[j]
            inter = sa & sb
            jac = len(inter) / len(sa | sb)
            if jac >= MIN_JACCARD:
                out.append({"variable_a": va, "variable_b": vb,
                            "jaccard": round(jac, 3),
                            "shared_terms": " ".join(sorted(inter))})
    df = pd.DataFrame(out)
    if df.empty:
        return df
    return df.sort_values("jaccard", ascending=False).head(limit).reset_index(drop=True)


def assess(frames: dict, cfg, constructs=("anx_symptoms", "internalising_broad"),
           tiers=("1",)) -> tuple[pd.DataFrame, pd.DataFrame]:
    from .mapping import match_construct

    cohorts = [c for c in cfg.cohort_order()
               if c in frames and (not tiers or str(cfg.cohorts[c]["tier"]) in tiers)]
    verdicts, pairs_out = [], []

    for cid in constructs:
        con = cfg.construct(cid)
        preferred = con.get("preferred_instruments") or []
        subs = {}
        for c in cohorts:
            df = frames[c]
            documented = pd.Series(
                cfg.cohorts[c]["evidence_tier"] != "official_dictionary", index=df.index)
            hit = match_construct(df["_blob"], con.get("match"),
                                  documented, con.get("documented_match"))
            # A CBCL item is a CBCL item whether or not its wording contains the word
            # "anxious", so rows already resolved to an instrument the application names
            # for this construct are eligible anchors too.
            if preferred:
                pat = "|".join(re.escape(x) for x in preferred)
                hit = hit | df["instrument_id"].str.contains(pat, regex=True, na=False)
            subs[c] = df.loc[hit]

        for a, b in itertools.combinations(cohorts, 2):
            sa, sb = subs[a], subs[b]
            ia = {i for cell in sa["instrument_id"].unique() for i in str(cell).split(";") if i}
            ib = {i for cell in sb["instrument_id"].unique() for i in str(cell).split(";") if i}
            shared = sorted(ia & ib)

            ta_ok = (_item_text_series(sa).str.len() > 8).sum() if len(sa) else 0
            tb_ok = (_item_text_series(sb).str.len() > 8).sum() if len(sb) else 0

            reasons = []
            for c, n in ((a, ta_ok), (b, tb_ok)):
                if n < MIN_ITEMS:
                    et = cfg.cohorts[c]["evidence_tier"]
                    reasons.append(
                        f"no item wording held for {c}"
                        + (f" (evidence tier: {et})" if et != "official_dictionary" else "")
                    )
            if not shared:
                reasons.append("no canonical instrument in common")

            # The gate belongs on the shared instrument, not on the whole construct
            # subset: two cohorts can each hold thousands of anxiety variables and still
            # share only a handful of items on the one instrument they have in common.
            usable, per_instrument = [], []
            for inst in shared:
                pat = rf"(?:^|;){re.escape(inst)}(?:;|$)"
                na = int(sa["instrument_id"].str.contains(pat, regex=True, na=False).sum())
                nb = int(sb["instrument_id"].str.contains(pat, regex=True, na=False).sum())
                per_instrument.append(f"{inst}: {a}={na}, {b}={nb}")
                if na >= MIN_ITEMS and nb >= MIN_ITEMS:
                    usable.append(inst)
            if shared and not usable:
                reasons.append("shared instrument held by both, but fewer than "
                               f"{MIN_ITEMS} items on one side ({'; '.join(per_instrument)})")

            cand = pd.DataFrame()
            if usable and not reasons:
                pat = "|".join(rf"(?:^|;){re.escape(x)}(?:;|$)" for x in usable)
                cand = anchor_candidates(
                    sa[sa["instrument_id"].str.contains(pat, regex=True, na=False)],
                    sb[sb["instrument_id"].str.contains(pat, regex=True, na=False)])

            if reasons:
                verdict = "inference_harmonisation_only"
            elif cand.empty:
                verdict = "shared_instrument_no_item_overlap"
                reasons.append("both cohorts administer the instrument, but the published "
                               "item wording does not overlap closely enough to propose anchors "
                               "from dictionaries alone; compare the questionnaires")
            else:
                verdict = "anchor_candidates_found"

            verdicts.append({
                "construct": cid,
                "cohort_a": a, "cohort_b": b,
                "tier_a": str(cfg.cohorts[a]["tier"]), "tier_b": str(cfg.cohorts[b]["tier"]),
                "items_a": len(sa), "items_b": len(sb),
                "instruments_a": "; ".join(sorted(ia)), "instruments_b": "; ".join(sorted(ib)),
                "shared_instruments": "; ".join(shared),
                "usable_instruments": "; ".join(usable),
                "items_per_shared_instrument": " | ".join(per_instrument),
                "item_text_available_a": int(ta_ok), "item_text_available_b": int(tb_ok),
                "n_anchor_candidates": len(cand),
                "step3_verdict": verdict,
                "why_not": "; ".join(dict.fromkeys(reasons)),
                "fallback": "" if verdict == "anchor_candidates_found"
                            else "harmonise the inference: replicate and meta-analyse standardised within-cohort estimates",
            })
            if not cand.empty:
                cand = cand.assign(construct=cid, cohort_a=a, cohort_b=b)
                pairs_out.append(cand)

    return (pd.DataFrame(verdicts),
            pd.concat(pairs_out, ignore_index=True) if pairs_out else pd.DataFrame())
