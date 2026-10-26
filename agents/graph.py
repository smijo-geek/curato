"""A minimal, dependency-free state-graph runner with the same shape as LangGraph.

Nodes are `fn(state) -> state`. Edges are a node name, "END", or a callable `fn(state) -> name`
for conditional routing (used for the Validation -> Transform retry loop). To move to real
LangGraph, replace this file with langgraph.graph.StateGraph; the node signatures are identical.
"""
from __future__ import annotations
from typing import Callable, Dict, Any, Union

Node = Callable[[Dict[str, Any]], Dict[str, Any]]
Edge = Union[str, Callable[[Dict[str, Any]], str]]
END = "END"


class Graph:
    def __init__(self) -> None:
        self.nodes: Dict[str, Node] = {}
        self.edges: Dict[str, Edge] = {}
        self.entry: str | None = None

    def add_node(self, name: str, fn: Node) -> "Graph":
        self.nodes[name] = fn
        return self

    def add_edge(self, src: str, dst: Edge) -> "Graph":
        self.edges[src] = dst
        return self

    def set_entry(self, name: str) -> "Graph":
        self.entry = name
        return self

    def invoke(self, state: Dict[str, Any], max_steps: int = 50) -> Dict[str, Any]:
        cur = self.entry
        steps = 0
        while cur and cur != END:
            if steps >= max_steps:
                raise RuntimeError("graph exceeded max_steps (cycle without exit?)")
            if cur not in self.nodes:
                raise KeyError(f"no node '{cur}'")
            state = self.nodes[cur](state)
            state["log"].append(cur)
            nxt = self.edges.get(cur, END)
            cur = nxt(state) if callable(nxt) else nxt
            steps += 1
        return state
