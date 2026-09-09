"""Reviewer-facing outputs.

The coverage matrix is the headline: constructs down, cohorts across, cells coloured by
mapping status, with the evidence tier visible so a reader can tell a custodian dictionary
from a published table at a glance. Pending cohorts are shown as pending.
"""
from __future__ import annotations

import html
import pathlib

import pandas as pd

from . import explore

STATUS_META = {
    "direct":               ("Direct", "s-direct"),
    "partial":              ("Partial", "s-partial"),
    "proxy":                ("Proxy", "s-proxy"),
    "governed_not_proxied": ("Governed", "s-governed"),
    "non_harmonisable":     ("Non-harmonisable", "s-nh"),
    "absent":               ("Absent", "s-absent"),
}
TIER_META = {
    "official_dictionary": ("custodian dictionary", "e-official"),
    "published_profile":   ("published profile", "e-profile"),
    "reconstructed":       ("reconstructed from publications", "e-recon"),
}
VERDICT_CLASS = {"PASS": "v-pass", "MISMATCH": "v-mismatch", "UNVERIFIABLE": "v-unver"}

CSS = """
:root{
  --bg:#fbfaf8; --panel:#ffffff; --ink:#1a1a1a; --muted:#63636b; --line:#e3e0da;
  --accent:#2b5f8e;
  --direct:#1f6f4a; --direct-bg:#e2f0e8;
  --partial:#8a6320; --partial-bg:#f6ecd9;
  --proxy:#6b5a8e; --proxy-bg:#ece7f4;
  --gov:#8c4a2f; --gov-bg:#f7e6de;
  --nh:#4a4a52; --nh-bg:#e9e8e6;
  --absent:#8d3b3b; --absent-bg:#f6e4e4;
}
:root:not([data-theme="light"]){ }
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --bg:#161618; --panel:#1e1e21; --ink:#ececec; --muted:#a0a0a8; --line:#33333a;
    --accent:#7fb3e0;
    --direct:#7fd3a6; --direct-bg:#1b3529;
    --partial:#e0bd7a; --partial-bg:#3a2f18;
    --proxy:#bfaee0; --proxy-bg:#2b2438;
    --gov:#e8a884; --gov-bg:#3a2419;
    --nh:#b8b8c0; --nh-bg:#2a2a2e;
    --absent:#e39a9a; --absent-bg:#3a1f1f;
  }
}
:root[data-theme="dark"]{
  --bg:#161618; --panel:#1e1e21; --ink:#ececec; --muted:#a0a0a8; --line:#33333a;
  --accent:#7fb3e0;
  --direct:#7fd3a6; --direct-bg:#1b3529;
  --partial:#e0bd7a; --partial-bg:#3a2f18;
  --proxy:#bfaee0; --proxy-bg:#2b2438;
  --gov:#e8a884; --gov-bg:#3a2419;
  --nh:#b8b8c0; --nh-bg:#2a2a2e;
  --absent:#e39a9a; --absent-bg:#3a1f1f;
}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);
  font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  margin:0;padding:32px 24px 72px}
.wrap{max-width:1180px;margin:0 auto}
h1{font-size:25px;line-height:1.25;margin:0 0 6px;letter-spacing:-.01em}
.sub{color:var(--muted);margin:0 0 4px}
h2{font-size:17px;margin:40px 0 6px;letter-spacing:-.005em}
h2 .n{color:var(--muted);font-weight:400}
p.lede{color:var(--muted);margin:0 0 14px;max-width:78ch}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:2px;overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:13.5px}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);
   position:sticky;top:0;background:var(--panel)}
tr:last-child td{border-bottom:none}
td.rowhead{font-weight:600;min-width:210px}
td.rowhead small{display:block;font-weight:400;color:var(--muted);font-size:11.5px}
.cell{display:inline-block;padding:2px 7px;border-radius:5px;font-size:12px;font-weight:600;white-space:nowrap}
.s-direct{color:var(--direct);background:var(--direct-bg)}
.s-partial{color:var(--partial);background:var(--partial-bg)}
.s-proxy{color:var(--proxy);background:var(--proxy-bg)}
.s-governed{color:var(--gov);background:var(--gov-bg)}
.s-nh{color:var(--nh);background:var(--nh-bg)}
.s-absent{color:var(--absent);background:var(--absent-bg)}
.wv{color:var(--muted);font-size:11px;display:block;margin-top:2px}
.chip{display:inline-block;font-size:11px;padding:1px 6px;border-radius:20px;border:1px solid var(--line);color:var(--muted)}
.e-official{border-color:var(--direct);color:var(--direct)}
.e-profile{border-color:var(--partial);color:var(--partial)}
.e-recon{border-color:var(--proxy);color:var(--proxy)}
.v-pass{color:var(--direct);background:var(--direct-bg)}
.v-mismatch{color:var(--absent);background:var(--absent-bg)}
.v-unver{color:var(--partial);background:var(--partial-bg)}
.legend{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0 0}
.kv{display:grid;grid-template-columns:auto 1fr;gap:4px 14px;font-size:13px;color:var(--muted)}
.small{font-size:12.5px;color:var(--muted)}
.stat{display:flex;gap:26px;flex-wrap:wrap;margin:14px 0 0}
.stat div{min-width:96px}
.stat b{display:block;font-size:22px;font-weight:650;color:var(--ink)}
.stat span{font-size:11.5px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}
footer{margin-top:44px;padding-top:14px;border-top:1px solid var(--line);color:var(--muted);font-size:12px}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px}
"""


