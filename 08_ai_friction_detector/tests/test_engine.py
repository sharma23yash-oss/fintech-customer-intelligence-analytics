"""Rule-level tests on tiny hand-built customers (fixed windows: KYC 10, bank 7, deposit 14, trade 11)."""
import pandas as pd
import pytest

from conftest import run, user, ticket
from friction_detector import config as C


def d(days_ago):
    return (pd.Timestamp("2026-10-31") - pd.Timedelta(days=days_ago)).strftime("%Y-%m-%d")


@pytest.mark.parametrize("stage_kw,window,cat", [
    ({}, 10, "KYC_PENDING"),
    ({"kyc": "K"}, 7, "BANK_LINK_PENDING"),
    ({"kyc": "K", "bank": "K"}, 14, "FIRST_DEPOSIT_PENDING"),
    ({"kyc": "K", "bank": "K", "dep": "K"}, 11, "FIRST_TRADE_PENDING"),
])
def test_window_boundary(stage_kw, window, cat):
    """dwell == window is NOT flagged; dwell == window + 1 IS flagged (anchor = last completed step)."""
    order = ["kyc", "bank", "dep", "trade"]
    n = len(stage_kw)
    out = {}
    for dwell in (window - 1, window, window + 1):
        kw = {k: d(dwell + (n - 1 - i)) for i, k in enumerate(order[:n])}   # last completed step dated `dwell` days ago
        reg = d(dwell) if n == 0 else d(dwell + n + 5)
        out[dwell] = run([user("U1", reg=reg, **kw)]).loc["U1"]
    assert out[window - 1]["is_flagged"] == 0
    assert out[window]["is_flagged"] == 0 and out[window]["primary_category"] == "WITHIN_WINDOW"
    assert out[window + 1]["is_flagged"] == 1 and out[window + 1]["primary_category"] == cat
    assert out[window + 1]["days_overdue"] == 1


def test_new_registrant_not_flagged():
    r = run([user("U1", reg=d(0))]).loc["U1"]
    assert r["is_flagged"] == 0 and r["primary_category"] == C.WITHIN_WINDOW
    assert r["priority_score"] == 0 and r["priority_band"] == "NOT_FLAGGED"


def test_registered_after_as_of_excluded():
    out = run([user("U1", reg="2026-11-05"), user("U2", reg=d(30))])
    assert list(out.index) == ["U2"]


def test_completed_customer_no_friction():
    r = run([user("U1", reg=d(60), kyc=d(55), bank=d(50), dep=d(45), trade=d(40), last=d(5))]).loc["U1"]
    assert r["primary_category"] == C.NO_FRICTION and r["stage_idx"] == 4


def test_inactivity_boundaries():
    base = dict(reg=d(120), kyc=d(115), bank=d(110), dep=d(105), trade=d(100))
    assert run([user("U1", last=d(30), **base)]).loc["U1"]["is_flagged"] == 0          # 30 days: not flagged
    r = run([user("U1", last=d(31), **base)]).loc["U1"]                               # 31 days: flagged
    assert r["primary_category"] == "INACTIVITY_RISK" and r["days_inactive"] == 31


def test_inactivity_requires_tenure():
    # traded 10 days after registering, registered 20 days ago, last active = trade date -> tenure 20 < 31
    r = run([user("U1", reg=d(20), kyc=d(19), bank=d(18), dep=d(17), trade=d(15), last=d(15))]).loc["U1"]
    assert r["is_flagged"] == 0 and r["eligibility_status"] == "TOO_NEW_FOR_INACTIVITY_CHECK"


def test_last_active_in_future_treated_as_zero_days():
    r = run([user("U1", reg=d(100), kyc=d(95), bank=d(90), dep=d(85), trade=d(80), last="2026-12-01")]).loc["U1"]
    assert r["days_inactive"] == 0 and r["is_flagged"] == 0


def test_missing_last_active_falls_back_to_trade_date():
    r = run([user("U1", reg=d(100), kyc=d(95), bank=d(90), dep=d(85), trade=d(80), last=None)]).loc["U1"]
    assert r["days_inactive"] == 80 and r["primary_category"] == "INACTIVITY_RISK"


# ------------------------------------------------------------------ support rules
def test_ticket_created_today_not_flagged_unless_escalated():
    u = [user("U1", reg=d(5)), user("U2", reg=d(5))]
    t = [ticket("T1", "U1", d(0), "Open"), ticket("T2", "U2", d(0), "Escalated")]
    out = run(u, t)
    assert out.loc["U1", "friction_categories"] == ""            # open ticket inside 2-day grace
    assert out.loc["U2", "friction_categories"] == "SUPPORT_UNRESOLVED"


def test_open_ticket_after_grace_flagged():
    t = [ticket("T1", "U1", d(2), "Open"), ticket("T2", "U2", d(3), "Open")]
    out = run([user("U1", reg=d(20)), user("U2", reg=d(20))], t)
    assert out.loc["U1", "tickets_unresolved"] == 1 and "SUPPORT_UNRESOLVED" not in out.loc["U1", "friction_categories"]
    assert "SUPPORT_UNRESOLVED" in out.loc["U2", "friction_categories"]


