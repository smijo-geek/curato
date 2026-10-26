"""Wiring: construct the ports from the project's config. Everything cloud-specific is chosen
here; the agents never know which implementation they got.

A "project" is the directory you run `curato` from (like dbt's project dir). It holds config.yaml
and the landing/ warehouse/ catalog/ folders. If there is no config.yaml, a bundled default is
used so the tool still runs.
"""
from __future__ import annotations
from pathlib import Path
import yaml

from curato.ports.storage import get_storage
from curato.ports.catalog import get_catalog
from curato.ports.compute import get_compute
from curato.ports.llm import get_llm
from curato.ports.extraction import PdfInvoiceExtractor

PKG = Path(__file__).resolve().parent


def project_dir() -> Path:
    return Path.cwd()


def config_path() -> Path:
    p = project_dir() / "config.yaml"
    return p if p.exists() else PKG / "default_config.yaml"


def load_config() -> dict:
    return yaml.safe_load(config_path().read_text(encoding="utf-8"))


def build() -> dict:
    cfg = load_config()
    root = str(project_dir())
    storage_cfg = dict(cfg.get("storage", {"kind": "local"}))
    storage_cfg["root"] = root
    return {
        "cfg": cfg,
        "project": root,
        "storage": get_storage(storage_cfg),
        "catalog": get_catalog({"root": root}),
        "compute": get_compute(cfg),
        "llm": get_llm(cfg.get("llm", {})),
        "extractor": PdfInvoiceExtractor(),
        "glossary": cfg["glossary"],
        "warehouse_root": str(project_dir() / "warehouse"),
    }
