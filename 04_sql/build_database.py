"""Builds 04_sql/fintech_analytics.db (SQLite) from the Phase 2 cleaned CSVs. SYNTHETIC DATA.
Run: python3 build_database.py        Idempotent: deletes and recreates the database."""
import sqlite3
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CL, DB = ROOT / "data" / "cleaned", ROOT / "04_sql" / "fintech_analytics.db"
if DB.exists():
    DB.unlink()
con = sqlite3.connect(DB)
con.executescript((ROOT / "04_sql" / "schema.sql").read_text())


def load(table, csv):
    cols = [r[1] for r in con.execute(f"PRAGMA table_info({table})")]
    df = pd.read_csv(CL / csv, usecols=lambda c: c in cols)
    df = df[[c for c in cols if c in df.columns]]
    for c in df.columns:                         # dates -> ISO text
        if c.endswith("_date") or c.endswith("_date_asof"):
            df[c] = pd.to_datetime(df[c]).dt.strftime("%Y-%m-%d")
        if c in ("activity_month", "registration_month", "created_month"):
            df[c] = df[c].astype(str).str[:7]
    df = df.astype(object).where(df.notna(), None)
    ph = ",".join("?" * len(df.columns))
    con.executemany(f"INSERT INTO {table} ({','.join(df.columns)}) VALUES ({ph})", df.itertuples(index=False, name=None))
    return len(df)


# Order respects foreign keys
n = {t: load(t, c) for t, c in [("campaigns", "Cleaned_Campaigns.csv"), ("users", "Cleaned_Users.csv"),
                                ("monthly_activity", "Cleaned_Monthly_Activity.csv"), ("support_tickets", "Cleaned_Support_Tickets.csv")]}
con.commit()
fk = con.execute("PRAGMA foreign_key_check").fetchall()
con.execute("ANALYZE"); con.close()
print("rows:", n, "| foreign-key violations:", len(fk), "| size MB:", round(DB.stat().st_size / 1e6, 1))
assert not fk and n == {"campaigns": 10, "users": 10000, "monthly_activity": 64645, "support_tickets": 7614}