def _esc(x) -> str:
    return html.escape("" if x is None else str(x))


def _cell(status: str, waves: int, n: int, total_waves=None, supp: int = 0) -> str:
    label, cls = STATUS_META.get(status, (status, ""))
    extra = ""
    if status in ("direct", "partial", "proxy"):
        of = f" of {int(total_waves)}" if total_waves else ""
        bits = [f"{int(waves)}{of} wave(s)", f"{int(n)} vars"]
        if supp:
            bits.append(f"+{int(supp)} suppl.")
        extra = f'<span class="wv">{" · ".join(bits)}</span>'
    return f'<span class="cell {cls}">{_esc(label)}</span>{extra}'


def _matrix_table(summary: pd.DataFrame, cfg) -> str:
    cohorts = [c for c in cfg.cohort_order() if c in set(summary["cohort"])]
    head = "".join(
        f'<th>{_esc(cfg.cohorts[c]["short_name"])}'
        f'<div class="small">cohort {cfg.cohorts[c]["cohort_number"]} · tier {cfg.cohorts[c]["tier"]}'
        f'<br>{cfg.cohorts[c].get("waves_per_participant", "?")} waves</div></th>'
        for c in cohorts)
    rows = []
    order = ["outcome", "outcome_secondary", "predictor", "core_layer", "mechanism"]
    summary = summary.assign(_o=summary["role"].map({r: i for i, r in enumerate(order)}).fillna(9))
    for (cid, clabel, role), grp in summary.sort_values(["_o", "construct"]).groupby(
            ["construct", "construct_label", "role"], sort=False):
        cells = []
        for c in cohorts:
            r = grp[grp["cohort"] == c]
            if r.empty:
                cells.append('<td><span class="cell s-absent">no data</span></td>')
            else:
                r = r.iloc[0]
                cells.append("<td>" + _cell(
                    r["status"], r["waves_with_data"], r["n_variables"],
                    cfg.cohorts[c].get("waves_per_participant"),
                    r.get("supplementary_sessions_with_data", 0)) + "</td>")
        core = " · core" if bool(grp["core"].iloc[0]) else ""
        rows.append(f'<tr><td class="rowhead">{_esc(clabel)}'
                    f'<small>{_esc(role)}{core}</small></td>{"".join(cells)}</tr>')
    return f'<div class="panel"><table><thead><tr><th>Construct</th>{head}</tr></thead>' \
           f'<tbody>{"".join(rows)}</tbody></table></div>'


def _df_table(df: pd.DataFrame, cols: dict, classer=None) -> str:
    head = "".join(f"<th>{_esc(v)}</th>" for v in cols.values())
    body = []
    for r in df.itertuples():
        tds = []
        for k in cols:
            val = getattr(r, k, "")
            cls = classer(k, val) if classer else None
            tds.append(f'<td><span class="cell {cls}">{_esc(val)}</span></td>' if cls
                       else f"<td>{_esc(val)}</td>")
        body.append(f"<tr>{''.join(tds)}</tr>")
    return f'<div class="panel"><table><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'