def test_resolved_tickets_not_unresolved_but_count_toward_repeat():
    t = [ticket(f"T{i}", "U1", d(20 + i)) for i in range(3)]
    r = run([user("U1", reg=d(60))], t).loc["U1"]
    assert r["tickets_unresolved"] == 0 and "REPEATED_SUPPORT_ISSUES" in r["friction_categories"]


def test_two_tickets_not_repeated():
    t = [ticket(f"T{i}", "U1", d(20 + i)) for i in range(2)]
    assert "REPEATED" not in run([user("U1", reg=d(60))], t).loc["U1", "friction_categories"]


def test_ticket_after_as_of_ignored():
    t = [ticket("T1", "U1", "2026-11-03", "Escalated")]
    assert run([user("U1", reg=d(5))], t).loc["U1", "tickets_total"] == 0


def test_resolved_after_as_of_counts_as_unresolved_in_replay():
    # created 5 days before as-of, resolved 10 days later -> still open at as-of
    t = [ticket("T1", "U1", d(5), "Resolved", hours=240)]
    assert run([user("U1", reg=d(20))], t).loc["U1", "tickets_unresolved"] == 1


# ------------------------------------------------------------------ multi-label and precedence
def test_multi_label_and_primary_precedence():
    t = [ticket("T1", "U1", d(10), "Escalated")]
    r = run([user("U1", reg=d(60))], t).loc["U1"]
    assert r["friction_categories"] == "KYC_PENDING|SUPPORT_UNRESOLVED"
    assert r["primary_category"] == "KYC_PENDING"


def test_inactive_trader_with_support_issue_primary_is_inactivity():
    t = [ticket("T1", "U1", d(10), "Escalated")]
    r = run([user("U1", reg=d(150), kyc=d(145), bank=d(140), dep=d(135), trade=d(130), last=d(90))], t).loc["U1"]
    assert r["primary_category"] == "INACTIVITY_RISK" and "SUPPORT_UNRESOLVED" in r["friction_categories"]


# ------------------------------------------------------------------ messy input
def test_out_of_order_dates_flagged_as_anomaly_not_crash():
    r = run([user("U1", reg=d(60), kyc=d(30), bank=d(40))]).loc["U1"]      # bank before KYC
    assert r["sequence_anomaly"] == 1


def test_bank_without_kyc_does_not_advance_stage():
    r = run([user("U1", reg=d(60), bank=d(40))]).loc["U1"]
    assert r["stage_idx"] == 0 and r["primary_category"] == "KYC_PENDING"


def test_duplicates_and_missing_values_handled():
    rows = [user("U1", reg=d(60)), user("U1", reg=d(60)), user(None, reg=d(10)),
            user("U2", reg=None), user("U3", reg=d(30), city=None)]
    out = run(rows)
    assert set(out.index) == {"U1", "U3"}
    assert out.loc["U3", "city"] == "Unknown"
    assert out.attrs["data_quality"]["duplicate_user_rows_dropped"] == 1


def test_invalid_date_string_treated_as_not_completed():
    r = run([user("U1", reg=d(60), kyc="not-a-date")]).loc["U1"]
    assert r["stage_idx"] == 0
    assert run([user("U1", reg=d(60), kyc="not-a-date")]).attrs["data_quality"]["unparseable_kyc_date_asof"] == 1


def test_no_tickets_and_no_monthly_log():
    r = run([user("U1", reg=d(60))], tickets=None, monthly=None).loc["U1"]
    assert r["tickets_total"] == 0 and r["data_confidence"] in ("HIGH", "LOW")


def test_empty_users_returns_empty():
    from friction_detector.engine import run_engine
    from conftest import make_cfg
    out = run_engine(pd.DataFrame([user("U1", reg="2027-01-01")]), pd.DataFrame(), "2026-10-31", make_cfg(),
                     watch={0: 8, 1: 5, 2: 10, 3: 8})
    assert len(out) == 0


# ------------------------------------------------------------------ data confidence
def test_low_confidence_when_log_has_trades_without_recorded_trade():
    m = pd.DataFrame([dict(user_id="U1", activity_month="2026-09", active_in_month=1, trade_count=2,
                           trading_value_inr=100.0, deposit_value_inr=0.0, withdrawal_value_inr=0.0)])
    r = run([user("U1", reg=d(60), kyc=d(55), bank=d(50), dep=d(45))], monthly=m).loc["U1"]
    assert r["primary_category"] == "FIRST_TRADE_PENDING" and r["data_confidence"] == "LOW"
    assert "trades" in r["conflict_detail"]


def test_high_confidence_without_conflict():
    r = run([user("U1", reg=d(60))]).loc["U1"]
    assert r["data_confidence"] == "HIGH"


def test_support_categories_always_high_confidence():
    t = [ticket("T1", "U1", d(10), "Escalated")]
    r = run([user("U1", reg=d(60), kyc=d(55), bank=d(50), dep=d(45), trade=d(40), last=d(3))], t).loc["U1"]
    assert r["primary_category"] == "SUPPORT_UNRESOLVED" and r["data_confidence"] == "HIGH"


# ------------------------------------------------------------------ replay
def test_replay_earlier_date_shrinks_population_and_stage():
    u = user("U1", reg="2026-10-01", kyc="2026-10-05", bank="2026-10-08")
    early = run([u], as_of="2026-10-06").loc["U1"]
    late = run([u], as_of="2026-10-31").loc["U1"]
    assert early["stage_idx"] == 1 and late["stage_idx"] == 2
