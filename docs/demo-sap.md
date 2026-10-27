# Demo runbook — Curato for a SAP shop (mixed audience)

A presenter's script for a ~35-minute **live demo + slides** to a mixed room (business + technical),
framed around **SAP CDS views**. The live segment runs on your laptop against a local HANA
stand-in, using Curato's real, tested SAP connector.

---

## Before the demo (do this the day before)

```bash
# from the repo root
pip install -e .
cd examples/sap_demo
python build_sample.py
curato pull sap_finance
curato serve "total spend by vendor" -d sap_finance.ZC_VendorInvoices -y
```

Checklist:
- [ ] The commands above all succeed; the BI report opens in a browser.
- [ ] **Reset to a clean state** right before presenting: delete `warehouse/` and `catalog/` in
      `examples/sap_demo/` so the audience sees the catalog build from empty.
- [ ] Terminal font **large** (18–22pt) — most of the room reads it from a screen share.
- [ ] Deck open and ready; the 30-second reel and a screenshot of a BI report ready as **fallback**.
- [ ] Browser tab ready to open the generated `.html` report.
- [ ] Close noisy apps / notifications; one clean terminal, one browser.

Reset command:
```bash
cd examples/sap_demo && rm -rf warehouse catalog
```

---

## The honest SAP framing (say this once, up front)

> "What you'll see connects to SAP **CDS views**. For today it's pointed at a local stand-in so it
> runs on my laptop — but it's the *same connector code* that talks to your HANA. In your
> landscape, one line changes: the connection URL. For S/4HANA Cloud, the same connector reads your
> published OData services instead."

Saying this plainly builds trust. Don't imply you're live on their SAP — offer that as the pilot.

---

## Run of show (~35 min)

### Part 1 — The story, in slides (~8 min)
Slides: **cover → problem → shift → what**.
- Open on the **problem**: every data request is a ticket; the business waits weeks.
- The **shift**: what if anyone could ask in plain language and get a *governed* product in minutes?
- **What Curato is**: metadata-driven, agentic, cloud-agnostic. "Let me show you — on SAP."

### Part 2 — The live proof (~12 min)  ← the heart of the demo
Switch to the terminal in `examples/sap_demo/`.

**1. Point at SAP (30s).** Show `config.yaml` briefly:
> "Here's the source — SAP, access mode HANA, and we pull the CDS consumption views, the `ZC_`
> ones. This URL is the only thing that differs from your real system."

**2. Pull + auto-catalog (2 min).**
```bash
curato pull sap_finance
curato catalog
```
> "Curato read the CDS views and their metadata and **built the catalog itself** — schema, row
> counts, and it mapped the SAP columns to business terms. Notice it **flagged PII automatically**
> on the vendor-invoices view — it saw the vendor email. No one configured that."

*(This PII beat lands with security/compliance people — point it out.)*

**3. Prompt → product, through the gate (4 min).** Run **without** `-y` so the gate is live:
```bash
curato serve "total spend by vendor" -d sap_finance.ZC_VendorInvoices
```
> "A business user just asked in plain English. Watch what the agents do: they understood the
> request, **grounded it to the real cataloged columns** — so it can't invent a field — generated
> the SQL, and **validated it on the actual data**. Rows came back, checks passed."

It pauses at `Approve and publish this product? [y/N]`.
> "And here's the point: it does **not** publish on its own. A human approves. I'll approve now."

Type `y`.

**4. Show the result (2 min).** Open the report:
```
warehouse/curated/total_spend_by_vendor.html
```
> "A governed data product and a live BI report — from one sentence, on SAP data, in under a
> minute. Every product records the prompt and the exact query that built it."

**5. (Optional) one more prompt (1 min).**
```bash
curato serve "monthly spend by vendor" -d sap_finance.ZC_VendorInvoices -y
```

### Part 3 — Why it holds up, and how you'd adopt it (~8 min)
Slides: **catalog → governance → cloud → value → adopt → close**.
- **catalog / governance**: for the technical + risk people — auto-catalog, validation, the gate,
  lineage, PII.
- **cloud**: no lock-in; runs in *your* environment (important for SAP data residency).
- **value / adopt**: minutes not weeks; 50–70% less repetitive work; start with a small pilot.

### Q&A, then the ask (~7 min)
Close with a concrete next step (below).

---

## Talk track for a MIXED room
- **Lead with business value, prove with the terminal.** Executives buy the "minutes not weeks"
  story; engineers buy the live SQL + validation + the gate. Give both, in that order.
- When you drop to the terminal, **narrate what each step means in business terms**, not just what
  you typed. The terminal is proof, not the point.
- Keep the engineers' deeper questions for Part 3 / Q&A so you don't lose the business audience
  mid-demo.

---

## If the live demo breaks (stay calm, have this ready)
1. You pre-reset, so the most likely issue is a typo — retype slowly.
2. If a command genuinely fails: "I'll show you the recorded version" → play the **30-second reel**
   or open a **pre-generated BI report** screenshot. Keep talking; don't debug on stage.
3. Worst case, fall back entirely to the deck + reel. The story still lands.

---

## Objection handling / FAQ

**"Is that really our SAP?"**
No — it's a local stand-in so it runs here. The *connector* is real and tested; against your system
only the connection URL changes (HANA for on-prem, OData for S/4HANA Cloud). That's exactly what a
pilot would wire up.

**"Does it write back to SAP?"**
No. The connector **reads** CDS views. The source system is untouched; products are written to your
own data lake.

**"Where does our data go? What about the LLM?"**
It runs **in your environment**. The AI reasons over schema and small samples, not row-level data,
and can run a **local/offline model** — today's demo used no external LLM at all. Nothing leaves
your perimeter.

**"How is PII / governance handled?"**
PII is flagged automatically at catalog time (you saw it). Nothing publishes without validation and
a **human approval**. Every product carries its prompt and query for audit.

**"Does this replace our data team?"**
No. It compresses the repetitive part of the lifecycle and lets the team focus on hard problems —
and *they* own the approval gate. It's leverage for the team, not a replacement.

**"How mature is it?"**
Honest answer: it's an early, open-source platform (Apache-2.0, CI-tested). That's why the right
next step is a **scoped pilot** on one real CDS view, not a big-bang rollout.

---

## The ask (end on this)
> "Let's run a **2–4 week pilot**: pick one real CDS view and one reporting need your team actually
> has. We point Curato at your HANA, auto-catalog it, and build that product live with your people
> in the room. Low cost, fast proof, and you'll know exactly what it's worth to you."
