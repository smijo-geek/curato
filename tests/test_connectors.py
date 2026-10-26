"""Connection-based source connectors + the pull → auto-catalog → serve path."""
import sqlite3
from types import SimpleNamespace

import pytest

from curato.ports.sources import (
    RDBMSConnector, SAPCDSConnector, SalesforceConnector, build_connector,
)


# ---------------- RDBMS (SQLite) ----------------

def _make_db(path):
    con = sqlite3.connect(path)
    con.executescript(
        "CREATE TABLE sales (vendor TEXT, amount REAL, dt TEXT);"
        "INSERT INTO sales VALUES ('Acme',100.5,'2026-01-01'),('Globex',250,'2026-01-02'),('Acme',50,'2026-02-01');"
        "CREATE VIEW ZC_SpendByVendor AS SELECT vendor, SUM(amount) AS amount FROM sales GROUP BY vendor;"
    )
    con.commit()
    con.close()


def test_rdbms_introspect_and_fetch(tmp_path):
    db = tmp_path / "shop.db"
    _make_db(str(db))
    c = RDBMSConnector(f"sqlite:///{db.as_posix()}")
    assert "sales" in c.list_objects()
    assert set(c.schema("sales")) == {"vendor", "amount", "dt"}
    rows = c.fetch("sales")
    assert len(rows) == 3
    assert rows[0]["vendor"] == "Acme"


def test_sap_cds_hana_mode_reads_a_view(tmp_path):
    """HANA mode is the SQL path; a SQLite view stands in for a CDS view in CI."""
    db = tmp_path / "shop.db"
    _make_db(str(db))
    c = SAPCDSConnector(access="hana", url=f"sqlite:///{db.as_posix()}", view_prefix="ZC_")
    objs = c.list_objects()
    assert objs == ["ZC_SpendByVendor"]          # prefix filter keeps only the CDS view
    assert set(c.schema("ZC_SpendByVendor")) == {"vendor", "amount"}
    rows = c.fetch("ZC_SpendByVendor")
    assert {r["vendor"] for r in rows} == {"Acme", "Globex"}


# ---------------- SAP CDS over OData (mock HTTP) ----------------

class _FakeResp:
    def __init__(self, payload=None, text=""):
        self._payload, self.text = payload, text
    def raise_for_status(self): pass
    def json(self): return self._payload


class _FakeSession:
    def __init__(self, entities_xml, rows):
        self._xml, self._rows = entities_xml, rows
    def get(self, url, **kw):
        if url.endswith("/$metadata"):
            return _FakeResp(text=self._xml)
        return _FakeResp(payload={"d": {"results": self._rows}})


def test_sap_cds_odata_mode():
    xml = '<EntitySet Name="SpendByVendor"/><EntitySet Name="Other"/>'
    rows = [{"__metadata": {"uri": "x"}, "vendor": "Acme", "amount": 150.0}]
    c = SAPCDSConnector(access="odata", service_url="https://sap/srv",
                        session=_FakeSession(xml, rows))
    assert c.list_objects() == ["SpendByVendor", "Other"]
    out = c.fetch("SpendByVendor")
    assert out == [{"vendor": "Acme", "amount": 150.0}]        # __metadata stripped
    assert c.schema("SpendByVendor") == {"vendor": "str", "amount": "float"}


# ---------------- Salesforce (mock client) ----------------

def test_salesforce_connector_mocked():
    account = SimpleNamespace(describe=lambda: {"fields": [
        {"name": "Id", "type": "id"}, {"name": "Name", "type": "string"}]})
    sf = SimpleNamespace(
        describe=lambda: {"sobjects": [{"name": "Account", "queryable": True}]},
        Account=account,
        query_all=lambda soql: {"records": [
            {"attributes": {"type": "Account"}, "Id": "001", "Name": "Acme"}]},
    )
    c = SalesforceConnector(client=sf)
    assert c.list_objects() == ["Account"]
    assert c.schema("Account") == {"Id": "id", "Name": "string"}
    rows = c.fetch("Account")
    assert rows == [{"Id": "001", "Name": "Acme"}]             # attributes stripped


def test_build_connector_dispatch():
    assert build_connector({"kind": "rdbms", "url": "sqlite://"}).__class__.__name__ == "RDBMSConnector"
    assert build_connector({"kind": "sap", "access": "odata", "service_url": "x"}).__class__.__name__ == "SAPCDSConnector"
    with pytest.raises(NotImplementedError):
        build_connector({"kind": "mystery"})


# ---------------- pull -> auto-catalog -> serve (end to end) ----------------

def test_pull_then_serve_end_to_end(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _make_db(str(tmp_path / "shop.db"))
    (tmp_path / "config.yaml").write_text(
        "storage:\n  kind: local\n  root: .\n"
        "llm:\n  provider: stub\n"
        "glossary:\n  vendor_name: [vendor]\n  spend_amount: [amount]\n"
        "sources:\n  shop:\n    kind: rdbms\n    url: \"sqlite:///shop.db\"\n    tables: [sales]\n",
        encoding="utf-8",
    )
    from curato.app import build
    from curato.pull import run_pull
    from curato.serve import run_serve

    env = build()
    assert run_pull("shop", env=env) == 0

    ds = env["catalog"].get_dataset("shop.sales")
    assert ds and ds["row_count"] == 3
    assert ds["mapping"] == {"vendor": "vendor_name", "amount": "spend_amount"}   # auto-cataloged
    assert ds["source_system"] == "rdbms"

    assert run_serve("total spend by vendor", auto_approve=True, dataset="shop.sales", env=env) == 0
    assert (tmp_path / "warehouse" / "curated" / "total_spend_by_vendor.csv").exists()
