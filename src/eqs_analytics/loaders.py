"""Raw ingestion. Provided for you - no changes required.

Everything lands in the ``raw`` schema as VARCHAR, deliberately. Source files
arrive from site portals and spreadsheets and are not type-safe; deciding how
to cast, coerce and reject values is your job, not the loader's.
"""

from __future__ import annotations

import duckdb

from .config import DATA_DIR

SOURCE_FILES = {
    "sites": "sites.csv",
    "metric_definitions": "metric_definitions.csv",
    "uom_conversions": "uom_conversions.csv",
    "readings": "readings.csv",
    "incidents": "incidents.csv",
}


def load_raw(con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    """Load every source CSV into raw.<name>. Returns row counts."""
    counts: dict[str, int] = {}
    for table, filename in SOURCE_FILES.items():
        path = DATA_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"Missing source file: {path}")
        con.execute(
            f"""
            CREATE OR REPLACE TABLE raw.{table} AS
            SELECT * FROM read_csv(
                ?,
                header = true,
                all_varchar = true,
                sample_size = -1
            )
            """,
            [str(path)],
        )
        counts[table] = con.execute(
            f"SELECT count(*) FROM raw.{table}"
        ).fetchone()[0]
    return counts
