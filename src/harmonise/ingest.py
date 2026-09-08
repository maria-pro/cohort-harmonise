"""Table B2 step 0 — read each cohort's dictionary into one common schema.

Four adapter kinds cover the four dictionary shapes we hold, plus one for cohorts
documented only in publications. No cohort-specific logic lives outside a config file.
"""
from __future__ import annotations

import pathlib
import re

import pandas as pd
from openpyxl import load_workbook

from . import SCHEMA


def _sheet_frame(path: pathlib.Path, sheet: str, header_row: int = 0) -> pd.DataFrame:
    """Read one worksheet with openpyxl in read-only mode."""
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb[sheet]
        rows = ws.iter_rows(values_only=True)
        header = None
        for i, r in enumerate(rows):
            if i == header_row:
                header = ["" if c is None else str(c).strip() for c in r]
                break
        if header is None:
            raise ValueError(f"no header row {header_row} in {sheet}")
        body = []
        for r in rows:
            body.append(["" if c is None else str(c).strip() for c in r])
        width = len(header)
        body = [(r + [""] * width)[:width] for r in body]
        df = pd.DataFrame(body, columns=header)
        # Excel duplicates some header names; keep the first occurrence.
        df = df.loc[:, ~df.columns.duplicated()]
        df["source_row"] = range(header_row + 2, header_row + 2 + len(df))
        return df
    finally:
        wb.close()


def _blank_frame(n: int) -> pd.DataFrame:
    return pd.DataFrame({c: [""] * n for c in SCHEMA})


def _stamp(out: pd.DataFrame, spec: dict, path: pathlib.Path, sheet: str) -> pd.DataFrame:
    out["cohort"] = spec["cohort_id"]
    out["cohort_number"] = spec["cohort_number"]
    out["tier"] = str(spec["tier"])
    out["release"] = spec.get("release", "")
    out["evidence_tier"] = spec["evidence_tier"]
    out["source_file"] = path.name if path else spec.get("_config_file", "")
    out["source_sheet"] = sheet
    gov = spec.get("governance", {}) or {}
    out["governance_required"] = bool(gov.get("restricted", False))
    return out


def _apply_map(df: pd.DataFrame, mapping: dict, out: pd.DataFrame) -> pd.DataFrame:
    """Copy mapped source columns into schema fields, reporting missing columns."""
    missing = []
    for field, col in mapping.items():
        if field in ("wave_raw", "wave_codes", "table_name", "instrument_src",
                     "source_ref", "response_type"):
            continue
        if col in df.columns:
            out[field] = df[col].values
        else:
            missing.append(f"{field}<-{col}")
    if missing:
        out.attrs.setdefault("missing_columns", []).extend(missing)
    return out


# --------------------------------------------------------------------------- adapters

def _long_sheet(spec: dict, path, sheet_cfg: dict, src: dict) -> pd.DataFrame:
    """One long-format worksheet: one row per variable, wave in a column."""
    df = _sheet_frame(path, sheet_cfg["sheet"], sheet_cfg.get("header_row", 0))
    out = _blank_frame(len(df))
    out = _apply_map(df, sheet_cfg["map"], out)
    out["source_row"] = df["source_row"].values
    out = _stamp(out, spec, path, sheet_cfg["sheet"])

    wave_col = sheet_cfg["map"].get("wave_raw")
    waves = df[wave_col].astype(str) if wave_col in df.columns else pd.Series([""] * len(df))
    norm = src.get("wave_normalise", {}) or {}
    out["wave_id"] = waves.replace(norm).values

    # Some dictionaries record a variable collected in several waves as one combined
    # value ("1+2+3"). Expand it so wave membership stays one row per wave.
    split_on = src.get("wave_split")
    if split_on:
        out["wave_id"] = out["wave_id"].astype(str).str.split(re.escape(split_on), regex=True)
        out = out.explode("wave_id")
        out["wave_id"] = out["wave_id"].astype(str).str.strip()
        out = out[out["wave_id"] != ""].reset_index(drop=True)

    resp = src.get("respondent", {}) or {}
    if resp.get("kind") == "constant":
        out["respondent"] = resp["value"]
    return out


def _excel_long(spec: dict, resolve) -> pd.DataFrame:
    """The primary sheet, plus any supplementary sheets the config declares.

    LSAC splits its dictionary across sheets: the release sheet carries derived scale
    scores, while the study-child sheet carries the self-report items and names the
    instrument in a 'Measure' column. Step 3 needs the items, so both are read.
    """
    src = spec["source"]
    path = resolve(src["path"])
    frames = [_long_sheet(spec, path, src, src)]
    for extra in spec.get("supplementary_sheets", []) or []:
        cfg = dict(extra)
        cfg.setdefault("header_row", src.get("header_row", 0))
        frames.append(_long_sheet(spec, path, cfg, src))

    out = pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]
    out = out.drop_duplicates(subset=["variable", "wave_id", "label"], keep="first")

    drop_vals = src.get("drop_respondent_values")
    if drop_vals:
        out.attrs["respondent_placeholder_values"] = drop_vals
    return out.reset_index(drop=True)


