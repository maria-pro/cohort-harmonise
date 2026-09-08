"""Configuration loading. Cohorts are config, not code."""
from __future__ import annotations

import pathlib
import yaml


class Config:
    def __init__(self, root: pathlib.Path, data_root: pathlib.Path):
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


def load(root: str | pathlib.Path, data_root: str | pathlib.Path | None = None) -> Config:
    root = pathlib.Path(root).resolve()
    dr = pathlib.Path(data_root).resolve() if data_root else root / "data" / "dictionaries"
    return Config(root, dr)
