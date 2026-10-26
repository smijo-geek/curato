"""One command, the whole loop: make samples -> ingest -> prompt -> product (auto-approved)."""
from __future__ import annotations
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
PY = sys.executable


def step(title: str, args: list[str]) -> None:
    print("\n" + "#" * 72 + f"\n# {title}\n" + "#" * 72)
    rc = subprocess.call([PY, *args], cwd=str(ROOT))
    if rc != 0:
        raise SystemExit(f"step failed: {title}")


def main() -> int:
    step("1/3  Generate sample invoice PDFs", ["scripts/make_sample_invoices.py"])
    step("2/3  Ingest: agents read the PDFs and catalog the metadata", ["run_ingest.py"])
    step("3/3  Serve: prompt -> validated, curated product + BI table",
         ["run_serve.py", "monthly spend by vendor", "--auto-approve"])
    print("\nDone. Inspect catalog/catalog.json and warehouse/curated/ for the outputs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
