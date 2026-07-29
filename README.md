# EQS Analytics Engineering — Take-Home Exercise

**Time box: 4 hours.** We mean it. If you run out of time, stop and write down what you'd
have done next in `DECISIONS.md`. An honest 80% with clear reasoning beats a rushed 100%.

---

## Context

EHS & Sustainability (EQS) reporting has just moved off a patchwork of site-level
spreadsheets onto a central analytics platform (Snowflake + Power BI). You are joining the
team that owns that platform.

This exercise is a miniature of the real job: monthly submissions from a dozen global sites
arrive as flat files, they are messy, and a Group Sustainability Reporting team needs
numbers out of them that end up in an **audited** annual report.

We use **DuckDB** here so you can run everything locally with no account. The SQL dialect is
close to Snowflake — window functions, `QUALIFY`, `date_trunc`, CTEs all behave the same —
so write it the way you would write it for Snowflake.

---

## The data (`data/`)

| File | Grain | Notes |
|---|---|---|
| `sites.csv` | one row per site | includes `valid_from` / `valid_to`, business unit, region, headcount |
| `metric_definitions.csv` | one row per metric code | category and canonical unit of measure |
| `uom_conversions.csv` | one row per unit pair | `from_uom → to_uom` conversion factors |
| `readings.csv` | one row per submission | site × period × metric × `submitted_at` |
| `incidents.csv` | one row per EHS incident | date, severity, `is_recordable`, `lost_days` |

Everything is loaded into the `raw` schema as **VARCHAR**, deliberately. Source files come
from site portals and spreadsheets and are not type-safe; deciding how to cast, coerce and
reject values is your job.

The data is **deliberately dirty.** It reflects things we actually see. Part of what we're
assessing is whether you find the problems without being told where they are.

---

## What's already built

You don't need to spend any of your four hours on plumbing:

- `src/eqs_analytics/db.py` — DuckDB connection, SQL file runner
- `src/eqs_analytics/loaders.py` — raw CSV ingestion
- `src/eqs_analytics/quality.py` — DQ rule runner + report writer, **one example rule**
- `src/eqs_analytics/marts.py` / `kpis.py` — build orchestration and the output contract
- `tests/` — the contract test suite

What's empty and yours to fill: `sql/marts/`, `sql/kpis/`, the `RULES` list in `quality.py`,
and `DECISIONS.md`.

---

## Task 1 — Ingest & data quality (~60 min)

Extend the `RULES` list in `src/eqs_analytics/quality.py`. Write your rules as **data, not
as scattered `if` statements** — a sustainability controller who doesn't write Python should
be able to read `RULES` and understand what's checked and what happens when it fails.

Set `severity` and `action` deliberately. Not every problem deserves to block the load;
argue your choices in `DECISIONS.md`.

**Deliverable:** `reports/dq_report.csv` — `rule_id, rule_name, severity, rows_checked,
rows_failed, action_taken`.

Rows you reject must be **quarantined and counted**, never silently dropped. Silent deletion
is how ESG numbers become unauditable.

---

## Task 2 — Dimensional model (~60 min)

Write SQL into `sql/marts/*.sql`. Files execute in filename order, so name them for
dependency order (`00_`, `10_`, `20_`). Required objects:

| Object | Grain |
|---|---|
| `marts.dim_site` | one row per site version |
| `marts.dim_metric` | one row per metric code |
| `marts.dim_date` | one row per month in the reporting window |
| `marts.fact_eqs_monthly` | site × period × metric |
| `marts.fact_incident` | one row per incident |

Constraints:

- Facts join to dimensions on **surrogate keys**, not natural text keys.
- No many-to-many relationships in the model you'd hand to Power BI.
- Sites are divested and acquired mid-year. Decide your SCD approach and justify it.

A staging layer between `raw` and `marts` is expected — use the `staging` schema.

---

## Task 3 — KPI layer (~45 min)

Write SQL into `sql/kpis/*.sql` creating tables or views in the `marts` schema. Names and
columns are a contract — see `KPI_CONTRACT` in `src/eqs_analytics/kpis.py`. They export to
`reports/` automatically.

1. **`kpi_emissions`** — Scope 1 + Scope 2 tCO₂e by month, site, business unit, region.
2. **`kpi_energy_intensity`** — MWh per 1,000 hours worked, by site and month.
3. **`kpi_trir`** — rolling 12-month Total Recordable Incident Rate:
   `recordable incidents × 200,000 / hours worked`. The denominator lives in a different
   table at a different grain.
4. **`kpi_yoy`** — year-over-year % change in Scope 1 + 2, at group and business-unit level.

> A month with **no submission** must be distinguishable from a month with a **zero**.
> Reporting a gap as zero is the single most common way this kind of dashboard misleads
> people, and we check for it.

---

## Task 4 — `DECISIONS.md` (~20 min)

Max one page, written for the **Group Sustainability Reporting lead**, not for an engineer.
A template is in the repo. Cover:

- Which numbers you'd sign off on and which you wouldn't, and why.
- The data quality issues you found, ranked by **materiality to the reported figures**.
- What you'd ask the site controllers to fix at source.
- What you'd build next, and what you deliberately left out.

This carries real weight in scoring. Most of this job is explaining data to people who
don't write SQL.

---

## Optional bonus

Only if you have time left. Pick at most one. These cannot make up for gaps in Tasks 1–4.

- **`dashboard/`** — a `.pbix` against your marts, **or** a `dashboard_spec.md` describing
  pages, visuals and interactions. Either is fine; we don't assume you have Power BI Desktop.
- **`dax/measures.md`** — DAX for the four KPIs, written as text. Note what belongs in DAX
  versus what's better pre-computed upstream, and why.
- **`SNOWFLAKE.md`** — how this changes on real Snowflake at 400 sites × 10 years:
  warehouse sizing, clustering, incremental loads, and what happens when a restatement
  arrives *after* the annual report is published.

---

## Running it

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m src.eqs_analytics.main    # run the pipeline
pytest                              # your gate
```

`build/eqs.duckdb` is a real file — open it in DBeaver, the DuckDB CLI or any SQL client to
inspect what your pipeline produced.

## Definition of done

`pytest` is green and `reports/` contains five CSVs: `dq_report`, `kpi_emissions`,
`kpi_energy_intensity`, `kpi_trir`, `kpi_yoy`.

The visible suite checks **structure** — schemas, grain, column contracts. There are
**additional hidden tests** that check whether you handled the specific data quality
problems in this dataset correctly. Passing the visible suite is necessary, not sufficient.
Read the data.

## Submitting

Fork this repo, work on a branch, open a pull request against your own fork, and send us the
link. We read the PR description and the commit history — commit as you go rather than in
one lump.

## Ground rules on AI tools

Use them. We do. But you'll walk us through your submission live for 30 minutes and we'll
ask why you made specific choices — so don't submit anything you can't defend.
