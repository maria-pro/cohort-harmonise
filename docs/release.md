# Releasing, and minting a DOI

A citation in a grant or paper should point at a fixed, archived version, not at a moving branch.

## The one thing that catches people out

**Zenodo triggers on a GitHub *Release*, not on a git tag.** Pushing a tag with `git push origin
v0.2.0` creates a tag and Zenodo never sees it. The Release object is what fires the webhook.

And it only fires for Releases created **after** the repository is switched on at Zenodo. A Release
published first is invisible, and you would need a further version to trigger one.

For this reason the existing `v0.1.0` tag is a plain annotated tag with no Release attached. It
marks the last commit before cohort 5 was removed, so the earlier configuration can be recovered,
and it deliberately does not appear on Zenodo.

## Order of operations

1. **zenodo.org** — sign in *with GitHub*, using the account that owns this repository.
2. Account menu → **GitHub** → find `cohort-harmonise` → switch it **on**.
3. Check `.zenodo.json` is current: title, description, keywords, licence, and the creator list
   with ORCIDs and affiliations. Zenodo reads this file at release time and it takes precedence
   over `CITATION.cff`.
4. Regenerate the outputs so the committed reports match the code being archived:

   ```
   harmonise run --public --data-root /path/to/your/dictionaries
   ```

5. Create the Release, on GitHub under **Releases → Draft a new release**, or:

   ```
   gh release create v0.2.0 --title "v0.2.0" --notes-file docs/release-notes-v0.2.0.md
   ```

6. Zenodo archives it within a minute or two and mints two DOIs.

## Which DOI to cite

Zenodo mints a **version DOI**, fixed to that release, and a **concept DOI**, which always resolves
to the latest version.

**Cite the concept DOI.** A reference in a document submitted for assessment should keep resolving
as the code changes, and the version DOI would freeze to whatever was true on the day. On the Zenodo
record the concept DOI is the one described as representing all versions.

Add it to `CITATION.cff` under `identifiers:` with `type: doi` once you have it.

## Before you tag

- `pytest -q` passes.
- `./tools/check_private.sh` passes — nothing supplied privately by a custodian has reached the
  tracked tree.
- The claims gate passes, or its remaining mismatches are ones you have decided to accept:

  ```
  harmonise audit --strict --require-cohorts lsac,abcd,ttm,lsic
  ```

- `outputs/provenance.json` names the dictionary releases you intend to cite.
- The author list is settled. It is written into the DOI record permanently, and reordering it
  afterwards means a new version.

## Authorship

Creators are listed in `.zenodo.json` and `CITATION.cff`, and the two must agree. The list is for
contribution to *this software and its analysis*, which is narrower than the investigator list of
any study the tool reads. A cohort being described here is not by itself authorship of the tool.
