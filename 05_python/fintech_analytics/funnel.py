"""Funnel analytics on the mature cohort (Users table is the source of truth for funnel metrics)."""
import numpy as np
import pandas as pd
from . import config as C
from .eda import style, BLUE, GREY, INK, ORANGE
import matplotlib.pyplot as plt


def wilson(k, n, z=1.96):
    if n == 0: return (np.nan, np.nan)
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def stage_counts(u):
    """Counts reaching each stage for a (mature) set of users."""
    return pd.Series({"Registered": len(u), "KYC Completed": int(u.kyc_asof.sum()), "Bank Linked": int(u.bank_asof.sum()),
                      "First Deposit": int(u.deposit_asof.sum()), "First Trade": int(u.trade_asof.sum()),
                      "Active (30d)": int(((u.trade_asof == 1) & (u.active_30d_adj == 1)).sum())})


def funnel_table(users):
    """Overall funnel on the mature cohort with step conversion, losses and share of all losses."""
    m = users[users.funnel_mature == 1]
    s = stage_counts(m)
    t = pd.DataFrame({"reached": s})
    t["pct_of_registered"] = 100 * t.reached / t.reached.iloc[0]
    t["step_conversion_pct"] = 100 * t.reached / t.reached.shift(1)
    t["users_lost"] = t.reached.shift(1) - t.reached
    t["share_of_all_losses_pct"] = 100 * t.users_lost / (t.reached.iloc[0] - t.reached.iloc[-1])
    ci = [wilson(r, p) for r, p in zip(t.reached.iloc[1:], t.reached.shift(1).iloc[1:])]
    t["conv_ci_low_pct"] = [np.nan] + [100 * c[0] for c in ci]; t["conv_ci_high_pct"] = [np.nan] + [100 * c[1] for c in ci]
    return t.round(2)


def funnel_by(users, dim):
    """Step conversions and end-to-end rate by a dimension (channel, device, city ...) on the mature cohort."""
    m = users[users.funnel_mature == 1]
    g = m.groupby(dim)
    t = pd.DataFrame({"mature_users": g.size(), "kyc": g.kyc_asof.sum(), "bank": g.bank_asof.sum(), "deposit": g.deposit_asof.sum(), "trade": g.trade_asof.sum()})
    t["kyc_pct"] = 100 * t.kyc / t.mature_users; t["bank_conv_pct"] = 100 * t.bank / t.kyc
    t["deposit_conv_pct"] = 100 * t.deposit / t.bank; t["trade_conv_pct"] = 100 * t.trade / t.deposit
    t["reg_to_trade_pct"] = 100 * t.trade / t.mature_users
    return t.round(2).sort_values("reg_to_trade_pct", ascending=False).reset_index()


def time_to_stage(users):
    """Median/p75 days between consecutive stages (users who reached the stage)."""
    cols = {"KYC Completed": "days_reg_to_kyc", "Bank Linked": "days_kyc_to_bank", "First Deposit": "days_bank_to_deposit", "First Trade": "days_deposit_to_trade"}
    m = users[users.funnel_mature == 1]
    return pd.DataFrame({k: m[v].dropna().describe(percentiles=[.5, .75])[["count", "mean", "50%", "75%"]] for k, v in cols.items()}).T.round(1)


def plot_funnel(users, ax=None):
    style(); ax = ax or plt.subplots(figsize=(7, 3.6))[1]
    t = funnel_table(users)
    ax.barh(t.index[::-1], t.reached[::-1], color=BLUE, height=.62)
    for y, (r, p, c) in enumerate(zip(t.reached[::-1], t.pct_of_registered[::-1], t.step_conversion_pct[::-1])):
        ax.text(r + 80, y, f"{r:,}  ({p:.1f}%)" + ("" if np.isnan(c) else f"   step {c:.1f}%"), va="center", fontsize=8, color=INK)
    ax.set_xlim(0, t.reached.max() * 1.55); ax.set_title("Onboarding funnel, mature cohort (synthetic)"); ax.set_xlabel("Users")
    return ax