def coverage_html(summary, audit_df, register, link, cfg, prov) -> str:
    cohorts = cfg.cohort_order()
    n_official = sum(1 for c in cohorts if cfg.cohorts[c]["evidence_tier"] == "official_dictionary")
    mism = int((audit_df["verdict"] == "MISMATCH").sum())
    unver = int((audit_df["verdict"] == "UNVERIFIABLE").sum())
    passed = int((audit_df["verdict"] == "PASS").sum())

    cohort_rows = []
    for c in cohorts:
        s = cfg.cohorts[c]
        tl, tc = TIER_META.get(s["evidence_tier"], (s["evidence_tier"], ""))
        gov = (s.get("governance") or {})
        cohort_rows.append(
            f'<tr><td class="rowhead">{_esc(s["short_name"])}'
            f'<small>{_esc(s["name"])}</small></td>'
            f'<td>{_esc(s["cohort_number"])}</td><td>{_esc(s["tier"])}</td>'
            f'<td>{_esc(s.get("country",""))}</td>'
            f'<td><span class="chip {tc}">{_esc(tl)}</span></td>'
            f'<td>{_esc(s.get("release",""))}</td>'
            f'<td>{prov["cohorts"][c]["rows_ingested"]:,}</td>'
            f'<td>{"sign-off required" if gov.get("requires_signoff") else ""}'
            f'{"<br><span class=small>pending: " + _esc(s["pending_from"]) + "</span>" if s.get("pending_from") else ""}</td></tr>')

    legend = "".join(f'<span class="cell {cls}">{lbl}</span>'
                     for lbl, cls in STATUS_META.values())

    audit_cols = {"claim_id": "Claim", "source": "Where it appears in the application",
                  "assertion": "Assertion", "verdict": "Verdict", "evidence": "What the dictionaries say"}
    reg_cols = {"construct_label": "Construct", "reason": "Why it cannot be harmonised",
                "absence_confirmed_in": "Absence confirmed in", "possible_partial_coverage": "Possible partial coverage"}
    link_cols = {"construct": "Construct", "cohort_a": "A", "cohort_b": "B",
                 "shared_instruments": "Shared instrument", "items_a": "Items A", "items_b": "Items B",
                 "n_anchor_candidates": "Anchor candidates", "step3_verdict": "Step 3 verdict",
                 "why_not": "Why not", "fallback": "Fallback"}

    return f"""<title>Cohort Harmonisation Coverage</title>
<style>{CSS}</style>
<div class="wrap">
<h1>Dictionary-level harmonisation across six cohorts</h1>
<p class="sub">Generated {_esc(prov["generated_utc"][:16].replace("T", " "))} UTC · cohort-harmonise {_esc(prov["version"])} · revision <code>{_esc(prov["git_revision"])}</code></p>
<p class="lede">Every construct below is matched against each cohort's own data dictionary or, where no custodian dictionary is held, against published documentation. Nothing is forced onto a common scale: what cannot be aligned is declared, with a reason.</p>

<div class="stat">
  <div><b>{len(cohorts)}</b><span>cohorts</span></div>
  <div><b>{n_official}</b><span>custodian dictionaries</span></div>
  <div><b>{sum(prov["cohorts"][c]["rows_ingested"] for c in cohorts):,}</b><span>cohort-wave-variable rows</span></div>
  <div><b>{passed}</b><span>claims verified</span></div>
  <div><b>{mism}</b><span>mismatches</span></div>
  <div><b>{unver}</b><span>unverifiable</span></div>
</div>

<h2>1 &nbsp;Coverage matrix <span class="n">— the harmonisation claim, as data</span></h2>
<p class="lede">Best status each cohort achieves for each construct. Wave counts are over primary
waves only: a dictionary lists every session a study ever ran, and counting mid-year check-ins,
screeners and substudies as waves would make the columns incomparable. Sessions of those kinds are
reported separately as supplementary.</p>
{_matrix_table(summary, cfg)}
<div class="legend">{legend}</div>

<h2>2 &nbsp;Claim audit <span class="n">— the application checked against the dictionaries</span></h2>
<p class="lede">Mismatches first. UNVERIFIABLE means no held dictionary can settle the claim either way, which is itself worth knowing before a reviewer asks.</p>
{_df_table(audit_df, audit_cols, lambda k, v: VERDICT_CLASS.get(v) if k == "verdict" else None)}

<h2>3 &nbsp;Declared non-harmonisable <span class="n">— Table B2 step 5</span></h2>
<p class="lede">A construct is written here only with a stated reason; the tool refuses the row otherwise. Absence is confirmed against the dictionaries rather than asserted.</p>
{_df_table(register, reg_cols)}

<h2>4 &nbsp;Pooled latent modelling feasibility <span class="n">— Table B2 step 3</span></h2>
<p class="lede">Step 3 applies only where genuine common items and adequate linking information exist. This evaluates that condition for each Tier 1 pair instead of assuming it.</p>
{_df_table(link, link_cols)}

<h2>5 &nbsp;Cohorts and evidence</h2>
<div class="panel"><table><thead><tr><th>Cohort</th><th>No.</th><th>Tier</th><th>Country</th>
<th>Evidence</th><th>Release</th><th>Rows</th><th>Governance</th></tr></thead>
<tbody>{"".join(cohort_rows)}</tbody></table></div>

<footer>
No participant data is read, produced or redistributed by this tool: it operates on variable-level
metadata only. Dictionary files are not committed to the repository. Cohort 6 (LSIC) is analysed only
under First Nations leadership and data-governance principles, and the mapping engine refuses to treat
its culturally grounded wellbeing indicators as a proxy for a diagnostic construct.
</footer>
</div>
"""


