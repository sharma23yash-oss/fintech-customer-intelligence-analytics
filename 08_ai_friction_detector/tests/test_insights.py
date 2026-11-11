import json

import pandas as pd
import pytest

from conftest import run, user, ticket
from friction_detector import insights as I


def d(n):
    return (pd.Timestamp("2026-10-31") - pd.Timedelta(days=n)).strftime("%Y-%m-%d")


def row(**kw):
    return run([user("U900001", reg=d(60), **kw)], [ticket("T1", "U900001", d(10), "Escalated")]).loc["U900001"].to_dict()


def test_explanation_has_reason_intervention_owner_and_disclaimer():
    e = I.explain_customer(row())
    assert e["why_flagged"] and e["recommended_intervention"] and e["owner_team"]
    assert "Synthetic" in e["disclaimer"] and "heuristic" in e["disclaimer"] and e["mode"] == "rule-based"


def test_explanation_quotes_actual_rule_values():
    r = row()
    e = I.explain_customer(r)
    text = " ".join(e["why_flagged"])
    assert str(int(r["window_days"])) in text and str(int(r["dwell_days"])) in text


def test_stale_cases_get_stronger_intervention():
    fresh = I.explain_customer(run([user("U1", reg=d(15))]).loc["U1"].to_dict())
    stale = I.explain_customer(run([user("U1", reg=d(200))]).loc["U1"].to_dict())
    assert fresh["recommended_intervention"] != stale["recommended_intervention"]


def test_unflagged_customer_gets_not_flagged_message():
    e = I.explain_customer(run([user("U1", reg=d(2))]).loc["U1"].to_dict())
    assert "Not flagged" in e["summary"] and "inside" in " ".join(e["why_flagged"])


def test_low_confidence_note_tells_ops_to_verify():
    m = pd.DataFrame([dict(user_id="U1", activity_month="2026-09", active_in_month=1, trade_count=2,
                           trading_value_inr=1.0, deposit_value_inr=0.0, withdrawal_value_inr=0.0)])
    r = run([user("U1", reg=d(60), kyc=d(55), bank=d(50), dep=d(45))], monthly=m).loc["U1"].to_dict()
    assert any("Verify" in n for n in I.explain_customer(r)["notes"])


def test_every_category_has_intervention_and_label():
    from friction_detector import config as C
    for c in C.FLAGGED_CATEGORIES:
        assert I.INTERVENTIONS[c]["action"] and I.CATEGORY_LABEL[c]


def test_intervention_never_promises_money_or_trades():
    for v in I.INTERVENTIONS.values():
        for t in v.values():
            assert "guarantee" not in t.lower() and "bonus" not in t.lower()


# ------------------------------------------------------------------ privacy of the optional LLM path
def test_customer_payload_is_whitelisted_and_deidentified():
    r = row()
    p = I.safe_customer_payload(r, I.explain_customer(r))
    assert set(p) <= set(I.ALLOWED_CUSTOMER_FIELDS)
    blob = json.dumps(p)
    assert "U900001" not in blob and "Pune" not in blob and "Organic" not in blob
    assert "2026" not in blob            # no dates


def test_payload_guard_rejects_extra_fields_and_ids():
    with pytest.raises(ValueError):
        I.assert_payload_safe({"user_id": "U100001"}, I.ALLOWED_CUSTOMER_FIELDS)
    with pytest.raises(ValueError):
        I.assert_payload_safe({"friction_category": "U100001 is stuck"}, I.ALLOWED_CUSTOMER_FIELDS)


def test_daily_payload_suppresses_small_cells():
    stats = dict(analysed=10000, newly_flagged=42, by_category=[("KYC_PENDING", 2831), ("X", 3)],
                 priority={"High": 2, "Medium": 50, "Low": 70})
    p = I.safe_daily_payload(stats)
    assert p["category_counts"]["X"] == "<5" and p["priority_counts"]["High"] == "<5"


def test_llm_disabled_without_key_uses_fallback(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    text, used = I.llm_rewrite("x", {"a": 1}, "fallback text")
    assert text == "fallback text" and used is False


def test_llm_with_mock_transport_is_used_and_receives_only_payload(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    monkeypatch.delenv("FRICTION_DISABLE_LLM", raising=False)
    seen = {}

    def fake(cfg, body):
        seen["body"] = json.dumps(body)
        return {"content": [{"type": "text", "text": "reworded"}]}

    r = row()
    payload = I.safe_customer_payload(r, I.explain_customer(r))
    text, used = I.llm_rewrite("customer", payload, "draft", transport=fake)
    assert (text, used) == ("reworded", True)
    assert "U900001" not in seen["body"] and "Pune" not in seen["body"]


def test_llm_failure_falls_back(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")

    def boom(cfg, body):
        raise OSError("network down")

    text, used = I.llm_rewrite("x", {"a": 1}, "fallback", transport=boom)
    assert (text, used) == ("fallback", False)


def test_llm_empty_response_falls_back(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    text, used = I.llm_rewrite("x", {}, "fallback", transport=lambda c, b: {"content": []})
    assert (text, used) == ("fallback", False)


def test_kill_switch(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    monkeypatch.setenv("FRICTION_DISABLE_LLM", "1")
    assert I.LLMConfig.from_env().available is False


def test_daily_summary_mentions_baseline_and_caveats():
    s = dict(run_date="2026-10-31", analysed=10, flagged=5, flagged_pct=50.0, high_priority=1, previous_run_date=None,
             newly_flagged=0, no_longer_flagged=0, by_category=[("KYC_PENDING", 5)], new_by_category=[],
             priority={"High": 1, "Medium": 2, "Low": 2}, by_team=[("Onboarding", 5)], verify_first=2,
             verify_first_pct=40.0, support_unresolved_old=0, avg_overdue_top=50)
    text = I.daily_operational_summary(s)
    assert "baseline" in text and "SYNTHETIC" in text and "Verify" in text and "not send messages" in text
