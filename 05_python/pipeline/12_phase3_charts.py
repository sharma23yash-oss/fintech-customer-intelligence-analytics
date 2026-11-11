"""
Phase 3 - charts (PNG) for the Excel / Word / PDF deliverables.
Inputs : Phase 3 tables (03_business_analytics/*)   Outputs: assets/charts/phase3_c*.png
Palette: validated categorical slots 1-2 (blue #2a78d6, orange #eb6834; validate_palette.js PASS, adjacent CVD dE 9.1+),
         single-hue blue ramp for magnitude/ordinal encodings. Text uses ink tokens, never series colour.
All data are synthetic.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # 05_python/ (for fintech_analytics)
from fintech_analytics import config as CFG

ROOT = CFG.ROOT
T = CFG.P3_TABLES
C = CFG.CHARTS_DIR
C.mkdir(parents=True, exist_ok=True)
R = json.load(open(T / "results.json"))

SURF, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8985", "#e4e3df"
BLUE, ORANGE = "#2a78d6", "#eb6834"
RAMP = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
ORD = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#184f95", "#104281"]   # ordinal ramp (>= step 250)
plt.rcParams.update({"figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF, "font.family": "DejaVu Sans",
                     "font.size": 10, "text.color": INK, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.edgecolor": GRID, "axes.spines.top": False, "axes.spines.right": False})
SRC = "Source: synthetic dataset (10,000 users, Nov 2025 - Oct 2026). Mature cohorts unless stated."
pct = FuncFormatter(lambda v, _: f"{v*100:.0f}%")


def finish(fig, name, title, sub=None, src=SRC):
    fig.suptitle(title, x=0.01, y=0.99, ha="left", va="top", fontsize=13, fontweight="bold", color=INK)
    if sub:
        fig.text(0.01, 0.925, sub, ha="left", va="top", fontsize=9.5, color=INK2)
    fig.text(0.01, 0.005, src, ha="left", va="bottom", fontsize=7.5, color=MUTED)
    fig.savefig(C / f"phase3_{name}.png", dpi=200)   # assets/charts/phase3_c01_funnel.png ...
    plt.close(fig)


def hbar(ax, labels, vals, colors=BLUE, fmt="{:.1%}", xmax=None, err=None):
    y = np.arange(len(labels))[::-1]
    ax.barh(y, vals, color=colors, height=0.62, edgecolor=SURF, linewidth=2)
    if err is not None:
        ax.errorbar(vals, y, xerr=err, fmt="none", ecolor=INK2, elinewidth=1, capsize=3)
    for yi, v in zip(y, vals):
        ax.text(v + (xmax or max(vals)) * 0.015 + (0 if err is None else max(np.array(err).max(), 0)), yi, fmt.format(v), va="center", fontsize=9, color=INK)
    ax.set_yticks(y); ax.set_yticklabels(labels)
    ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True); ax.tick_params(length=0)
    if xmax:
        ax.set_xlim(0, xmax)


# 01 funnel
fn = pd.read_csv(T / "Funnel_Analysis.csv"); fo = fn[fn.cut_type == "Overall"]
fig, ax = plt.subplots(figsize=(8.5, 4.4)); fig.subplots_adjust(top=0.80, left=0.17, right=0.93, bottom=0.1)
y = np.arange(len(fo))[::-1]
ax.barh(y, fo.conv_from_registration, color=ORD, height=0.64, edgecolor=SURF, linewidth=2)
for yi, (_, r) in zip(y, fo.iterrows()):
    t = f"{r.conv_from_registration:.1%}" + ("" if r.stage_order == 1 else f"   (step conv. {r.conv_from_previous:.1%}, lost {int(r.users_lost_from_previous):,})")
    ax.text(r.conv_from_registration + 0.012, yi, t, va="center", fontsize=9, color=INK)
ax.set_yticks(y); ax.set_yticklabels(fo.stage_name); ax.set_xlim(0, 1.35); ax.set_xticks([0, .2, .4, .6, .8, 1.0]); ax.xaxis.set_major_formatter(pct)
ax.grid(axis="x", color=GRID, lw=.8); ax.set_axisbelow(True); ax.tick_params(length=0)
finish(fig, "c01_funnel", "Only 38% of registrants place a first trade; KYC is the largest leak",
       f"Share of {R['n_mature']:,} mature registrants reaching each stage (cumulative), with step conversion and users lost")

# 02 registrations + MAU
rm = pd.read_csv(T / "m1_registrations_monthly.csv"); mau = pd.read_csv(T / "m3_mau_and_flows_monthly.csv")
fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 4)); fig.subplots_adjust(top=0.78, bottom=0.17, left=0.07, right=0.98, wspace=0.22)
x = np.arange(len(rm)); lab = [m[2:] for m in rm.registration_month]
a1.bar(x, rm.registrations, color=BLUE, width=0.66, edgecolor=SURF, linewidth=2); a1.set_ylim(0, 1000)
a1.set_xticks(x); a1.set_xticklabels(lab, rotation=60, fontsize=8); a1.set_title("New registrations per month", loc="left", fontsize=10, color=INK2)
a1.axhline(R["reg_monthly_mean"], color=ORANGE, lw=1.5); a1.text(-0.4, 915, f"orange line = mean {R['reg_monthly_mean']:.0f}", color=INK2, ha="left", fontsize=8.5)
a2.plot(x, mau.mau, color=BLUE, lw=2); a2.scatter(x, mau.mau, s=26, color=BLUE, zorder=3, edgecolor=SURF, linewidth=1.5)
a2.plot(x, mau.mau_from_new_registrants, color=ORANGE, lw=2); a2.scatter(x, mau.mau_from_new_registrants, s=26, color=ORANGE, zorder=3, edgecolor=SURF, linewidth=1.5)
a2.text(11.2, mau.mau.iloc[-1] + 150, f"All MAU {int(mau.mau.iloc[-1]):,}", ha="right", fontsize=8.5, color=INK2)
a2.text(11.2, mau.mau_from_new_registrants.iloc[-1] - 420, "In registration month", ha="right", fontsize=8.5, color=INK2)
a2.set_xticks(x); a2.set_xticklabels(lab, rotation=60, fontsize=8); a2.set_ylim(0, 5200); a2.set_title("Monthly active users (MAU)", loc="left", fontsize=10, color=INK2)
for a in (a1, a2):
    a.grid(axis="y", color=GRID, lw=.8); a.set_axisbelow(True); a.tick_params(length=0)
finish(fig, "c02_registrations_mau", "Registrations are flat; MAU grows because the active base accumulates",
       f"Registration trend is not significant (slope {R['reg_trend_slope_per_month']:+.1f}/month, p={R['reg_trend_p']:.2f}); MAU in Oct 2026 = {R['mau_pct_last']:.0%} of users registered to date",
       src="Source: synthetic dataset; MAU from Monthly_Activity (active_in_month = 1). Window starts Nov 2025, so early MAU is mechanically low.")

# 03 channel quality
ch = pd.read_csv(T / "m1_channel_performance.csv").sort_values("first_trade_rate", ascending=False)
fig, ax = plt.subplots(figsize=(8.5, 4.2)); fig.subplots_adjust(top=0.8, left=0.27, right=0.95, bottom=0.1)
err = np.array([ch.first_trade_rate - ch.first_trade_ci_low, ch.first_trade_ci_high - ch.first_trade_rate])
hbar(ax, [f"{c}  (n={int(n):,})" for c, n in zip(ch.acquisition_channel, ch.mature_users)], ch.first_trade_rate.values, xmax=0.7, err=err)
ax.xaxis.set_major_formatter(pct)
finish(fig, "c03_channel_first_trade", "Referral and Organic acquire the highest-quality customers",
       "First-trade rate by acquisition channel, with 95% Wilson interval (mature cohorts)")

# 04 cost per first trader
cp = pd.read_csv(T / "Campaign_Performance.csv"); cp = cp[cp.is_paid == 1].sort_values("cost_per_first_trade_at_maturity_inr")
fig, ax = plt.subplots(figsize=(8.5, 4.6)); fig.subplots_adjust(top=0.8, left=0.31, right=0.95, bottom=0.1)
v = cp.cost_per_first_trade_at_maturity_inr.values
err = np.array([v - cp.cost_per_first_trade_ci_low, cp.cost_per_first_trade_ci_high - v])
y = np.arange(len(cp))[::-1]
cols = [ORANGE if cid in ("CMP04", "CMP06") else BLUE for cid in cp.campaign_id]
ax.barh(y, v, color=cols, height=0.62, edgecolor=SURF, linewidth=2); ax.errorbar(v, y, xerr=err, fmt="none", ecolor=INK2, elinewidth=1, capsize=3)
for yi, val, hi in zip(y, v, cp.cost_per_first_trade_ci_high):
    ax.text(hi + 25, yi, f"Rs {val:,.0f}", va="center", fontsize=9, color=INK)
ax.set_yticks(y); ax.set_yticklabels([f"{n} ({i})" for n, i in zip(cp.campaign_name, cp.campaign_id)]); ax.set_xlim(0, 1700)
ax.grid(axis="x", color=GRID, lw=.8); ax.set_axisbelow(True); ax.tick_params(length=0)
finish(fig, "c04_cost_per_first_trader", "Referral costs about a third of the weakest campaigns per first trader",
       "Cost per first trader at maturity (Rs) = CAC / first-trade rate; orange = tier C (CMP04, CMP06); whiskers = 95% interval",
       src="Source: synthetic dataset; spend is recorded campaign spend. Organic has no recorded spend and is excluded (CAC not defined). No revenue/ROI is calculated.")

# 05 retention curve + 06 by channel
rc = pd.read_csv(T / "m3_retention_curve_pooled.csv")
fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.2, 4.2), gridspec_kw={"width_ratios": [1.15, 1]}); fig.subplots_adjust(top=0.78, bottom=0.12, left=0.07, right=0.98, wspace=0.42)
a1.plot(rc.months_since_registration, rc.rate, color=BLUE, lw=2.2); a1.scatter(rc.months_since_registration, rc.rate, s=30, color=BLUE, zorder=3, edgecolor=SURF, linewidth=1.5)
for m in (1, 3, 6):
    r = rc.rate[rc.months_since_registration == m].iloc[0]; a1.annotate(f"M{m} {r:.0%}", (m, r), xytext=(8, 8), textcoords="offset points", fontsize=9, color=INK)
a1.set_ylim(0, 0.9); a1.yaxis.set_major_formatter(pct); a1.set_xlabel("Calendar months since registration"); a1.set_xticks(range(0, 12))
a1.set_title("Pooled retention curve (cohorts old enough to observe)", loc="left", fontsize=10, color=INK2)
m3 = pd.Series(R["retention_by_channel_m3"]).sort_values(ascending=False)
hbar(a2, list(m3.index), m3.values, xmax=0.8, fmt="{:.1%}"); a2.xaxis.set_major_formatter(pct)
a2.axvline(R["m3"], color=ORANGE, lw=1.5); a2.text(R["m3"] + 0.008, 6.45, f"all users {R['m3']:.0%}", color=INK2, fontsize=8.5, ha="left")
a2.set_title("M3 retention by channel", loc="left", fontsize=10, color=INK2)
a1.grid(axis="y", color=GRID, lw=.8); a1.tick_params(length=0)
finish(fig, "c05_retention", "Retention falls from 68% at M1 to 56% at M3 and 41% at M6",
       "Share of registrants active in the n-th calendar month after the registration month. Inactivity proxies, not confirmed churn",
       src="Source: synthetic dataset; Monthly_Activity. Each point uses only cohorts that have reached that month (denominator shrinks to 827 at M11).")

# 07 cohort heatmap
cm = pd.read_csv(T / "m3_cohort_retention_matrix.csv").set_index("registration_month")
fig, ax = plt.subplots(figsize=(9.2, 4.8)); fig.subplots_adjust(top=0.8, left=0.09, right=0.98, bottom=0.12)
from matplotlib.colors import LinearSegmentedColormap
cmap = LinearSegmentedColormap.from_list("blue", ["#cde2fb", "#2a78d6", "#0d366b"])
arr = cm.values.astype(float); im = ax.imshow(np.ma.masked_invalid(arr), cmap=cmap, vmin=0.2, vmax=0.8, aspect="auto")
for i in range(arr.shape[0]):
    for j in range(arr.shape[1]):
        if not np.isnan(arr[i, j]):
            ax.text(j, i, f"{arr[i,j]*100:.0f}", ha="center", va="center", fontsize=8, color=INK if arr[i, j] < 0.5 else "#ffffff")
ax.set_xticks(range(arr.shape[1])); ax.set_xticklabels([f"M{c}" for c in cm.columns]); ax.set_yticks(range(arr.shape[0])); ax.set_yticklabels(cm.index)
for s in ax.spines.values():
    s.set_visible(False)
ax.tick_params(length=0); cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02); cb.ax.yaxis.set_major_formatter(pct); cb.outline.set_visible(False)
finish(fig, "c07_cohort_heatmap", "Cohort curves are almost identical, so there is no cohort-quality drift",
       "Retention % by registration-month cohort (rows) and months since registration (columns); blank = not yet observable",
       src="Source: synthetic dataset; Customer_Cohorts logic on Monthly_Activity. Blank cells are right-censored, not churn.")

# 08 journey segments
js = pd.read_csv(T / "m4_journey_segment_profile.csv"); js["lab"] = js.journey_segment.str[3:]
fig, ax = plt.subplots(figsize=(9, 4.8)); fig.subplots_adjust(top=0.8, left=0.36, right=0.95, bottom=0.1)
hbar(ax, js.lab.str.replace(r"\(.*?\)", "", regex=True).str.strip(), js.share.values, xmax=0.4, fmt="{:.1%}"); ax.xaxis.set_major_formatter(pct)
finish(fig, "c08_journey_segments", "59% of users sit in a stalled onboarding state; only 9% are high-engagement traders",
       "Journey segments, share of all 10,000 users (mutually exclusive rule-based segments)",
       src="Source: synthetic dataset. Stalled = days since last stage event above the max historic lag; 91-98% of stalled users have a funnel/activity-log conflict.")

# 09 tickets
tc = pd.read_csv(T / "m6_ticket_categories.csv").sort_values("tickets_per_1000_customer_months", ascending=False)
ba = pd.read_csv(T / "m6_backlog_ageing.csv")
fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.4, 4.2), gridspec_kw={"width_ratios": [1.35, 1]}); fig.subplots_adjust(top=0.78, bottom=0.1, left=0.17, right=0.98, wspace=0.55)
hbar(a1, tc.category, tc.tickets_per_1000_customer_months.values, xmax=34, fmt="{:.1f}"); a1.set_title("Tickets per 1,000 customer-months", loc="left", fontsize=10, color=INK2)
x = np.arange(len(ba)); a2.bar(x, ba.tickets, color=[RAMP[1], RAMP[2], RAMP[4], RAMP[5]], width=0.66, edgecolor=SURF, linewidth=2)
for xi, v in zip(x, ba.tickets):
    a2.text(xi, v + 8, f"{v}", ha="center", fontsize=9, color=INK)
a2.set_xticks(x); a2.set_xticklabels(ba.backlog_age_bucket); a2.set_ylim(0, 480); a2.set_title("Unresolved tickets by age", loc="left", fontsize=10, color=INK2)
a2.grid(axis="y", color=GRID, lw=.8); a2.set_axisbelow(True); a2.tick_params(length=0)
finish(fig, "c09_support", "Onboarding categories drive 55% of tickets; 563 open tickets are older than 90 days",
       f"{R['tickets']:,} tickets, median resolution {R['res_median']:.1f}h, mean CSAT {R['csat_mean']:.2f}; priority makes no difference to resolution time in this data")

# 10 experiments
ex = pd.read_csv(T / "m7_experiments.csv").sort_values("experiment_id", ascending=False)
fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.4, 4.6), sharey=True); fig.subplots_adjust(top=0.78, bottom=0.1, left=0.30, right=0.97, wspace=0.08)
y = np.arange(len(ex))
a1.barh(y, ex.n_total, color=BLUE, height=0.62, edgecolor=SURF, linewidth=2)
for yi, v in zip(y, ex.n_total):
    a1.text(v + 80, yi, f"{v:,}", va="center", fontsize=8.5, color=INK)
a2.barh(y, ex.accrual_weeks, color=BLUE, height=0.62, edgecolor=SURF, linewidth=2, label="Accrual")
a2.barh(y, ex.follow_up_weeks, left=ex.accrual_weeks, color=ORANGE, height=0.62, edgecolor=SURF, linewidth=2, label="Follow-up")
for yi, a, f in zip(y, ex.accrual_weeks, ex.follow_up_weeks):
    a2.text(a + f + 0.8, yi, f"{a + f} wk", va="center", fontsize=8.5, color=INK)
a1.set_yticks(y); a1.set_yticklabels([f"{i}  {a}" for i, a in zip(ex.experiment_id, ex.area)], fontsize=8.5)
a1.set_xlim(0, 7000); a2.set_xlim(0, 58); a1.set_title("Total sample needed (2 arms)", loc="left", fontsize=10, color=INK2); a2.set_title("Duration (weeks)", loc="left", fontsize=10, color=INK2)
for a in (a1, a2):
    a.grid(axis="x", color=GRID, lw=.8); a.set_axisbelow(True); a.tick_params(length=0)
a2.legend(frameon=False, loc="upper right", bbox_to_anchor=(1, 1.14), ncol=2, fontsize=8.5)
finish(fig, "c10_experiment_power", "At ~190 registrations a week, most tests need 5-27 weeks; retention and paid-social tests need 40+",
       "PROPOSED experiments (none conducted): two-sided alpha 0.05, power 80%, ASSUMED effects; launch backlog pools shorten stage tests",
       src="Source: synthetic dataset baselines; effect sizes are analyst assumptions, not forecasts.")

# 11 budget reallocation sensitivity
rb = pd.read_csv(T / "m5_budget_reallocation_scenarios.csv"); xs = rb.destination_cost_penalty.str.replace("%", "").str.replace("+", "").astype(int)
fig, ax = plt.subplots(figsize=(8, 4.2)); fig.subplots_adjust(top=0.8, left=0.1, right=0.97, bottom=0.14)
ax.plot(xs, rb.net_change_first_traders, color=BLUE, lw=2.2); ax.scatter(xs, rb.net_change_first_traders, s=36, color=BLUE, zorder=3, edgecolor=SURF, linewidth=1.5)
for xv, yv in zip(xs, rb.net_change_first_traders):
    ax.annotate(f"{yv:.0f}", (xv, yv), xytext=(0, 9), textcoords="offset points", ha="center", fontsize=9, color=INK)
ax.axhline(0, color=ORANGE, lw=1.5); ax.text(2, 8, "break-even (zero net gain)", color=INK2, ha="left", fontsize=8.5)
ax.set_xlabel("Assumed rise in cost per first trader at the destination campaigns (%)"); ax.set_ylabel("Net change in first traders"); ax.set_ylim(-20, 300)
ax.grid(axis="y", color=GRID, lw=.8); ax.tick_params(length=0)
finish(fig, "c11_budget_reallocation", "Moving Rs 190,000 to Referral and Email gains traders until costs rise ~170%",
       "Arithmetic, not a forecast: 25% of CMP04/CMP06 budgets moved to CMP05/CMP10",
       src="Source: synthetic dataset; recorded spend and mature first-trade rates. Diminishing returns are what the penalty axis represents.")

print(sorted(p.name for p in C.glob("*.png")))
