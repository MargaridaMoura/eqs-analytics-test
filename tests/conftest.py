"""Shared fixtures. Runs your pipeline once, then inspects what it produced."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import duckdb
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "build" / "eqs.duckdb"
REPORTS = ROOT / "reports"


@pytest.fixture(scope="session")
def pipeline() -> None:
    """Run `python -m src.eqs_analytics.main` exactly once for the test session."""
    result = subprocess.run(
        [sys.executable, "-m", "src.eqs_analytics.main"],
        cwd=ROOT, capture_output=True, text=True, timeout=600,
    )
    if result.returncode != 0:
        pytest.fail(
            "pipeline failed to run\n"
            f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
        )


@pytest.fixture(scope="session")
def con(pipeline) -> duckdb.DuckDBPyConnection:
    if not DB.exists():
        pytest.fail(f"expected a database at {DB}")
    connection = duckdb.connect(str(DB), read_only=True)
    yield connection
    connection.close()


@pytest.fixture(scope="session")
def report(pipeline):
    """report('kpi_emissions') -> DataFrame from reports/kpi_emissions.csv"""

    def _load(name: str) -> pd.DataFrame:
        path = REPORTS / f"{name}.csv"
        if not path.exists():
            pytest.fail(f"missing expected output: reports/{name}.csv")
        return pd.read_csv(path)

    return _load


def table_exists(con, schema: str, table: str) -> bool:
    return bool(
        con.execute(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema = ? AND table_name = ?",
            [schema, table],
        ).fetchone()[0]
    )
