import numpy as np
import pandas as pd

from conftest import run, user, ticket
from friction_detector import config as C


def d(n):
    return (pd.Timestamp("2026-10-31") - pd.Timedelta(days=n)).strftime("%Y-%m-%d")


def test_score_bounds_and_labels(real):
    r = real["res"]
    f = r[r.is_flagged == 1]
    assert f.priority_score.between(0, 100).all()
    assert (r.loc[r.is_flagged == 0, "priority_score"] == 0).all()
    assert set(r.score_type) == {C.SCORE_TYPE}
    assert "NOT_a_probability" in C.SCORE_TYPE


def test_components_sum_to_score(real):
    r = real["res"]
    f = r[r.is_flagged == 1]
    cols = [c for c in r.columns if c.startswith("pts_")]
    assert len(cols) == 6
    assert ((f[cols].sum(axis=1).round(1) - f.priority_score).abs() < 0.06).all()


def test_band_thresholds():
    # High >= 55, Medium >= 35, otherwise Low
    rows = [user(f"U{i}", reg=d(100)) for i in range(1)]
    r = run(rows).loc["U0"]
    expected = "High" if r.priority_score >= 55 else "Medium" if r.priority_score >= 35 else "Low"
    assert r.priority_band == expected


def test_more_inactivity_scores_higher():
    base = dict(reg=d(200), kyc=d(195), bank=d(190), dep=d(185), trade=d(180))
    a = run([user("U1", last=d(40), **base)]).loc["U1"]
    b = run([user("U1", last=d(100), **base)]).loc["U1"]
    assert b.priority_score > a.priority_score and b.pts_inactivity > a.pts_inactivity


def test_inactivity_points_capped_at_20():
    base = dict(reg=d(400), kyc=d(395), bank=d(390), dep=d(385), trade=d(380))
    r = run([user("U1", last=d(380), **base)]).loc["U1"]
    assert r.pts_inactivity == 20


def test_escalated_ticket_adds_support_points_more_than_open():
    u = [user("U1", reg=d(60)), user("U2", reg=d(60))]
    t = [ticket("T1", "U1", d(10), "Escalated"), ticket("T2", "U2", d(10), "Open")]
    out = run(u, t)
    assert out.loc["U1", "pts_support"] > out.loc["U2", "pts_support"] > 0


def test_support_points_capped():
    t = [ticket(f"T{i}", "U1", d(100 + i), "Escalated") for i in range(6)]
    assert run([user("U1", reg=d(200))], t).loc["U1", "pts_support"] <= 20


def test_funded_stage_scores_highest_stage_points():
    f = run([user("U1", reg=d(60), kyc=d(55), bank=d(50), dep=d(40))]).loc["U1"]
    k = run([user("U1", reg=d(60))]).loc["U1"]
    assert f.pts_funnel_stage == 20 and k.pts_funnel_stage == 4


def test_score_is_deterministic():
    u = [user("U1", reg=d(60))]
    assert run(u).loc["U1", "priority_score"] == run(u).loc["U1", "priority_score"]
