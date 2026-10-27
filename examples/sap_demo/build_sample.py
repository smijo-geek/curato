"""Build a local SQLite database that stands in for SAP HANA for the demo.

It creates CDS-style views (ZC_ prefix) over a base finance table, with SAP-flavoured columns —
so Curato's SAP connector (access: hana) runs end-to-end on a laptop via the exact same SQL path
it would use against a real HANA. In a real landscape you swap the SQLite URL for a HANA URL;
nothing else changes.
"""
from __future__ import annotations
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent / "sap_hana.db"

VENDORS = [
    ("Siemens AG",         "ap@siemens.example",     "CC-1000"),
    ("Bosch GmbH",         "billing@bosch.example",  "CC-1000"),
    ("SAP SE",             "invoices@sap.example",   "CC-2000"),
    ("Deutsche Telekom",   "ar@telekom.example",     "CC-2000"),
    ("Accenture",          "finance@accenture.example", "CC-3000"),
]

# (vendor_index, posting_date, amount_eur)
ROWS = [
    (0, "2026-01-08", 48250.00), (1, "2026-01-15", 12900.50), (2, "2026-01-22", 98000.00),
    (3, "2026-01-29", 7430.25),  (4, "2026-02-03", 155000.00),(0, "2026-02-11", 23110.00),
    (2, "2026-02-18", 98000.00), (1, "2026-02-25", 18740.75), (3, "2026-03-04", 8120.00),
    (4, "2026-03-09", 142300.00),(0, "2026-03-16", 51990.00), (2, "2026-03-23", 76500.00),
    (1, "2026-03-30", 9980.00),  (4, "2026-04-07", 160450.00),(3, "2026-04-14", 6650.50),
    (0, "2026-04-21", 33200.00), (2, "2026-04-28", 54000.00), (1, "2026-05-05", 14220.00),
]


def main() -> None:
    if DB.exists():
        DB.unlink()
    con = sqlite3.connect(DB)
    c = con.cursor()
    c.execute("""
        CREATE TABLE ZFI_DOCS (
            doc_no        TEXT,
            vendor        TEXT,
            vendor_email  TEXT,
            amount        REAL,
            currency      TEXT,
            posting_date  TEXT,
            cost_center   TEXT,
            fiscal_year   INTEGER
        )""")
    for i, (vi, date, amt) in enumerate(ROWS, start=1):
        vendor, email, cc = VENDORS[vi]
        c.execute("INSERT INTO ZFI_DOCS VALUES (?,?,?,?,?,?,?,?)",
                  (f"510000{i:03d}", vendor, email, amt, "EUR", date, cc, 2026))
    # CDS-style consumption views (what Curato pulls)
    c.execute("""
        CREATE VIEW ZC_VendorInvoices AS
        SELECT doc_no, vendor, vendor_email, amount, currency, posting_date, cost_center, fiscal_year
        FROM ZFI_DOCS""")
    c.execute("""
        CREATE VIEW ZC_SpendByCostCenter AS
        SELECT cost_center, vendor, amount, posting_date FROM ZFI_DOCS""")
    con.commit()
    con.close()
    print(f"Built {DB.name} with {len(ROWS)} documents and 2 CDS views (ZC_VendorInvoices, ZC_SpendByCostCenter).")


if __name__ == "__main__":
    main()
