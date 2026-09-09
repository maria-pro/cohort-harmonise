"""The interactive report.

A single self-contained page: no server, no build step, no external requests. The
crosswalk travels with it as JSON so a reader can filter, search and drill into any cell
offline, which is what a reviewer needs and what a static table cannot give.

Two payload modes. `internal=False` embeds counts, statuses, instrument resolution,
informants and example variable *names* only. `internal=True` adds variable labels, which
reproduce dictionary content ABCD's NDA and the AIFS terms do not let us redistribute, so
that page is written under a separate name and is never committed.

Rows are stored as arrays against a column list rather than objects, which roughly thirds
the payload: a dictionary crosswalk repeats the same twenty keys 1,500 times.
"""
from __future__ import annotations

import html
import json

PUBLIC_COLS = ["construct", "cohort", "wave_id", "wave_kind", "wave_year", "year_source",
               "digital_era", "status", "n_variables", "instruments_matched",
               "respondents", "example_variables"]
INTERNAL_EXTRA = ["example_labels"]

STATUS_LABELS = {
    "direct": "Direct",
    "partial": "Partial",
    "proxy": "Proxy",
    "governed_not_proxied": "Governed",
    "non_harmonisable": "Non-harmonisable",
    "absent": "Absent",
    "undeclared_wave": "Undeclared session",
}
TIER_LABELS = {
    "official_dictionary": "custodian dictionary",
    "published_profile": "published profile",
    "reconstructed": "reconstructed from publications",
}


def payload(cw, summary, audit_df, register, link, cfg, prov, internal: bool = False) -> dict:
    cols = PUBLIC_COLS + (INTERNAL_EXTRA if internal else [])
    d = cw[~cw["wave_id"].astype(str).str.startswith("UNDECLARED")].copy()
    for c in cols:
        if c not in d.columns:
            d[c] = ""
    d["wave_year"] = d["wave_year"].fillna("").astype(str).str.replace(".0", "", regex=False)
    rows = d[cols].astype(str).values.tolist()

    constructs = []
    seen = []
    for con in cfg.constructs:
        sub = summary[summary["construct"] == con["id"]]
        constructs.append({
            "id": con["id"],
            "label": con["label"],
            "role": con.get("role", ""),
            "core": bool(con.get("core", False)),
            "nh": bool(con.get("declared_non_harmonisable", False)),
            "reason": " ".join(str(con.get("reason", "")).split()),
            "note": " ".join(str(con.get("partial_coverage_note", "")).split()),
            "instruments": con.get("preferred_instruments", []) or [],
            "best": {r["cohort"]: {"status": r["status"],
                                  "waves": int(r["waves_with_data"]),
                                  "supp": int(r.get("supplementary_sessions_with_data", 0)),
                                  "n": int(r["n_variables"])}
                     for _, r in sub.iterrows()},
        })
        seen.append(con["id"])

    cohorts = []
    for cid in cfg.cohort_order():
        spec = cfg.cohorts[cid]
        gov = spec.get("governance") or {}
        cohorts.append({
            "id": cid,
            "short": spec["short_name"],
            "name": spec["name"],
            "number": spec["cohort_number"],
            "tier": str(spec["tier"]),
            "country": spec.get("country", ""),
            "release": spec.get("release", ""),
            "evidence": spec["evidence_tier"],
            "evidence_label": TIER_LABELS.get(spec["evidence_tier"], spec["evidence_tier"]),
            "waves": spec.get("waves_per_participant"),
            "waves_note": " ".join(str(spec.get("waves_per_participant_note", "")).split()),
            "rows": prov["cohorts"][cid]["rows_ingested"],
            "governed": bool(gov.get("requires_signoff", False)),
            "pending": spec.get("pending_from", ""),
        })

    thresholds = []
    for t in cfg.thresholds:
        thresholds.append({
            "cohort": t["cohort"], "instrument": t.get("instrument") or "",
            "rule": t.get("rule", ""), "status": t.get("status", ""),
            "citation": " ".join(str(t.get("citation", "")).split()),
            "caveat": " ".join(str(t.get("primary_source_unresolved", "")).split()),
            "sex_specific": t.get("sex_specific") or None,
        })

    return {
        "generated": prov["generated_utc"],
        "version": prov["version"],
        "revision": prov["git_revision"],
        "internal": internal,
        "cols": cols,
        "rows": rows,
        "constructs": constructs,
        "cohorts": cohorts,
        "audit": audit_df.fillna("").astype(str).to_dict("records"),
        "register": register.fillna("").astype(str).to_dict("records"),
        "linkage": link.fillna("").astype(str).to_dict("records"),
        "thresholds": thresholds,
        "statusLabels": STATUS_LABELS,
        "totalRows": sum(c["rows"] for c in cohorts),
    }


