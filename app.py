"""Wiring: load config and construct the ports. Everything cloud-specific is chosen here.
The agents receive these objects and never know which implementation they got.
"""
from __future__ import annotations
from pathlib import Path
import yaml

from ports.storage import get_storage
from ports.catalog import get_catalog
from ports.compute import get_compute
from ports.llm import get_llm
from ports.extraction import PdfInvoiceExtractor

ROOT = Path(__file__).resolve().parent


def load_config() -> dict:
    return yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))


def build():
    cfg = load_config()
    storage_cfg = cfg["storage"]
    storage_cfg.setdefault("root", str(ROOT))
    return {
        "cfg": cfg,
        "storage": get_storage(storage_cfg),
        "catalog": get_catalog({"root": storage_cfg["root"]}),
        "compute": get_compute(cfg),
        "llm": get_llm(cfg.get("llm", {})),
        "extractor": PdfInvoiceExtractor(),
        "glossary": cfg["glossary"],
        "warehouse_root": str(Path(storage_cfg["root"]) / "warehouse"),
    }
