"""SQLite layer: build the database from the synthetic CSVs, read inputs, save engine runs."""
from __future__ import annotations

import datetime as dt
import json
import sqlite3
from pathlib import Path

import pandas as pd

from . import config as C
from .engine import derive_config, watch_windows

PERSIST_COLS = [
    "user_id", "as_of_date", "registration_date", "registration_month", "city", "acquisition_channel",
    "stage_idx", "stage_name", "journey_status", "anchor_event", "anchor_date", "dwell_days", "window_days",
    "days_overdue", "tenure_days", "days_inactive", "eligibility_status", "friction_categories",
    "primary_category", "is_flagged", "tickets_total", "tickets_unresolved", "tickets_escalated",
    "oldest_unresolved_days", "source_conflict_relevant", "conflict_detail", "data_confidence",
    "sequence_anomaly", "pts_days_since_registration", "pts_funnel_stage", "pts_inactivity", "pts_support",
    "pts_activity", "pts_prior_transactions", "priority_score", "priority_band", "score_type", "data_label",
]


def connect(db_path: Path | str = C.DB_PATH) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def build_database(data_dir: Path | str = C.DATA_DIR, db_path: Path | str = C.DB_PATH,
                   schema_path: Path | str = C.SCHEMA_SQL) -> dict:
    """(Re)create the database and load the three synthetic input tables. Returns row counts."""
    db_path = Path(db_path)
    if db_path.exists():
        db_path.unlink()
    conn = connect(db_path)
    conn.executescript(Path(schema_path).read_text())
    data_dir = Path(data_dir)
    users = pd.read_csv(data_dir / "users.csv")
    tickets = pd.read_csv(data_dir / "tickets.csv")
    monthly = pd.read_csv(data_dir / "monthly_activity.csv")
    users.to_sql("users", conn, if_exists="append", index=False)
    tickets.to_sql("tickets", conn, if_exists="append", index=False)
    monthly.to_sql("monthly_activity", conn, if_exists="append", index=False)
    cfg = derive_config(users, tickets)
    watch = watch_windows(users, cfg)
    rows = [(k, json.dumps(v) if not isinstance(v, (int, float, str)) else str(v), "engine configuration")
            for k, v in cfg.to_dict().items()]
    rows += [(f"watch_window_stage_{s}", str(w), "75th percentile lag: WATCH band start (not flagged)")
             for s, w in watch.items()]
    rows += [("snapshot_date", C.SNAPSHOT_DATE, "last day covered by the synthetic dataset"),
             ("data_label", "SYNTHETIC", "all records are synthetic")]
    conn.executemany("INSERT OR REPLACE INTO config(key, value, note) VALUES (?,?,?)", rows)
    conn.commit()
    counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ("users", "tickets", "monthly_activity", "config")}
    conn.close()
    return counts


def load_inputs(conn: sqlite3.Connection) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    users = pd.read_sql("SELECT * FROM users", conn)
    tickets = pd.read_sql("SELECT * FROM tickets", conn)
    monthly = pd.read_sql("SELECT * FROM monthly_activity", conn)
    return users, tickets, monthly


def load_config_from_db(conn: sqlite3.Connection):
    """Rebuild the EngineConfig stored at build time (so runs use identical, auditable parameters)."""
    from .config import EngineConfig
    kv = dict(conn.execute("SELECT key, value FROM config").fetchall())
    cfg = EngineConfig()
    for k in cfg.to_dict():
        if k in kv and kv[k] not in ("None", None):
            cur = getattr(cfg, k)
            raw = kv[k]
            try:
                setattr(cfg, k, type(cur)(float(raw)) if isinstance(cur, float) else int(float(raw)))
            except (TypeError, ValueError):
                pass
    for k in ("window_kyc_days", "window_bank_days", "window_deposit_days", "window_trade_days"):
        if k in kv:
            setattr(cfg, k, int(float(kv[k])))
    for k in ("deposit_p50", "deposit_p75", "trading6m_p75"):
        if k in kv:
            setattr(cfg, k, float(kv[k]))
    watch = {s: int(kv[f"watch_window_stage_{s}"]) for s in range(4) if f"watch_window_stage_{s}" in kv}
    return cfg, watch


def save_run(conn: sqlite3.Connection, df: pd.DataFrame, run_date: str, previous_run_date: str | None,
             newly: int, dropped: int, llm_used: bool, note: str = "") -> None:
    out = df[PERSIST_COLS].copy()
    for c in ("anchor_date", "registration_date"):
        out[c] = pd.to_datetime(out[c]).dt.strftime("%Y-%m-%d")
    conn.execute("DELETE FROM customer_friction")
    out.to_sql("customer_friction", conn, if_exists="append", index=False)
    conn.execute("DELETE FROM friction_snapshot WHERE run_date = ?", (run_date,))
    snap = df.loc[df["is_flagged"] == 1, ["user_id", "primary_category", "friction_categories",
                                           "priority_score", "priority_band"]].copy()
    snap.insert(0, "run_date", run_date)
    snap.to_sql("friction_snapshot", conn, if_exists="append", index=False)
    conn.execute(
        "INSERT OR REPLACE INTO friction_runs VALUES (?,?,?,?,?,?,?,?,?)",
        (run_date, dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), int(len(df)),
         int(df["is_flagged"].sum()), int(newly), int(dropped), previous_run_date, int(llm_used), note))
    conn.commit()
