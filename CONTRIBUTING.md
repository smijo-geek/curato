# Contributing to Curato

Thanks for your interest. Curato is young and the surface area is small, which makes it a good time
to contribute — especially **new port adapters**, which are self-contained and don't touch agent
logic.

## Ways to help

- **Write an adapter** (storage, compute, catalog, extraction, LLM) — start with
  [`docs/adapters.md`](docs/adapters.md). This is the highest-leverage contribution.
- **Add an extractor** for a new file type (Excel, CSV, a relational source).
- **Improve the agents** — better intent parsing, a real semantic-layer resolver, more validation
  checks.
- **Docs, examples, bug reports.**

## Development setup

```bash
git clone https://github.com/smijo-geek/curato.git
cd curato
python -m venv .venv && source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
pip install -e ".[llm]"
curato demo    # should run the whole loop end-to-end and publish a product
```

Python 3.10+. The demo must run **offline** (deterministic LLM stub) — don't introduce a hard
dependency on a network model or a cloud credential in the core path.

## Ground rules

- **Keep the ports clean.** Agents depend only on the abstract port interfaces — never on a cloud
  SDK. If you need a vendor library, it belongs in an adapter, imported lazily, behind an optional
  extra in `pyproject.toml`.
- **The human gate stays.** The Curator must not auto-publish. Governance is a feature, not
  friction to optimize away.
- **The LLM emits code; engines run it.** Don't push row-level data through the model.
- **Match the surrounding style.** Small, readable functions; type hints; short docstrings that say
  *why*.

## Pull requests

1. Branch off `main`.
2. Keep the PR focused — one adapter or one feature.
3. Make sure `curato demo` still runs clean.
4. Describe what you changed and how you tested it.

## Reporting bugs

Open an issue with the command you ran, what you expected, what happened (full traceback), and your
OS + Python version. A minimal `config.yaml` that reproduces it helps a lot.

## License

By contributing you agree your contributions are licensed under the project's
[Apache 2.0](LICENSE) license.
