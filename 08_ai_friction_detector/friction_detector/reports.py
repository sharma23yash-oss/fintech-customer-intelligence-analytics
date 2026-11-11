"""Daily automation: run the engine, find newly flagged customers, write CSV + markdown reports.

Safe by design: this module only reads the database and writes files under outputs/. It does not
send messages, call any customer channel, or trigger trades, deposits or withdrawals.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from . import config as C
from . import db
from .engine import run_engine
from .insights import (LLMConfig, daily_operational_summary, explain_customer, llm_rewrite,
                       safe_daily_payload)

REPORT_COLS = ["data_label", "user_id", "primary_category", "friction_categories", "priority_band", "priority_score",
               "score_type", "stage_name", "days_overdue", "days_inactive", "tickets_unresolved", "tickets_escalated",
               "data_confidence", "owner_team", "recommended_intervention", "is_new_today", "first_flagged_in_stored_runs",
               "city", "acquisition_channel", "registration_date"]


def _csv_safe(df: pd.DataFrame) -> pd.DataFrame:
    """Neutralise spreadsheet formula injection in text cells (defence in depth)."""
    out = df.copy()
    for c in out.columns:
        if out[c].dtype == object or str(out[c].dtype).startswith("str"):
            out[c] = out[c].map(lambda v: "'" + v if isinstance(v, str) and v[:1] in ("=", "+", "-", "@") else v)
    return out


def previous_run(conn, run_date: str) -> str | None:
    r = conn.execute("SELECT MAX(run_date) FROM friction_runs WHERE run_date < ?", (run_date,)).fetchone()
    return r[0] if r and r[0] else None


def build_stats(df: pd.DataFrame, run_date: str, prev: str | None, new_ids: set, dropped: int) -> dict:
    f = df[df["is_flagged"] == 1]
    by_cat = list(f["primary_category"].value_counts().items())
    newf = f[f["user_id"].isin(new_ids)]
    pr = f["priority_band"].value_counts()
    top_cat = by_cat[0][0] if by_cat else None
    return {
        "run_date": run_date, "previous_run_date": prev, "analysed": int(len(df)), "flagged": int(len(f)),
        "flagged_pct": float(len(f) / max(len(df), 1) * 100), "high_priority": int(pr.get("High", 0)),
        "newly_flagged": int(len(newf)), "no_longer_flagged": int(dropped),
        "by_category": [(k, int(v)) for k, v in by_cat],
        "new_by_category": [(k, int(v)) for k, v in newf["primary_category"].value_counts().items()],
        "priority": {k: int(pr.get(k, 0)) for k in ("High", "Medium", "Low")},
        "by_team": [(k, int(v)) for k, v in f["owner_team"].value_counts().items()] if "owner_team" in f else [],
        "verify_first": int((f["data_confidence"] == "LOW").sum()),
        "verify_first_pct": float((f["data_confidence"] == "LOW").mean() * 100) if len(f) else 0.0,
        "support_unresolved_old": int((f["oldest_unresolved_days"] > 90).sum()),
        "avg_overdue_top": float(f.loc[f["primary_category"] == top_cat, "days_overdue"].mean()) if top_cat else 0.0,
    }


def run_daily(db_path=C.DB_PATH, as_of: str = C.SNAPSHOT_DATE, out_root=C.OUTPUT_DIR, use_llm: bool = False) -> dict:
    """Run one day: detect, compare with the previous stored run, store snapshot, write reports."""
    conn = db.connect(db_path)
    users, tickets, monthly = db.load_inputs(conn)
    cfg, watch = db.load_config_from_db(conn)
    df = run_engine(users, tickets, as_of, cfg, monthly=monthly, watch=watch)
    df["owner_team"] = df["primary_category"].map(C.OWNER_TEAM).fillna("")
    cfg_dict = cfg.to_dict()
    flagged = df[df["is_flagged"] == 1]
    df["recommended_intervention"] = ""
    idx = flagged.index
    df.loc[idx, "recommended_intervention"] = [explain_customer(row, cfg_dict)["recommended_intervention"]
                                               for row in flagged.to_dict("records")]

    prev = previous_run(conn, as_of)
    prev_ids: set = set()
    prev_cat: dict = {}
    if prev:
        p = pd.read_sql("SELECT user_id, primary_category FROM friction_snapshot WHERE run_date = ?", conn, params=(prev,))
        prev_ids = set(p["user_id"])
        prev_cat = dict(zip(p["user_id"], p["primary_category"]))
    today_ids = set(flagged["user_id"])
    new_ids = (today_ids - prev_ids) if prev else set()
    dropped = len(prev_ids - today_ids) if prev else 0
    changed = sum(1 for u, c in zip(flagged["user_id"], flagged["primary_category"])
                  if u in prev_cat and prev_cat[u] != c)

    first_seen = pd.read_sql("SELECT user_id, MIN(run_date) AS first_flagged_in_stored_runs FROM friction_snapshot "
                             "WHERE run_date <= ? GROUP BY user_id", conn, params=(as_of,))
    df = df.merge(first_seen, on="user_id", how="left")
    df["first_flagged_in_stored_runs"] = df["first_flagged_in_stored_runs"].where(df["is_flagged"] == 0, df["first_flagged_in_stored_runs"].fillna(as_of))
    df["is_new_today"] = df["user_id"].isin(new_ids).astype(int)

    stats = build_stats(df, as_of, prev, new_ids, dropped)
    stats["category_changed"] = changed
    summary = daily_operational_summary(stats)
    llm_used = False
    if use_llm:
        summary, llm_used = llm_rewrite("daily summary", safe_daily_payload(stats), summary, LLMConfig.from_env())

    db.save_run(conn, df, as_of, prev, len(new_ids), dropped, llm_used,
                note="baseline run" if not prev else "")
    conn.close()

    out = Path(out_root) / as_of
    (out / "by_category").mkdir(parents=True, exist_ok=True)
    rep = df[df["is_flagged"] == 1].sort_values(["priority_score", "days_overdue"], ascending=[False, False])
    rep = rep.reindex(columns=REPORT_COLS)
    _csv_safe(rep).to_csv(out / "exception_report.csv", index=False)
    _csv_safe(rep[rep["is_new_today"] == 1]).to_csv(out / "newly_flagged.csv", index=False)
    for cat, g in rep.groupby("primary_category"):
        _csv_safe(g).to_csv(out / "by_category" / f"{cat}.csv", index=False)
    summ = (rep.groupby("primary_category")
            .agg(customers=("user_id", "size"), high=("priority_band", lambda s: int((s == "High").sum())),
                 medium=("priority_band", lambda s: int((s == "Medium").sum())),
                 low=("priority_band", lambda s: int((s == "Low").sum())),
                 newly_flagged=("is_new_today", "sum"),
                 verify_first=("data_confidence", lambda s: int((s == "LOW").sum())),
                 avg_priority_score=("priority_score", "mean"))
            .round(1).sort_values("customers", ascending=False).reset_index())
    summ.insert(0, "data_label", "SYNTHETIC")
    summ.to_csv(out / "summary_by_category.csv", index=False)
    (out / "daily_summary.md").write_text(summary + "\n")
    manifest = {"run_date": as_of, "previous_run_date": prev, "synthetic": True, "llm_used": llm_used,
                "customers_analysed": stats["analysed"], "customers_flagged": stats["flagged"],
                "newly_flagged": stats["newly_flagged"], "no_longer_flagged": dropped,
                "category_changed": changed,
                "files": ["exception_report.csv", "newly_flagged.csv", "summary_by_category.csv",
                          "daily_summary.md", "by_category/*.csv"],
                "safety": "Reports only. No customer messages were sent; no trades, deposits or withdrawals were initiated."}
    (out / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return {"stats": stats, "out_dir": str(out), "manifest": manifest, "df": df}


def replay(db_path=C.DB_PATH, start: str = "2026-10-24", end: str = C.SNAPSHOT_DATE,
           out_root=C.OUTPUT_DIR) -> list[dict]:
    """Run consecutive days oldest to newest so each day can be compared with the one before."""
    res = []
    for d in pd.date_range(start, end, freq="D"):
        res.append(run_daily(db_path, d.strftime("%Y-%m-%d"), out_root)["stats"])
    return res
