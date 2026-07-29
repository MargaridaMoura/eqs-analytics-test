"""Visible test suite - the contract your pipeline must satisfy.

These check STRUCTURE, not judgement. Passing them means your pipeline runs
and produces the right shapes. It does not mean your numbers are right.

There is a second, hidden suite that checks whether you handled the specific
data quality problems in the dataset correctly. Read the data.
"""

from __future__ import annotations

import pytest

from src.eqs_analytics.kpis import KPI_CONTRACT
from src.eqs_analytics.marts import REQUIRED_TABLES

from .conftest import table_exists


# ------------------------------------------------------------------ marts
@pytest.mark.parametrize("table", REQUIRED_TABLES)
def test_required_mart_exists(con, table):
    assert table_exists(con, "marts", table), f"marts.{table} was not created"


def test_dimension_row_counts(con):
    assert con.execute("SELECT count(*) FROM marts.dim_site").fetchone()[0] == 12
    assert con.execute("SELECT count(*) FROM marts.dim_date").fetchone()[0] == 24
    assert con.execute("SELECT count(*) FROM marts.dim_metric").fetchone()[0] == 6


def test_dim_site_has_surrogate_key(con):
    cols = {c[0] for c in con.execute("DESCRIBE marts.dim_site").fetchall()}
    assert "site_key" in cols, "dim_site needs a surrogate key named site_key"
    dupes = con.execute(
        "SELECT count(*) FROM (SELECT site_key FROM marts.dim_site "
        "GROUP BY 1 HAVING count(*) > 1)"
    ).fetchone()[0]
    assert dupes == 0, "site_key is not unique"


def test_fact_joins_on_surrogate_keys(con):
    cols = {c[0] for c in con.execute("DESCRIBE marts.fact_eqs_monthly").fetchall()}
    for key in ("site_key", "date_key", "metric_key"):
        assert key in cols, f"fact_eqs_monthly must expose {key}"


def test_fact_has_no_orphan_site_keys(con):
    orphans = con.execute(
        "SELECT count(*) FROM marts.fact_eqs_monthly f "
        "LEFT JOIN marts.dim_site s USING (site_key) WHERE s.site_key IS NULL"
    ).fetchone()[0]
    assert orphans == 0, "fact_eqs_monthly contains site_keys not in dim_site"


def test_fact_grain_is_site_period_metric(con):
    dupes = con.execute(
        "SELECT count(*) FROM (SELECT site_key, date_key, metric_key "
        "FROM marts.fact_eqs_monthly GROUP BY 1,2,3 HAVING count(*) > 1)"
    ).fetchone()[0]
    assert dupes == 0, (
        "fact_eqs_monthly is not unique on site x period x metric - "
        "check how you handled resubmissions"
    )


def test_incident_grain_is_unique(con):
    dupes = con.execute(
        "SELECT count(*) FROM (SELECT incident_id FROM marts.fact_incident "
        "GROUP BY 1 HAVING count(*) > 1)"
    ).fetchone()[0]
    assert dupes == 0, "incident_id is not unique in fact_incident"


# -------------------------------------------------------------------- KPIs
@pytest.mark.parametrize("name,columns", list(KPI_CONTRACT.items()))
def test_kpi_report_columns(report, name, columns):
    df = report(name)
    assert list(df.columns) == columns, (
        f"reports/{name}.csv columns are wrong\n"
        f"  expected: {columns}\n  got:      {list(df.columns)}"
    )


@pytest.mark.parametrize("name", list(KPI_CONTRACT))
def test_kpi_report_not_empty(report, name):
    assert len(report(name)) > 0, f"reports/{name}.csv is empty"


def test_emissions_covers_reporting_window(report):
    periods = set(report("kpi_emissions")["period"])
    assert "2024-01" in periods and "2025-12" in periods


def test_trir_is_plausible(report):
    trir = report("kpi_trir")["trir_r12"].dropna()
    assert (trir >= 0).all(), "TRIR cannot be negative"
    assert trir.max() < 100, "TRIR above 100 suggests a broken denominator"


def test_yoy_has_both_grouping_levels(report):
    levels = set(report("kpi_yoy")["grouping_level"])
    assert levels == {"GROUP", "BUSINESS_UNIT"}, f"got {levels}"


# ---------------------------------------------------------- data quality
def test_dq_report_shape(report):
    df = report("dq_report")
    assert list(df.columns) == [
        "rule_id", "rule_name", "severity", "rows_checked",
        "rows_failed", "action_taken",
    ]


def test_dq_has_a_real_rule_set(report):
    df = report("dq_report")
    assert len(df) >= 6, (
        f"only {len(df)} data quality rule(s) defined - the dataset has more "
        "problems than that"
    )
    assert (df["rows_failed"] > 0).sum() >= 4, (
        "your rules found almost nothing; the source data is not that clean"
    )
    assert "ERROR" in set(df["severity"]), "no rule is severity ERROR"


def test_dq_rules_actually_check_something(report):
    df = report("dq_report")
    assert (df["rows_checked"] > 0).all(), "a rule checked zero rows"