CSS = """
:root{
  --paper:#f4f6fa;--panel:#fff;--panel-2:#e9eef5;--ink:#151a21;--soft:#586371;--faint:#828d9c;
  --rule:#d8dfe8;--accent:#26618f;
  --direct:#0f6d5c;--direct-bg:#dcefeb;--partial:#4a5aa8;--partial-bg:#e3e6f7;
  --proxy:#6a58a4;--proxy-bg:#e7e3f4;--gov:#8a4b74;--gov-bg:#f2e3ed;
  --nh:#495260;--nh-bg:#e5e9f0;--absent:#98304c;--absent-bg:#f5e1e7;
  --pass:#0f6d5c;--mismatch:#98304c;--unver:#4a5aa8;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --paper:#0f1318;--panel:#161b22;--panel-2:#1d242d;--ink:#e5eaf1;--soft:#98a3b2;--faint:#6f7a8a;
  --rule:#2a323c;--accent:#79b2e8;
  --direct:#6ad0bd;--direct-bg:#11302b;--partial:#98a4f0;--partial-bg:#1d2040;
  --proxy:#b7a7e8;--proxy-bg:#241e37;--gov:#dc9abf;--gov-bg:#321c29;
  --nh:#b2bbc9;--nh-bg:#222832;--absent:#ef8f9d;--absent-bg:#391b24;
  --pass:#6ad0bd;--mismatch:#ef8f9d;--unver:#98a4f0;
}}
:root[data-theme="dark"]{
  --paper:#0f1318;--panel:#161b22;--panel-2:#1d242d;--ink:#e5eaf1;--soft:#98a3b2;--faint:#6f7a8a;
  --rule:#2a323c;--accent:#79b2e8;
  --direct:#6ad0bd;--direct-bg:#11302b;--partial:#98a4f0;--partial-bg:#1d2040;
  --proxy:#b7a7e8;--proxy-bg:#241e37;--gov:#dc9abf;--gov-bg:#321c29;
  --nh:#b2bbc9;--nh-bg:#222832;--absent:#ef8f9d;--absent-bg:#391b24;
  --pass:#6ad0bd;--mismatch:#ef8f9d;--unver:#98a4f0;
}
*{box-sizing:border-box}
body{background:var(--paper);color:var(--ink);margin:0;padding:28px 20px 80px;
 font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:1240px;margin:0 auto}
h1{font-size:24px;line-height:1.2;letter-spacing:-.012em;margin:0 0 6px;text-wrap:balance}
.sub{color:var(--faint);font-size:12.5px;margin:0 0 16px;font-variant-numeric:tabular-nums}
.lede{color:var(--soft);max-width:82ch;margin:0 0 18px}
h2{font-size:17px;margin:34px 0 4px;letter-spacing:-.005em}
h2 .n{color:var(--faint);font-weight:400;font-size:13px}
mark{background:var(--partial-bg);color:var(--ink);border-radius:2px;padding:0 1px}

/* tabs */
.tabs{display:flex;gap:2px;flex-wrap:wrap;border-bottom:1px solid var(--rule);margin:0 0 18px}
.tab{appearance:none;background:none;border:0;border-bottom:2px solid transparent;
 color:var(--soft);font:inherit;font-size:14px;padding:9px 13px;cursor:pointer;border-radius:4px 4px 0 0}
.tab:hover{color:var(--ink);background:var(--panel-2)}
.tab[aria-selected="true"]{color:var(--ink);font-weight:600;border-bottom-color:var(--accent)}
.tab:focus-visible{outline:2px solid var(--accent);outline-offset:-2px}
.tab .c{color:var(--faint);font-weight:400;font-variant-numeric:tabular-nums}

/* controls */
.controls{display:flex;flex-wrap:wrap;gap:14px 22px;align-items:flex-end;
 background:var(--panel);border:1px solid var(--rule);border-radius:8px;padding:13px 15px;margin:0 0 16px}
.ctl{display:flex;flex-direction:column;gap:6px}
.ctl>label{font-size:10.5px;letter-spacing:.07em;text-transform:uppercase;color:var(--faint)}
input[type=search]{font:inherit;font-size:14px;padding:6px 10px;min-width:230px;
 background:var(--paper);color:var(--ink);border:1px solid var(--rule);border-radius:5px}
input[type=search]:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
.chips{display:flex;flex-wrap:wrap;gap:5px}
.chip{appearance:none;font:inherit;font-size:12px;padding:3px 9px;cursor:pointer;
 background:var(--paper);color:var(--soft);border:1px solid var(--rule);border-radius:20px}
.chip:hover{color:var(--ink)}
.chip[aria-pressed="true"]{background:var(--ink);color:var(--paper);border-color:var(--ink)}
.chip:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
.chip.s-direct[aria-pressed="true"]{background:var(--direct);border-color:var(--direct);color:var(--paper)}
.chip.s-partial[aria-pressed="true"]{background:var(--partial);border-color:var(--partial);color:var(--paper)}
.chip.s-proxy[aria-pressed="true"]{background:var(--proxy);border-color:var(--proxy);color:var(--paper)}
.chip.s-absent[aria-pressed="true"]{background:var(--absent);border-color:var(--absent);color:var(--paper)}
.chip.s-non_harmonisable[aria-pressed="true"]{background:var(--nh);border-color:var(--nh);color:var(--paper)}
.chip.s-governed_not_proxied[aria-pressed="true"]{background:var(--gov);border-color:var(--gov);color:var(--paper)}
.reset{margin-left:auto;color:var(--accent);background:none;border:0;font:inherit;font-size:13px;cursor:pointer;padding:6px 0}
.reset:focus-visible{outline:2px solid var(--accent);outline-offset:2px}

/* tables */
.panel{background:var(--panel);border:1px solid var(--rule);border-radius:8px;overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:13.5px}
th,td{text-align:left;padding:8px 11px;border-bottom:1px solid var(--rule);vertical-align:top}
th{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--faint);font-weight:600;
 position:sticky;top:0;background:var(--panel);z-index:2}
tr:last-child td{border-bottom:0}
td.rowhead{font-weight:600;min-width:200px}
td.rowhead small{display:block;font-weight:400;color:var(--faint);font-size:11px;margin-top:1px}
th .small,td .small{font-size:10.5px;font-weight:400;color:var(--faint);text-transform:none;letter-spacing:0}
.num{font-variant-numeric:tabular-nums}

/* cells */
.cellbtn{appearance:none;background:none;border:0;padding:0;font:inherit;cursor:pointer;text-align:left;width:100%;border-radius:5px}
.cellbtn:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.pill{display:inline-block;padding:2px 7px;border-radius:5px;font-size:12px;font-weight:600;white-space:nowrap}
.cellbtn:hover .pill{filter:brightness(.96)}
.s-direct{color:var(--direct);background:var(--direct-bg)}
.s-partial{color:var(--partial);background:var(--partial-bg)}
.s-proxy{color:var(--proxy);background:var(--proxy-bg)}
.s-governed_not_proxied{color:var(--gov);background:var(--gov-bg)}
.s-non_harmonisable{color:var(--nh);background:var(--nh-bg)}
.s-absent{color:var(--absent);background:var(--absent-bg)}
.wv{display:block;color:var(--faint);font-size:10.5px;margin-top:2px;font-variant-numeric:tabular-nums}
.v-PASS{color:var(--pass);background:var(--direct-bg)}
.v-MISMATCH{color:var(--mismatch);background:var(--absent-bg)}
.v-UNVERIFIABLE{color:var(--unver);background:var(--partial-bg)}
.tierchip{display:inline-block;font-size:10.5px;padding:1px 6px;border-radius:14px;border:1px solid var(--rule);color:var(--faint)}
.e-official_dictionary{border-color:var(--direct);color:var(--direct)}
.e-published_profile{border-color:var(--partial);color:var(--partial)}
.e-reconstructed{border-color:var(--proxy);color:var(--proxy)}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11.5px}
.empty{padding:26px 14px;color:var(--faint);text-align:center}

/* drawer */
.scrim{position:fixed;inset:0;background:rgba(10,10,12,.42);opacity:0;pointer-events:none;transition:opacity .16s}
.scrim.open{opacity:1;pointer-events:auto}
.drawer{position:fixed;top:0;right:0;bottom:0;width:min(660px,94vw);background:var(--panel);
 border-left:1px solid var(--rule);box-shadow:-14px 0 40px rgba(0,0,0,.16);
 transform:translateX(100%);transition:transform .18s ease;overflow-y:auto;padding:20px 22px 40px;z-index:10}
.drawer.open{transform:none}
@media (prefers-reduced-motion:reduce){.drawer,.scrim{transition:none}}
.drawer h3{margin:0 0 2px;font-size:18px;letter-spacing:-.01em}
.drawer .dsub{color:var(--faint);font-size:12.5px;margin:0 0 14px}
.close{position:absolute;top:14px;right:16px;appearance:none;background:var(--panel-2);border:1px solid var(--rule);
 color:var(--soft);border-radius:6px;font:inherit;font-size:13px;padding:4px 9px;cursor:pointer}
.close:hover{color:var(--ink)}
.close:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
.kv{display:grid;grid-template-columns:auto 1fr;gap:5px 14px;font-size:13px;margin:0 0 16px}
.kv dt{color:var(--faint)}
.kv dd{margin:0}
.callout{border-left:3px solid var(--rule);padding:8px 12px;margin:0 0 16px;font-size:13px;color:var(--soft);background:var(--panel-2);border-radius:0 5px 5px 0}
.callout.nh{border-left-color:var(--nh)}
.callout.note{border-left-color:var(--partial)}
footer{margin-top:44px;padding-top:14px;border-top:1px solid var(--rule);color:var(--faint);font-size:12px;max-width:88ch}
.banner{background:var(--absent-bg);color:var(--absent);border:1px solid var(--absent);
 border-radius:6px;padding:9px 13px;font-size:13px;font-weight:600;margin:0 0 16px}
"""

