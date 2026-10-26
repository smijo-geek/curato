"""Extraction port — turns an unstructured file into (records, raw_text).

MVP default: pypdf text + rules tuned for invoices. Production adapters (Docling, Azure Doc
Intelligence, Textract) implement the same interface and handle arbitrary layouts / OCR.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any
import re


@dataclass
class Extraction:
    records: List[Dict[str, Any]] = field(default_factory=list)
    raw_text: str = ""


class ExtractionPort(ABC):
    @abstractmethod
    def supports(self, filename: str) -> bool: ...
    @abstractmethod
    def extract(self, filename: str, data: bytes) -> Extraction: ...


class PdfInvoiceExtractor(ExtractionPort):
    """Rules-based invoice reader. In production the LLM/vision model does this step, but the
    rules make the demo deterministic and offline."""

    FIELDS = {
        "invoice_number": re.compile(r"Invoice Number:\s*(\S+)", re.I),
        "invoice_date":   re.compile(r"Date:\s*(\d{4}-\d{2}-\d{2})", re.I),
        "vendor":         re.compile(r"Vendor:\s*(.+)", re.I),
        "_amount":        re.compile(r"Amount Due:\s*([\d,]+\.\d{2})\s*([A-Z]{3})", re.I),
    }

    def supports(self, filename: str) -> bool:
        return filename.lower().endswith(".pdf")

    def _read_text(self, data: bytes) -> str:
        from io import BytesIO
        from pypdf import PdfReader
        reader = PdfReader(BytesIO(data))
        return "\n".join((page.extract_text() or "") for page in reader.pages)

    def extract(self, filename: str, data: bytes) -> Extraction:
        text = self._read_text(data)
        rec: Dict[str, Any] = {}
        for key, rx in self.FIELDS.items():
            m = rx.search(text)
            if not m:
                continue
            if key == "_amount":
                rec["amount"] = float(m.group(1).replace(",", ""))
                rec["currency"] = m.group(2).upper()
            else:
                rec[key] = m.group(1).strip()
        rec["source_file"] = filename
        return Extraction(records=[rec] if rec.get("invoice_number") else [], raw_text=text)
