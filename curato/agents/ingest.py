"""Ingest-side agents: Classifier -> Extraction -> Profiler -> Mapping.
Input: a file that landed. Output: records + rich metadata ready for the catalog.
"""
from __future__ import annotations
from typing import Dict, Any, List
import re

from curato.ports.extraction import ExtractionPort
from curato.ports.llm import LLMPort
from curato.agents.graph import Graph, END
from curato.glossary import map_terms

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def make_ingest_graph(extractor: ExtractionPort, llm: LLMPort, glossary: Dict[str, List[str]]) -> Graph:

    def classifier(state: Dict[str, Any]) -> Dict[str, Any]:
        name = state["file"]
        modality = "pdf" if name.lower().endswith(".pdf") else "unknown"
        # A real deployment asks the LLM "what is this?"; the MVP keys off extension + extractor.
        state["classification"] = {
            "modality": modality,
            "doctype": "invoice" if modality == "pdf" else "unknown",
            "processable": extractor.supports(name),
        }
        return state

    def extraction(state: Dict[str, Any]) -> Dict[str, Any]:
        if not state["classification"]["processable"]:
            state["records"] = []
            return state
        ext = extractor.extract(state["file"], state["_bytes"])
        state["records"] = ext.records
        # PII flag from the raw text (trivial; a real agent uses a proper detector).
        state["_pii"] = bool(_EMAIL.search(ext.raw_text))
        return state

    def profiler(state: Dict[str, Any]) -> Dict[str, Any]:
        recs = state["records"] or []
        schema: Dict[str, str] = {}
        nulls: Dict[str, int] = {}
        for r in recs:
            for k, v in r.items():
                schema.setdefault(k, type(v).__name__)
                if v in (None, ""):
                    nulls[k] = nulls.get(k, 0) + 1
        state["schema"] = schema
        state["quality"] = {"row_count": len(recs), "null_counts": nulls}
        return state

    def mapping(state: Dict[str, Any]) -> Dict[str, Any]:
        # Ground each source field onto a canonical glossary term. This is the semantic step the
        # LLM owns in production; here it is a synonym lookup (shared with the pull path) so the
        # demo is deterministic.
        state["mapping"] = map_terms((state["schema"] or {}).keys(), glossary)
        return state

    g = Graph()
    g.add_node("classifier", classifier).add_node("extraction", extraction)
    g.add_node("profiler", profiler).add_node("mapping", mapping)
    g.set_entry("classifier")
    g.add_edge("classifier", "extraction").add_edge("extraction", "profiler")
    g.add_edge("profiler", "mapping").add_edge("mapping", END)
    return g
