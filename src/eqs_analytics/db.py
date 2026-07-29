"""DuckDB connection helpers. Provided for you - no changes required."""

from __future__ import annotations

from pathlib import Path

import duckdb

from .config import BUILD_DIR, DB_PATH, SQL_DIR


def connect(fresh: bool = True) -> duckdb.DuckDBPyConnection:
    """Open (and optionally recreate) the project database."""
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    if fresh and DB_PATH.exists():
        DB_PATH.unlink()
    con = duckdb.connect(str(DB_PATH))
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute("CREATE SCHEMA IF NOT EXISTS staging")
    con.execute("CREATE SCHEMA IF NOT EXISTS marts")
    return con


def run_sql_file(con: duckdb.DuckDBPyConnection, path: Path) -> None:
    """Execute a .sql file. Statements are separated by semicolons."""
    con.execute(path.read_text())


def run_sql_dir(con: duckdb.DuckDBPyConnection, subdir: str) -> list[str]:
    """Execute every .sql file in sql/<subdir> in filename order.

    Name your files so they sort into dependency order, e.g.
        01_dim_site.sql, 02_dim_metric.sql, 10_fact_eqs_monthly.sql
    """
    executed: list[str] = []
    target = SQL_DIR / subdir
    for path in sorted(target.glob("*.sql")):
        run_sql_file(con, path)
        executed.append(path.name)
    return executed
