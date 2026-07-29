"""Data quality framework.

The runner and the report writer are provided. ONE example rule is implemented
so you can see the shape. The rest is yours.

Design intent: a data quality rule is *data*, not a branch in a function. A
sustainability controller who does not write Python should be able to read
RULES and understand what is being checked and what happens when it fails.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import duckdb
import pandas as pd

from .config import REPORTS_DIR

Severity = Literal["ERROR", "WARN", "INFO"]
Action = Literal["BLOCK", "QUARANTINE", "COERCE", "FLAG"]


@dataclass(frozen=True)
class Rule:
    rule_id: str
    rule_name: str
    severity: Severity
    action: Action
    # SQL returning ONE row: (rows_checked BIGINT, rows_failed BIGINT)
    check_sql: str
    # Optional SQL returning the offending rows, for the quarantine table.
    detail_sql: str | None = None


RULES: list[Rule] = [
    # ---------------------------------------------------------------- EXAMPLE
    Rule(
        rule_id="DQ001",
        rule_name="reading value is numeric",
        severity="ERROR",
        action="QUARANTINE",
        check_sql="""
            SELECT
                count(*)                                        AS rows_checked,
                count(*) FILTER (
                    WHERE try_cast(value AS DOUBLE) IS NULL
                )                                               AS rows_failed
            FROM raw.readings
        """,
        detail_sql="""
            SELECT reading_id, site_id, period, metric_code, value,
                   'value is not numeric' AS reason
            FROM raw.readings
            WHERE try_cast(value AS DOUBLE) IS NULL
        """,
    ),
    # ------------------------------------------------------------------ TODO
    # Add your rules below. Think about what would actually mislead the Group
    # Sustainability lead if it went unnoticed, and set severity accordingly.
    # Not every problem deserves to block the load - argue your choices in
    # DECISIONS.md.
]


def run_rules(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Execute every rule, persist offending rows, return the report frame."""
    results = []
    con.execute("DROP TABLE IF EXISTS staging.dq_quarantine")
    quarantine_created = False

    for rule in RULES:
        checked, failed = con.execute(rule.check_sql).fetchone()
        results.append(
            {
                "rule_id": rule.rule_id,
                "rule_name": rule.rule_name,
                "severity": rule.severity,
                "rows_checked": int(checked),
                "rows_failed": int(failed),
                "action_taken": rule.action if failed else "NONE",
            }
        )

        if rule.detail_sql and failed:
            payload = f"""
                SELECT '{rule.rule_id}' AS rule_id, *
                FROM ({rule.detail_sql})
            """
            if not quarantine_created:
                con.execute(
                    f"CREATE TABLE staging.dq_quarantine AS "
                    f"SELECT rule_id, reading_id, site_id, period, metric_code, "
                    f"CAST(value AS VARCHAR) AS value, reason FROM ({payload})"
                )
                quarantine_created = True
            else:
                con.execute(
                    f"INSERT INTO staging.dq_quarantine "
                    f"SELECT rule_id, reading_id, site_id, period, metric_code, "
                    f"CAST(value AS VARCHAR) AS value, reason FROM ({payload})"
                )

    return pd.DataFrame(
        results,
        columns=["rule_id", "rule_name", "severity",
                 "rows_checked", "rows_failed", "action_taken"],
    )


def write_dq_report(df: pd.DataFrame) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(REPORTS_DIR / "dq_report.csv", index=False)


def has_blocking_failures(df: pd.DataFrame) -> bool:
    """True if any rule with action BLOCK failed. Wire this in if you want the
    pipeline to refuse to publish - that is a judgement call, and we want to
    see which way you go and why."""
    return bool(((df["action_taken"] == "BLOCK") & (df["rows_failed"] > 0)).any())
