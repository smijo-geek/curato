# Curato

**Curated data products, from a prompt.** A metadata-driven, agentic, cloud-agnostic data platform.

A thin, runnable slice: **a PDF lands → agents read & extract it → metadata goes to a catalog → a
business prompt becomes a validated, curated data product + a BI table — with a human approval
gate.**

It touches every box in the architecture so the whole loop is provable on a laptop. It runs
**fully offline** (no cloud, no API key): the LLM is a *port* with a deterministic fallback, so you
can watch the loop work, then plug a real model (OpenAI / Bedrock / Vertex / Ollama) in behind the
same interface.

```
landing/ (PDFs)
  → Classifier → Extraction → Profiler → Mapping      [ingest agents]
  → catalog/catalog.json  +  warehouse/bronze/*.parquet [the metadata hub]
  → Intent → Resolver → Transform → Validation         [serving agents]
  → HUMAN APPROVES
  → Curator → warehouse/curated/*.parquet + BI table   [curated product]
```

## The ports (swap any one with a cloud adapter — core & agents untouched)

| Port | MVP default (open source, local) | Production adapter |
|------|----------------------------------|--------------------|
| Storage   | local filesystem (S3-style API) | S3 / ADLS / GCS / MinIO |
| Extraction| `pypdf` + rules                 | Docling / Doc Intelligence / Textract |
| Catalog   | JSON file                       | OpenMetadata / Polaris / Purview |
| Compute   | DuckDB                          | Spark / Trino |
| LLM       | deterministic stub              | LiteLLM → any model (incl. Ollama offline) |

The agents (`agents/`) depend only on these interfaces, never on a vendor SDK.

## Run it (Windows PowerShell, from the repo root)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# one command, the whole loop end-to-end (auto-approves the gate for the demo):
python demo.py
```

Or step through it:

```powershell
python scripts\make_sample_invoices.py      # drop sample invoice PDFs in landing/
python run_ingest.py                         # agents read + catalog them
python run_serve.py "monthly spend by vendor"  # prompt -> product (asks you to approve)
```

Other prompts the MVP understands out of the box:
`"total spend by vendor"`, `"number of invoices by vendor"`, `"monthly spend"`.

## Where the AI plugs in

Everything structural (schema inference, SQL generation, validation) is deterministic so the demo
runs without a model. The LLM is used through `ports/llm.py` and, in production, takes over the
*reasoning* steps — classification of messy docs, column→glossary mapping, prompt→SQL for arbitrary
requests. Set a key and the adapter switches on:

```powershell
$env:OPENAI_API_KEY = "sk-..."   # or configure any LiteLLM-supported provider
```

## What this MVP deliberately does NOT do yet
Video / COBOL ingestion, Spark-scale compute, multi-cloud conformance tests, a real semantic layer
beyond the glossary in `config.yaml`, and auto-publishing (the human gate is mandatory by design).
Those are the *widen-the-loop* phases — see the architecture page.
