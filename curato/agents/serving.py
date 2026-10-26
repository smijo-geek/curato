"""Serving-side agents: Intent -> Resolver -> Transform -> Validation (with a retry loop).
Input: a business prompt. Output: validated SQL + a preview, ready for the human gate.
The Curator runs only AFTER a human approves (see run_serve.py).
"""
from __future__ import annotations
from typing import Dict, Any
from pathlib import Path

from curato.ports.catalog import CatalogPort
from curato.ports.compute import ComputePort
from curato.ports.llm import LLMPort
from curato.agents.graph import Graph, END

MAX_ATTEMPTS = 2


def parse_intent(prompt: str) -> Dict[str, Any]:
    """Turn a prompt into a structured request. Keyword-based in the MVP; the LLM does this for
    arbitrary language in production."""
    p = prompt.lower()
    measure = "count" if ("count" in p or "number of" in p) else "spend"
    dims = []
    if any(w in p for w in ("vendor", "supplier", "payee")):
        dims.append("vendor_name")
    if any(w in p for w in ("month", "monthly")):
        dims.append("_month")  # a derived time grain on invoice_date
    return {"measure": measure, "dims": dims}


def make_serving_graph(catalog: CatalogPort, compute: ComputePort, llm: LLMPort,
                       dataset: str = "invoices") -> Graph:

    def intent(state: Dict[str, Any]) -> Dict[str, Any]:
        state["intent"] = parse_intent(state["prompt"])
        return state

    def resolver(state: Dict[str, Any]) -> Dict[str, Any]:
        ds = catalog.get_dataset(dataset)
        if not ds:
            state["resolved"] = {"error": f"dataset '{dataset}' not in catalog — ingest first."}
            return state
        # canonical term -> source column, from the mapping the ingest agents wrote.
        term2col = {term: col for col, term in ds["mapping"].items()}
        intent = state["intent"]
        resolved: Dict[str, Any] = {"location": ds["location"], "group_cols": [], "errors": []}

        # measure
        if intent["measure"] == "count":
            resolved["measure_sql"] = "COUNT(*)"
            resolved["measure_name"] = "invoice_count"
        else:
            col = term2col.get("spend_amount")
            if not col:
                resolved["errors"].append("no 'spend_amount' in catalog to sum")
            resolved["measure_sql"] = f"SUM({col})"
            resolved["measure_name"] = "total_spend"

        # dimensions — only those grounded in the catalog survive
        for dim in intent["dims"]:
            if dim == "_month":
                dcol = term2col.get("invoice_date")
                if dcol:
                    resolved["group_cols"].append(
                        (f"date_trunc('month', CAST({dcol} AS DATE))", "month"))
                else:
                    resolved["errors"].append("no 'invoice_date' to build a monthly grain")
            else:
                col = term2col.get(dim)
                if col:
                    resolved["group_cols"].append((col, col))
                else:
                    resolved["errors"].append(f"term '{dim}' not found in catalog")
        state["resolved"] = resolved
        return state

    def transform(state: Dict[str, Any]) -> Dict[str, Any]:
        state["attempts"] += 1
        r = state["resolved"]
        if r.get("error"):
            state["sql"] = None
            return state
        groups = list(r["group_cols"])
        # retry strategy: if a previous attempt failed, drop the time grain and keep it simple.
        if state["attempts"] > 1:
            groups = [g for g in groups if g[1] != "month"]
        loc = Path(r["location"]).as_posix()
        select = [f"{expr} AS {alias}" for expr, alias in groups]
        select.append(f"{r['measure_sql']} AS {r['measure_name']}")
        sql = f"SELECT {', '.join(select)}\nFROM read_parquet('{loc}')"
        if groups:
            keys = ", ".join(str(i + 1) for i in range(len(groups)))
            sql += f"\nGROUP BY {keys}\nORDER BY {len(groups) + 1} DESC"
        state["sql"] = sql
        state["_groups"] = groups
        return state

    def validation(state: Dict[str, Any]) -> Dict[str, Any]:
        if not state["sql"]:
            state["validation"] = {"ok": False, "issues": ["no SQL generated"], "preview": None}
            return state
        issues = []
        try:
            df = compute.query(state["sql"])
        except Exception as e:  # SQL didn't even run
            state["validation"] = {"ok": False, "issues": [f"query error: {e}"], "preview": None}
            return state
        if len(df) == 0:
            issues.append("result is empty")
        for expr, alias in state.get("_groups", []):
            if alias in df.columns and df[alias].isnull().any():
                issues.append(f"group key '{alias}' has nulls")
        state["validation"] = {
            "ok": len(issues) == 0,
            "issues": issues,
            "rows": int(len(df)),
            "preview": df.head(20),
        }
        return state

    def after_validation(state: Dict[str, Any]) -> str:
        v = state["validation"]
        if v["ok"] or state["attempts"] >= MAX_ATTEMPTS:
            return END
        return "transform"  # loop back and try a simpler transform

    g = Graph()
    g.add_node("intent", intent).add_node("resolver", resolver)
    g.add_node("transform", transform).add_node("validation", validation)
    g.set_entry("intent")
    g.add_edge("intent", "resolver").add_edge("resolver", "transform")
    g.add_edge("transform", "validation").add_edge("validation", after_validation)
    return g


def run_curator(state: Dict[str, Any], product_name: str, catalog: CatalogPort,
                compute: ComputePort, llm: LLMPort, warehouse_root: str) -> Dict[str, Any]:
    """Materialize the approved product: curated parquet + a CSV BI table + a catalog entry."""
    df = compute.query(state["sql"])
    out_parquet = str(Path(warehouse_root) / "curated" / f"{product_name}.parquet")
    out_csv = str(Path(warehouse_root) / "curated" / f"{product_name}.csv")
    compute.write_table(df, out_parquet)
    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)

    cols = list(df.columns)
    description = llm.explain_product(product_name, state["sql"], cols)
    catalog.put_product(product_name, {
        "prompt": state["prompt"],
        "sql": state["sql"],
        "columns": cols,
        "rows": int(len(df)),
        "location": out_parquet,
        "bi_table": out_csv,
        "description": description,
        "approved": True,
    })
    state["product"] = {"name": product_name, "table": df, "csv": out_csv,
                        "parquet": out_parquet, "description": description}
    return state
