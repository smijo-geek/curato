"""The `curato` command. Mirrors dbt's shape: a project in the current directory, subcommands
that build and publish.

    curato demo                         # whole loop end-to-end (auto-approves)
    curato samples                      # drop sample invoice PDFs in landing/
    curato ingest                       # agents read landing/ -> catalog + bronze
    curato serve "monthly spend ..."    # prompt -> validated product (asks to approve)
    curato catalog                      # print what's in the catalog
"""
from __future__ import annotations
import argparse
import json
import sys

from curato import __version__


def _cmd_demo(args) -> int:
    from curato.demo import run_demo
    return run_demo()


def _cmd_samples(args) -> int:
    from curato import samples
    try:
        n = samples.generate()
    except ImportError:
        print("reportlab not installed — run: pip install reportlab")
        return 1
    print(f"Wrote {n} invoice PDFs to ./landing")
    return 0


def _cmd_ingest(args) -> int:
    from curato.ingest import run_ingest
    return run_ingest()


def _cmd_pull(args) -> int:
    from curato.pull import run_pull
    return run_pull(args.source)


def _cmd_serve(args) -> int:
    from curato.serve import run_serve
    return run_serve(args.prompt, auto_approve=args.yes, dataset=args.dataset)


def _cmd_catalog(args) -> int:
    from curato.app import build
    snap = build()["catalog"].snapshot()
    datasets = snap.get("datasets", {})
    products = snap.get("data_products", {})
    if not datasets and not products:
        print("Catalog is empty. Run:  curato ingest")
        return 0
    print(f"DATASETS ({len(datasets)}):")
    for name, d in datasets.items():
        print(f"  {name}: {d['row_count']} rows | PII={d['pii']} | terms={d['glossary_terms']}")
    print(f"\nDATA PRODUCTS ({len(products)}):")
    for name, p in products.items():
        print(f"  {name}: {p['rows']} rows | from \"{p['prompt']}\" | {p['bi_table']}")
    if args.json:
        print("\n" + json.dumps(snap, indent=2, default=str))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="curato", description="Curated data products, from a prompt.")
    parser.add_argument("--version", action="version", version=f"curato {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("demo", help="run the whole loop end-to-end").set_defaults(func=_cmd_demo)
    sub.add_parser("samples", help="generate sample invoice PDFs").set_defaults(func=_cmd_samples)
    sub.add_parser("ingest", help="read landing/ and catalog the metadata").set_defaults(func=_cmd_ingest)

    pl = sub.add_parser("pull", help="pull from connection sources (RDBMS/SAP/Salesforce) and auto-catalog")
    pl.add_argument("source", nargs="?", help="a source name from config.yaml; omit to pull all")
    pl.set_defaults(func=_cmd_pull)

    s = sub.add_parser("serve", help="turn a prompt into a curated data product")
    s.add_argument("prompt", help='e.g. "monthly spend by vendor"')
    s.add_argument("-y", "--yes", action="store_true", help="auto-approve the human gate")
    s.add_argument("-d", "--dataset", default="invoices",
                   help="catalog dataset to build from (e.g. mydb.sales); default: invoices")
    s.set_defaults(func=_cmd_serve)

    c = sub.add_parser("catalog", help="print the catalog contents")
    c.add_argument("--json", action="store_true", help="also dump the full catalog JSON")
    c.set_defaults(func=_cmd_catalog)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
