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


class S3Storage(StoragePort):
    """S3 adapter — also works against any S3-compatible store (MinIO, Ceph) via `endpoint_url`.
    Keys are the same relative paths the local adapter uses, so the agents behave identically.
    Needs the `s3` extra (boto3), imported lazily."""

    def __init__(self, bucket: str, prefix: str = "", **client_kwargs):
        import boto3
        self.s3 = boto3.client("s3", **client_kwargs)
        self.bucket = bucket
        self.prefix = prefix.strip("/")

    def _k(self, key: str) -> str:
        return f"{self.prefix}/{key}" if self.prefix else key

    def list(self, prefix: str) -> List[str]:
        full = self._k(prefix)
        out, token = [], None
        while True:
            kw = {"Bucket": self.bucket, "Prefix": full}
            if token:
                kw["ContinuationToken"] = token
            resp = self.s3.list_objects_v2(**kw)
            for o in resp.get("Contents", []):
                k = o["Key"]
                if self.prefix and k.startswith(self.prefix + "/"):
                    k = k[len(self.prefix) + 1:]
                out.append(k)
            if not resp.get("IsTruncated"):
                return out
            token = resp.get("NextContinuationToken")

    def read_bytes(self, key: str) -> bytes:
        return self.s3.get_object(Bucket=self.bucket, Key=self._k(key))["Body"].read()

    def put_bytes(self, key: str, data: bytes) -> None:
        self.s3.put_object(Bucket=self.bucket, Key=self._k(key), Body=data)

    def local_path(self, key: str) -> str:
        # DuckDB/Spark read s3:// URIs directly (with httpfs + credentials configured).
        return f"s3://{self.bucket}/{self._k(key)}"


def get_storage(cfg: dict) -> StoragePort:
    kind = cfg.get("kind", "local")
    if kind == "local":
        return LocalStorage(cfg.get("root", "."))
    if kind == "s3":
        return S3Storage(cfg["bucket"], cfg.get("prefix", ""), **cfg.get("client", {}))
    raise NotImplementedError(
        f"Storage adapter '{kind}' not registered. Implement StoragePort and add it here."
    )
