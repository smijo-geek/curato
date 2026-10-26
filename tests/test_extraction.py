"""Extraction registry + source extractors."""
import pytest

from curato.ports.extraction import (
    ExtractionRegistry, PdfInvoiceExtractor, CsvExtractor, ExcelExtractor,
)

REGISTRY = ExtractionRegistry([PdfInvoiceExtractor(), CsvExtractor(), ExcelExtractor()])


def test_registry_routes_by_extension():
    assert REGISTRY.supports("a.pdf")
    assert REGISTRY.supports("b.csv")
    assert REGISTRY.supports("c.tsv")
    assert REGISTRY.supports("d.xlsx")
    assert not REGISTRY.supports("e.docx")      # not yet shipped
    assert not REGISTRY.supports("f.unknown")


def test_csv_coerces_numbers_and_tags_source():
    data = b"vendor,amount,qty\nAcme,100.50,3\nGlobex,250,1\n"
    ext = CsvExtractor().extract("sales.csv", data)
    assert len(ext.records) == 2
    r = ext.records[0]
    assert r["vendor"] == "Acme"
    assert r["amount"] == 100.5          # float, not "100.50"
    assert r["qty"] == 3                 # int, not "3"
    assert r["source_file"] == "sales.csv"


def test_tsv_delimiter():
    ext = CsvExtractor().extract("x.tsv", b"a\tb\n1\t2\n")
    assert ext.records[0] == {"a": 1, "b": 2, "source_file": "x.tsv"}


def test_excel_reads_rows():
    openpyxl = pytest.importorskip("openpyxl")
    from io import BytesIO
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["vendor", "amount"])
    ws.append(["Acme", 100.5])
    ws.append(["Globex", 250])
    buf = BytesIO()
    wb.save(buf)

    ext = ExcelExtractor().extract("sales.xlsx", buf.getvalue())
    assert len(ext.records) == 2
    assert ext.records[0]["vendor"] == "Acme"
    assert ext.records[0]["amount"] == 100.5
    assert ext.records[1]["source_file"] == "sales.xlsx"
