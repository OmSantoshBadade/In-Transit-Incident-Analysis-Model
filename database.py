"""
database.py
Persists cleaned incident rows to SQLite, keyed by FIR NUMBER, so that
uploading a new year's file adds to the history instead of overwriting it.
Re-uploading the same file (or overlapping rows) safely upserts rather than
duplicating.
"""

import sqlite3
import pandas as pd

DB_PATH = "incident_data.db"
TABLE = "incidents"


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    return sqlite3.connect(db_path)


def upsert_dataframe(df: pd.DataFrame, db_path: str = DB_PATH) -> int:
    """Insert new rows / replace rows with a matching FIR NUMBER.
    Returns the number of rows written."""
    conn = get_connection(db_path)
    try:
        existing_cols = set()
        try:
            existing_cols = {
                r[1] for r in conn.execute(f"PRAGMA table_info({TABLE})").fetchall()
            }
        except Exception:
            pass

        # Make sure every column df needs exists in the table (SQLite is
        # schema-flexible enough that we can just let pandas create/extend it).
        if not existing_cols:
            df.to_sql(TABLE, conn, if_exists="replace", index=False)
            conn.execute(f'CREATE UNIQUE INDEX IF NOT EXISTS idx_fir ON {TABLE}("FIR NUMBER")')
            conn.commit()
            return len(df)

        # Upsert: delete any existing rows with the same FIR NUMBER, then append.
        fir_numbers = tuple(df["FIR NUMBER"].astype(str).tolist())
        if fir_numbers:
            placeholders = ",".join(["?"] * len(fir_numbers))
            conn.execute(
                f'DELETE FROM {TABLE} WHERE "FIR NUMBER" IN ({placeholders})', fir_numbers
            )
        df.to_sql(TABLE, conn, if_exists="append", index=False)
        conn.commit()
        return len(df)
    finally:
        conn.close()


def load_all(db_path: str = DB_PATH) -> pd.DataFrame:
    conn = get_connection(db_path)
    try:
        try:
            df = pd.read_sql(f"SELECT * FROM {TABLE}", conn)
        except Exception:
            return pd.DataFrame()
    finally:
        conn.close()
    # Restore datetime dtypes lost on the SQLite round-trip
    for c in df.columns:
        if c.endswith("_PARSED"):
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def delete_all_data(db_path: str = DB_PATH) -> None:
    """Delete all stored incident rows and remove the SQLite table."""
    conn = get_connection(db_path)
    try:
        conn.execute(f"DROP TABLE IF EXISTS {TABLE}")
        conn.commit()
    finally:
        conn.close()


def clear_all(db_path: str = DB_PATH) -> None:
    """Backward-compatible wrapper for resetting stored data."""
    delete_all_data(db_path)


def summary_stats(db_path: str = DB_PATH) -> dict:
    df = load_all(db_path)
    if df.empty:
        return {"total_incidents": 0, "years": [], "total_rows": 0}
    return {
        "total_incidents": len(df),
        "years": sorted(df["FINANCIAL_YEAR"].dropna().unique().tolist()),
        "total_rows": len(df),
    }
