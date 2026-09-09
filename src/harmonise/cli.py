"""Command line interface.

  harmonise run     ingest, map, audit and report in one pass
  harmonise ingest  read the dictionaries and write the normalised table
  harmonise audit   check the application's assertions and print the verdicts
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import pandas as pd

from . import __version__, SCHEMA, audit as audit_mod, config, governance, ingest, linkage, mapping, normalise, provenance, report


def _load_frames(cfg, include_governed: bool, only=None):
    frames, skipped = {}, {}
    for cid in cfg.cohort_order():
        spec = cfg.cohorts[cid]
        if only and cid not in only:
            continue
        if not governance.gate(spec, include_governed):
            skipped[cid] = "governed cohort — pass --include-governed with documented sign-off"
            continue
        src = spec.get("source", {})
        rel = src.get("path")
        if rel and not cfg.resolve(rel).exists():
            skipped[cid] = f"dictionary not found at {cfg.resolve(rel)}"
            continue
        df = ingest.ingest_cohort(spec, cfg.resolve)
        df = normalise.build(df, spec, cfg.bands, cfg.instruments)
        frames[cid] = df
    return frames, skipped


def _report_frames(frames, skipped, cfg, stream=sys.stdout):
    for cid, df in frames.items():
        spec = cfg.cohorts[cid]
        miss = df.attrs.get("missing_columns")
        unk = df.attrs.get("unknown_waves")
        print(f"  {cid:6s} {len(df):>9,} rows   {spec['evidence_tier']:<20s} "
              f"{spec.get('release','')[:38]}", file=stream)
        if miss:
            print(f"         ! unmapped source columns: {', '.join(sorted(set(miss)))}", file=stream)
        if unk:
            print(f"         ! waves seen in the dictionary but not declared in config: "
                  f"{', '.join(unk[:8])}{' …' if len(unk) > 8 else ''}", file=stream)
    for cid, why in skipped.items():
        print(f"  {cid:6s}    skipped   {why}", file=stream)


def cmd_run(args) -> int:
    cfg = config.load(args.root, args.data_root)
    print(f"cohort-harmonise {__version__}")
    print(f"data root: {cfg.data_root}\n")

    print("step 0  ingest dictionaries")
    frames, skipped = _load_frames(cfg, args.include_governed)
    _report_frames(frames, skipped, cfg)
    if not frames:
        print("\nnothing ingested. See docs/data_sources.md for how to place the dictionaries.")
        return 2

    print("\nsteps 1, 2, 4  crosswalk constructs")
    cw = mapping.crosswalk(frames, cfg, progress=print if args.verbose else None)
    summary = mapping.cohort_construct_summary(cw)
    print(f"  {len(cw):,} construct x cohort x wave cells; "
          f"{len(summary):,} construct x cohort summaries")
    counts = cw["status"].value_counts()
    print("  " + " · ".join(f"{k}={v}" for k, v in counts.items()))

    print("\nstep 3  pooled-modelling feasibility")
    link, pairs = linkage.assess(frames, cfg, tiers=(args.linkage_tier,) if args.linkage_tier else ())
    if len(link):
        for r in link.itertuples():
            print(f"  {r.construct:<20s} {r.cohort_a}-{r.cohort_b:<6s} {r.step3_verdict}"
                  + (f"  ({r.n_anchor_candidates} candidates on {r.shared_instruments})"
                     if r.n_anchor_candidates else f"  [{r.why_not}]"))

    print("\nstep 5  declared non-harmonisable")
    register = mapping.non_harmonisable_register(cw, cfg)
    for r in register.itertuples():
        print(f"  {r.construct_label:<52s} absence confirmed in: {r.absence_confirmed_in or '(none)'}"
              + (f"  ! also matched: {r.possible_partial_coverage}" if r.possible_partial_coverage else ""))

    print("\naudit  the application's assertions")
    adf = audit_mod.run(frames, cw, link, cfg)
    for r in adf.itertuples():
        print(f"  [{r.verdict:<12s}] {r.claim_id:<26s} {r.assertion[:78]}")
        if r.verdict != "PASS":
            print(f"                 -> {r.evidence[:150]}")

    normalised = pd.concat(
        [df[[c for c in SCHEMA if c in df.columns]] for df in frames.values()],
        ignore_index=True)
    prov = provenance.build(cfg, frames, __version__)

    outdir = pathlib.Path(args.outdir)
    written = report.write_all(outdir, normalised=normalised, crosswalk=cw, summary=summary,
                               audit_df=adf, register=register, link=link, pairs=pairs,
                               cfg=cfg, prov=prov,
                               docs_dir=None if args.no_publish_docs else cfg.root / "docs")
    provenance.write(prov, outdir / "provenance.json")

    print(f"\noutputs -> {outdir}")
    for k, v in written.items():
        print(f"  {k:<38s} {v:,} rows" if k.endswith('.csv') else f"  {k}")
    print("  provenance.json")

    n_mismatch = int((adf["verdict"] == "MISMATCH").sum())
    print(f"\n{n_mismatch} mismatch(es), "
          f"{int((adf['verdict'] == 'UNVERIFIABLE').sum())} unverifiable, "
          f"{int((adf['verdict'] == 'PASS').sum())} verified.")
    return 1 if (args.strict and n_mismatch) else 0


def cmd_ingest(args) -> int:
    cfg = config.load(args.root, args.data_root)
    frames, skipped = _load_frames(cfg, args.include_governed)
    _report_frames(frames, skipped, cfg)
    return 0 if frames else 2


def cmd_audit(args) -> int:
    """The pre-submission gate.

    Passing the audit on a partial run means nothing, so --require-cohorts fails loudly
    when a named cohort's dictionary is absent rather than reporting a clean sheet that
    only reflects the cohorts that happened to load.
    """
    cfg = config.load(args.root, args.data_root)
    frames, skipped = _load_frames(cfg, args.include_governed)
    required = [c.strip() for c in (args.require_cohorts or "").split(",") if c.strip()]
    absent = [c for c in required if c not in frames]
    if absent:
        for c in absent:
            print(f"required cohort {c!r} not ingested: {skipped.get(c, 'unknown reason')}",
                  file=sys.stderr)
        print(f"\nrefusing to report an audit that omits {', '.join(absent)}.", file=sys.stderr)
        return 2
    cw = mapping.crosswalk(frames, cfg)
    link, _ = linkage.assess(frames, cfg)
    adf = audit_mod.run(frames, cw, link, cfg)
    for r in adf.itertuples():
        print(f"[{r.verdict:<12s}] {r.claim_id}\n    {r.assertion}\n    {r.evidence}\n")
    return 1 if (args.strict and (adf["verdict"] == "MISMATCH").any()) else 0


def main(argv=None) -> int:
    root_default = pathlib.Path(__file__).resolve().parents[2]
    p = argparse.ArgumentParser(prog="harmonise", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    for name, fn, helptext in (("run", cmd_run, "ingest, map, audit and report"),
                               ("ingest", cmd_ingest, "read dictionaries only"),
                               ("audit", cmd_audit, "check the application's assertions")):
        s = sub.add_parser(name, help=helptext)
        s.add_argument("--root", default=str(root_default), help="repository root")
        s.add_argument("--data-root", default=None,
                       help="directory holding the cohort dictionaries (default: data/dictionaries)")
        s.add_argument("--outdir", default=str(root_default / "outputs"))
        s.add_argument("--include-governed", action="store_true",
                       help="include cohort 6 (LSIC); requires documented First Nations sign-off")
        s.add_argument("--linkage-tier", default="",
                       help="restrict step 3 assessment to one tier; default assesses every pair")
        s.add_argument("--strict", action="store_true", help="exit non-zero if any claim mismatches")
        s.add_argument("-v", "--verbose", action="store_true", help="print progress per construct")
        s.add_argument("--require-cohorts", default=None,
                       help="comma-separated cohorts whose dictionaries must be present; "
                            "exit 2 if any is missing, so a partial run cannot pass the gate")
        s.add_argument("--no-publish-docs", action="store_true",
                       help="do not copy the report to docs/index.html for GitHub Pages")
        s.set_defaults(func=fn)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
