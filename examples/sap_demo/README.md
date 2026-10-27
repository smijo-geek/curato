# SAP demo (CDS views)

A ready-to-run demo of Curato pulling **SAP CDS views**, auto-cataloging them, and building a
curated data product + BI report from a plain-language prompt.

It runs on a laptop: the SAP connector (`access: hana`) points at a local **SQLite stand-in for
HANA** (`sap_hana.db`) via the exact same SQL path it uses against a real HANA. In a real landscape
you change one line in `config.yaml` — the `url` — to your HANA URL. Nothing else changes.

## Run it

```bash
# from the repo root, once:
pip install -e .

cd examples/sap_demo
python build_sample.py                 # creates sap_hana.db (ZC_ CDS views over a finance table)

curato pull sap_finance                # read the CDS views + their metadata -> catalog + bronze
curato catalog                         # the catalog generated itself (note PII flagged on ZC_VendorInvoices)
curato serve "total spend by vendor" -d sap_finance.ZC_VendorInvoices      # pauses at the approval gate
curato serve "monthly spend by vendor" -d sap_finance.ZC_VendorInvoices -y # -y auto-approves
```

Open the generated report at `warehouse/curated/total_spend_by_vendor.html`.

## What it shows

- **Connect SAP CDS views** — `ZC_VendorInvoices`, `ZC_SpendByCostCenter` (prefix-filtered).
- **Auto-catalog** — schema, business-term mapping, row counts, and **automatic PII detection**
  (the `vendor_email` column flags `ZC_VendorInvoices` as containing PII).
- **Prompt → product** — a validated, governed spend product + BI report, behind a human gate.

The full presenter runbook is in [`docs/demo-sap.md`](../../docs/demo-sap.md).
