"""The shared state object passed between agent nodes — the agents' working memory for one run.
A plain dict keeps the MVP dependency-free; it matches the TypedDict shape LangGraph expects, so
swapping agents/graph.py for a real langgraph.graph.StateGraph needs no change to the nodes.
"""
from __future__ import annotations
from typing import Any, Dict


def new_state(**kw: Any) -> Dict[str, Any]:
    s: Dict[str, Any] = {
        # ingest
        "file": None, "classification": None, "records": None,
        "schema": None, "quality": None, "mapping": None,
        # serving
        "prompt": None, "intent": None, "resolved": None,
        "sql": None, "validation": None, "attempts": 0,
        "product": None,
        # shared
        "log": [],
    }
    s.update(kw)
    return s
