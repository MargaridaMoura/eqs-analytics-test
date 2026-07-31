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


 Rule(
        rule_id="DQ002",
        rule_name="reading references a known site",
        severity="ERROR",
        action="QUARANTINE",
        check_sql="""
            SELECT
                count(*) AS rows_checked,
                count(*) FILTER (
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM raw.sites AS s
                        WHERE s.site_id = r.site_id
                    )
                ) AS rows_failed
            FROM raw.readings AS r
        """,
        detail_sql="""
            SELECT
                r.reading_id,
                r.site_id,
                r.period,
                r.metric_code,
                r.value,
                'site_id does not exist in the site master' AS reason
            FROM raw.readings AS r
            WHERE NOT EXISTS (
                SELECT 1
                FROM raw.sites AS s
                WHERE s.site_id = r.site_id
            )
        """,
    ),


    Rule(
        rule_id="DQ003",
        rule_name="reading references a defined metric",
        severity="ERROR",
        action="QUARANTINE",
        check_sql="""
            SELECT
                count(*) AS rows_checked,
                count(*) FILTER (
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM raw.metric_definitions AS m
                        WHERE m.metric_code = r.metric_code
                    )
                ) AS rows_failed
            FROM raw.readings AS r
        """,
        detail_sql="""
            SELECT
                r.reading_id,
                r.site_id,
                r.period,
                r.metric_code,
                r.value,
                'metric_code does not exist in metric definitions' AS reason
            FROM raw.readings AS r
            WHERE NOT EXISTS (
                SELECT 1
                FROM raw.metric_definitions AS m
                WHERE m.metric_code = r.metric_code
            )
        """,
    ),

    Rule(
        rule_id="DQ004",
        rule_name="reading unit can be converted to the canonical unit",
        severity="ERROR",
        action="QUARANTINE",
        check_sql="""
            SELECT
                count(*) AS rows_checked,
                count(*) FILTER (
                    WHERE m.metric_code IS NOT NULL
                      AND c.from_uom IS NULL
                ) AS rows_failed
            FROM raw.readings AS r
            LEFT JOIN raw.metric_definitions AS m
                ON m.metric_code = r.metric_code
            LEFT JOIN raw.uom_conversions AS c
                ON c.from_uom = r.uom
               AND c.to_uom = m.canonical_uom
        """,
        detail_sql="""
            SELECT
                r.reading_id,
                r.site_id,
                r.period,
                r.metric_code,
                r.value,
                'unit cannot be converted to the metric canonical unit'
                    AS reason
            FROM raw.readings AS r
            INNER JOIN raw.metric_definitions AS m
                ON m.metric_code = r.metric_code
            LEFT JOIN raw.uom_conversions AS c
                ON c.from_uom = r.uom
               AND c.to_uom = m.canonical_uom
            WHERE c.from_uom IS NULL
        """,
    ),

 
    Rule(
        rule_id="DQ005",
        rule_name="reading period is within the site consolidation period",
        severity="ERROR",
        action="QUARANTINE",
        check_sql="""
            SELECT
                count(*) AS rows_checked,
                count(*) FILTER (
                    WHERE try_cast(r.period || '-01' AS DATE)
                          < date_trunc(
                                'month',
                                try_cast(s.valid_from AS DATE)
                            )
                       OR (
                            nullif(trim(s.valid_to), '') IS NOT NULL
                            AND try_cast(r.period || '-01' AS DATE)
                                > date_trunc(
                                    'month',
                                    try_cast(s.valid_to AS DATE)
                                )
                       )
                ) AS rows_failed
            FROM raw.readings AS r
            INNER JOIN raw.sites AS s
                ON s.site_id = r.site_id
        """,
        detail_sql="""
            SELECT
                r.reading_id,
                r.site_id,
                r.period,
                r.metric_code,
                r.value,
                'reading is outside the site consolidation period'
                    AS reason
            FROM raw.readings AS r
            INNER JOIN raw.sites AS s
                ON s.site_id = r.site_id
            WHERE try_cast(r.period || '-01' AS DATE)
                  < date_trunc(
                        'month',
                        try_cast(s.valid_from AS DATE)
                    )
               OR (
                    nullif(trim(s.valid_to), '') IS NOT NULL
                    AND try_cast(r.period || '-01' AS DATE)
                        > date_trunc(
                            'month',
                            try_cast(s.valid_to AS DATE)
                        )
               )
        """,
    ),


    Rule(
        rule_id="DQ006",
        rule_name="reported metric values are not negative",
        severity="ERROR",
        action="QUARANTINE",
        check_sql="""
            SELECT
                count(*) AS rows_checked,
                count(*) FILTER (
                    WHERE try_cast(value AS DOUBLE) < 0
                      AND metric_code IN (
                          'SCOPE1_GHG',
                          'SCOPE2_GHG',
                          'ENERGY_CONS',
                          'WATER_WD',
                          'WASTE_TOTAL',
                          'HOURS_WORKED'
                      )
                ) AS rows_failed
            FROM raw.readings
        """,
        detail_sql="""
            SELECT
                reading_id,
                site_id,
                period,
                metric_code,
                value,
                'negative value is not accepted for this metric'
                    AS reason
            FROM raw.readings
            WHERE try_cast(value AS DOUBLE) < 0
              AND metric_code IN (
                  'SCOPE1_GHG',
                  'SCOPE2_GHG',
                  'ENERGY_CONS',
                  'WATER_WD',
                  'WASTE_TOTAL',
                  'HOURS_WORKED'
              )
        """,
    ),

    
    Rule(
        rule_id="DQ007",
        rule_name="multiple submissions exist for the same site period and metric",
        severity="INFO",
        action="FLAG",
        check_sql="""
            SELECT
                count(*) AS rows_checked,
                count(*) FILTER (
                    WHERE EXISTS (
                        SELECT 1
                        FROM raw.readings AS duplicate_reading
                        WHERE duplicate_reading.site_id = r.site_id
                          AND duplicate_reading.period = r.period
                          AND duplicate_reading.metric_code = r.metric_code
                        GROUP BY
                            duplicate_reading.site_id,
                            duplicate_reading.period,
                            duplicate_reading.metric_code
                        HAVING count(*) > 1
                    )
                ) AS rows_failed
            FROM raw.readings AS r
        """,
    ),


    Rule(
        rule_id="DQ008",
        rule_name="reading period type is supported",
        severity="ERROR",
        action="QUARANTINE",
        check_sql="""
            SELECT
                count(*) AS rows_checked,
                count(*) FILTER (
                    WHERE period_type NOT IN ('M', 'Q')
                       OR period_type IS NULL
                ) AS rows_failed
            FROM raw.readings
        """,
        detail_sql="""
            SELECT
                reading_id,
                site_id,
                period,
                metric_code,
                value,
                'period_type must be M or Q' AS reason
            FROM raw.readings
            WHERE period_type NOT IN ('M', 'Q')
               OR period_type IS NULL
        """,
    ),

   

    Rule(
        rule_id="DQ009",
        rule_name="reading submission timestamp is valid",
        severity="ERROR",
        action="QUARANTINE",
        check_sql="""
            SELECT
                count(*) AS rows_checked,
                count(*) FILTER (
                    WHERE try_cast(submitted_at AS TIMESTAMP) IS NULL
                ) AS rows_failed
            FROM raw.readings
        """,
        detail_sql="""
            SELECT
                reading_id,
                site_id,
                period,
                metric_code,
                value,
                'submitted_at is not a valid timestamp' AS reason
            FROM raw.readings
            WHERE try_cast(submitted_at AS TIMESTAMP) IS NULL
        """,
    ),
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