def _excel_wide_waves(spec: dict, resolve) -> pd.DataFrame:
    """One column per wave; a non-empty cell means the variable was collected that wave."""
    src = spec["source"]
    path = resolve(src["path"])
    df = _sheet_frame(path, src["sheet"], src.get("header_row", 0))
    prefix = src["wave_columns_prefix"]
    wave_cols = [c for c in df.columns if c.startswith(prefix) and c[len(prefix):].strip().isdigit()]

    base = _blank_frame(len(df))
    base = _apply_map(df, src["map"], base)
    base["source_row"] = df["source_row"].values
    base = _stamp(base, spec, path, src["sheet"])

    frames = []
    for wc in wave_cols:
        present = df[wc].astype(str).str.strip() != ""
        if not present.any():
            continue
        part = base.loc[present.values].copy()
        part["wave_id"] = wc
        part["population"] = df.loc[present, wc].values  # e.g. "B&K" cohort presence
        frames.append(part)
    return pd.concat(frames, ignore_index=True) if frames else base.iloc[0:0]


def _excel_wavecodes(spec: dict, resolve) -> pd.DataFrame:
    """Wave membership arrives as a delimited list of session codes in one column."""
    src = spec["source"]
    path = resolve(src["path"])
    df = _sheet_frame(path, src["sheet"], src.get("header_row", 0))

    base = _blank_frame(len(df))
    base = _apply_map(df, src["map"], base)
    base["source_row"] = df["source_row"].values
    base = _stamp(base, spec, path, src["sheet"])

    inst_col = src["map"].get("instrument_src")
    if inst_col in df.columns:
        base["instrument"] = df[inst_col].values

    tbl_col = src["map"].get("table_name")
    resp = src.get("respondent", {}) or {}
    if resp.get("kind") == "from_table_name_token" and tbl_col in df.columns:
        tok = df[tbl_col].astype(str).str.split("_").str[resp.get("token_index", 1)]
        base["respondent"] = tok.map(resp["lookup"]).fillna(resp.get("default", "")).values

    sep = src.get("wave_code_separator", ";")
    codes = df[src["map"]["wave_codes"]].astype(str).str.split(sep)
    base = base.assign(wave_id=codes.values).explode("wave_id")
    base["wave_id"] = base["wave_id"].astype(str).str.strip()
    base = base[base["wave_id"] != ""]
    return base.reset_index(drop=True)


def _documented(spec: dict, resolve) -> pd.DataFrame:
    """Cohorts with no custodian dictionary: an inventory built from published sources."""
    src = spec["source"]
    entries = src["entries"]
    cites = spec.get("citations", {}) or {}
    wave_index = {}
    for w in spec.get("waves", []):
        wave_index.setdefault(str(w.get("age_range", "")), w["wave_id"])
        wave_index[str(w["wave_id"])] = w["wave_id"]

    rows = []
    for i, e in enumerate(entries):
        keys = e.get("ages") or e.get("waves") or []
        cite = cites.get(e.get("cite", ""), {})
        cite_txt = cite.get("ref") or cite.get("url") or e.get("cite", "")
        for k in keys:
            wid = wave_index.get(str(k))
            if wid is None:
                # AStRA reports wave numbers per subcohort; expand across subcohorts.
                matches = [w["wave_id"] for w in spec.get("waves", [])
                           if str(w["wave_id"]).endswith(f"W{k}")]
                if not matches:
                    continue
            else:
                matches = [wid]
            for m in matches:
                rows.append({
                    "variable": f"{spec['cohort_id']}__{i:02d}",
                    "label": e["domain"],
                    "item_text": e.get("note", ""),
                    "instrument": e.get("instrument", ""),
                    "domain": e["domain"],
                    "construct_src": e.get("construct_src", ""),
                    "respondent": e.get("respondent", ""),
                    "coding": "",
                    "population": "",
                    "confidence": e.get("confidence", "reported"),
                    "wave_id": m,
                    "source_row": i + 1,
                    "citation": cite_txt,
                })
    out = _blank_frame(len(rows))
    src_df = pd.DataFrame(rows)
    for c in src_df.columns:
        if c in out.columns:
            out[c] = src_df[c].values
    out = _stamp(out, spec, None, "documented inventory")
    out["citation"] = src_df["citation"].values if len(src_df) else []
    return out


ADAPTERS = {
    "excel_long": _excel_long,
    "excel_wide_waves": _excel_wide_waves,
    "excel_wavecodes": _excel_wavecodes,
    "documented": _documented,
}


def ingest_cohort(spec: dict, resolve) -> pd.DataFrame:
    kind = spec["source"]["kind"]
    if kind not in ADAPTERS:
        raise ValueError(f"unknown adapter kind {kind!r} for {spec['cohort_id']}")
    return ADAPTERS[kind](spec, resolve)
