"""KPI layer.

Put your SQL in ``sql/kpis/*.sql``. Each file must create a table or view in
the ``marts`` schema with the name given below and exactly the columns listed
(names and order both matter - the tests check them).

Exported to reports/<name>.csv automatically.
"""

from __future__ import annotations

import duckdb

from .config import REPORTS_DIR
from .db import run_sql_dir

# name -> required columns, in order
KPI_CONTRACT: dict[str, list[str]] = {
    # Scope 1 + Scope 2, tCO2e, canonical units, restatement-aware.
    # Divested sites must not contribute from their divestment date onward.
    "kpi_emissions": [
        "period", "site_id", "site_name", "business_unit", "region",
        "scope1_tco2e", "scope2_tco2e", "total_tco2e",
    ],
    # MWh per 1,000 hours worked. is_estimated flags rows where the hours
    # denominator had to be derived rather than read directly.
    "kpi_energy_intensity": [
        "period", "site_id", "site_name",
        "energy_mwh", "hours_worked", "mwh_per_1000_hours", "is_estimated",
    ],
    # Rolling 12-month TRIR = recordable incidents * 200,000 / hours worked.
    # has_full_window is false where fewer than 12 months of data exist.
    "kpi_trir": [
        "period", "site_id", "site_name",
        "recordable_incidents_r12", "hours_worked_r12", "trir_r12",
        "has_full_window",
    ],
    # Year-over-year change in Scope 1 + 2, at group and business-unit level.
    # grouping_level is 'GROUP' or 'BUSINESS_UNIT'.
    "kpi_yoy": [
        "period", "grouping_level", "grouping_value",
        "total_tco2e", "total_tco2e_ly", "yoy_abs", "yoy_pct",
    ],
}


def build_kpis(con: duckdb.DuckDBPyConnection) -> list[str]:
    executed = run_sql_dir(con, "kpis")

    present = {
        row[0]
        for row in con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'marts'"
        ).fetchall()
    }
    missing = [k for k in KPI_CONTRACT if k not in present]
    if missing:
        raise RuntimeError("KPI build incomplete - missing: " + ", ".join(missing))
    return executed


def export_kpis(con: duckdb.DuckDBPyConnection) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    for name, columns in KPI_CONTRACT.items():
        cols = ", ".join(f'"{c}"' for c in columns)
        out = REPORTS_DIR / f"{name}.csv"
        con.execute(
            f"COPY (SELECT {cols} FROM marts.{name}) "
            f"TO '{out}' (HEADER, DELIMITER ',')"
        )
