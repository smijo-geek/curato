"""Render a curated product as a self-contained HTML BI report.

No external resources — it opens offline by double-clicking, and travels as one file. The Curator
calls this so "generate a BI report" is a real pipeline artifact, not a side demo.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime
import html as _html

import pandas as pd


def _fmt(v) -> str:
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, (int, float)):
        f = float(v)
        return f"{int(f):,}" if f.is_integer() else f"{f:,.2f}"
    return _html.escape(str(v))


def generate(df: pd.DataFrame, name: str, prompt: str, sql: str,
             description: str, out_path: str) -> str:
    cols = list(df.columns)
    num_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
    measure = num_cols[-1] if num_cols else None
    label_cols = [c for c in cols if c != measure]
    rows = df.to_dict("records")

    # --- bar chart (pure HTML/CSS, no JS) ---
    chart = ""
    if measure and rows:
        maxv = max((r[measure] for r in rows), default=0) or 1
        bars = []
        for r in rows[:20]:
            label = " · ".join(_fmt(r[c]) for c in label_cols) or _html.escape(name)
            pct = max(float(r[measure]) / maxv * 100, 1.5)
            bars.append(
                f'<div class="row"><span class="lab">{label}</span>'
                f'<span class="track"><span class="fill" style="width:{pct:.1f}%"></span></span>'
                f'<span class="val">{_fmt(r[measure])}</span></div>')
        chart = (f'<section class="card"><h2>{_html.escape(measure.replace("_"," "))}</h2>'
                 f'<div class="chart">{"".join(bars)}</div></section>')

    # --- table ---
    thead = "".join(f"<th>{_html.escape(c)}</th>" for c in cols)
    trows = "".join("<tr>" + "".join(f"<td>{_fmt(r[c])}</td>" for c in cols) + "</tr>" for r in rows)
    table = (f'<section class="card"><h2>Data</h2><div class="scroll"><table>'
             f'<thead><tr>{thead}</tr></thead><tbody>{trows}</tbody></table></div></section>')

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_html.escape(name)} — Curato report</title>
<style>
  :root{{--bg:#f7f8fa;--card:#fff;--ink:#15202b;--muted:#5b6b7a;--line:#e2e8f0;--accent:#2d6ae0;
    --track:#eef1f5;--mono:ui-monospace,"Cascadia Code",Consolas,monospace}}
  @media(prefers-color-scheme:dark){{:root{{--bg:#0e141b;--card:#161f29;--ink:#eef3f8;--muted:#92a3b4;
    --line:#273340;--accent:#5c91ff;--track:#1f2b37}}}}
  *{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);
    font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}}
  .wrap{{max-width:860px;margin:0 auto;padding:28px 18px 48px}}
  .kick{{font-family:var(--mono);font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}}
  h1{{font-size:26px;margin:6px 0 4px;letter-spacing:-.01em}}
  .desc{{color:var(--muted);max-width:60ch}}
  .card{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px;margin-top:16px;
    box-shadow:0 1px 2px rgba(16,30,54,.05),0 6px 20px rgba(16,30,54,.05)}}
  h2{{font-size:15px;margin:0 0 12px}}
  .chart{{display:flex;flex-direction:column;gap:9px}}
  .row{{display:grid;grid-template-columns:minmax(90px,38%) 1fr auto;gap:10px;align-items:center}}
  .lab{{color:var(--ink);font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
  .track{{background:var(--track);border-radius:5px;height:18px;overflow:hidden}}
  .fill{{display:block;height:100%;background:var(--accent);border-radius:5px}}
  .val{{font-family:var(--mono);font-size:13px;color:var(--muted);text-align:right;white-space:nowrap}}
  .scroll{{overflow-x:auto}} table{{border-collapse:collapse;width:100%;font-size:13px}}
  th,td{{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);white-space:nowrap}}
  th{{color:var(--muted);font-weight:600}} td{{font-variant-numeric:tabular-nums}}
  code{{display:block;white-space:pre-wrap;font-family:var(--mono);font-size:12px;color:var(--muted);
    background:var(--track);border-radius:8px;padding:10px 12px;margin-top:6px}}
  .foot{{color:var(--muted);font-size:12px;margin-top:22px}}
  .pill{{display:inline-block;font-size:11px;color:#fff;background:#17916b;border-radius:99px;padding:2px 9px;margin-left:8px;vertical-align:middle}}
</style></head><body><div class="wrap">
  <p class="kick">Curato · curated data product</p>
  <h1>{_html.escape(name)}<span class="pill">human-approved</span></h1>
  <p class="desc">{_html.escape(description)}</p>
  {chart}
  {table}
  <section class="card"><h2>Provenance</h2>
    <div style="color:var(--muted);font-size:13px">Generated from the prompt:</div>
    <div style="font-weight:600;margin:3px 0 8px">“{_html.escape(prompt)}”</div>
    <code>{_html.escape(sql)}</code>
  </section>
  <p class="foot">Built by Curato on {stamp} · {len(rows)} rows. This report regenerates every time the
  product is published, from the validated query above.</p>
</div></body></html>"""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    return out_path
