"""Exploratory data analysis helpers: profiling tables and standard EDA charts."""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from . import config as C

INK, BLUE, ORANGE, GREY = "#1F2937", "#2563EB", "#D97706", "#9CA3AF"


def style():
    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False,
                         "axes.edgecolor": GREY, "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK,
                         "axes.titleweight": "bold", "axes.titlesize": 11, "figure.dpi": 110})


def profile(df, name):
    """Column profile: dtype, missing %, unique values, min/max for numerics."""
    p = pd.DataFrame({"dtype": df.dtypes.astype(str), "missing_pct": (df.isna().mean() * 100).round(1), "unique": df.nunique()})
    num = df.select_dtypes("number")
    p["min"] = num.min(); p["max"] = num.max()
    p.insert(0, "table", name)
    return p.reset_index(names="column")


def monthly_registrations(users):
    return users.groupby("registration_month").size().rename("registrations").reset_index()


def channel_mix(users):
    t = users.groupby("acquisition_channel").size().rename("registrations").reset_index()
    t["share_pct"] = (100 * t.registrations / t.registrations.sum()).round(1)
    return t.sort_values("registrations", ascending=False)


def plot_registrations(users, ax=None):
    style(); ax = ax or plt.subplots(figsize=(7, 3.2))[1]
    m = monthly_registrations(users)
    ax.bar(m.registration_month, m.registrations, color=BLUE, width=.65)
    ax.set_title("Registrations per month (synthetic data)"); ax.set_ylabel("Users"); ax.tick_params(axis="x", rotation=45)
    return ax


def plot_channel_mix(users, ax=None):
    style(); ax = ax or plt.subplots(figsize=(6, 3.2))[1]
    t = channel_mix(users).sort_values("registrations")
    ax.barh(t.acquisition_channel, t.registrations, color=BLUE, height=.6)
    for y, (v, s) in enumerate(zip(t.registrations, t.share_pct)): ax.text(v + 15, y, f"{v:,} ({s}%)", va="center", fontsize=8, color=INK)
    ax.set_title("Registrations by channel"); ax.set_xlabel("Users"); ax.set_xlim(0, t.registrations.max() * 1.25)
    return ax


def plot_deposit_hist(users, ax=None):
    style(); ax = ax or plt.subplots(figsize=(6, 3.2))[1]
    v = users.first_deposit_amount_asof_inr.dropna()
    ax.hist(np.log10(v[v > 0]), bins=30, color=BLUE)
    ax.axvline(np.log10(v.median()), color=ORANGE, lw=1.5); ax.text(np.log10(v.median()), ax.get_ylim()[1] * .92, f"  median Rs{v.median():,.0f}", color=ORANGE, fontsize=8)
    ax.set_title("First deposit amount (log10 INR)"); ax.set_xlabel("log10(INR)"); ax.set_ylabel("Users")
    return ax


def plot_missingness(df, ax=None, top=15):
    style(); ax = ax or plt.subplots(figsize=(6, 3.8))[1]
    m = (df.isna().mean() * 100).sort_values(ascending=False).head(top)[::-1]
    ax.barh(m.index, m.values, color=GREY); ax.set_title(f"Missing values by column (top {top}, %)"); ax.set_xlabel("% missing")
    return ax
