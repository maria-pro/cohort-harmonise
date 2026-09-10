"""Table B2 step 0 and step 4 — one row per (cohort, wave, variable), reporter and era carried.

Three fields matter more than they look:
  respondent   step 4 forbids treating a parent report at 10 y as a youth self-report at 14 y,
               so the informant is a first-class field rather than a note;
  wave_year    step 4 puts digital era inside the exposure definition, so calendar year is
               carried separately from wave index and the era is derived from it;
  source_*     a reviewer must be able to trace any mapping back to a cell.
"""
from __future__ import annotations

import re

import pandas as pd

BLOB_FIELDS = ["variable", "label", "item_text", "instrument", "domain", "construct_src"]


def era_for_year(year, bands) -> str:
    if year in ("", None) or pd.isna(year):
        return ""
    y = int(year)
    for b in bands:
        lo, hi = b.get("from"), b.get("to")
        if (lo is None or y >= lo) and (hi is None or y <= hi):
            return b["era"]
    return ""


def attach_waves(df: pd.DataFrame, spec: dict, bands) -> pd.DataFrame:
    """Join the cohort's declared wave metadata onto the ingested rows."""
    waves = spec.get("waves", [])
    if not waves:
        return df
    wmeta = pd.DataFrame(waves)
    wmeta["wave_id"] = wmeta["wave_id"].astype(str)
    keep = [c for c in ["wave_id", "wave_year", "year_source", "digital_era", "age_range", "subcohort"]
            if c in wmeta.columns]
    wmeta = wmeta[keep].rename(columns={c: f"_w_{c}" for c in keep if c != "wave_id"})

    df["wave_id"] = df["wave_id"].astype(str).str.strip()
    out = df.merge(wmeta, on="wave_id", how="left")

    for c in ["wave_year", "year_source", "subcohort"]:
        src = f"_w_{c}"
        if src in out.columns:
            out[c] = out[src]
    # The dictionary's own age is better evidence than the config's; keep it when present.
    if "_w_age_range" in out.columns:
        have = out["age_range"].astype(str).str.strip() != ""
        out.loc[~have, "age_range"] = out.loc[~have, "_w_age_range"]
    # Era: prefer the config's declared era, else derive from the calendar year.
    declared = out["_w_digital_era"] if "_w_digital_era" in out.columns else pd.Series([None] * len(out))
    derived = out["wave_year"].map(lambda y: era_for_year(y, bands))
    out["digital_era"] = declared.where(declared.notna() & (declared.astype(str) != ""), derived)

    out = out.drop(columns=[c for c in out.columns if c.startswith("_w_")])
    unknown = sorted(set(df["wave_id"]) - set(wmeta["wave_id"]))
    if unknown:
        out.attrs["unknown_waves"] = unknown
    return out


def resolve_instruments(df: pd.DataFrame, instruments) -> pd.DataFrame:
    """The application's instrument names are not the dictionaries' names.

    This is the alias layer. It records which canonical instrument each row belongs to,
    and leaves the field empty rather than guessing when nothing matches.
    """
    blob = df["_blob"]
    hits = {}
    for inst in instruments:
        # Two kinds of alias need two treatments. Short ones are acronyms where a
        # substring collision is the risk — "sdq" must not match "sdqi", "cbcl" must not
        # match "acbclite" — so they take a right boundary that rejects a following
        # letter. Longer ones are phrases or deliberate stems where a suffix is wanted:
        # "emotional symptom" must reach "emotional symptoms" and "unsociab" must reach
        # "unsociability". The left boundary is strict in both cases.
        parts = []
        for a in inst["aliases"]:
            right = r"(?![a-z])" if len(a) <= 6 else ""
            parts.append(rf"(?<![a-z0-9]){re.escape(a)}{right}")
        pat = "|".join(parts)
        hit = blob.str.contains(pat, regex=True, na=False)
        # Some collisions are not structural and no boundary rule reaches them: "SDQ-I"
        # is the Self-Description Questionnaire, not the Strengths and Difficulties
        # Questionnaire, and both are written "SDQ".
        for ex in inst.get("exclude_if", []) or []:
            hit &= ~blob.str.contains(re.escape(ex), regex=True, na=False)
        hits[inst["id"]] = hit
    # A row may belong to more than one instrument (an SDQ emotional-symptoms item is both
    # SDQ and its subscale), so every match is kept rather than the first one winning.
    ids = pd.DataFrame(hits)
    df["instrument_id"] = [";".join(ids.columns[row]) for row in ids.to_numpy()]
    return df


def apply_instrument_overrides(df: pd.DataFrame, spec: dict) -> pd.DataFrame:
    """Resolve an instrument the dictionary administers but never names.

    LSAC is the case that forced this: it carries the CAS-8 at item level as
    [ghi]se16b1-b8 ("Worry about things", "Feel afraid", ...), but only the derived
    total is labelled "Spence Anxiety Scale". Alias matching over the row text
    therefore sees eight anxiety items and no instrument, which made a pooled model
    look impossible when the items were there all along.
    """
    for rule in spec.get("source", {}).get("instrument_overrides", []) or []:
        hit = df["variable"].astype(str).str.contains(rule["variable_pattern"], regex=True, na=False)
        if "wave_in" in rule:
            hit &= df["wave_id"].astype(str).isin([str(w) for w in rule["wave_in"]])
        inst = rule["instrument"]
        cur = df.loc[hit, "instrument_id"].astype(str)
        df.loc[hit, "instrument_id"] = [
            v if inst in v.split(";") else (f"{v};{inst}" if v else inst) for v in cur]
    return df


def clean_respondent(df: pd.DataFrame, placeholders) -> pd.DataFrame:
    if not placeholders:
        return df
    low = df["respondent"].astype(str).str.strip()
    df.loc[low.isin(placeholders), "respondent"] = ""
    return df


def build(df: pd.DataFrame, spec: dict, bands, instruments) -> pd.DataFrame:
    placeholders = df.attrs.get("respondent_placeholder_values")
    df = attach_waves(df, spec, bands)
    df["_blob"] = (
        df[BLOB_FIELDS].astype(str).agg(" | ".join, axis=1).str.lower()
    )
    df = resolve_instruments(df, instruments)
    df = apply_instrument_overrides(df, spec)
    df = clean_respondent(df, placeholders)
    df["wave_year"] = pd.to_numeric(df["wave_year"], errors="coerce")
    return df
