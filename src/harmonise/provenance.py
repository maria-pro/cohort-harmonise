"""Provenance. The harmonisation claim is only reproducible against specific releases."""
from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
import platform
import subprocess


def _sha256(p: pathlib.Path, limit: int = 1 << 30) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        read = 0
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
            read += len(chunk)
            if read >= limit:
                break
    return h.hexdigest()


def _git_rev(root: pathlib.Path) -> str:
    try:
        return subprocess.run(["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, timeout=10).stdout.strip() or "not a git checkout"
    except Exception:
        return "unavailable"


def build(cfg, frames: dict, version: str) -> dict:
    cohorts = {}
    for cid, spec in cfg.cohorts.items():
        src = spec.get("source", {})
        rel = src.get("path")
        entry = {
            "name": spec["name"],
            "cohort_number": spec["cohort_number"],
            "tier": str(spec["tier"]),
            "release": spec.get("release", ""),
            "evidence_tier": spec["evidence_tier"],
            "adapter": src.get("kind"),
            "config_file": spec.get("_config_file"),
            "rows_ingested": int(len(frames[cid])) if cid in frames else 0,
            "governance_required": bool((spec.get("governance") or {}).get("restricted", False)),
        }
        if rel:
            p = cfg.resolve(rel)
            entry["source_file"] = rel
            entry["source_present"] = p.exists()
            if p.exists():
                st = p.stat()
                entry["source_bytes"] = st.st_size
                entry["source_mtime"] = datetime.datetime.fromtimestamp(
                    st.st_mtime, datetime.timezone.utc).isoformat()
                entry["source_sha256"] = _sha256(p)
        if spec.get("pending_from"):
            entry["pending_from"] = spec["pending_from"]
        if spec.get("citations"):
            entry["citations"] = {k: (v.get("doi") or v.get("url") or v.get("ref"))
                                  for k, v in spec["citations"].items()}
        cohorts[cid] = entry

    return {
        "tool": "cohort-harmonise",
        "version": version,
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "git_revision": _git_rev(cfg.root),
        "python": platform.python_version(),
        "periodisation": cfg.constructs_doc["periodisation"],
        "cohorts": cohorts,
        "note": (
            "Dictionary files are not redistributed. Hashes let a third party confirm they ran "
            "the tool against the same releases."
        ),
    }


def write(obj: dict, path: pathlib.Path) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=False) + "\n")
