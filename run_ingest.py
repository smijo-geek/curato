"""Ingest every file in landing/ through the ingest agents, write Bronze parquet, and record
rich metadata in the catalog. Run after dropping files in landing/.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd

from app import build
from agents.state import new_state
from agents.ingest import make_ingest_graph

DATASET = "invoices"


def main() -> int:
    env = build()
    storage, catalog, compute = env["storage"], env["catalog"], env["compute"]
    graph = make_ingest_graph(env["extractor"], env["llm"], env["glossary"])

    files = [f for f in storage.list("landing") if f.lower().endswith(".pdf")]
    if not files:
        print("Nothing in landing/. Run: python scripts\\make_sample_invoices.py")
        return 1

    all_records, schema, mapping, pii = [], {}, {}, False
    for f in files:
        st = new_state(file=f, _bytes=storage.read_bytes(f))
        st = graph.invoke(st)
        all_records.extend(st["records"])
        schema.update(st["schema"] or {})
        mapping.update(st["mapping"] or {})
        pii = pii or st.get("_pii", False)
        print(f"  {f:28s} -> {len(st['records'])} record(s)   path: {'->'.join(st['log'])}")

    if not all_records:
        print("No records extracted.")
        return 1

    df = pd.DataFrame(all_records)
    bronze = str(Path(env["warehouse_root"]) / "bronze" / f"{DATASET}.parquet")
    compute.write_table(df, bronze)

    catalog.put_dataset(DATASET, {
        "location": bronze,
        "schema": schema,
        "mapping": mapping,                      # source column -> business glossary term
        "glossary_terms": sorted(set(mapping.values())),
        "row_count": len(df),
        "pii": pii,
        "source_files": files,
    })

    print(f"\nBronze written: {bronze}  ({len(df)} rows)")
    print(f"Catalog updated. Grounded terms: {sorted(set(mapping.values()))}")
    print("Now run:  python run_serve.py \"monthly spend by vendor\"")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
