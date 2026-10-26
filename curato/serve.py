"""Turn a business prompt into a curated data product — with a mandatory human gate."""
from __future__ import annotations
import re

from curato.app import build
from curato.agents.state import new_state
from curato.agents.serving import make_serving_graph, run_curator


def slugify(prompt: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", prompt.lower()).strip("_")[:60] or "product"


def run_serve(prompt: str, auto_approve: bool = False, dataset: str = "invoices",
              env: dict | None = None) -> int:
    env = env or build()
    graph = make_serving_graph(env["catalog"], env["compute"], env["llm"], dataset=dataset)
    st = graph.invoke(new_state(prompt=prompt))

    r = st["resolved"]
    if r.get("error"):
        print(f"Cannot build product: {r['error']}")
        return 1
    if r.get("errors"):
        print("Grounding warnings:", "; ".join(r["errors"]))

    v = st["validation"]
    print("\n" + "=" * 68)
    print(f"PROMPT:   {prompt}")
    print(f"INTENT:   {st['intent']}")
    print(f"ATTEMPTS: {st['attempts']}   AGENT PATH: {' -> '.join(st['log'])}")
    print("-" * 68)
    print("GENERATED SQL:\n" + (st["sql"] or "(none)"))
    print("-" * 68)
    print(f"VALIDATION: ok={v['ok']}  rows={v.get('rows')}  issues={v['issues']}")
    if v.get("preview") is not None:
        print("\nPREVIEW:")
        print(v["preview"].to_string(index=False))
    print("=" * 68)

    if not v["ok"]:
        print("\nValidation failed — not eligible for publishing. Route to an engineer.")
        return 1

    # ---- HUMAN APPROVAL GATE (the Curator never auto-publishes) ----
    if auto_approve:
        print("\n[--yes] gate auto-approved.")
        approved = True
    else:
        try:
            approved = input("\nApprove and publish this product? [y/N] ").strip().lower() == "y"
        except EOFError:
            approved = False
    if not approved:
        print("Not approved. Nothing published.")
        return 0

    name = slugify(prompt)
    st = run_curator(st, name, env["catalog"], env["compute"], env["llm"], env["warehouse_root"])
    p = st["product"]
    print(f"\nPUBLISHED data product '{p['name']}'")
    print(f"  description: {p['description']}")
    print(f"  BI report (HTML): {p['report']}")
    print(f"  BI table (CSV):   {p['csv']}")
    print(f"  curated parquet:  {p['parquet']}")
    return 0