JS = r"""
const D = window.__HARMONISE__;
const $ = (s, r) => (r || document).querySelector(s);
const el = (t, a, kids) => {
  const n = document.createElement(t);
  for (const k in (a || {})) {
    if (k === 'class') n.className = a[k];
    else if (k === 'text') n.textContent = a[k];
    else if (k === 'html') n.innerHTML = a[k];
    else n.setAttribute(k, a[k]);
  }
  (kids || []).forEach(c => c && n.appendChild(c));
  return n;
};
const esc = s => String(s == null ? '' : s);

const C = {};   // column index lookup
D.cols.forEach((c, i) => C[c] = i);

const state = {
  tab: 'coverage',
  q: '',
  cohorts: new Set(D.cohorts.map(c => c.id)),
  statuses: new Set(['direct', 'partial', 'proxy', 'governed_not_proxied', 'non_harmonisable', 'absent']),
  coreOnly: false,
  verdicts: new Set(['MISMATCH', 'UNVERIFIABLE', 'PASS'])
};

const cohortById = {};
D.cohorts.forEach(c => cohortById[c.id] = c);
const conById = {};
D.constructs.forEach(c => conById[c.id] = c);

const ROLE_ORDER = ['outcome', 'outcome_secondary', 'predictor', 'core_layer', 'mechanism'];
const roleRank = r => { const i = ROLE_ORDER.indexOf(r); return i < 0 ? 99 : i; };

function matchesQuery(con) {
  if (!state.q) return true;
  const q = state.q.toLowerCase();
  return (con.label + ' ' + con.id + ' ' + con.role + ' ' + (con.instruments || []).join(' '))
    .toLowerCase().includes(q);
}

function highlight(text) {
  if (!state.q) return esc(text);
  const i = text.toLowerCase().indexOf(state.q.toLowerCase());
  if (i < 0) return esc(text);
  const before = text.slice(0, i), hit = text.slice(i, i + state.q.length), after = text.slice(i + state.q.length);
  return esc(before) + '<mark>' + esc(hit) + '</mark>' + esc(after);
}

function visibleConstructs() {
  return D.constructs
    .filter(c => matchesQuery(c))
    .filter(c => !state.coreOnly || c.core)
    .filter(c => {
      const cs = [...state.cohorts];
      return cs.some(id => {
        const b = c.best[id];
        return b && state.statuses.has(b.status);
      });
    })
    .sort((a, b) => roleRank(a.role) - roleRank(b.role) || a.id.localeCompare(b.id));
}

/* ---------------------------------------------------------------- coverage */
function renderCoverage() {
  const cohorts = D.cohorts.filter(c => state.cohorts.has(c.id));
  const cons = visibleConstructs();
  const host = $('#view');
  host.innerHTML = '';

  if (!cons.length || !cohorts.length) {
    host.appendChild(el('div', { class: 'panel' }, [
      el('p', { class: 'empty', text: 'Nothing matches those filters. Clear them to see the full matrix.' })]));
    return;
  }

  const thead = el('tr', {}, [el('th', { text: 'Construct' })].concat(cohorts.map(c =>
    el('th', {}, [
      el('div', { text: c.short }),
      el('div', { class: 'small', html: 'cohort ' + c.number + ' &middot; tier ' + c.tier + '<br>' + (c.waves || '?') + ' waves' })
    ]))));

  const rows = cons.map(con => {
    const head = el('td', { class: 'rowhead' }, [
      el('div', { html: highlight(con.label) }),
      el('small', { text: con.role.replace('_', ' ') + (con.core ? ' · core' : '') })
    ]);
    const cells = cohorts.map(c => {
      const b = con.best[c.id];
      const td = el('td');
      if (!b) { td.appendChild(el('span', { class: 'pill s-absent', text: 'no data' })); return td; }
      const bits = [];
      if (['direct', 'partial', 'proxy'].includes(b.status)) {
        bits.push(b.waves + (c.waves ? ' of ' + c.waves : '') + ' wave(s)');
        bits.push(b.n + ' vars');
        if (b.supp) bits.push('+' + b.supp + ' suppl.');
      }
      const btn = el('button', { class: 'cellbtn', type: 'button',
        'aria-label': con.label + ' in ' + c.short + ': ' + (D.statusLabels[b.status] || b.status) }, [
        el('span', { class: 'pill s-' + b.status, text: D.statusLabels[b.status] || b.status }),
        bits.length ? el('span', { class: 'wv', text: bits.join(' · ') }) : null
      ]);
      btn.addEventListener('click', () => openDrawer(con.id, c.id));
      td.appendChild(btn);
      return td;
    });
    return el('tr', {}, [head].concat(cells));
  });

  host.appendChild(el('div', { class: 'panel' }, [
    el('table', {}, [el('thead', {}, [thead]), el('tbody', {}, rows)])]));
  $('#shown').textContent = cons.length + ' of ' + D.constructs.length + ' constructs';
}

/* ------------------------------------------------------------------ drawer */
function openDrawer(conId, cohortId) {
  const con = conById[conId], co = cohortById[cohortId];
  const rows = D.rows.filter(r => r[C.construct] === conId && r[C.cohort] === cohortId);
  const body = $('#drawerBody');
  body.innerHTML = '';

  $('#drawerTitle').textContent = con.label;
  $('#drawerSub').innerHTML = co.short + ' &middot; cohort ' + co.number + ' &middot; tier ' + co.tier +
    ' &middot; <span class="tierchip e-' + co.evidence + '">' + co.evidence_label + '</span>';

  const b = con.best[cohortId] || {};
  const kv = el('dl', { class: 'kv' });
  const add = (k, v) => { if (!v && v !== 0) return; kv.appendChild(el('dt', { text: k })); kv.appendChild(el('dd', { html: v })); };
  add('Best status', '<span class="pill s-' + b.status + '">' + (D.statusLabels[b.status] || b.status) + '</span>');
  add('Primary waves with data', (b.waves || 0) + (co.waves ? ' of ' + co.waves : ''));
  if (b.supp) add('Supplementary sessions', b.supp);
  add('Variables matched', (b.n || 0).toLocaleString());
  add('Named instruments', (con.instruments || []).join(', ') || '—');
  add('Release', co.release);
  body.appendChild(kv);

  if (con.nh && con.reason) {
    body.appendChild(el('div', { class: 'callout nh' },
      [el('strong', { text: 'Declared non-harmonisable. ' }), el('span', { text: con.reason })]));
  }
  if (con.note) {
    body.appendChild(el('div', { class: 'callout note' },
      [el('strong', { text: 'Partial coverage. ' }), el('span', { text: con.note })]));
  }
  if (co.pending) {
    body.appendChild(el('div', { class: 'callout note' },
      [el('strong', { text: 'No custodian dictionary held. ' }),
       el('span', { text: 'Inventory built from publications; pending from ' + co.pending })]));
  }

  const hdr = ['Wave', 'Kind', 'Year', 'Era', 'Status', 'Vars', 'Instruments', 'Informants', 'Example variables'];
  if (D.internal) hdr.push('Example labels');
  const trs = rows.map(r => {
    const tds = [
      el('td', { class: 'mono', text: r[C.wave_id] }),
      el('td', { class: 'small', text: (r[C.wave_kind] || '').replace('_', ' ') }),
      el('td', { class: 'num', text: r[C.wave_year] || '—' }),
      el('td', { class: 'small', text: r[C.digital_era] }),
      el('td', {}, [el('span', { class: 'pill s-' + r[C.status], text: D.statusLabels[r[C.status]] || r[C.status] })]),
      el('td', { class: 'num', text: r[C.n_variables] }),
      el('td', { class: 'mono', text: r[C.instruments_matched] || '—' }),
      el('td', { class: 'small', text: r[C.respondents] || '—' }),
      el('td', { class: 'mono', text: r[C.example_variables] || '—' })
    ];
    if (D.internal) tds.push(el('td', { class: 'small', text: r[C.example_labels] || '—' }));
    return el('tr', {}, tds);
  });
  body.appendChild(el('div', { class: 'panel' }, [el('table', {}, [
    el('thead', {}, [el('tr', {}, hdr.map(h => el('th', { text: h })))]),
    el('tbody', {}, trs)])]));

  const th = D.thresholds.filter(t => t.cohort === cohortId && (conId === 'anx_caseness' || t.construct === conId));
  if (conId === 'anx_caseness' && th.length) {
    th.forEach(t => {
      const c = el('div', { class: 'callout note' }, [
        el('strong', { text: 'Threshold. ' }),
        el('span', { text: t.rule + (t.sex_specific ? ' (male ' + t.sex_specific.male + ', female ' + t.sex_specific.female + ')' : '') + ' — ' + t.citation })
      ]);
      if (t.caveat) c.appendChild(el('p', { style: 'margin:6px 0 0', text: t.caveat }));
      body.appendChild(c);
    });
  }

  $('#scrim').classList.add('open');
  $('#drawer').classList.add('open');
  $('#drawer').setAttribute('aria-hidden', 'false');
  $('#closeDrawer').focus();
}

function closeDrawer() {
  $('#scrim').classList.remove('open');
  $('#drawer').classList.remove('open');
  $('#drawer').setAttribute('aria-hidden', 'true');
}

/* ------------------------------------------------------------------- other tabs */
function renderClaims() {
  const host = $('#view');
  host.innerHTML = '';
  const rows = D.audit.filter(a => state.verdicts.has(a.verdict))
    .filter(a => !state.q || (a.assertion + ' ' + a.claim_id + ' ' + a.source + ' ' + a.evidence)
      .toLowerCase().includes(state.q.toLowerCase()));
  if (!rows.length) {
    host.appendChild(el('div', { class: 'panel' }, [el('p', { class: 'empty', text: 'No claims match those filters.' })]));
    return;
  }
  const trs = rows.map(a => el('tr', {}, [
    el('td', { class: 'mono', text: a.claim_id }),
    el('td', { class: 'small', text: a.source }),
    el('td', { html: highlight(a.assertion) }),
    el('td', {}, [el('span', { class: 'pill v-' + a.verdict, text: a.verdict })]),
    el('td', { class: 'small' }, [
      el('div', { text: a.evidence }),
      a.note ? el('div', { style: 'margin-top:5px;font-style:italic', text: a.note }) : null])
  ]));
  host.appendChild(el('div', { class: 'panel' }, [el('table', {}, [
    el('thead', {}, [el('tr', {}, ['Claim', 'Where it appears', 'Assertion', 'Verdict', 'What the dictionaries say']
      .map(h => el('th', { text: h })))]),
    el('tbody', {}, trs)])]));
  $('#shown').textContent = rows.length + ' of ' + D.audit.length + ' claims';
}

function renderRegister() {
  const host = $('#view');
  host.innerHTML = '';
  const trs = D.register.map(r => el('tr', {}, [
    el('td', { class: 'rowhead', text: r.construct_label }),
    el('td', { class: 'small', text: r.reason }),
    el('td', { class: 'small mono', text: r.absence_confirmed_in || '—' }),
    el('td', { class: 'small mono', text: r.possible_partial_coverage || '—' })
  ]));
  host.appendChild(el('div', { class: 'panel' }, [el('table', {}, [
    el('thead', {}, [el('tr', {}, ['Construct', 'Why it cannot be harmonised', 'Absence confirmed in', 'Possible partial coverage']
      .map(h => el('th', { text: h })))]),
    el('tbody', {}, trs)])]));
  $('#shown').textContent = D.register.length + ' declared non-harmonisable';
}

function renderLinkage() {
  const host = $('#view');
  host.innerHTML = '';
  const rows = D.linkage.slice().sort((a, b) =>
    (b.shared_instruments ? 1 : 0) - (a.shared_instruments ? 1 : 0) ||
    a.construct.localeCompare(b.construct));
  const trs = rows.map(r => el('tr', {}, [
    el('td', { class: 'small', text: r.construct }),
    el('td', { class: 'mono', text: r.cohort_a + ' ↔ ' + r.cohort_b }),
    el('td', { class: 'mono', text: r.shared_instruments || '—' }),
    el('td', { class: 'num', text: r.items_a + ' / ' + r.items_b }),
    el('td', { class: 'num', text: r.n_anchor_candidates }),
    el('td', {}, [el('span', {
      class: 'pill ' + (r.step3_verdict === 'anchor_candidates_found' ? 's-direct'
        : r.step3_verdict === 'shared_instrument_no_item_overlap' ? 's-partial' : 's-absent'),
      text: r.step3_verdict.replace(/_/g, ' ')
    })]),
    el('td', { class: 'small', text: r.why_not || '—' })
  ]));
  host.appendChild(el('div', { class: 'panel' }, [el('table', {}, [
    el('thead', {}, [el('tr', {}, ['Construct', 'Pair', 'Shared instrument', 'Items A / B', 'Anchors', 'Step 3 verdict', 'Why not']
      .map(h => el('th', { text: h })))]),
    el('tbody', {}, trs)])]));
  $('#shown').textContent = rows.length + ' cohort pairs assessed';
}

/* -------------------------------------------------------------------- shell */
function render() {
  const coverageOnly = $('#coverageControls');
  const claimOnly = $('#claimControls');
  coverageOnly.hidden = state.tab !== 'coverage';
  claimOnly.hidden = state.tab !== 'claims';
  ({ coverage: renderCoverage, claims: renderClaims, register: renderRegister, linkage: renderLinkage })[state.tab]();
}

function buildChips(host, items, isOn, toggle, cls) {
  host.innerHTML = '';
  items.forEach(it => {
    const b = el('button', {
      class: 'chip ' + (cls ? cls + it.id : ''), type: 'button',
      'aria-pressed': isOn(it.id) ? 'true' : 'false', text: it.label
    });
    b.addEventListener('click', () => { toggle(it.id); syncChips(); render(); });
    host.appendChild(b);
  });
}

function syncChips() {
  buildChips($('#cohortChips'), D.cohorts.map(c => ({ id: c.id, label: c.short })),
    id => state.cohorts.has(id), id => state.cohorts.has(id) ? state.cohorts.delete(id) : state.cohorts.add(id));
  buildChips($('#statusChips'),
    ['direct', 'partial', 'proxy', 'governed_not_proxied', 'non_harmonisable', 'absent']
      .map(s => ({ id: s, label: D.statusLabels[s] })),
    id => state.statuses.has(id),
    id => state.statuses.has(id) ? state.statuses.delete(id) : state.statuses.add(id), 's-');
  buildChips($('#verdictChips'), ['MISMATCH', 'UNVERIFIABLE', 'PASS'].map(v => ({ id: v, label: v })),
    id => state.verdicts.has(id),
    id => state.verdicts.has(id) ? state.verdicts.delete(id) : state.verdicts.add(id), 'v-');
  $('#coreToggle').setAttribute('aria-pressed', state.coreOnly ? 'true' : 'false');
}

function init() {
  document.querySelectorAll('.tab').forEach(t => t.addEventListener('click', () => {
    state.tab = t.dataset.tab;
    document.querySelectorAll('.tab').forEach(x => x.setAttribute('aria-selected', String(x === t)));
    render();
  }));
  $('#q').addEventListener('input', e => { state.q = e.target.value.trim(); render(); });
  $('#coreToggle').addEventListener('click', () => {
    state.coreOnly = !state.coreOnly; syncChips(); render();
  });
  $('#reset').addEventListener('click', () => {
    state.q = ''; $('#q').value = '';
    state.cohorts = new Set(D.cohorts.map(c => c.id));
    state.statuses = new Set(['direct', 'partial', 'proxy', 'governed_not_proxied', 'non_harmonisable', 'absent']);
    state.verdicts = new Set(['MISMATCH', 'UNVERIFIABLE', 'PASS']);
    state.coreOnly = false;
    syncChips(); render();
  });
  $('#closeDrawer').addEventListener('click', closeDrawer);
  $('#scrim').addEventListener('click', closeDrawer);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeDrawer(); });
  syncChips();
  render();
}
init();
"""


