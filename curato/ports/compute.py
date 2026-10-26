"""Compute port — runs the deterministic transforms the agents generate. MVP: DuckDB.
Production adapters run the same SQL/jobs on Spark or Trino.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
import pandas as pd


class ComputePort(ABC):
    @abstractmethod
    def query(self, sql: str) -> pd.DataFrame: ...
    @abstractmethod
    def write_table(self, df: pd.DataFrame, path: str) -> None: ...


class DuckDBCompute(ComputePort):
    def __init__(self):
        import duckdb
        self.con = duckdb.connect()

    def query(self, sql: str) -> pd.DataFrame:
        return self.con.execute(sql).fetchdf()

    def write_table(self, df: pd.DataFrame, path: str) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        posix = p.as_posix()
        self.con.register("_tmp", df)
        try:
            self.con.execute(f"COPY _tmp TO '{posix}' (FORMAT PARQUET)")
        finally:
            self.con.unregister("_tmp")


def get_compute(cfg: dict) -> ComputePort:
    return DuckDBCompute()
