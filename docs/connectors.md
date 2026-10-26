# Connecting real systems (runbook)

How to point Curato at a live database, SAP, or Salesforce. Connection sources are *pulled*
(`curato pull`), and the **catalog is generated from the source's own metadata** — you don't write
schema by hand.

All sources are declared under `sources:` in `config.yaml`. Each gets a name you choose; a pulled
object becomes the catalog dataset `<source-name>.<object>`, which you then build products from:

```bash
curato pull <source-name>                               # introspect + load + auto-catalog
curato catalog                                          # verify what was cataloged
curato serve "<prompt>" -d <source-name>.<object>       # build a product from it
```

> **Secrets:** the examples below show passwords inline for clarity. In production, do **not** commit
> credentials. Keep `config.yaml` out of source control (or template it) and inject secrets from the
> environment or a secret store (Vault, cloud KMS, Key Vault). The LLM port already reads keys from
> env vars; treat source credentials the same way.

---

## Relational databases (RDBMS)

One connector, any SQLAlchemy dialect. Install the base extra plus your DB driver.

```bash
pip install -e ".[rdbms]"
# then the driver for your DB, e.g.:
#   Postgres:    pip install "psycopg[binary]"
#   MySQL:       pip install pymysql
#   SQL Server:  pip install pyodbc
#   Oracle:      pip install oracledb
```

`config.yaml`:

```yaml
sources:
  mydb:
    kind: rdbms
    url: "postgresql+psycopg://user:pw@host:5432/dbname"
    tables: [sales, customers]     # optional; omit to pull every table
```

SQLAlchemy URL formats:

| DB | URL |
|----|-----|
| PostgreSQL | `postgresql+psycopg://user:pw@host:5432/db` |
| MySQL | `mysql+pymysql://user:pw@host:3306/db` |
| SQL Server | `mssql+pyodbc://user:pw@host:1433/db?driver=ODBC+Driver+18+for+SQL+Server` |
| Oracle | `oracle+oracledb://user:pw@host:1521/?service_name=ORCLPDB1` |
| SQLite | `sqlite:///absolute/or/relative/path.db` |

---

## SAP — CDS views

CDS views are consumed two ways. Pick per source with `access:`.

### Mode A — HANA SQL (CDS views are SQL views in HANA)

Use this when you have database-level access to HANA. CDS views appear as SQL views, so Curato reads
them over a SQLAlchemy HANA connection — the same SQL path as any RDBMS.

```bash
pip install -e ".[hana]"     # sqlalchemy-hana + hdbcli
```

```yaml
sources:
  sap_finance:
    kind: sap
    access: hana
    url: "hana+hdbcli://USER:PW@hana-host:39015"   # port: 3<instance>15, e.g. 39015 for instance 90
    view_prefix: "ZC_"            # filter to your CDS naming convention (ZC_, C_, I_, ...)
    objects: [ZC_SpendByVendor]   # optional; omit to pull all views matching the prefix
```

Notes:
- `view_prefix` keeps the pull focused on your consumption-layer CDS views instead of every table.
- The CDS view (and the service user) must be exposed in the schema the connection lands in; set the
  default schema on the user or fully-qualify the view name in `objects`.
- HANA Cloud uses port `443` with encryption — add it to the URL query if your driver needs it, e.g.
  `?encrypt=true`.

### Mode B — OData (CDS views published as a service, e.g. S/4HANA Cloud)

Use this when direct DB access isn't available (S/4HANA Cloud / RAP). The CDS view is exposed as an
OData service (via `@OData.publish` or a Gateway service), and Curato reads its entity sets over HTTP.

```bash
pip install -e ".[sap]"      # requests
```

```yaml
sources:
  sap_cloud:
    kind: sap
    access: odata
    service_url: "https://my-s4.example.com/sap/opu/odata/sap/ZSPEND_SRV"
    user: "CURATO_SVC"
    password: "..."            # inject from a secret store in production
    entities: [SpendByVendor]  # optional; omit to discover entity sets from $metadata
```

Notes:
- `service_url` is the OData **service root** (ends at the service name, no entity set).
- Works with OData v2 (`d.results`) and v4 (`value`) response shapes.
- For OAuth/SAML-protected gateways, authenticate your own `requests.Session` and pass it in code,
  or extend `SAPCDSConnector` to accept a token — basic auth is the built-in default.

---

## Salesforce

```bash
pip install -e ".[sf]"       # simple-salesforce
```

```yaml
sources:
  salesforce:
    kind: salesforce
    username: "svc@example.com"
    password: "..."
    security_token: "..."      # from Setup -> Reset My Security Token
    domain: "login"            # "test" for a sandbox
    objects: [Opportunity, Account]   # optional; omit to pull all queryable sobjects
```

Notes:
- Pull a focused `objects` list first — a full org has hundreds of sobjects.
- `query_all` follows pagination, so large objects come back complete.

---

## What a pull writes to the catalog

For each object, `curato pull` records a dataset with metadata it read from the source itself:

```json
{
  "mydb.sales": {
    "location": "warehouse/bronze/mydb__sales.parquet",
    "schema": { "vendor": "VARCHAR", "amount": "DOUBLE PRECISION", "dt": "DATE" },
    "mapping": { "vendor": "vendor_name", "amount": "spend_amount" },
    "glossary_terms": ["spend_amount", "vendor_name"],
    "row_count": 1203,
    "pii": false,
    "source_system": "rdbms",
    "source_object": "sales"
  }
}
```

The `mapping` is what makes a prompt resolvable: extend the `glossary:` in `config.yaml` so your
real column names (SAP's technical names, Salesforce API names) map to business terms. That glossary
is the semantic layer — the better it is, the more prompts resolve without an engineer.

## Troubleshooting

- **`NotImplementedError: Source connector '<kind>' not registered`** — check `kind:` is one of
  `rdbms` / `sap` / `salesforce`.
- **Driver import error on pull** — install the matching extra/driver (tables above). The connectors
  import their SDK lazily, so a missing driver only errors when you actually pull that source.
- **A prompt won't resolve against a pulled dataset** — run `curato catalog`; if `glossary_terms` is
  empty, add synonyms for those columns to `glossary:` and pull again.
- **HANA/SAP/Salesforce quirks** — the connector logic is unit-tested, but a real system can surface
  a dialect or response shape we didn't anticipate. Capture the error and open an
  [adapter issue](../.github/ISSUE_TEMPLATE/adapter_request.md).
