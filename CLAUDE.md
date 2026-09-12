# Working notes for this repository

Load-bearing things a new session needs before touching anything. Detail lives in `README.md`
and `docs/`; this is the short list of what will otherwise cost you an hour.

## Never commit custodian material

A study custodian supplied documentation privately. It must not reach the tracked tree. This has
been got wrong **twice**, and both times because the check ran in the same command as the commit,
so its output scrolled past unread.

```
./tools/check_private.sh && git commit ...
```

Run it as a **gate**, never alongside. The marker list is `configs/cohorts/local/private-markers.txt`,
which is gitignored — a list of private instrument names is itself private. It records which
instruments are *not* listed and why: CSPS, the ActiGraph scoring algorithms, PAPA, CAPA, CBCL and
the SDQ are all established by published papers and are ours to cite.

`configs/cohorts/local/` holds overlay configs merged over the committed ones at load time.
`--public` ignores them; **the committed artefacts must be generated with `--public`.**

A note in a config that quotes the claim under audit is also a leak, and worse, it lets the tool
resolve an instrument from our own commentary. Entry notes are deliberately kept out of any
searchable field.

## Two separate credential systems

| | Reads from | Account |
|---|---|---|
| `git push` | macOS keychain, `credential.helper = osxkeychain` | `maria-pro` |
| `gh` commands | gh's own keyring | `MariaAise` |

They do not share. `gh` fails on this repo with a misleading *"workflow scope may be required"* —
the real cause is that the gh account has no write access. Use the browser for Releases, or
`gh auth login` as `maria-pro` then `gh auth switch --user maria-pro`.

## Regenerating

A full run reads ~516,000 cohort–wave–variable rows and takes several minutes. For presentation
changes use `harmonise render`, which rebuilds the HTML from the last run's tables in about a
second and refuses if those tables are absent.

```
harmonise run --public --data-root "/Volumes/Crucial X9/grant"     # full, publishable
harmonise run --public --include-governed --internal-detail ...    # local only, never committed
harmonise render                                                   # pages only
harmonise audit --strict --require-cohorts lsac,abcd,ttm,lsic      # the pre-submission gate
```

Dictionaries live outside the repo at `/Volumes/Crucial X9/grant/`. They are not redistributable.

## Things that are deliberate, not bugs

- **LSIC keeps `cohort_number: 6`** with a gap at 5. Cohort 5 was assessed and removed in v0.2.0;
  reindexing is a decision about the study protocol, not about code, and the gap records the removal.
- **The `reconstructed` evidence tier is unused.** It encodes a property of the method — a cohort
  documented only from publications can fail to confirm a claim but cannot contradict one — not a
  property of any one cohort.
- **LSIC is excluded from published output** unless `--include-governed`, and its wellbeing
  indicators cannot be mapped as standing in for a diagnostic construct. Both are enforced in
  `governance.py` and reachable from a real run; there are tests for both.

## Counts are not tallies

`n_variables` is a count of rows matching a keyword rule. Independent review found real false
positives inside it — a CBCL Thought Problems item matched on "Nervous", ABCD administrative
metadata matched as social context, ABCD longitudinal variable variants counted twice. **Read a
count as *where to look*, not as *how much is there*.** Status, instrument resolution and informant
are more reliable than the number beside them.

## Traps that have already bitten

- Matching patterns need word boundaries: `panic` matched **Hispanic** across 117 ABCD rows;
  `late` matched *related*; `k10` matched `k100`. Short aliases take a right boundary, long ones are
  stems and must not.
- `SDQ-I` and `SDQ-II` are the **Self-Description** Questionnaire. No boundary rule separates them
  from `SDQ-25`; they are excluded by name in `exclude_if`.
- LSAC's `Person Label` is `"Not applicable"` for **all 40 CAS-8 item rows**, which are child
  self-complete. Do not take the informant from that column for LSAC's anxiety items.
- A check that cannot fail is worse than no check. `construct_not_pooled` once had a hard-coded
  `PASS` and reported green beside evidence contradicting it. There is now a test asserting the
  verdict is not unconditional.
- Editing a test file by index slicing silently deleted eight tests and the suite still passed at
  21. Check the test count, not just the colour.

## Layout

```
configs/cohorts/*.yaml    one per cohort; adding one is config, not code
configs/cohorts/local/    gitignored overlays and the private marker list
configs/constructs.yaml   target constructs, instrument aliases, thresholds
configs/claims.yaml       the assertions the audit checks, each with its source
src/harmonise/            ingest → normalise → mapping → linkage → audit → report/explore
outputs/                  generated; the bulk tables are gitignored
docs/                     Pages serves this; index.html is the interactive report
tools/check_private.sh    the commit gate
```