def page(data: dict) -> str:
    counts = {}
    for a in data["audit"]:
        counts[a["verdict"]] = counts.get(a["verdict"], 0) + 1
    banner = ""
    if data["internal"]:
        banner = ('<p class="banner">Internal view &mdash; contains variable labels drawn from the '
                  'cohort dictionaries. Do not publish or circulate outside the study team.</p>')
    n_official = sum(1 for c in data["cohorts"] if c["evidence"] == "official_dictionary")

    return f"""<title>Cohort Harmonisation Explorer</title>
<style>{CSS}</style>
<div class="wrap">
{banner}
<h1>Dictionary-level harmonisation across six cohorts</h1>
<p class="sub">{data['totalRows']:,} cohort&ndash;wave&ndash;variable rows &middot;
{n_official} of {len(data['cohorts'])} from custodian dictionaries &middot;
{counts.get('PASS', 0)} claims verified, {counts.get('MISMATCH', 0)} mismatches,
{counts.get('UNVERIFIABLE', 0)} unverifiable &middot;
generated {html.escape(data['generated'][:16].replace('T', ' '))} UTC &middot;
v{html.escape(data['version'])} &middot; rev {html.escape(data['revision'])}</p>
<p class="lede">Every construct is matched against each cohort&rsquo;s own data dictionary or, where no
custodian dictionary is held, against published documentation. Nothing is forced onto a common scale:
what cannot be aligned is declared, with a reason. Filter and search below, and select any cell to see
its wave-by-wave detail, informants and instrument resolution.</p>

<div class="tabs" role="tablist">
  <button class="tab" role="tab" data-tab="coverage" aria-selected="true">Coverage matrix</button>
  <button class="tab" role="tab" data-tab="claims" aria-selected="false">Claim audit <span class="c">{len(data['audit'])}</span></button>
  <button class="tab" role="tab" data-tab="register" aria-selected="false">Non-harmonisable <span class="c">{len(data['register'])}</span></button>
  <button class="tab" role="tab" data-tab="linkage" aria-selected="false">Step 3 feasibility <span class="c">{len(data['linkage'])}</span></button>
</div>

<div class="controls">
  <div class="ctl">
    <label for="q">Search</label>
    <input type="search" id="q" placeholder="construct, instrument, claim&hellip;" autocomplete="off">
  </div>
  <div class="ctl" id="coverageControls">
    <label>Cohorts</label>
    <div class="chips" id="cohortChips"></div>
  </div>
  <div class="ctl" id="coverageControls2">
    <label>Mapping status</label>
    <div class="chips" id="statusChips"></div>
  </div>
  <div class="ctl" id="claimControls" hidden>
    <label>Verdict</label>
    <div class="chips" id="verdictChips"></div>
  </div>
  <div class="ctl">
    <label>&nbsp;</label>
    <div class="chips"><button class="chip" type="button" id="coreToggle" aria-pressed="false">Core constructs only</button></div>
  </div>
  <button class="reset" type="button" id="reset">Reset filters</button>
</div>

<p class="sub" id="shown"></p>
<div id="view"></div>

<footer>
No participant data is read, produced or redistributed by this tool: it operates on variable-level
metadata only, and the dictionary files themselves are not committed to the repository. Wave counts are
over primary waves; mid-year check-ins, screeners and substudies are reported separately as
supplementary. Cohort 6 (LSIC) is analysed only under First Nations leadership and data-governance
principles, and the mapping engine refuses to treat its culturally grounded wellbeing indicators as a
proxy for a diagnostic construct.
</footer>
</div>

<div class="scrim" id="scrim"></div>
<aside class="drawer" id="drawer" aria-hidden="true" aria-labelledby="drawerTitle">
  <button class="close" type="button" id="closeDrawer">Close</button>
  <h3 id="drawerTitle"></h3>
  <p class="dsub" id="drawerSub"></p>
  <div id="drawerBody"></div>
</aside>

<script>window.__HARMONISE__ = {json.dumps(data, separators=(',', ':'))};</script>
<script>{JS}</script>
"""
