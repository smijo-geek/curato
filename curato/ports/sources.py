"""Source connector port — connection-based ingestion (pull), for systems you query rather than
files you drop: relational databases, Salesforce, SAP CDS views.

A connector introspects the source's own metadata (table/field/view definitions), which is what
lets the catalog be generated automatically, and fetches rows on demand. Heavy SDKs are imported
lazily and gated behind optional extras, so the package installs without them.

Shipped & tested: RDBMSConnector (SQLAlchemy — Postgres/MySQL/SQL Server/Oracle/SQLite).
SAPCDSConnector — HANA-SQL mode shares the SQL path (tested on a SQLite view); OData mode tested
with a mock session. SalesforceConnector — tested with a mock client. The live drivers (HANA,
a real SAP OData service, a real Salesforce org) need those systems to run end-to-end.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class SourceConnector(ABC):
    @abstractmethod
    def list_objects(self) -> List[str]:
        """Tables / views / entities / sobjects available in the source."""
    @abstractmethod
    def schema(self, obj: str) -> Dict[str, str]:
        """Column -> source type, read from the system's own metadata (auto-catalog)."""
    @abstractmethod
    def fetch(self, obj: str) -> List[Dict[str, Any]]:
        """Rows for one object, as plain dicts."""


def _infer_types(records: List[Dict[str, Any]]) -> Dict[str, str]:
    schema: Dict[str, str] = {}
    for r in records:
        for k, v in r.items():
            if k not in schema and v is not None:
                schema[k] = type(v).__name__
    for r in records:            # ensure all-null columns still appear
        for k in r:
            schema.setdefault(k, "str")
    return schema


class _SqlMixin:
    """Shared SQLAlchemy plumbing for anything reachable over SQL."""

    def _connect(self, url: str) -> None:
        from sqlalchemy import create_engine, inspect, text
        self._text = text
        self._inspect = inspect
        self.engine = create_engine(url)

    def _schema_sql(self, obj: str) -> Dict[str, str]:
        return {c["name"]: str(c["type"]) for c in self._inspect(self.engine).get_columns(obj)}

    def _fetch_sql(self, obj: str) -> List[Dict[str, Any]]:
        safe = '"' + obj.replace('"', '') + '"'   # obj comes from metadata/config, not free text
        with self.engine.connect() as conn:
            result = conn.execute(self._text(f"SELECT * FROM {safe}"))
            return [dict(row._mapping) for row in result]


class RDBMSConnector(_SqlMixin, SourceConnector):
    """Any database SQLAlchemy can reach. `url` is a SQLAlchemy URL, e.g.
    sqlite:///app.db · postgresql+psycopg://user:pw@host/db · mssql+pyodbc://... · oracle+oracledb://..."""

    def __init__(self, url: str):
        self._connect(url)

    def list_objects(self) -> List[str]:
        return list(self._inspect(self.engine).get_table_names())

    def schema(self, obj: str) -> Dict[str, str]:
        return self._schema_sql(obj)

    def fetch(self, obj: str) -> List[Dict[str, Any]]:
        return self._fetch_sql(obj)


