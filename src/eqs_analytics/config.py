"""Paths and constants. You may edit anything in here."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
SQL_DIR = PROJECT_ROOT / "sql"
BUILD_DIR = PROJECT_ROOT / "build"
REPORTS_DIR = PROJECT_ROOT / "reports"

# A file-backed database rather than in-memory, so you can open build/eqs.duckdb
# in any SQL client and inspect what your pipeline produced.
DB_PATH = BUILD_DIR / "eqs.duckdb"

# Reporting boundary for the exercise.
REPORT_START = "2024-01"
REPORT_END = "2025-12"

# TRIR is conventionally expressed per 200,000 hours worked (100 FTE-years).
TRIR_BASIS = 200_000
