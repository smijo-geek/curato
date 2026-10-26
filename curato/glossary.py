"""Shared semantic helpers: map source column names onto canonical business-glossary terms.

Used by both the file-ingest Mapping agent and the connection-based pull, so a column means the
same thing no matter which source it came from.
"""
from __future__ import annotations
from typing import Dict, List, Iterable
import re

_PII = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+|\b\d{3}-\d{2}-\d{4}\b")  # email or SSN-like
_PII_NAMES = ("email", "ssn", "phone", "mobile", "passport", "aadhaar", "dob", "card")


def map_terms(columns: Iterable[str], glossary: Dict[str, List[str]]) -> Dict[str, str]:
    syn = {s.lower(): term for term, syns in glossary.items() for s in list(syns) + [term]}
    out: Dict[str, str] = {}
    for c in columns:
        key = c.lower().replace("_", " ")
        if key in syn:
            out[c] = syn[key]
    return out


def detect_pii(columns: Iterable[str], sample_text: str = "") -> bool:
    if any(any(p in c.lower() for p in _PII_NAMES) for c in columns):
        return True
    return bool(_PII.search(sample_text))