def custodian_template(cfg, cohort_id: str) -> pd.DataFrame:
    """A pre-filled inventory for a cohort whose custodian has not sent a dictionary.

    The ask becomes 'confirm or correct these rows' rather than 'please send documentation'.
    """
    spec = cfg.cohorts[cohort_id]
    cites = spec.get("citations", {}) or {}
    rows = []
    for e in spec["source"]["entries"]:
        cite = cites.get(e.get("cite", ""), {})
        rows.append({
            "domain_or_construct": e["domain"],
            "instrument_we_have_assumed": e.get("instrument", ""),
            "informant_we_have_assumed": e.get("respondent", ""),
            "waves_or_ages_we_have_assumed": ", ".join(str(x) for x in (e.get("ages") or e.get("waves") or [])),
            "our_confidence": e.get("confidence", ""),
            "our_source": cite.get("doi") or cite.get("url") or cite.get("ref", ""),
            "our_note": e.get("note", ""),
            "CONFIRM_correct?": "",
            "CORRECTION_instrument": "",
            "CORRECTION_informant": "",
            "CORRECTION_waves": "",
            "anxiety_or_internalising_threshold_used": "",
            "item_level_data_available?": "",
            "comments": "",
        })
    return pd.DataFrame(rows)


def write_all(outdir: pathlib.Path, *, normalised, crosswalk, summary, audit_df,
              register, link, pairs, cfg, prov, docs_dir: pathlib.Path | None = None,
              internal_detail: bool = False) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)
    written = {}

    def _w(name, df):
        p = outdir / name
        df.to_csv(p, index=False)
        written[name] = len(df)

    _w("dictionary_normalised.csv", normalised)
    _w("crosswalk_full.csv", crosswalk)
    _w("coverage_matrix.csv", summary)
    _w("claim_audit.csv", audit_df)
    _w("non_harmonisable_register.csv", register)
    _w("step3_linkage.csv", link)
    if len(pairs):
        _w("anchor_item_pairs.csv", pairs)

    for cid, spec in cfg.cohorts.items():
        if spec["source"]["kind"] == "documented":
            _w(f"custodian_template_{cid}.csv", custodian_template(cfg, cid))

    static_page = coverage_html(summary, audit_df, register, link, cfg, prov)
    (outdir / "coverage_matrix.html").write_text(static_page)
    written["coverage_matrix.html"] = 1

    # The interactive page is what a reader actually uses; the static one stays as a
    # plain-HTML fallback and a print view.
    interactive = explore.page(explore.payload(
        crosswalk, summary, audit_df, register, link, cfg, prov, internal=False))
    (outdir / "explore.html").write_text(interactive)
    written["explore.html"] = 1

    if internal_detail:
        # Carries variable labels. Gitignored, and the page says so at the top.
        internal = explore.page(explore.payload(
            crosswalk, summary, audit_df, register, link, cfg, prov, internal=True))
        (outdir / "explore_internal.html").write_text(internal)
        written["explore_internal.html"] = 1

    # GitHub Pages serves /docs, so the report is browsable without cloning the repository.
    if docs_dir is not None:
        docs_dir.mkdir(parents=True, exist_ok=True)
        (docs_dir / "index.html").write_text(interactive)
        (docs_dir / "static.html").write_text(static_page)
        (docs_dir / ".nojekyll").write_text("")
        written["docs/index.html"] = 1
    return written
