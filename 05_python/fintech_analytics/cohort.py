"""Cohort retention, MAU and repeat trading. Monthly_Activity is the source of truth for activity.
M1/M3/M6 = share active in calendar month k after the registration month (a proxy, not exact 30/90/180 days)."""
import numpy as np
import pandas as pd
from .eda import style, BLUE, GREY, INK, ORANGE
import matplotlib.pyplot as plt


def retention_matrix(activity, max_offset=6):
    """Cohort (registration month) x offset retention in %, plus a pooled row."""
    a = activity[activity.months_since_registration <= max_offset]
    m = a.pivot_table(index="registration_month", columns="months_since_registration", values="active_in_month", aggfunc="mean") * 100
    pooled = a.groupby("months_since_registration").active_in_month.mean() * 100
    m.loc["POOLED"] = pooled
    m.columns = [f"M{c}" for c in m.columns]
    return m.round(2)


def retention_summary(activity):
    p = activity.groupby("months_since_registration").active_in_month.agg(["mean", "size"])
    return {f"M{k}": float(p.loc[k, "mean"]) for k in (1, 3, 6)}


def mau_table(users, activity):
    reg = users.groupby("registration_month").size().cumsum().rename("registered_to_date")
    a = activity.groupby("activity_month").agg(mau=("active_in_month", "sum"))
    a["mau_new"] = activity[activity.months_since_registration == 0].groupby("activity_month").active_in_month.sum()
    a["mau_existing"] = a.mau - a.mau_new
    a = a.join(reg)
    a["mau_pct_of_registered"] = 100 * a.mau / a.registered_to_date
    return a.round(1).reset_index()


def repeat_trading(users):
    """Repeat-trader share among ever-traders, users with >= 4 observed months (monthly source)."""
    b = users[users.months_observed >= 4]; tr = b[b.trade_months >= 1]
    return dict(base_users=len(b), ever_traded_pct=100 * (b.trade_months >= 1).mean(),
                repeat_pct_of_traders=100 * (tr.trade_months >= 2).mean(), repeat3_pct_of_traders=100 * (tr.trade_months >= 3).mean())


def dormancy_rate(users):
    d = users.dormant_3m_monthly.dropna()
    return dict(eligible=len(d), dormant_3m_pct=100 * d.mean())


def plot_retention_curve(activity, ax=None):
    style(); ax = ax or plt.subplots(figsize=(6, 3.4))[1]
    r = activity.groupby("months_since_registration").active_in_month.mean() * 100
    ax.plot(r.index, r.values, color=BLUE, lw=2, marker="o", ms=4)
    for k in (1, 3, 6): ax.annotate(f"M{k} {r.loc[k]:.1f}%", (k, r.loc[k]), xytext=(5, 6), textcoords="offset points", fontsize=8, color=INK)
    ax.set_ylim(0, 85); ax.set_xlabel("Calendar months since registration month"); ax.set_ylabel("% of cohort active"); ax.set_title("Pooled retention curve (synthetic)")
    return ax


def plot_retention_heatmap(mat, ax=None):
    style(); ax = ax or plt.subplots(figsize=(7, 4.2))[1]
    im = ax.imshow(mat.values.astype(float), cmap="Blues", aspect="auto", vmin=30, vmax=80)
    ax.set_xticks(range(mat.shape[1])); ax.set_xticklabels(mat.columns); ax.set_yticks(range(mat.shape[0])); ax.set_yticklabels(mat.index, fontsize=7.5)
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            v = mat.values[i, j]
            if not np.isnan(v): ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=7, color="white" if v > 60 else INK)
    ax.set_title("Cohort retention % (blank = not yet observable)")
    return ax
