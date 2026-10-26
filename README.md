# Curato

**Curated data products, from a prompt.**
A metadata-driven, agentic, cloud-agnostic data platform.

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Status: MVP](https://img.shields.io/badge/status-MVP-orange.svg)](#roadmap)

Drop a file in a landing zone. AI agents read it, extract everything, and write rich **metadata to
a catalog**. Then a business user asks for a data product in plain language — and agents ground the
request against that catalog, generate the transformation, validate it, and (after a human
approves) publish a curated data product and a BI table.

Think of it as **dbt, but the model is written from a prompt and the inputs can be unstructured** —
and nothing ships without passing a validation gate and a human sign-off.

```
landing/ (PDFs)
  → Classifier → Extraction → Profiler → Mapping          [ingest agents]
  → catalog/catalog.json  +  warehouse/bronze/*.parquet    [the metadata hub]
  → Intent → Resolver → Transform → Validation             [serving agents]
  → HUMAN APPROVES
  → Curator → warehouse/curated/*.parquet + BI table       [curated product]
```

---

## Quickstart (your first win in 3 commands)

Runs **fully offline** — no cloud, no API key. The LLM is a *port* with a deterministic fallback,
so you can watch the whole loop work, then plug a real model in behind the same interface.

```bash
pip install -e .     # installs the `curato` command (Python 3.10+)
curato demo          # samples → ingest → prompt → validated, curated product
curato catalog       # see what the agents learned and published
```

`curato demo` generates seven sample invoice PDFs, lets the agents read and catalog them, then turns
the prompt *“monthly spend by vendor”* into a validated data product in `warehouse/curated/` — a
parquet table, a CSV, and a **self-contained HTML BI report** you can open in any browser.

Step through it yourself — from any directory with a `config.yaml` (this repo is the example
project, exactly like a dbt project dir):

```bash
curato samples                           # drop sample invoice PDFs in landing/
curato ingest                            # agents read landing/ → catalog + bronze
curato serve "monthly spend by vendor"   # prompt → product (asks you to approve; -y to skip)
curato catalog                           # list datasets and published products
```

Prompts it understands out of the box: `"total spend by vendor"`,
`"number of invoices by vendor"`, `"monthly spend"`.

> On Windows, if the `curato` command isn't found after install, either add your Python `Scripts`
> directory to `PATH` or run it as `python -m curato.cli ...`.

---

## How it works

**The LLM decides; the infrastructure executes.** Agents are a thin reasoning layer — they read
schemas and samples and emit *code* (SQL), which deterministic engines run at scale. That split
keeps it cheap, fast, and auditable.

- **Ingest agents** — `Classifier` (what is this? PII?), `Extraction` (pull the fields),
  `Profiler` (schema + quality), `Mapping` (columns → your business glossary).
- **The catalog** — every finding is written here: schema, lineage, PII flags, glossary terms. It
  is both the governance record and the agents' shared memory. This is the *metadata-driven* core.
- **Serving agents** — `Intent` (parse the request), `Resolver` (ground it to real cataloged
  columns — so it can't invent data), `Transform` (generate the SQL), `Validation` (run on a
  sample, check rows/nulls/totals).
- **The human gate** — agents draft and prove; a person signs off. The `Curator` never
  auto-publishes. This is what makes the speed trustworthy.

See [`docs/architecture.md`](docs/architecture.md) for the full picture.

## Cloud-agnostic by construction

The core and agents depend only on **ports** (interfaces). Each port has a local open-source
default; a production deployment adds one adapter per cloud — the agents never change.

| Port | Default (local, open source) | Production adapters |
|------|------------------------------|---------------------|
| Storage    | local filesystem (S3-style API) | S3 · ADLS · GCS · MinIO · HDFS |
| Extraction | PDF (rules) + CSV/TSV, via a registry | Docling · Azure Doc Intelligence · Textract · Unstructured |
| Catalog    | JSON file                       | OpenMetadata · Polaris · Purview |
| Compute    | DuckDB                          | Spark · Trino |
| LLM        | deterministic stub              | LiteLLM → any model (incl. Ollama, offline) |

Want to add one? See **[`docs/adapters.md`](docs/adapters.md)** — writing an adapter is the easiest
way to contribute.

### Any source, one extractor each

A source can be anything. Each type is a single `ExtractionPort`; the registry routes each file to
the one that handles it, so adding a source never touches the agents.

| Source | Status | Approach |
|--------|--------|----------|
| PDF                     | ✅ shipped  | `pypdf` + rules (invoices); LLM/vision for arbitrary layouts |
| CSV · TSV · delimited   | ✅ shipped  | stdlib, with numeric type coercion |
| Excel                   | ⏳ planned | `openpyxl` adapter |
| Word · XML · text       | ⏳ planned | per-format extractor |
| Images · video          | ⏳ planned | vision / Whisper transcript + frames (specialist) |
| COBOL copybooks         | ⏳ planned | copybook parse + EBCDIC decode (specialist) |
| SAP · Salesforce · RDBMS| ⏳ planned | connector extractors (API / JDBC) |

### Plugging in a real model

```bash
export OPENAI_API_KEY=sk-...     # or any LiteLLM-supported provider
pip install -e ".[llm]"
```

With a key set, the LLM port takes over the reasoning steps (classifying messy docs,
column→glossary mapping, prompt→SQL for arbitrary requests). Without one, the deterministic stub
keeps the demo fully runnable.

## Roadmap

- [x] Runnable PDF → catalog → prompt → curated product loop
- [x] Ports & adapters; installable `curato` CLI
- [x] Self-contained HTML BI report from the Curator (regenerated on every publish)
- [x] Extractor registry + CSV/TSV source (multi-source seam)
- [ ] More extractors: Excel, Word, XML, then SAP / Salesforce / RDBMS connectors
- [ ] Real LangGraph + LLM-driven Transform for arbitrary prompts
- [ ] Cloud adapters: S3, Spark, OpenMetadata — with a conformance test suite (CI on ≥2 backends)
- [ ] A proper semantic-layer / glossary service
- [ ] Video / COBOL ingestion (specialist)

## Contributing

Contributions welcome — especially new port adapters. See
[`CONTRIBUTING.md`](CONTRIBUTING.md) and [`docs/adapters.md`](docs/adapters.md).

## License

[Apache License 2.0](LICENSE) — the same license as dbt Core. Use it, fork it, build on it.
