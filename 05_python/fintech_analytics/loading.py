"""Data loading: Phase 2 cleaned CSVs (default) or the SQLite database."""
import sqlite3
import pandas as pd
from . import config as C


def load_users(path=None):
    return pd.read_csv(path or C.DATA_CLEAN / "Cleaned_Users.csv", parse_dates=C.DATE_COLS_USERS)


def load_activity(path=None):
    return pd.read_csv(path or C.DATA_CLEAN / "Cleaned_Monthly_Activity.csv")


def load_tickets(path=None):
    return pd.read_csv(path or C.DATA_CLEAN / "Cleaned_Support_Tickets.csv", parse_dates=["created_date"])


def load_campaigns(path=None):
    return pd.read_csv(path or C.DATA_CLEAN / "Cleaned_Campaigns.csv")


def load_all():
    """Return dict(users, activity, tickets, campaigns) from the cleaned CSVs."""
    return dict(users=load_users(), activity=load_activity(), tickets=load_tickets(), campaigns=load_campaigns())


def load_from_sqlite(db_path=None):
    """Return the four tables from the SQLite database built by 04_sql/build_database.py."""
    con = sqlite3.connect(db_path or C.DB_PATH)
    try:
        return {t: pd.read_sql_query(f"SELECT * FROM {t}", con) for t in ["users", "monthly_activity", "support_tickets", "campaigns"]}
    finally:
        con.close()


def mature(users):
    """Mature cohort: registered before 2026-10 (funnel_mature == 1)."""
    return users[users.funnel_mature == 1]
