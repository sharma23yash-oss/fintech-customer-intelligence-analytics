import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from friction_detector import config as C
from friction_detector.config import EngineConfig

AS_OF = pd.Timestamp("2026-10-31")
# fixed windows so unit tests do not depend on the dataset
CFG_KW = dict(window_kyc_days=10, window_bank_days=7, window_deposit_days=14, window_trade_days=11,
              deposit_p50=5000.0, deposit_p75=20000.0, trading6m_p75=50000.0)


def make_cfg():
    return EngineConfig(**CFG_KW)


def user(uid="U1", reg="2026-09-01", kyc=None, bank=None, dep=None, trade=None, last=None, **kw):
    row = dict(user_id=uid, registration_date=reg, registration_month=(reg[:7] if reg else None), city="Pune",
               acquisition_channel="Organic", device_type="iOS", kyc_date_asof=kyc, bank_date_asof=bank,
               deposit_date_asof=dep, trade_date_asof=trade, first_deposit_amount_asof_inr=(1000.0 if dep else None),
               last_active_date_adj=last, total_trades=1 if trade else 0, total_trading_value_inr=0.0,
               total_deposit_value_inr=0.0, trading_value_6m_inr=0.0, trade_months_6m=0, active_months_6m=0,
               activity_ratio=0.0, flag_trade_conflict=0, flag_deposit_conflict=0, flag_last_active_conflict=0,
               flag_activity_conflict=0)
    row.update(kw)
    return row


def ticket(tid, uid, created, status="Resolved", hours=5.0, category="Bank linking"):
    return dict(ticket_id=tid, user_id=uid, created_date=created, category=category, priority="Medium",
                status=status, resolution_time_hours=(None if status != "Resolved" else hours), csat_score=None)


def run(users, tickets=None, as_of="2026-10-31", cfg=None, monthly=None):
    from friction_detector.engine import run_engine
    t = pd.DataFrame(tickets) if tickets else pd.DataFrame(
        columns=["ticket_id", "user_id", "created_date", "category", "priority", "status", "resolution_time_hours",
                 "csat_score"])
    cfg = cfg or make_cfg()
    watch = {0: 8, 1: 5, 2: 10, 3: 8}
    return run_engine(pd.DataFrame(users), t, as_of, cfg, monthly=monthly, watch=watch).set_index("user_id")


@pytest.fixture(scope="session")
def real():
    d = ROOT / "data" / "synthetic"
    from friction_detector.engine import derive_config, run_engine, watch_windows
    u, t, m = (pd.read_csv(d / f) for f in ("users.csv", "tickets.csv", "monthly_activity.csv"))
    cfg = derive_config(u, t)
    return dict(users=u, tickets=t, monthly=m, cfg=cfg,
                res=run_engine(u, t, C.SNAPSHOT_DATE, cfg, monthly=m, watch=watch_windows(u, cfg)))


@pytest.fixture()
def tmp_db(tmp_path):
    from friction_detector import db
    p = tmp_path / "t.db"
    db.build_database(db_path=p)
    return p
