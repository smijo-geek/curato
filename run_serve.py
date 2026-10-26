"""Turn a business prompt into a curated data product — with a mandatory human gate.

Usage:
    python run_serve.py "monthly spend by vendor"
    python run_serve.py "total spend by vendor" --auto-approve
"""
from __future__ import annotations
import sys
import re

from app import build
from agents.state import new_state
from agents.serving import make_serving_graph, run_curator


def slugify(prompt: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", prompt.lower()).strip("_")[:60] or "product"


def main(argv: list[str]) -> int:
    args = [a for a in argv if a != "--auto-approve"]
    auto = "--auto-approve" in argv
    if not args:
        print('Give a prompt, e.g.  python run_serve.py "monthly spend by vendor"')
        return 1
    prompt = args[0]

    env = build()
    graph = make_serving_graph(env["catalog"], env["compute"], env["llm"])
    st = graph.invoke(new_state(prompt=prompt))

    r = st["resolved"]
    if r.get("error"):
        print(f"Cannot build product: {r['error']}")
        return 1
    if r.get("errors"):
        print("Grounding warnings:", "; ".join(r["errors"]))

    v = st["validation"]
    print("\n" + "=" * 68)
    print(f"PROMPT:  {prompt}")
    print(f"INTENT:  {st['intent']}")
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
    if auto:
        approved = True
        print("\n[--auto-approve] gate bypassed for demo.")
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
    print(f"  BI table (CSV): {p['csv']}")
    print(f"  curated parquet: {p['parquet']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
