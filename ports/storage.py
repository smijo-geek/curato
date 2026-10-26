"""Storage port — an S3-style object interface. The MVP binds it to the local filesystem;
a cloud deployment swaps in an S3/ADLS/GCS adapter with the same four methods.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List


class StoragePort(ABC):
    @abstractmethod
    def list(self, prefix: str) -> List[str]: ...
    @abstractmethod
    def read_bytes(self, key: str) -> bytes: ...
    @abstractmethod
    def put_bytes(self, key: str, data: bytes) -> None: ...
    @abstractmethod
    def local_path(self, key: str) -> str:
        """Absolute path for engines (DuckDB/Spark) that read the object directly."""
        ...


class LocalStorage(StoragePort):
    def __init__(self, root: str = "."):
        self.root = Path(root).resolve()

    def _p(self, key: str) -> Path:
        return (self.root / key).resolve()

    def list(self, prefix: str) -> List[str]:
        base = self._p(prefix)
        if not base.exists():
            return []
        return [str(p.relative_to(self.root).as_posix())
                for p in sorted(base.rglob("*")) if p.is_file()]

    def read_bytes(self, key: str) -> bytes:
        return self._p(key).read_bytes()

    def put_bytes(self, key: str, data: bytes) -> None:
        p = self._p(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def local_path(self, key: str) -> str:
        return self._p(key).as_posix()


def get_storage(cfg: dict) -> StoragePort:
    kind = cfg.get("kind", "local")
    if kind == "local":
        return LocalStorage(cfg.get("root", "."))
    raise NotImplementedError(
        f"Storage adapter '{kind}' not in the MVP. Implement StoragePort and register it here."
    )
