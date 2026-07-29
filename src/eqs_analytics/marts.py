"""Dimensional model build.

Put your DDL/DML in ``sql/marts/*.sql``. Files run in filename order, so name
them for dependency order (01_, 02_, 10_ ...). Each file should create objects
in the ``marts`` schema.

Required objects and their grain:

    marts.dim_site          one row per site version
    marts.dim_metric        one row per metric_code
    marts.dim_date          one row per calendar month in the reporting window
    marts.fact_eqs_monthly  one row per site x period x metric
    marts.fact_incident     one row per incident

Requirements:
  * facts join to dims on surrogate keys, not on natural text keys
  * no many-to-many relationships in the model you hand to Power BI
  * sites are divested and acquired mid-year - decide your SCD approach and
    justify it in DECISIONS.md
"""

from __future__ import annotations

import duckdb

from .db import run_sql_dir

REQUIRED_TABLES = [
    "dim_site",
    "dim_metric",
    "dim_date",
    "fact_eqs_monthly",
    "fact_incident",
]


def build_marts(con: duckdb.DuckDBPyConnection) -> list[str]:
    """Run every file in sql/marts/ and verify the required objects exist."""
    executed = run_sql_dir(con, "marts")

    present = {
        row[0]
        for row in con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'marts'"
        ).fetchall()
    }
    missing = [t for t in REQUIRED_TABLES if t not in present]
    if missing:
        raise RuntimeError(
            "marts build incomplete - missing: " + ", ".join(missing)
        )
    return executed
