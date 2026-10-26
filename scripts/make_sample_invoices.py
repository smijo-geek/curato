"""Generate a handful of sample invoice PDFs into landing/ so the demo has something to ingest."""
from __future__ import annotations
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
LANDING = ROOT / "landing"

INVOICES = [
    ("INV-1001", "2026-01-12", "Acme Industrial Supplies", "12,480.00", "USD"),
    ("INV-1002", "2026-01-28", "Northwind Logistics",      "3,250.50",  "USD"),
    ("INV-1003", "2026-02-09", "Acme Industrial Supplies", "8,990.00",  "USD"),
    ("INV-1004", "2026-02-17", "Globex Cloud Services",    "15,200.00", "USD"),
    ("INV-1005", "2026-03-03", "Northwind Logistics",      "4,100.75",  "USD"),
    ("INV-1006", "2026-03-22", "Globex Cloud Services",    "15,200.00", "USD"),
    ("INV-1007", "2026-03-30", "Acme Industrial Supplies", "2,340.00",  "USD"),
]


def main() -> int:
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
    except ImportError:
        print("reportlab not installed. Run: pip install -r requirements.txt")
        return 1

    LANDING.mkdir(parents=True, exist_ok=True)
    for num, date, vendor, amount, cur in INVOICES:
        path = LANDING / f"{num}.pdf"
        c = canvas.Canvas(str(path), pagesize=A4)
        y = 780
        for line in [
            "INVOICE",
            f"Invoice Number: {num}",
            f"Date: {date}",
            f"Vendor: {vendor}",
            "Description: Professional services",
            f"Amount Due: {amount} {cur}",
            "Remit to: accounts@example-vendor.com",
        ]:
            c.drawString(60, y, line)
            y -= 26
        c.save()
    print(f"Wrote {len(INVOICES)} invoice PDFs to {LANDING}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
