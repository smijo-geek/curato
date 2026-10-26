"""Generate sample invoice PDFs into the project's landing/ folder, so the demo has input."""
from __future__ import annotations
from pathlib import Path

INVOICES = [
    ("INV-1001", "2026-01-12", "Acme Industrial Supplies", "12,480.00", "USD"),
    ("INV-1002", "2026-01-28", "Northwind Logistics",      "3,250.50",  "USD"),
    ("INV-1003", "2026-02-09", "Acme Industrial Supplies", "8,990.00",  "USD"),
    ("INV-1004", "2026-02-17", "Globex Cloud Services",    "15,200.00", "USD"),
    ("INV-1005", "2026-03-03", "Northwind Logistics",      "4,100.75",  "USD"),
    ("INV-1006", "2026-03-22", "Globex Cloud Services",    "15,200.00", "USD"),
    ("INV-1007", "2026-03-30", "Acme Industrial Supplies", "2,340.00",  "USD"),
]


def generate(landing: Path | None = None) -> int:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4

    landing = landing or (Path.cwd() / "landing")
    landing.mkdir(parents=True, exist_ok=True)
    for num, date, vendor, amount, cur in INVOICES:
        c = canvas.Canvas(str(landing / f"{num}.pdf"), pagesize=A4)
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
    return len(INVOICES)
