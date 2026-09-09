"""Configuration loading. Cohorts are config, not code."""
from __future__ import annotations

import pathlib
import yaml


class Config:
    def __init__(self, root: pathlib.Path, data_root: pathlib.Path, use_local: bool = True):
        self.root = root
        self.data_root = data_root
        self.cohorts = {}
        cdir = root / "configs" / "cohorts"
        # macOS writes AppleDouble sidecar files (._name) on non-HFS volumes; ignore them.
        for f in sorted(cdir.glob("*.yaml")):
            if f.name.startswith("._"):
                continue
            spec = yaml.safe_load(f.read_text(encoding="utf-8"))
            spec["_config_file"] = f.name
            # A cohort may have material that cannot be published — documentation supplied
            # privately by a custodian, say. The committed file carries only what public
            # sources support; an overlay under cohorts/local/ (gitignored) adds the rest
            # for runs inside the study team, and records that it did.
            overlay_path = cdir / "local" / f.name
            if use_local and overlay_path.exists():
                overlay = yaml.safe_load(overlay_path.read_text(encoding="utf-8")) or {}
                for k, v in overlay.items():
                    if k.startswith("_") or k == "cohort_id":
                        continue
                    if isinstance(v, dict) and isinstance(spec.get(k), dict):
                        spec[k] = {**spec[k], **v}
                    else:
                        spec[k] = v
                spec["_local_overlay"] = True
            self.cohorts[spec["cohort_id"]] = spec
        self.constructs_doc = yaml.safe_load((root / "configs" / "constructs.yaml").read_text(encoding="utf-8"))
        self.claims_doc = yaml.safe_load((root / "configs" / "claims.yaml").read_text(encoding="utf-8"))

    @property
    def constructs(self) -> list[dict]:
        return self.constructs_doc["constructs"]

    @property
    def instruments(self) -> list[dict]:
        return self.constructs_doc["instruments"]

    @property
    def thresholds(self) -> list[dict]:
        return self.constructs_doc.get("thresholds", [])

    @property
    def bands(self) -> list[dict]:
        return self.constructs_doc["periodisation"]["bands"]

    def construct(self, cid: str) -> dict:
        for c in self.constructs:
            if c["id"] == cid:
                return c
        raise KeyError(cid)

    def cohort_order(self) -> list[str]:
        """Cohorts in the application's Table B1 order."""
        return [c["cohort_id"] for c in sorted(self.cohorts.values(), key=lambda s: s["cohort_number"])]

    def resolve(self, rel: str) -> pathlib.Path:
        return self.data_root / rel


def load(root: str | pathlib.Path, data_root: str | pathlib.Path | None = None,
         use_local: bool = True) -> Config:
    root = pathlib.Path(root).resolve()
    dr = pathlib.Path(data_root).resolve() if data_root else root / "data" / "dictionaries"
    return Config(root, dr, use_local=use_local)
