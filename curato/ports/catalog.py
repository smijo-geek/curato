"""Catalog port — the metadata hub and the agents' shared memory. MVP: a JSON file.
Production adapters front OpenMetadata / Polaris / Purview with the same methods.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional
import json


class CatalogPort(ABC):
    @abstractmethod
    def put_dataset(self, name: str, meta: Dict[str, Any]) -> None: ...
    @abstractmethod
    def get_dataset(self, name: str) -> Optional[Dict[str, Any]]: ...
    @abstractmethod
    def put_product(self, name: str, meta: Dict[str, Any]) -> None: ...
    @abstractmethod
    def snapshot(self) -> Dict[str, Any]: ...


class JsonCatalog(CatalogPort):
    def __init__(self, path: str = "catalog/catalog.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._db = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.path.exists():
            return json.loads(self.path.read_text(encoding="utf-8"))
        return {"datasets": {}, "data_products": {}}

    def _save(self) -> None:
        self.path.write_text(json.dumps(self._db, indent=2, default=str), encoding="utf-8")

    def put_dataset(self, name: str, meta: Dict[str, Any]) -> None:
        self._db["datasets"][name] = meta
        self._save()

    def get_dataset(self, name: str) -> Optional[Dict[str, Any]]:
        return self._db["datasets"].get(name)

    def put_product(self, name: str, meta: Dict[str, Any]) -> None:
        self._db["data_products"][name] = meta
        self._save()

    def snapshot(self) -> Dict[str, Any]:
        return self._db


def get_catalog(cfg: dict) -> CatalogPort:
    root = cfg.get("root", ".")
    return JsonCatalog(str(Path(root) / "catalog" / "catalog.json"))
