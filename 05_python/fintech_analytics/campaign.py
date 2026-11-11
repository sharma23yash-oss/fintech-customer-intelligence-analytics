"""Campaign analysis: CAC, cost per first trader at maturity, quality, ranking. Organic CAC is NULL (no recorded spend)."""
import numpy as np
import pandas as pd
from .eda import style, BLUE, GREY, INK, ORANGE
import matplotlib.pyplot as plt


def campaign_scorecard(users, campaigns):
    g = users.groupby("acquisition_campaign_id")
    m = users[users.funnel_mature == 1].groupby("acquisition_campaign_id")
    t = campaigns.set_index("campaign_id")[["campaign_name", "channel", "campaign_spend_inr", "is_paid"]].copy()
    t["registered_users"] = g.size()
    t["mature_users"] = m.size()
    t["first_trade_rate_mature_pct"] = 100 * m.trade_asof.mean()
    t["kyc_rate_mature_pct"] = 100 * m.kyc_asof.mean()
    t["m3_retention_pct"] = 100 * g.m3_retained.mean()
    t["dormant_3m_pct"] = 100 * g.dormant_3m_monthly.mean()
    paid = t.is_paid == 1
    t["cac_inr"] = np.where(paid, t.campaign_spend_inr / t.registered_users, np.nan)
    t["cost_per_first_trader_inr"] = np.where(paid, t.cac_inr / (t.first_trade_rate_mature_pct / 100), np.nan)
    t["rank_first_trade"] = t.first_trade_rate_mature_pct.rank(ascending=False, method="min").astype(int)
    t["rank_m3_retention"] = t.m3_retention_pct.rank(ascending=False, method="min").astype(int)
    t["rank_cost_per_first_trader_paid"] = t.cost_per_first_trader_inr.rank(method="min")
    return t.round(2).reset_index().sort_values("rank_first_trade")


def channel_scorecard(users):
    g = users.groupby("acquisition_channel"); m = users[users.funnel_mature == 1].groupby("acquisition_channel")
    t = pd.DataFrame({"registrations": g.size(), "first_trade_pct": 100 * m.trade_asof.mean(), "m3_retention_pct": 100 * g.m3_retained.mean(),
                      "dormant_3m_pct": 100 * g.dormant_3m_monthly.mean(),
                      "tickets_per_1000_users": 1000 * g.ticket_count.sum() / g.size()})
    return t.round(1).sort_values("first_trade_pct", ascending=False).reset_index()


def plot_cost_vs_quality(sc, ax=None):
    """Paid campaigns: CAC (x) vs first-trade rate (y), bubble = registrations."""
    style(); ax = ax or plt.subplots(figsize=(6.4, 3.8))[1]
    p = sc[sc.is_paid == 1]
    ax.scatter(p.cac_inr, p.first_trade_rate_mature_pct, s=p.registered_users / 5, color=BLUE, alpha=.75, edgecolor="white")
    for r in p.itertuples(): ax.annotate(r.campaign_name, (r.cac_inr, r.first_trade_rate_mature_pct), xytext=(6, 4), textcoords="offset points", fontsize=7.5, color=INK)
    ax.set_xlabel("CAC (INR per registered user)"); ax.set_ylabel("First-trade rate, mature cohort (%)"); ax.set_title("Paid campaigns: cost vs quality (synthetic)")
    return ax
