"""One command, the whole loop: samples -> ingest -> prompt -> product (auto-approved)."""
from __future__ import annotations

from curato.app import build
from curato.ingest import run_ingest
from curato.serve import run_serve
from curato import samples


def run_demo() -> int:
    env = build()
    print("#" * 72 + "\n# 1/3  Generate sample invoice PDFs\n" + "#" * 72)
    try:
        n = samples.generate()
        print(f"Wrote {n} invoice PDFs to {env['project']}\\landing")
    except ImportError:
        print("reportlab not installed — run: pip install reportlab")
        return 1

    print("\n" + "#" * 72 + "\n# 2/3  Ingest: agents read the PDFs and catalog the metadata\n" + "#" * 72)
    if run_ingest(env):
        return 1

    print("\n" + "#" * 72 + "\n# 3/3  Serve: prompt -> validated, curated product + BI table\n" + "#" * 72)
    run_serve("monthly spend by vendor", auto_approve=True, env=env)

    print("\nDone. Inspect catalog/catalog.json and warehouse/curated/ for the outputs.")
    return 0
