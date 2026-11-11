"""
Phase 3 - Business analytics (Modules 1-6) on the CLEANED Phase 2 tables only.

Inputs : data/cleaned/*.csv          Outputs: 03_business_analytics/<module>/m*.csv + summary/results.json
Run    : python3 10_phase3_analysis.py        (deterministic: seed 42)
All data are synthetic. Calculations are labelled as such; nothing here is real brokerage performance.
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import adjusted_rand_score, roc_auc_score, silhouette_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.preprocessing import StandardScaler

import sys
from pathlib import Path as _P
sys.path.insert(0, str(_P(__file__).resolve().parents[1]))   # 05_python/ (for fintech_analytics)
from fintech_analytics import config as CFG
SEED = 42
rng = np.random.default_rng(SEED)
ROOT = CFG.ROOT
CL = CFG.CLEAN_TABLES      # data/cleaned (+ derived/)
OUT = CFG.P3_TABLES        # 03_business_analytics/<module>/ (see config.p3_path)
OUT.mkdir(parents=True, exist_ok=True)
R = {}            # headline results for the report builders


def save(name, df, idx=False):
    df.to_csv(OUT / f"{name}.csv", index=idx)
    return df


def wilson(k, n, z=1.96):
    k, n = np.asarray(k, float), np.asarray(n, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        p = k / n
        d = 1 + z * z / n
        c = (p + z * z / (2 * n)) / d
        h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def rate_row(k, n):
    lo, hi = wilson(k, n)
    return dict(n=int(n), successes=int(k), rate=k / n if n else np.nan, ci_low=float(lo), ci_high=float(hi))


def chi2_p(df, group, flag):
    t = pd.crosstab(df[group], df[flag])
    if t.shape[0] < 2 or t.shape[1] < 2:
        return np.nan, np.nan
    c, p, _, _ = stats.chi2_contingency(t)
    return float(c), float(p)


U = pd.read_csv(CL / "Cleaned_Users.csv", parse_dates=["registration_date", "kyc_date_asof", "bank_date_asof", "deposit_date_asof", "trade_date_asof"])
M = pd.read_csv(CL / "Cleaned_Monthly_Activity.csv")
T = pd.read_csv(CL / "Cleaned_Support_Tickets.csv", parse_dates=["created_date"])
CA = pd.read_csv(CL / "Cleaned_Campaigns.csv")
CP2 = pd.read_csv(CL / "Campaign_Performance.csv")
COH = pd.read_csv(CL / "Customer_Cohorts.csv")
FUN = pd.read_csv(CL / "Customer_Funnel.csv")
SEG2 = pd.read_csv(CL / "Customer_Segments.csv")
SNAP = pd.Timestamp("2026-10-31")
MU = U[U.funnel_mature == 1].copy()        # mature cohorts for conversion metrics
R["n_users"] = len(U); R["n_mature"] = len(MU); R["n_immature"] = int((U.funnel_mature == 0).sum())

# ======================================================================================
# MODULE 1 - ACQUISITION
# ======================================================================================
reg_m = U.groupby("registration_month").size().rename("registrations").reset_index()
by_ch_m = U.pivot_table(index="registration_month", columns="acquisition_channel", values="user_id", aggfunc="count").reset_index()
reg_m = reg_m.merge(by_ch_m, on="registration_month")
slope = stats.linregress(np.arange(len(reg_m)), reg_m.registrations)
reg_m["mom_change_pct"] = reg_m.registrations.pct_change().round(4)
save("m1_registrations_monthly", reg_m)
R["reg_monthly_mean"] = float(reg_m.registrations.mean()); R["reg_monthly_min"] = int(reg_m.registrations.min()); R["reg_monthly_max"] = int(reg_m.registrations.max())
R["reg_trend_slope_per_month"] = float(slope.slope); R["reg_trend_p"] = float(slope.pvalue)

camp_ch = CA.groupby("channel").agg(spend=("campaign_spend_inr", "sum"), campaigns=("campaign_id", "count")).reset_index().rename(columns={"channel": "acquisition_channel"})
rows = []
for ch, d in U.groupby("acquisition_channel"):
    m = d[d.funnel_mature == 1]; e30 = d[d.eligible_30d == 1]
    k = rate_row(m.kyc_asof.sum(), len(m)); tr = rate_row(m.trade_asof.sum(), len(m)); bk = rate_row(m.bank_asof.sum(), len(m)); dp = rate_row(m.deposit_asof.sum(), len(m))
    a30 = rate_row(e30.active_30d_adj.sum(), len(e30))
    m1 = d[d.m1_retained.notna()]; m3 = d[d.m3_retained.notna()]; dm = d[d.dormant_3m_monthly.notna()]
    rows.append(dict(acquisition_channel=ch, registered=len(d), share_of_registrations=len(d) / len(U), mature_users=len(m),
                     kyc_rate=k["rate"], kyc_ci_low=k["ci_low"], kyc_ci_high=k["ci_high"], bank_rate=bk["rate"], deposit_rate=dp["rate"],
                     first_trade_rate=tr["rate"], first_trade_ci_low=tr["ci_low"], first_trade_ci_high=tr["ci_high"],
                     active_30d_rate=a30["rate"], m1_retention=m1.m1_retained.mean(), m3_retention=m3.m3_retained.mean(), dormant_3m_rate=dm.dormant_3m_monthly.mean(),
                     first_trade_per_registered_all=d.trade_asof.mean()))
ch = pd.DataFrame(rows).merge(camp_ch, on="acquisition_channel")
ch["cac_inr"] = np.where(ch.spend > 0, ch.spend / ch.registered, np.nan)
ch["cost_per_kyc_at_maturity_inr"] = ch.cac_inr / ch.kyc_rate
ch["cost_per_first_trade_at_maturity_inr"] = ch.cac_inr / ch.first_trade_rate
ch["cost_per_first_trade_ci_low"] = ch.cac_inr / ch.first_trade_ci_high
ch["cost_per_first_trade_ci_high"] = ch.cac_inr / ch.first_trade_ci_low
ch["cost_per_active_30d_inr"] = ch.cac_inr / ch.active_30d_rate
ch = ch.sort_values("registered", ascending=False)
save("m1_channel_performance", ch)
c_, p_ = chi2_p(MU, "acquisition_channel", "trade_asof"); R["chan_trade_chi2_p"] = p_
c_, p_ = chi2_p(MU, "acquisition_channel", "kyc_asof"); R["chan_kyc_chi2_p"] = p_

# paid vs organic
U["paid_flag"] = np.where(U.acquisition_channel == "Organic", "Organic", "Paid / incentivised")
grp = []
for gname, col in [("paid_vs_organic", "paid_flag"), ("channel_group", None)]:
    if col is None:
        U = U.merge(CA[["campaign_id", "channel_group"]], left_on="acquisition_campaign_id", right_on="campaign_id", how="left")
        col = "channel_group"
    for v, d in U.groupby(col):
        m = d[d.funnel_mature == 1]; e30 = d[d.eligible_30d == 1]
        sp = CA.loc[CA.campaign_id.isin(d.acquisition_campaign_id.unique()), "campaign_spend_inr"].sum()
        grp.append(dict(grouping=gname, group=v, registered=len(d), share=len(d) / len(U), spend_inr=sp, cac_inr=(sp / len(d) if sp > 0 else np.nan),
                        kyc_rate=m.kyc_asof.mean(), first_trade_rate=m.trade_asof.mean(), active_30d_rate=e30.active_30d_adj.mean(),
                        m3_retention=d.m3_retained.mean(), first_trade_ci_low=wilson(m.trade_asof.sum(), len(m))[0], first_trade_ci_high=wilson(m.trade_asof.sum(), len(m))[1]))
po = save("m1_paid_vs_organic", pd.DataFrame(grp))
org = po[(po.grouping == "paid_vs_organic") & (po.group == "Organic")].iloc[0]; pd_ = po[(po.grouping == "paid_vs_organic") & (po.group == "Paid / incentivised")].iloc[0]
R["organic_share"] = float(org.share); R["organic_trade_rate"] = float(org.first_trade_rate); R["paid_trade_rate"] = float(pd_.first_trade_rate)
R["organic_active"] = float(org.active_30d_rate); R["paid_active"] = float(pd_.active_30d_rate)
# test organic vs paid first trade rate
a = MU[MU.acquisition_channel == "Organic"]; b = MU[MU.acquisition_channel != "Organic"]
_, p_ = stats.chi2_contingency(pd.crosstab(MU.acquisition_channel == "Organic", MU.trade_asof))[:2]; R["organic_vs_paid_p"] = float(p_)

# dimensions: city / device / age / risk
dim_rows, test_rows = [], []
for dim in ["city", "device_type", "age_group", "risk_profile"]:
    for v, d in U.groupby(dim):
        m = d[d.funnel_mature == 1]; e30 = d[d.eligible_30d == 1]
        dim_rows.append(dict(dimension=dim, value=v, registered=len(d), share=len(d) / len(U), mature_users=len(m), kyc_rate=m.kyc_asof.mean(), bank_rate=m.bank_asof.mean(),
                             deposit_rate=m.deposit_asof.mean(), first_trade_rate=m.trade_asof.mean(), active_30d_rate=e30.active_30d_adj.mean(),
                             m3_retention=d.m3_retained.mean(), median_first_deposit_inr=d.first_deposit_amount_asof_inr.median(),
                             first_trade_ci_low=wilson(m.trade_asof.sum(), len(m))[0], first_trade_ci_high=wilson(m.trade_asof.sum(), len(m))[1]))
    for outc in ["kyc_asof", "trade_asof"]:
        c_, p_ = chi2_p(MU, dim, outc)
        g = MU.groupby(dim)[outc].mean()
        test_rows.append(dict(dimension=dim, outcome=outc, chi2=c_, p_value=p_, highest=g.idxmax(), highest_rate=g.max(), lowest=g.idxmin(), lowest_rate=g.min(), spread_pp=(g.max() - g.min()) * 100))
    c_, p_ = chi2_p(U[U.m3_retained.notna()], dim, "m3_retained")
    g = U[U.m3_retained.notna()].groupby(dim).m3_retained.mean()
    test_rows.append(dict(dimension=dim, outcome="m3_retained", chi2=c_, p_value=p_, highest=g.idxmax(), highest_rate=g.max(), lowest=g.idxmin(), lowest_rate=g.min(), spread_pp=(g.max() - g.min()) * 100))
dimdf = save("m1_dimension_performance", pd.DataFrame(dim_rows)); tests = save("m2_dimension_significance_tests", pd.DataFrame(test_rows))

# campaign-level (phase 2 table already holds cost metrics; add CIs + tests)
cp = CP2.copy()
cp["first_trade_ci_low"] = [wilson(r * n, n)[0] for r, n in zip(cp.first_trade_rate_mature, cp.mature_users)]
cp["first_trade_ci_high"] = [wilson(r * n, n)[1] for r, n in zip(cp.first_trade_rate_mature, cp.mature_users)]
cp["cost_per_first_trade_ci_low"] = cp.cac_inr / cp.first_trade_ci_high
cp["cost_per_first_trade_ci_high"] = cp.cac_inr / cp.first_trade_ci_low
c_, p_ = chi2_p(MU, "acquisition_campaign_id", "trade_asof"); R["campaign_trade_chi2_p"] = p_
# each campaign vs all others (two-proportion z, Holm-adjusted)
zrows = []
for cid in cp.campaign_id:
    a = MU[MU.acquisition_campaign_id == cid].trade_asof; b = MU[MU.acquisition_campaign_id != cid].trade_asof
    p1, p2, n1, n2 = a.mean(), b.mean(), len(a), len(b); pp = (a.sum() + b.sum()) / (n1 + n2)
    z = (p1 - p2) / np.sqrt(pp * (1 - pp) * (1 / n1 + 1 / n2)); zrows.append(dict(campaign_id=cid, rate=p1, rate_others=p2, diff_pp=(p1 - p2) * 100, z=z, p_raw=2 * (1 - stats.norm.cdf(abs(z)))))
z = pd.DataFrame(zrows).sort_values("p_raw"); mm_ = len(z); z["p_holm"] = np.minimum.accumulate((z.p_raw * (mm_ - np.arange(mm_))).clip(upper=1)[::-1])[::-1]
z["p_holm"] = np.maximum.accumulate(np.minimum(1, z.p_raw.values * (mm_ - np.arange(mm_)))); z["significant_at_5pct_holm"] = z.p_holm < 0.05
save("m5_campaign_vs_others_tests", z)

# ======================================================================================
# MODULE 2 - FUNNEL
# ======================================================================================
fun = FUN.copy()
prev_n = fun.groupby(["cut_type", "cut_value"]).users_reached.shift(1)
fun["ci_low"] = [wilson(r, p)[0] if (p == p and r == r and p > 0) else np.nan for r, p in zip(fun.users_reached, prev_n)]
fun["ci_high"] = [wilson(r, p)[1] if (p == p and r == r and p > 0) else np.nan for r, p in zip(fun.users_reached, prev_n)]
fun["users_lost_from_previous"] = prev_n - fun.users_reached
save("Funnel_Analysis", fun)
ov = fun[(fun.cut_type == "Overall")].set_index("stage_name")
R["funnel"] = {s: dict(reached=int(ov.at[s, "users_reached"]), conv_prev=float(ov.at[s, "conv_from_previous"]), conv_reg=float(ov.at[s, "conv_from_registration"]),
                       lost=(float(ov.at[s, "users_lost_from_previous"]) if s != "Registered" else 0), median_days=(float(ov.at[s, "median_days_from_previous"]) if ov.at[s, "median_days_from_previous"] == ov.at[s, "median_days_from_previous"] else None),
                       p75_days=(float(ov.at[s, "p75_days_from_previous"]) if ov.at[s, "p75_days_from_previous"] == ov.at[s, "p75_days_from_previous"] else None),
                       ci=[float(ov.at[s, "ci_low"]), float(ov.at[s, "ci_high"])] if s != "Registered" else None) for s in ov.index}
R["median_days_reg_to_trade"] = float(MU.days_reg_to_trade.median()); R["p75_days_reg_to_trade"] = float(MU.days_reg_to_trade.quantile(.75))
# stage timing by channel/device
tm = MU.groupby("acquisition_channel")[["days_reg_to_kyc", "days_kyc_to_bank", "days_bank_to_deposit", "days_deposit_to_trade", "days_reg_to_trade"]].median().reset_index()
save("m2_stage_timing_by_channel", tm)
tm_dev = MU.groupby("device_type")[["days_reg_to_kyc", "days_kyc_to_bank", "days_bank_to_deposit", "days_deposit_to_trade"]].median().reset_index(); save("m2_stage_timing_by_device", tm_dev)
R["timing_channel_spread_days"] = float((tm.days_reg_to_trade.max() - tm.days_reg_to_trade.min()))

# bottleneck ranking + ticket evidence
stages = [("KYC Completed", "kyc", "KYC & verification"), ("Bank Linked", "bank", "Bank linking"), ("First Deposit", "deposit", "Deposits & withdrawals"), ("First Trade", "trade", "Trading & orders")]
tk = T.merge(U[["user_id", "funnel_mature"]], on="user_id"); tk = tk[tk.funnel_mature == 1]
bn = []
prev_stage_flag = {"kyc": None, "bank": "kyc_asof", "deposit": "bank_asof", "trade": "deposit_asof"}
for sname, key, cat in stages:
    base = MU if prev_stage_flag[key] is None else MU[MU[prev_stage_flag[key]] == 1]    # users at risk at that step
    reached = base[f"{key}_asof"]
    lost = int((reached == 0).sum())
    pend = tk[(tk.category == cat) & (tk.stage_pending_at_ticket == 1)].user_id.unique()
    filer = base.user_id.isin(pend)
    comp_f, comp_n = reached[filer].mean(), reached[~filer].mean()
    bn.append(dict(stage=sname, users_at_risk=len(base), users_lost=lost, drop_rate=lost / len(base), share_of_all_funnel_losses=np.nan,
                   median_days=float(base[{"kyc": "days_reg_to_kyc", "bank": "days_kyc_to_bank", "deposit": "days_bank_to_deposit", "trade": "days_deposit_to_trade"}[key]].median()),
                   users_who_raised_related_ticket_while_pending=int(filer.sum()), pct_of_at_risk_who_raised_ticket=filer.mean(),
                   completion_rate_ticket_raisers=comp_f, completion_rate_non_raisers=comp_n))
act_base = MU[MU.trade_asof == 1]
bn.append(dict(stage="Active (30d)", users_at_risk=len(act_base), users_lost=int((act_base.active_30d_adj == 0).sum()), drop_rate=float((act_base.active_30d_adj == 0).mean()), share_of_all_funnel_losses=np.nan,
               median_days=np.nan, users_who_raised_related_ticket_while_pending=np.nan, pct_of_at_risk_who_raised_ticket=np.nan, completion_rate_ticket_raisers=np.nan, completion_rate_non_raisers=np.nan))
bn = pd.DataFrame(bn); bn["share_of_all_funnel_losses"] = bn.users_lost / bn.users_lost.sum()
bn["rank_by_users_lost"] = bn.users_lost.rank(ascending=False).astype(int); save("m2_bottlenecks", bn)
R["bottlenecks"] = bn.sort_values("users_lost", ascending=False).to_dict("records")

# ======================================================================================
# MODULE 3 - RETENTION
# ======================================================================================
mau = M.groupby("activity_month").agg(mau=("active_in_month", "sum"), trading_users=("traded_in_month", "sum"), users_with_row=("user_id", "nunique"), trades=("trade_count", "sum"),
                                       trading_value_inr=("trading_value_inr", "sum"), deposit_value_inr=("deposit_value_inr", "sum"), withdrawal_value_inr=("withdrawal_value_inr", "sum"),
                                       depositing_users=("deposited_in_month", "sum"), withdrawing_users=("withdrew_in_month", "sum"), new_registrations=("is_registration_month", "sum")).reset_index()
mau["mau_pct_of_registered_to_date"] = mau.mau / mau.users_with_row
mau["net_flow_inr"] = mau.deposit_value_inr - mau.withdrawal_value_inr
mau["withdrawal_to_deposit_ratio"] = mau.withdrawal_value_inr / mau.deposit_value_inr
mau["mau_from_new_registrants"] = M[M.is_registration_month == 1].groupby("activity_month").active_in_month.sum().reindex(mau.activity_month).values
mau["mau_from_existing"] = mau.mau - mau.mau_from_new_registrants
save("m3_mau_and_flows_monthly", mau)
R["mau_last"] = int(mau.mau.iloc[-1]); R["mau_first"] = int(mau.mau.iloc[0]); R["mau_peak"] = int(mau.mau.max()); R["mau_peak_month"] = mau.loc[mau.mau.idxmax(), "activity_month"]
R["mau_pct_last"] = float(mau.mau_pct_of_registered_to_date.iloc[-1]); R["wd_ratio_total"] = float(mau.withdrawal_value_inr.sum() / mau.deposit_value_inr.sum())
R["mau_existing_last"] = int(mau.mau_from_existing.iloc[-1]); R["mau_new_last"] = int(mau.mau_from_new_registrants.iloc[-1])

obs = COH[COH.observable == 1]
cm = obs.groupby(["registration_month", "months_since_registration"]).agg(cohort_users=("cohort_users", "sum"), active_users=("active_users", "sum"), trading_users=("trading_users", "sum")).reset_index()
cm["retention_rate"] = cm.active_users / cm.cohort_users; cm["trading_rate"] = cm.trading_users / cm.cohort_users
save("m3_cohort_retention_long", cm)
save("m3_cohort_retention_matrix", cm.pivot(index="registration_month", columns="months_since_registration", values="retention_rate").round(4).reset_index())
avg_curve = cm.groupby("months_since_registration").agg(a=("active_users", "sum"), c=("cohort_users", "sum")).assign(rate=lambda d: d.a / d.c).reset_index()
save("m3_retention_curve_pooled", avg_curve); R["retention_curve"] = {int(r.months_since_registration): float(r.rate) for r in avg_curve.itertuples()}

ret_rows = []
def add_ret(dim, val, d):
    specs = [("m1_retention", d.m1_retained.dropna(), "Active in the calendar month after registration month (30-day retention proxy)"),
             ("m3_retention", d.m3_retained.dropna(), "Active 3 calendar months after registration month (90-day retention proxy); registered <= Jul-2026"),
             ("m6_retention", d.m6_retained.dropna(), "Active 6 calendar months after registration month; registered <= Apr-2026"),
             ("active_last_30d", d.active_30d_adj.dropna(), "Recency proxy: days since last activity <= 30; tenure >= 31 d"),
             ("inactive_90d_proxy", d.inactive_90d_adj.dropna(), "Recency proxy: days since last activity > 90 (bounded at 120 d); tenure >= 91 d"),
             ("dormant_3m", d.dormant_3m_monthly.dropna(), "No active month Aug-Oct 2026 (monthly source); registered <= Jul-2026")]
    for mname, s, defn in specs:
        if len(s) == 0: continue
        rr = rate_row(s.sum(), len(s)); ret_rows.append(dict(dimension=dim, value=val, metric=mname, eligible_n=rr["n"], successes=rr["successes"], rate=rr["rate"], ci_low=rr["ci_low"], ci_high=rr["ci_high"], definition=defn))
add_ret("Overall", "All", U)
U["deposit_band"] = pd.cut(U.first_deposit_amount_asof_inr, [0, 3000, 6500, 11352, 1e9], labels=["< Rs3k", "Rs3-6.5k", "Rs6.5-11.4k", ">= Rs11.4k (top quartile)"]).astype(object).fillna("No deposit")
U["first_trade_segment"] = U.first_trade_segment.fillna("No trade")
for dim in ["acquisition_channel", "acquisition_campaign_id", "device_type", "age_group", "risk_profile", "city", "first_trade_segment", "deposit_band", "furthest_stage_asof"]:
    for v, d in U.groupby(dim): add_ret(dim, v, d)
U["ticket_status"] = np.select([U.ticket_count == 0, U.unresolved_ticket_count > 0], ["No ticket", "Has unresolved ticket"], "Tickets all resolved")
for v, d in U.groupby("ticket_status"): add_ret("ticket_status", v, d)
RET = pd.DataFrame(ret_rows); save("Retention_Analysis", RET)
g = lambda dim, val, metric: float(RET[(RET.dimension == dim) & (RET.value == val) & (RET.metric == metric)].rate.iloc[0])
R["m1"] = g("Overall", "All", "m1_retention"); R["m3"] = g("Overall", "All", "m3_retention"); R["m6"] = g("Overall", "All", "m6_retention")
R["active30"] = g("Overall", "All", "active_last_30d"); R["inactive90"] = g("Overall", "All", "inactive_90d_proxy"); R["dormant3m"] = g("Overall", "All", "dormant_3m")
R["retention_by_channel_m3"] = {v: g("acquisition_channel", v, "m3_retention") for v in U.acquisition_channel.unique()}
R["retention_by_channel_dormant"] = {v: g("acquisition_channel", v, "dormant_3m") for v in U.acquisition_channel.unique()}
# channel m3 chi2
c_, p_ = chi2_p(U[U.m3_retained.notna()], "acquisition_channel", "m3_retained"); R["chan_m3_chi2_p"] = p_

# repeat trading (monthly source)
rt = U[(U.months_observed >= 4)].copy()
traders = rt[rt.trade_months >= 1]
R["repeat_base_n"] = len(rt); R["ever_traded_monthly_pct"] = float((rt.trade_months >= 1).mean())
R["repeat_trader_share_of_traders"] = float((traders.trade_months >= 2).mean()); R["repeat3_share_of_traders"] = float((traders.trade_months >= 3).mean())
R["trades_per_trading_month"] = float(M[M.trade_count > 0].trade_count.mean()); R["median_trade_months_traders"] = float(traders.trade_months.median())
rtc = []
for chn, d in rt.groupby("acquisition_channel"):
    tr_ = d[d.trade_months >= 1]; rtc.append(dict(acquisition_channel=chn, users_4m_plus=len(d), ever_traded_pct=len(tr_) / len(d), repeat_trader_pct_of_traders=(tr_.trade_months >= 2).mean(),
                                                  three_plus_months_pct_of_traders=(tr_.trade_months >= 3).mean(), avg_trade_months_per_trader=tr_.trade_months.mean(),
                                                  avg_trades_per_trader=tr_.total_trades.mean(), median_trading_value_6m_inr=tr_.trading_value_6m_inr.median()))
save("m3_repeat_trading_by_channel", pd.DataFrame(rtc))
dist = traders.trade_months.clip(upper=8).value_counts(normalize=True).sort_index().rename_axis("trade_months").reset_index(name="share_of_traders"); save("m3_trade_months_distribution", dist)
# first-trade-month stickiness: traded in month after first trade month (monthly source)
mm = M.merge(U[["user_id", "registration_month"]], on="user_id")
first_trade_mi = mm[mm.trade_count > 0].groupby("user_id").months_since_registration.min().rename("ftm")
nxt = mm.merge(first_trade_mi, on="user_id")
nxt = nxt[(nxt.months_since_registration == nxt.ftm + 1)]
elig = first_trade_mi[first_trade_mi.index.isin(U[U.registration_month < "2026-10"].user_id)]
# eligible only if month ftm+1 is observable
obs_ids = U.set_index("user_id").months_observed
okids = [u for u, f in first_trade_mi.items() if obs_ids[u] > f + 1]
back = nxt[nxt.user_id.isin(okids)].traded_in_month.mean() if len(okids) else np.nan
R["traded_again_next_month"] = float(back); R["traded_again_n"] = len(okids)

# inactivity distribution
e30 = U[U.eligible_30d == 1]
bins = [-1, 7, 30, 60, 90, 130]; labs = ["0-7 d", "8-30 d", "31-60 d", "61-90 d", "91-120 d"]
inact = pd.cut(e30.days_inactive_adj, bins, labels=labs).value_counts(normalize=True).sort_index().rename_axis("days_since_last_activity").reset_index(name="share_of_eligible_users"); save("m3_inactivity_distribution", inact)
inch = e30.groupby("acquisition_channel").apply(lambda d: pd.Series(dict(eligible=len(d), inactive_30d_rate=d.inactive_30d_adj.mean(), median_days_inactive=d.days_inactive_adj.median()))).reset_index(); save("m3_inactivity_by_channel", inch)

# early disengagement signals - month 0/1 behaviour vs month-3 retention (association, not causation)
piv = lambda col: mm.pivot_table(index="user_id", columns="months_since_registration", values=col, aggfunc="max")
A_, TR_, DP_ = piv("active_in_month"), piv("traded_in_month"), piv("deposited_in_month")
E = U[U.m3_retained.notna()].set_index("user_id")[["m3_retained", "registration_month", "acquisition_channel", "device_type", "age_group", "risk_profile", "city"]].copy()
E["active_m0"], E["active_m1"] = A_[0], A_[1]; E["traded_m0_m1"] = ((TR_[0] + TR_[1]) > 0).astype(int); E["deposited_m0_m1"] = ((DP_[0] + DP_[1]) > 0).astype(int)
tk30 = T[T.days_since_registration <= 30].groupby("user_id").size(); E["ticket_first_30d"] = pd.Series(E.index.map(tk30), index=E.index).fillna(0).clip(upper=1).astype(int)
E["not_kyc_by_14d"] = (pd.Series(E.index.map(U.set_index("user_id").days_reg_to_kyc.fillna(99)), index=E.index) > 14).astype(int)
E["active_m0"] = E.active_m0.astype(int); E["active_m1"] = E.active_m1.astype(int)
sig_rows = []
for s, lab in [("active_m1", "Active in month 1"), ("active_m0", "Active in registration month"), ("traded_m0_m1", "Traded in months 0-1"), ("deposited_m0_m1", "Deposited in months 0-1"),
               ("ticket_first_30d", "Raised a ticket in first 30 days"), ("not_kyc_by_14d", "No KYC within 14 days (as-of)")]:
    for v in (1, 0):
        d = E[E[s] == v]; rr = rate_row(d.m3_retained.sum(), len(d)); sig_rows.append(dict(signal=lab, signal_value=v, users=rr["n"], m3_retention=rr["rate"], ci_low=rr["ci_low"], ci_high=rr["ci_high"]))
sig = pd.DataFrame(sig_rows); piv_ = sig.pivot(index="signal", columns="signal_value", values="m3_retention"); sig = sig.merge(((piv_[1] / piv_[0]).rename("lift_present_vs_absent")).reset_index(), on="signal"); save("m3_early_disengagement_signals", sig)
R["signals"] = {r.signal: dict(present=float(piv_.loc[r.signal, 1]), absent=float(piv_.loc[r.signal, 0])) for r in sig.drop_duplicates("signal").itertuples()}
# early-warning prototype (logistic, time-aware validation). PROTOTYPE - signals only from months 0-1 + registration attributes
X = pd.get_dummies(E[["active_m0", "active_m1", "traded_m0_m1", "deposited_m0_m1", "ticket_first_30d", "not_kyc_by_14d", "acquisition_channel", "device_type", "age_group", "risk_profile"]], drop_first=True).astype(float)
y = E.m3_retained.astype(int)
skf = StratifiedKFold(5, shuffle=True, random_state=SEED)
lr = LogisticRegression(max_iter=1000, C=1.0)
cv_auc = roc_auc_score(y, cross_val_predict(lr, X, y, cv=skf, method="predict_proba")[:, 1])
train = E.registration_month <= "2026-04"; test = ~train
lr.fit(X[train], y[train]); t_auc = roc_auc_score(y[test], lr.predict_proba(X[test])[:, 1])
base_auc = roc_auc_score(y[test], X.loc[test, "active_m1"])
lr.fit(X, y); coefs = pd.DataFrame(dict(feature=X.columns, coef=lr.coef_[0], odds_ratio=np.exp(lr.coef_[0]))).sort_values("odds_ratio", ascending=False); save("m3_early_warning_model_coefficients", coefs)
R["ew_model"] = dict(n=len(E), cv_auc=float(cv_auc), temporal_test_auc=float(t_auc), single_signal_auc=float(base_auc), base_rate=float(y.mean()), train_n=int(train.sum()), test_n=int(test.sum()))

# ======================================================================================
# MODULE 4 - SEGMENTATION
# ======================================================================================
lag = {k: MU[c].max() for k, c in [("kyc", "days_reg_to_kyc"), ("bank", "days_kyc_to_bank"), ("deposit", "days_bank_to_deposit"), ("trade", "days_deposit_to_trade")]}
R["max_stage_lag_days"] = {k: float(v) for k, v in lag.items()}
last_ev = U.registration_date.copy()
last_ev = U[["registration_date", "kyc_date_asof", "bank_date_asof", "deposit_date_asof"]].max(axis=1)
U["days_since_last_stage_event"] = (SNAP - last_ev).dt.days
U["days_since_first_trade"] = (SNAP - U.trade_date_asof).dt.days
def journey(r):
    st = r.furthest_stage_asof
    if st != "Traded":
        nxt, k = {"Registered": ("KYC", "kyc"), "KYC Completed": ("Bank", "bank"), "Bank Linked": ("Deposit", "deposit"), "Funded": ("Trade", "trade")}[st]
        inflight = r.days_since_last_stage_event <= lag[k]
        if inflight: return "01 New / in-flight onboarding"
        return {"Registered": "02 KYC-pending (stalled)", "KYC Completed": "03 Bank-link pending (stalled)", "Bank Linked": "04 Deposit-pending (stalled)", "Funded": "05 Deposited, never traded (stalled)"}[st]
    if r.days_since_first_trade <= 30: return "06 First-time trader (<=30d since first trade)"
    if r.dormant_3m_monthly == 1: return "09 Inactive trader (no activity Aug-Oct)"
    if r.trade_months_6m >= 4: return "08 High-engagement trader (>=4 trading months of last 6)"
    if r.trade_months_6m >= 2: return "07 Repeat trader (2-3 trading months of last 6)"
    return "10 Occasional trader (0-1 trading months of last 6)"
U["journey_segment"] = U.apply(journey, axis=1)
S = U.merge(SEG2[["user_id", "lifecycle_segment", "rfm_segment", "r_score", "f_score", "m_score", "flag_needs_support", "flag_support_stuck_at_funnel_stage"]], on="user_id", how="left")
S["flag_frequent_support_issues"] = ((S.ticket_count >= 3) | (S.unresolved_ticket_count >= 1)).astype(int)
S["flag_ticket_3plus"] = (S.ticket_count >= 3).astype(int)

# K-means (users with >= 90 days tenure so behavioural windows are meaningful)
KM = S[S.tenure_days >= 90].copy()
feat = pd.DataFrame(dict(activity_ratio=KM.activity_ratio, trade_months_6m=KM.trade_months_6m, log_trading_value_6m=np.log1p(KM.trading_value_6m_inr),
                         months_since_last_active=KM.months_since_last_active_monthly.fillna(12), log_first_deposit=np.log1p(KM.first_deposit_amount_asof_inr.fillna(0)),
                         ticket_count=KM.ticket_count.clip(upper=5), funnel_depth=KM.furthest_stage_asof.map({"Registered": 0, "KYC Completed": 1, "Bank Linked": 2, "Funded": 3, "Traded": 4})), index=KM.index)
Z = StandardScaler().fit_transform(feat)
sel = []
for k in range(2, 9):
    km = KMeans(k, n_init=10, random_state=SEED).fit(Z)
    labs_ = [KMeans(k, n_init=3, random_state=s).fit(Z[rng.choice(len(Z), len(Z), replace=True)]).predict(Z) for s in range(5)]
    ari = np.mean([adjusted_rand_score(labs_[i], labs_[j]) for i in range(5) for j in range(i + 1, 5)])
    sel.append(dict(k=k, inertia=km.inertia_, silhouette=silhouette_score(Z, km.labels_, sample_size=4000, random_state=SEED), bootstrap_stability_ARI=ari))
sel = pd.DataFrame(sel); save("m4_kmeans_selection", sel)
# K rule (stated up-front, not tuned after the fact): among k >= 3, keep k with bootstrap stability ARI >= 0.85, then take the highest silhouette
cand = sel[(sel.k >= 3) & (sel.bootstrap_stability_ARI >= 0.85)]
K = int(cand.loc[cand.silhouette.idxmax(), "k"])
km = KMeans(K, n_init=20, random_state=SEED).fit(Z); KM["kmeans_cluster"] = km.labels_
prof = feat.assign(cluster=km.labels_).groupby("cluster").mean()
prof["size"] = pd.Series(km.labels_).value_counts().sort_index().values; prof["share"] = prof["size"] / len(KM)
prof["first_trade_rate_funnel"] = KM.groupby("kmeans_cluster").trade_asof.mean()
prof["unresolved_ticket_pct"] = KM.groupby("kmeans_cluster").unresolved_ticket_count.apply(lambda s: (s > 0).mean())
prof["dormant_3m_rate"] = KM.groupby("kmeans_cluster").dormant_3m_monthly.mean()
# deterministic naming from centroid values (first matching rule wins)
names = {}
for c in prof.index:
    p = prof.loc[c]
    if p.trade_months_6m >= 3 and p.funnel_depth >= 3: names[c] = "Active high-value traders"
    elif p.months_since_last_active >= 3: names[c] = "Lapsed (long inactive)"
    elif p.funnel_depth < 1.5 and p.trade_months_6m >= 0.8: names[c] = "Unfunded per funnel but trading in activity log (source conflict)"
    elif p.trade_months_6m < 0.3: names[c] = "Non-trading, partly onboarded"
    elif p.funnel_depth >= 3: names[c] = "Engaged regulars"
    else: names[c] = "Other"
seen = {}
for c in prof.index:
    n = names[c]; seen[n] = seen.get(n, 0) + 1
    if seen[n] > 1: names[c] = f"{n} ({seen[n]})"
prof.insert(0, "cluster_name", pd.Series(names)); save("m4_kmeans_profile", prof.reset_index())
KM["kmeans_segment"] = KM.kmeans_cluster.map(names)
S = S.merge(KM[["user_id", "kmeans_cluster", "kmeans_segment"]], on="user_id", how="left")
R["kmeans"] = dict(n=len(KM), k=K, silhouette=float(sel.loc[sel.k == K, "silhouette"].iloc[0]), ari=float(sel.loc[sel.k == K, "bootstrap_stability_ARI"].iloc[0]), best_k_by_silhouette=int(sel.loc[sel.silhouette.idxmax(), "k"]), best_sil=float(sel.silhouette.max()))

segcols = ["user_id", "registration_month", "acquisition_channel", "age_group", "city", "device_type", "risk_profile", "tenure_days", "furthest_stage_asof", "journey_segment", "lifecycle_segment", "rfm_segment",
           "r_score", "f_score", "m_score", "kmeans_cluster", "kmeans_segment", "trade_months_6m", "trading_value_6m_inr", "activity_ratio", "months_since_last_active_monthly", "dormant_3m_monthly",
           "first_deposit_amount_asof_inr", "ticket_count", "unresolved_ticket_count", "flag_frequent_support_issues", "flag_ticket_3plus", "flag_support_stuck_at_funnel_stage", "flag_activity_conflict"]
save("Customer_Segmentation", S[segcols])
jp = S.groupby("journey_segment").agg(users=("user_id", "size"), share=("user_id", lambda s: len(s) / len(S)), avg_tenure_days=("tenure_days", "mean"),
                                         pct_frequent_support_issues=("flag_frequent_support_issues", "mean"), median_first_deposit_inr=("first_deposit_amount_asof_inr", "median"),
                                         avg_trading_value_6m_inr=("trading_value_6m_inr", "mean"), pct_source_conflict=("flag_activity_conflict", "mean")).reset_index()
save("m4_journey_segment_profile", jp); R["journey_segments"] = jp.to_dict("records")
save("m4_rfm_profile", S[S.rfm_segment.notna()].groupby("rfm_segment").agg(users=("user_id", "size"), avg_trading_value_6m_inr=("trading_value_6m_inr", "mean"), avg_trade_months_6m=("trade_months_6m", "mean"),
                                                                              dormant_rate=("dormant_3m_monthly", "mean"), pct_support_issues=("flag_frequent_support_issues", "mean")).reset_index())
save("m4_kmeans_vs_journey_crosstab", pd.crosstab(S.kmeans_segment, S.journey_segment).reset_index())

# ======================================================================================
# MODULE 5 - CAMPAIGN SCORECARD
# ======================================================================================
sc = cp.copy()
n_c = len(sc)
def rank_score(s, higher_better=True):
    r = s.rank(ascending=not higher_better, method="min"); n = s.notna().sum()
    return 100 * (n - r) / (n - 1) if n > 1 else np.nan
sc["qs_kyc"] = rank_score(sc.kyc_rate_mature); sc["qs_trade"] = rank_score(sc.first_trade_rate_mature); sc["qs_active"] = rank_score(sc.active_30d_rate); sc["qs_m3"] = rank_score(sc.m3_retention)
sc["quality_score"] = sc[["qs_kyc", "qs_trade", "qs_active", "qs_m3"]].mean(axis=1)
sc["cs_cost_kyc"] = rank_score(sc.cost_per_kyc_at_maturity_inr, False); sc["cs_cost_trade"] = rank_score(sc.cost_per_first_trade_at_maturity_inr, False)
sc["cost_efficiency_score"] = sc[["cs_cost_kyc", "cs_cost_trade"]].mean(axis=1)
sc["overall_score"] = np.where(sc.cost_efficiency_score.notna(), (sc.quality_score + sc.cost_efficiency_score) / 2, np.nan)
sc["overall_rank_paid"] = sc.overall_score.rank(ascending=False, method="min")
sc["quality_rank_all"] = sc.quality_score.rank(ascending=False, method="min")
sc["scorecard_tier"] = np.select([sc.overall_score >= 75, sc.overall_score >= 40, sc.overall_score.notna()], ["A - scale / protect", "B - maintain & optimise", "C - fix or cut back"], "Organic - quality only")
sc = sc.merge(z[["campaign_id", "diff_pp", "p_holm", "significant_at_5pct_holm"]].rename(columns={"diff_pp": "first_trade_diff_vs_others_pp", "p_holm": "first_trade_p_holm"}), on="campaign_id")
sc["revenue_data_available"] = "No - ROI not calculated"
save("Campaign_Performance", sc)
R["campaign_scorecard"] = sc[["campaign_id", "campaign_name", "channel", "campaign_spend_inr", "registered_users", "cac_inr", "cost_per_first_trade_at_maturity_inr", "first_trade_rate_mature", "kyc_rate_mature", "active_30d_rate", "m3_retention",
                              "quality_score", "cost_efficiency_score", "overall_score", "scorecard_tier", "first_trade_diff_vs_others_pp", "first_trade_p_holm", "first_trade_ci_low", "first_trade_ci_high", "cost_per_first_trade_ci_low", "cost_per_first_trade_ci_high"]].to_dict("records")

# budget reallocation arithmetic (a SCENARIO, not a forecast): move budget between campaigns at constant observed efficiency, with a cost penalty p on destinations
paid = sc[sc.is_paid == 1].set_index("campaign_id")
worst = paid.cost_per_first_trade_at_maturity_inr.sort_values(ascending=False).index[:2].tolist()
best = paid.cost_per_first_trade_at_maturity_inr.sort_values().index[:2].tolist()
shift_pct = .25
moved = paid.loc[worst, "campaign_spend_inr"].sum() * shift_pct
src_cost = (paid.loc[worst, "campaign_spend_inr"] * shift_pct).sum() / (paid.loc[worst, "campaign_spend_inr"] * shift_pct / paid.loc[worst, "cost_per_first_trade_at_maturity_inr"]).sum()
dst_cost = moved / (moved / 2 / paid.loc[best[0], "cost_per_first_trade_at_maturity_inr"] + moved / 2 / paid.loc[best[1], "cost_per_first_trade_at_maturity_inr"])
base_traders = (paid.campaign_spend_inr / paid.cost_per_first_trade_at_maturity_inr).sum()
sc_rows = []
for pen in [0, .25, .5, 1.0, 1.5]:
    gain = moved / (dst_cost * (1 + pen)) - moved / src_cost
    sc_rows.append(dict(scenario=f"Move {int(shift_pct*100)}% of {worst[0]} & {worst[1]} budgets (Rs {moved:,.0f}) to {best[0]} & {best[1]}", destination_cost_penalty=f"+{int(pen*100)}%",
                        source_cost_per_first_trader_inr=src_cost, destination_cost_per_first_trader_inr=dst_cost * (1 + pen), first_traders_lost=moved / src_cost, first_traders_gained=moved / (dst_cost * (1 + pen)),
                        net_change_first_traders=gain, net_change_pct_of_paid_baseline=gain / base_traders))
rb = pd.DataFrame(sc_rows); save("m5_budget_reallocation_scenarios", rb)
R["realloc"] = dict(worst=worst, best=best, moved=float(moved), src_cost=float(src_cost), dst_cost=float(dst_cost), breakeven_penalty=float(src_cost / dst_cost - 1), base_traders=float(base_traders), table=rb.to_dict("records"))

# ======================================================================================
# MODULE 6 - SUPPORT
# ======================================================================================
n_t = len(T); n_cm = len(M)
R["tickets"] = n_t; R["tickets_per_1000_users"] = n_t / len(U) * 1000; R["tickets_per_1000_cm"] = n_t / n_cm * 1000
R["users_with_ticket_pct"] = float((U.ticket_count > 0).mean())
res = T[T.is_resolved == 1]
R["resolved_pct"] = float(T.is_resolved.mean()); R["open_n"] = int((T.status == "Open").sum()); R["escalated_n"] = int((T.status == "Escalated").sum())
R["res_mean"] = float(res.resolution_time_hours.mean()); R["res_median"] = float(res.resolution_time_hours.median()); R["res_p90"] = float(res.resolution_time_hours.quantile(.9))
R["csat_mean"] = float(res.csat_score.mean()); R["csat_low_pct"] = float((res.csat_score <= 2).mean()); R["csat_high_pct"] = float((res.csat_score >= 4).mean())
R["backlog_over_90"] = int(((T.is_unresolved == 1) & (T.ticket_age_days > 90)).sum()); R["backlog_over_180"] = int(((T.is_unresolved == 1) & (T.ticket_age_days > 180)).sum())
cat = T.groupby("category").agg(tickets=("ticket_id", "size"), share=("ticket_id", lambda s: len(s) / n_t), resolved=("is_resolved", "sum"), unresolved=("is_unresolved", "sum"),
                                escalated=("status", lambda s: (s == "Escalated").sum()), median_res_h=("resolution_time_hours", "median"), mean_res_h=("resolution_time_hours", "mean"),
                                p90_res_h=("resolution_time_hours", lambda s: s.quantile(.9)), csat=("csat_score", "mean"), csat_low_pct=("csat_score", lambda s: (s.dropna() <= 2).mean()),
                                high_priority_pct=("priority", lambda s: (s == "High").mean())).reset_index()
cat["unresolved_pct"] = cat.unresolved / cat.tickets; cat["tickets_per_1000_users"] = cat.tickets / len(U) * 1000; cat["tickets_per_1000_customer_months"] = cat.tickets / n_cm * 1000
stage_pend = T.groupby("category").stage_pending_at_ticket.mean().rename("pct_raised_while_stage_pending").reset_index(); cat = cat.merge(stage_pend, on="category", how="left")
cat = cat.sort_values("tickets", ascending=False); save("m6_ticket_categories", cat)
pri = T.groupby("priority").agg(tickets=("ticket_id", "size"), escalated_pct=("status", lambda s: (s == "Escalated").mean()), open_pct=("status", lambda s: (s == "Open").mean()), median_res_h=("resolution_time_hours", "median"),
                                 mean_res_h=("resolution_time_hours", "mean"), csat=("csat_score", "mean")).reset_index(); save("m6_priority", pri)
cr = res[["priority", "resolution_time_hours"]]; kw = stats.kruskal(*[g.resolution_time_hours for _, g in cr.groupby("priority")]); R["priority_res_kruskal_p"] = float(kw.pvalue)
mt = T.groupby("created_month").agg(tickets=("ticket_id", "size")).reset_index().merge(M.groupby("activity_month").size().rename("customer_months").reset_index().rename(columns={"activity_month": "created_month"}), on="created_month")
mt["tickets_per_1000_customer_months"] = mt.tickets / mt.customer_months * 1000; save("m6_tickets_monthly", mt)
csat_res = res.groupby(pd.cut(res.resolution_time_hours, [0, 4, 8, 12, 24, 100], labels=["<=4h", "4-8h", "8-12h", "12-24h", ">24h"])).agg(tickets=("ticket_id", "size"), csat=("csat_score", "mean")).reset_index(); save("m6_csat_by_resolution_time", csat_res)
R["csat_corr_res_time"] = float(res[["resolution_time_hours", "csat_score"]].corr(method="spearman").iloc[0, 1])
bk = T[T.is_unresolved == 1].groupby("backlog_age_bucket").size().reindex(["0-30d", "31-90d", "91-180d", ">180d"]).rename("tickets").reset_index(); save("m6_backlog_ageing", bk)
ten = T.merge(U[["user_id", "device_type", "acquisition_channel", "age_group"]], on="user_id")
for dim in ["device_type", "acquisition_channel", "age_group"]:
    base = M.merge(U[["user_id", dim]], on="user_id").groupby(dim).size().rename("customer_months")
    x = ten.groupby(dim).size().rename("tickets").to_frame().join(base); x["tickets_per_1000_customer_months"] = x.tickets / x.customer_months * 1000
    save(f"m6_tickets_by_{dim}", x.reset_index())
# support vs inactivity - tenure-controlled (cohort fixed effects)
SE = U[U.dormant_3m_monthly.notna()].copy()
SE["any_ticket"] = (SE.ticket_count > 0).astype(int); SE["any_unresolved"] = (SE.unresolved_ticket_count > 0).astype(int); SE["ticket_3plus"] = (SE.ticket_count >= 3).astype(int)
sup_rows = []
def mh_or(df, exp, out="dormant_3m_monthly"):
    num = den = 0.0
    for _, d in df.groupby("registration_month"):
        a = ((d[exp] == 1) & (d[out] == 1)).sum(); b = ((d[exp] == 1) & (d[out] == 0)).sum(); c = ((d[exp] == 0) & (d[out] == 1)).sum(); dd = ((d[exp] == 0) & (d[out] == 0)).sum(); n = len(d)
        num += a * dd / n; den += b * c / n
    return num / den if den else np.nan
for exp, lab in [("any_ticket", "Raised any ticket"), ("any_unresolved", "Has an unresolved (Open/Escalated) ticket"), ("ticket_3plus", "Raised 3+ tickets")]:
    d1 = SE[SE[exp] == 1]; d0 = SE[SE[exp] == 0]; orr = mh_or(SE, exp)
    boots = []
    for _ in range(300):
        bs = SE.sample(len(SE), replace=True, random_state=int(rng.integers(1e9))); boots.append(mh_or(bs, exp))
    lo, hi = np.nanpercentile(boots, [2.5, 97.5])
    sup_rows.append(dict(exposure=lab, users_exposed=len(d1), dormant_rate_exposed=d1.dormant_3m_monthly.mean(), dormant_rate_unexposed=d0.dormant_3m_monthly.mean(),
                         crude_diff_pp=(d1.dormant_3m_monthly.mean() - d0.dormant_3m_monthly.mean()) * 100, mantel_haenszel_odds_ratio_cohort_adjusted=orr, or_ci_low=lo, or_ci_high=hi))
sup = pd.DataFrame(sup_rows); save("m6_support_vs_inactivity", sup); R["support_vs_inactivity"] = sup.to_dict("records")
cs_ = res.merge(U[["user_id", "dormant_3m_monthly"]], on="user_id"); cs_ = cs_[cs_.dormant_3m_monthly.notna()]
csat_in = cs_.groupby(pd.cut(cs_.csat_score, [0, 2, 3, 5], labels=["CSAT 1-2", "CSAT 3", "CSAT 4-5"])).agg(tickets=("ticket_id", "size"), user_dormant_rate=("dormant_3m_monthly", "mean")).reset_index(); save("m6_csat_vs_dormancy", csat_in)
stuck = []
for _, key, catn in stages:
    d = MU[MU[f"{key}_asof"] == 0]; pend = tk[(tk.category == catn) & (tk.stage_pending_at_ticket == 1)].user_id.unique()
    stuck.append(dict(stage_not_completed=key, mature_users_stuck=len(d), raised_related_ticket_pct=d.user_id.isin(pend).mean(), tickets_unresolved_among_raisers=float(tk[(tk.category == catn) & tk.user_id.isin(d.user_id)].is_unresolved.mean())))
save("m6_stuck_users_and_tickets", pd.DataFrame(stuck))
R["support_cats"] = cat.to_dict("records"); R["priority"] = pri.to_dict("records")

# ======================================================================================
json.dump(R, open(OUT / "results.json", "w"), indent=1, default=lambda o: (None if (isinstance(o, float) and np.isnan(o)) else float(o) if isinstance(o, (np.floating,)) else int(o) if isinstance(o, np.integer) else str(o)))
print("done", len(list(OUT.glob("*.csv"))), "tables")
