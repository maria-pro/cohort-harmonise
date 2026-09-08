# Releasing, and minting a DOI

A grant reference should point at a fixed, citable version, not at a moving branch.

## One-time setup (account owner)

1. Sign in at <https://zenodo.org> using the GitHub account that owns this repository.
2. Go to **GitHub** in the Zenodo account menu and switch this repository **on**.

Zenodo then watches for releases. This step needs a human with the GitHub account; it
cannot be scripted with a token.

## Each release

```bash
git tag -a v0.1.0 -m "First release: six-cohort dictionary harmonisation and claim audit"
git push origin v0.1.0
gh release create v0.1.0 --title "v0.1.0" --notes-file docs/release-notes-v0.1.0.md
```

Zenodo archives the tag and mints two DOIs:

- a **version DOI**, fixed to that tag; and
- a **concept DOI**, which always resolves to the latest version.

**Cite the concept DOI in a grant application.** The reference stays valid if the code
changes after submission, which a bare repository URL does not guarantee and a version DOI
does not do.

Add the DOI to `CITATION.cff` (`identifiers:` with `type: doi`) and to the README badge line
after the first release.

## Before tagging

- `pytest -q` passes.
- `harmonise run` completes against the dictionaries you hold, and `outputs/` is regenerated
  so the committed reports match the code.
- `CITATION.cff` carries the author list, ORCIDs and affiliations you want on the archive
  record — Zenodo reads it.
- `outputs/provenance.json` records the release version of every dictionary read. Check that
  the releases named there are the ones you intend to cite.
