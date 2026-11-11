"""Database + daily workflow + dashboard smoke tests (use a temporary database)."""
import csv
import json

import pandas as pd
import pytest

from friction_detector import db, reports


def test_build_db_row_counts_and_views(tmp_db):
    conn = db.connect(tmp_db)
    assert conn.execute("select count(*) from users").fetchone()[0] == 10000
    assert conn.execute("select count(*) from tickets").fetchone()[0] == 7614
    assert conn.execute("select count(*) from config where key='data_label'").fetchone()[0] == 1
    names = {r[0] for r in conn.execute("select name from sqlite_master where type in ('table','view')")}
    assert {"users", "tickets", "customer_friction", "friction_snapshot", "friction_runs", "v_flagged",
            "v_category_summary"} <= names


def test_config_roundtrip(tmp_db):
    from friction_detector.engine import derive_config
    conn = db.connect(tmp_db)
    cfg, watch = db.load_config_from_db(conn)
    users, tickets, _ = db.load_inputs(conn)
    fresh = derive_config(users, tickets)
    assert cfg.windows() == fresh.windows() and cfg.deposit_p75 == pytest.approx(fresh.deposit_p75)
    assert set(watch) == {0, 1, 2, 3}


def test_daily_run_writes_expected_files(tmp_db, tmp_path):
    out = tmp_path / "rep"
    res = reports.run_daily(tmp_db, "2026-10-31", out)
    day = out / "2026-10-31"
    for f in ("exception_report.csv", "newly_flagged.csv", "summary_by_category.csv", "daily_summary.md",
              "run_manifest.json"):
        assert (day / f).exists(), f
    assert (day / "by_category" / "KYC_PENDING.csv").exists()
    m = json.loads((day / "run_manifest.json").read_text())
    assert m["synthetic"] is True and "No customer messages were sent" in m["safety"]
    rows = list(csv.DictReader(open(day / "exception_report.csv")))
    assert len(rows) == m["customers_flagged"] == res["stats"]["flagged"]
    assert {r["data_label"] for r in rows} == {"SYNTHETIC"}
    assert {r["score_type"] for r in rows} == {"heuristic_priority_score_NOT_a_probability"}
    scores = [float(r["priority_score"]) for r in rows]
    assert scores == sorted(scores, reverse=True)


def test_first_run_is_baseline_with_no_new_flags(tmp_db, tmp_path):
    res = reports.run_daily(tmp_db, "2026-10-30", tmp_path)
    assert res["stats"]["newly_flagged"] == 0 and res["stats"]["previous_run_date"] is None


def test_newly_flagged_equals_set_difference(tmp_db, tmp_path):
    reports.run_daily(tmp_db, "2026-10-30", tmp_path)
    res = reports.run_daily(tmp_db, "2026-10-31", tmp_path)
    conn = db.connect(tmp_db)
    a = {r[0] for r in conn.execute("select user_id from friction_snapshot where run_date='2026-10-30'")}
    b = {r[0] for r in conn.execute("select user_id from friction_snapshot where run_date='2026-10-31'")}
    new = pd.read_csv(tmp_path / "2026-10-31" / "newly_flagged.csv")
    assert set(new["user_id"]) == b - a and len(new) == res["stats"]["newly_flagged"] > 0
    assert res["stats"]["no_longer_flagged"] == len(a - b)
    # every newly flagged customer really was not flagged the day before
    assert not (set(new["user_id"]) & a)


def test_rerun_same_day_is_idempotent(tmp_db, tmp_path):
    reports.run_daily(tmp_db, "2026-10-30", tmp_path)
    r1 = reports.run_daily(tmp_db, "2026-10-31", tmp_path)["stats"]
    r2 = reports.run_daily(tmp_db, "2026-10-31", tmp_path)["stats"]
    assert r1["flagged"] == r2["flagged"] and r1["newly_flagged"] == r2["newly_flagged"]
    conn = db.connect(tmp_db)
    assert conn.execute("select count(*) from friction_runs where run_date='2026-10-31'").fetchone()[0] == 1
    assert conn.execute("select count(*) from friction_snapshot where run_date='2026-10-31'").fetchone()[0] == r2["flagged"]


def test_category_csvs_partition_the_exception_report(tmp_db, tmp_path):
    reports.run_daily(tmp_db, "2026-10-31", tmp_path)
    day = tmp_path / "2026-10-31"
    total = pd.read_csv(day / "exception_report.csv")
    parts = sum(len(pd.read_csv(p)) for p in (day / "by_category").glob("*.csv"))
    assert parts == len(total)


def test_csv_formula_injection_neutralised():
    df = pd.DataFrame({"a": ["=SUM(1)", "+cmd", "@x", "-1+1", "safe", None]})
    out = reports._csv_safe(df)["a"].tolist()
    assert out[:4] == ["'=SUM(1)", "'+cmd", "'@x", "'-1+1"] and out[4] == "safe"


def test_database_user_data_not_modified_by_runs(tmp_db, tmp_path):
    before = pd.read_sql("select * from users order by user_id", db.connect(tmp_db))
    reports.run_daily(tmp_db, "2026-10-31", tmp_path)
    after = pd.read_sql("select * from users order by user_id", db.connect(tmp_db))
    assert before.equals(after)


def test_streamlit_app_smoke():
    from streamlit.testing.v1 import AppTest
    from friction_detector import config as C
    if not C.DB_PATH.exists():
        pytest.skip("db/friction.db not built")
    at = AppTest.from_file(str(C.PROJECT_DIR / "app" / "streamlit_app.py"), default_timeout=90).run()
    assert not at.exception
    labels = [m.label for m in at.metric]
    assert "Customers analysed" in labels and "Customers flagged" in labels
    for view in ("Customer lookup", "Daily report", "Method & limits"):
        at.sidebar.radio[0].set_value(view).run()
        assert not at.exception, view
    at.sidebar.radio[0].set_value("Customer lookup").run()
    at.text_input[0].set_value("U999999").run()
    assert any("No customer" in e.value for e in at.error)
    at.text_input[0].set_value("u100109").run()          # lower case accepted
    assert not at.exception and not at.error
