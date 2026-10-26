# Architecture

Curato has one organizing idea: **the LLM decides, the infrastructure executes.** Agents are a thin
reasoning layer on top of deterministic engines. They read schemas, samples, and metadata, then
emit *code* (SQL today) that an engine runs at scale. The data itself never flows through the model.

```
┌──────────────────── CONTROL PLANE (agents, reasoning) ───────────────────┐
│  Classifier → Extraction → Profiler → Mapping    (ingest)                 │
│  Intent → Resolver → Transform → Validation       (serving)               │
└───────────────────────────────┬──────────────────────────────────────────┘
                                 │  calls through ports (never a cloud SDK)
┌───────────────────────────────┴──────────────────────────────────────────┐
│          EXECUTION PLANE (deterministic infrastructure)                    │
│   Storage · Extraction · Catalog · Compute · LLM                           │
└────────────────────────────────────────────────────────────────────────── ┘
```

## Two halves of the pipeline

### Ingest — "a file landed, understand it"

| Agent | Responsibility | Port(s) used |
|-------|----------------|--------------|
| **Classifier** | Identify modality/doctype; flag PII and processability | Extraction, LLM |
| **Extraction** | Pull records out of the file | Extraction, Storage |
| **Profiler** | Infer schema, types, quality rules | — (operates on records) |
| **Mapping** | Map raw columns onto the business glossary (the semantic step) | — (glossary from config) |

The output is **rich metadata written to the catalog**, plus Bronze records in object storage.

### Serving — "a business asked for a product"

| Agent | Responsibility | Port(s) used |
|-------|----------------|--------------|
| **Intent** | Parse the prompt into a structured request (measure, dims, grain) | LLM |
| **Resolver** | Ground the request to **real cataloged columns** — no hallucinated fields | Catalog |
| **Transform** | Generate the transformation SQL | Compute |
| **Validation** | Run on a sample; check row counts, nulls, group keys | Compute |
| **Curator** | After a human approves, materialize the product + BI table + catalog entry | Catalog, Compute, LLM |

A retry loop runs Validation → Transform when a generated query fails, capped by `MAX_ATTEMPTS`.
The **human approval gate** sits between Validation and Curator and is mandatory by design.

## The catalog is the hub

Everything the ingest agents learn is written to the catalog, and everything the serving agents do
is grounded against it. It serves two roles at once:

1. **Governance record** — schema, lineage, PII flags, glossary terms, and every published product
   with the exact prompt and SQL that produced it.
2. **The agents' shared memory** — the serving side can only build products from assets the ingest
   side has cataloged.

## Ports & adapters

Agents and the orchestration graph depend only on the abstract port classes in
[`curato/ports/`](../curato/ports). No agent imports `boto3`, a Spark session, or any vendor SDK —
that indirection is what makes Curato cloud-agnostic. To target a new backend you implement one
adapter; nothing in `curato/agents/` changes. See [`adapters.md`](adapters.md).

## The orchestration graph

[`curato/agents/graph.py`](../curato/agents/graph.py) is a tiny, dependency-free state-graph runner
with the **same shape as LangGraph** — nodes are `fn(state) -> state`, edges are a node name or a
conditional `fn(state) -> name`. This keeps the MVP installable with no heavy dependency while
making the move to real LangGraph a drop-in: the node signatures are identical.

## Project layout

```
curato/
  cli.py            # the `curato` command (demo | samples | ingest | serve | catalog)
  app.py            # wiring: build ports from the project's config.yaml
  ingest.py         # the ingest run
  serve.py          # the serving run + human gate
  demo.py           # the end-to-end demo
  samples.py        # sample invoice generator
  ports/            # the interfaces + local open-source defaults
  agents/           # the reasoning layer (ingest + serving graphs)
config.yaml         # the example project config (glossary, storage, llm)
```
