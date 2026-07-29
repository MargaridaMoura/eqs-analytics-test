"""Pipeline entry point.

    python -m src.eqs_analytics.main

Feel free to restructure this. It is a starting point, not a contract.
"""

from __future__ import annotations

import logging
import sys

from .db import connect
from .kpis import build_kpis, export_kpis
from .loaders import load_raw
from .marts import build_marts
from .quality import RULES, run_rules, write_dq_report

log = logging.getLogger("eqs")


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )

    con = connect(fresh=True)

    counts = load_raw(con)
    for table, n in counts.items():
        log.info("loaded raw.%-20s %6d rows", table, n)

    dq = run_rules(con)
    write_dq_report(dq)
    failed = int(dq["rows_failed"].sum()) if len(dq) else 0
    log.info("data quality: %d rules, %d failing rows", len(RULES), failed)
    if len(RULES) <= 1:
        log.warning("only the example DQ rule is defined - see quality.py")

    built = build_marts(con)
    log.info("marts built from: %s", ", ".join(built) or "(nothing)")

    built = build_kpis(con)
    log.info("kpis built from: %s", ", ".join(built) or "(nothing)")

    export_kpis(con)
    log.info("reports written")

    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