class SAPCDSConnector(_SqlMixin, SourceConnector):
    """SAP CDS views, two access modes:

      access: hana   — CDS views are SQL views in HANA; read them over a SQLAlchemy HANA URL
                       (needs the `hana` extra: sqlalchemy-hana + hdbcli). Same SQL path as RDBMS.
      access: odata  — CDS views published as an OData service (e.g. S/4HANA Cloud); read the
                       entity sets over HTTP (needs `requests`).

    `view_prefix` (hana) filters to your CDS naming convention (e.g. "ZC_", "C_", "I_").
    """

    def __init__(self, access: str = "hana", url: str = "", view_prefix: str = "",
                 service_url: str = "", entities: List[str] | None = None,
                 user: str = "", password: str = "", session: Any = None):
        self.access = access
        if access in ("hana", "sql"):
            self._connect(url)
            self.view_prefix = view_prefix
        elif access == "odata":
            self.service_url = service_url.rstrip("/")
            self._entities = entities
            if session is not None:
                self.session = session
            else:
                import requests
                s = requests.Session()
                if user:
                    s.auth = (user, password)
                self.session = s
        else:
            raise ValueError("SAP CDS access must be 'hana' or 'odata'")

    # -- OData helpers --
    def _odata_json(self, path: str) -> dict:
        url = f"{self.service_url}/{path}"
        sep = "&" if "?" in url else "?"
        resp = self.session.get(f"{url}{sep}$format=json")
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _odata_rows(payload: dict) -> List[Dict[str, Any]]:
        d = payload.get("d", payload)
        rows = d.get("results", d) if isinstance(d, dict) else d
        if isinstance(rows, dict):
            rows = rows.get("value", [])
        out = []
        for r in (rows or []):
            r = dict(r)
            r.pop("__metadata", None)
            out.append(r)
        return out

    def list_objects(self) -> List[str]:
        if self.access in ("hana", "sql"):
            insp = self._inspect(self.engine)
            names = set(insp.get_view_names()) | set(insp.get_table_names())
            if self.view_prefix:
                names = {n for n in names if n.startswith(self.view_prefix)}
            return sorted(names)
        if self._entities:
            return list(self._entities)
        import re
        md = self.session.get(f"{self.service_url}/$metadata")
        md.raise_for_status()
        return re.findall(r'EntitySet Name="([^"]+)"', md.text)

    def schema(self, obj: str) -> Dict[str, str]:
        if self.access in ("hana", "sql"):
            return self._schema_sql(obj)
        return _infer_types(self.fetch(obj)[:50])

    def fetch(self, obj: str) -> List[Dict[str, Any]]:
        if self.access in ("hana", "sql"):
            return self._fetch_sql(obj)
        return self._odata_rows(self._odata_json(obj))


class SalesforceConnector(SourceConnector):
    """EXPERIMENTAL — unit-tested with a mock client; run against a real org to use for real.
    Needs the `sf` extra (simple-salesforce)."""

    def __init__(self, username: str = "", password: str = "", security_token: str = "",
                 domain: str = "login", objects: List[str] | None = None, client: Any = None):
        if client is not None:
            self.sf = client
        else:
            from simple_salesforce import Salesforce
            self.sf = Salesforce(username=username, password=password,
                                 security_token=security_token, domain=domain)
        self._objects = objects

    def list_objects(self) -> List[str]:
        if self._objects:
            return self._objects
        return [s["name"] for s in self.sf.describe()["sobjects"] if s.get("queryable", True)]

    def schema(self, obj: str) -> Dict[str, str]:
        meta = getattr(self.sf, obj).describe()
        return {f["name"]: f["type"] for f in meta["fields"]}

    def fetch(self, obj: str) -> List[Dict[str, Any]]:
        fields = list(self.schema(obj).keys())
        res = self.sf.query_all(f"SELECT {', '.join(fields)} FROM {obj}")
        rows = []
        for r in res["records"]:
            r = dict(r)
            r.pop("attributes", None)
            rows.append(r)
        return rows


def build_connector(cfg: Dict[str, Any]) -> SourceConnector:
    kind = cfg.get("kind")
    if kind in ("rdbms", "sql", "database"):
        return RDBMSConnector(cfg["url"])
    if kind == "sap":
        return SAPCDSConnector(
            access=cfg.get("access", "hana"), url=cfg.get("url", ""),
            view_prefix=cfg.get("view_prefix", ""), service_url=cfg.get("service_url", ""),
            entities=cfg.get("entities"), user=cfg.get("user", ""), password=cfg.get("password", ""))
    if kind in ("salesforce", "sf"):
        return SalesforceConnector(
            username=cfg.get("username", ""), password=cfg.get("password", ""),
            security_token=cfg.get("security_token", ""), domain=cfg.get("domain", "login"),
            objects=cfg.get("objects"))
    raise NotImplementedError(f"Source connector '{kind}' not registered. See curato/ports/sources.py.")
