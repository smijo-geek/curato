# Writing an adapter

An **adapter** is a concrete implementation of a port. Ports are the abstract interfaces the agents
depend on; adapters bind them to a real backend (a cloud, an engine, a catalog service). Writing one
is the easiest and most valuable way to contribute — the agents never change, so a good adapter is
self-contained and independently testable.

All ports live in [`curato/ports/`](../curato/ports). Each file defines an abstract base class and
one or more local, open-source implementations.

## The five ports

| Port | File | Interface (methods you implement) |
|------|------|-----------------------------------|
| Storage    | `ports/storage.py`    | `list`, `read_bytes`, `put_bytes`, `local_path` |
| Extraction | `ports/extraction.py` | `supports`, `extract` |
| Catalog    | `ports/catalog.py`    | `put_dataset`, `get_dataset`, `put_product`, `snapshot` |
| Compute    | `ports/compute.py`    | `query`, `write_table` |
| LLM        | `ports/llm.py`        | `complete` (+ optional `explain_product`) |

## Recipe: add an S3 storage adapter

1. **Implement the port.** Subclass `StoragePort` and fill in the four methods.

   ```python
   # curato/ports/storage.py
   class S3Storage(StoragePort):
       def __init__(self, bucket: str, prefix: str = ""):
           import boto3
           self.s3 = boto3.client("s3")
           self.bucket, self.prefix = bucket, prefix

       def list(self, prefix):
           out, token = [], None
           key = f"{self.prefix}{prefix}"
           while True:
               kw = {"Bucket": self.bucket, "Prefix": key}
               if token:
                   kw["ContinuationToken"] = token
               resp = self.s3.list_objects_v2(**kw)
               out += [o["Key"] for o in resp.get("Contents", [])]
               if not resp.get("IsTruncated"):
                   return out
               token = resp["NextContinuationToken"]

       def read_bytes(self, key):
           return self.s3.get_object(Bucket=self.bucket, Key=key)["Body"].read()

       def put_bytes(self, key, data):
           self.s3.put_object(Bucket=self.bucket, Key=key, Body=data)

       def local_path(self, key):
           # engines read S3 directly; return an s3:// URI (DuckDB/Spark understand it)
           return f"s3://{self.bucket}/{key}"
   ```

2. **Register it** in the factory so `config.yaml` can select it:

   ```python
   def get_storage(cfg: dict) -> StoragePort:
       kind = cfg.get("kind", "local")
       if kind == "local":
           return LocalStorage(cfg.get("root", "."))
       if kind == "s3":
           return S3Storage(cfg["bucket"], cfg.get("prefix", ""))
       raise NotImplementedError(f"Storage adapter '{kind}' not found.")
   ```

3. **Select it** in a project's `config.yaml`:

   ```yaml
   storage:
     kind: s3
     bucket: my-landing-bucket
     prefix: curato/
   ```

4. **Add its dependency** as an optional extra in `pyproject.toml`:

   ```toml
   [project.optional-dependencies]
   s3 = ["boto3>=1.34"]
   ```

That's the whole pattern. A Spark `ComputePort`, an OpenMetadata `CatalogPort`, or a Textract
`ExtractionPort` follow the same three steps: implement the interface, register it in the factory,
select it in config.

## Rules for a good adapter

- **Depend only on the port's methods.** Don't reach into another port or into agent code.
- **Keep the heavy SDK import inside `__init__` or the method**, not at module top level, so the
  package still imports when that SDK isn't installed. Gate the dependency behind an extra.
- **Preserve semantics.** `Storage.list(prefix)` returns keys relative to the storage root, the
  same shape the local adapter returns, so the agents behave identically.
- **Make it swappable with no agent change.** If an agent needs to know which adapter it got, the
  abstraction has leaked — fix the interface instead.

## Testing an adapter

There is a **conformance suite** in [`tests/test_storage_conformance.py`](../tests/test_storage_conformance.py):
one contract function run against every backend — today the local adapter and a mocked S3 adapter
(`moto`), in CI on every push. Add your adapter to that parametrization so it's held to the same
contract. Run it with:

```bash
pip install -e ".[s3,xlsx,test]"
pytest -q
```

You can also prove an adapter by pointing a `config.yaml` at it and running `curato demo` — the
output in `warehouse/curated/` should match the local run. A cloud-agnostic claim is only true while
it's exercised on more than one backend.
