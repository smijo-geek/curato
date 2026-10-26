"""Pull from connection-based sources (RDBMS / SAP CDS / Salesforce) and auto-generate the catalog.

For each configured source and object: introspect the schema from the system itself, fetch the
rows into Bronze, map columns onto the business glossary, flag PII, and write a catalog dataset
named `<source>.<object>`. No schema is written by hand — this is the metadata-driven catalog,
generated from the source's own metadata.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd

from curato.app import build
from curato.ports.sources import build_connector
from curato.glossary import map_terms, detect_pii


def run_pull(source_name: str | None = None, env: dict | None = None) -> int:
    env = env or build()
    catalog, compute = env["catalog"], env["compute"]
    glossary = env["glossary"]
    sources = env["cfg"].get("sources") or {}
    if not sources:
        print("No 'sources:' configured in config.yaml. Add a connection source to pull.")
        return 1

    names = [source_name] if source_name else list(sources)
    for name in names:
        if name not in sources:
            print(f"Unknown source '{name}'. Known: {list(sources)}")
            return 1
        scfg = sources[name]
        print(f"\n== source '{name}' ({scfg.get('kind')}) ==")
        connector = build_connector(scfg)
        objects = scfg.get("objects") or scfg.get("tables") or connector.list_objects()

        for obj in objects:
            src_schema = connector.schema(obj)              # auto-catalog: the source's own metadata
            rows = connector.fetch(obj)
            df = pd.DataFrame(rows)
            dataset = f"{name}.{obj}"
            bronze = str(Path(env["warehouse_root"]) / "bronze" / f"{name}__{obj}.parquet")
            if len(df):
                compute.write_table(df, bronze)

            mapping = map_terms(src_schema.keys(), glossary)
            sample = " ".join(str(v) for r in rows[:25] for v in r.values())
            pii = detect_pii(src_schema.keys(), sample)
            catalog.put_dataset(dataset, {
                "location": bronze,
                "schema": src_schema,
                "mapping": mapping,
                "glossary_terms": sorted(set(mapping.values())),
                "row_count": int(len(df)),
                "pii": pii,
                "source_system": scfg.get("kind"),
                "source_object": obj,
            })
            print(f"  {dataset:32s} {len(df):>6} rows  terms={sorted(set(mapping.values()))}")

    print('\nCataloged. Build a product with:  curato serve "<prompt>" --dataset <source>.<object>')
    return 0
