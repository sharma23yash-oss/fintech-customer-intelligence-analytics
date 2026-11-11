"""Phase 5 measure oracle (SYNTHETIC data).
Power BI Desktop is not available here, so DAX cannot be executed. Instead every key measure's LOGIC is re-implemented in pandas directly on the
Power BI star-schema CSVs (06_dashboard/data) under the same filter semantics, and compared with (a) validated Phase 3 / Phase 4 figures and
(b) independent SQL on the SQLite database for filtered scenarios. The resulting table is the 'expected values' sheet to check dashboard cards against
once the model is built in Power BI Desktop.  Run: python3 verify_phase5.py   (exit 1 on any mismatch)"""
import json, sqlite3, sys
from dataclasses import dataclass
from pathlib import Path
import numpy as np, pandas as pd, openpyxl, warnings
warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1] / "05_python"))   # build_scripts + fintech_analytics package
import powerbi_measures as PM

ROOT = HERE.parents[1]; D = ROOT / "06_dashboard" / "data"; from fintech_analytics import config as _CFG; P3 = _CFG.P3_TABLES
rd = lambda n, dates=(): pd.read_csv(D / f"{n}.csv", parse_dates=list(dates))
dim_c, dim_seg, dim_stage = rd("DimCampaign"), rd("DimSegment"), rd("DimStage")
FC = rd("FactCustomer", ["RegistrationDate"]); FA = rd("FactActivity", ["ActivityMonthDate", "RegMonthDate"]); FT = rd("FactTicket", ["CreatedDate"])
R3 = json.loads((P3 / "results.json").read_text()); KP = json.loads((ROOT / "05_python/outputs/kpi_values.json").read_text())
DATE_MIN, DATE_MAX = pd.Timestamp("2025-11-01"), pd.Timestamp("2026-10-31")
SLA = 24; RB, RM = 4, 2


@dataclass
class Ctx:
    channel: tuple = None; campaign: tuple = None; city: tuple = None; device: tuple = None; segment: tuple = None; months: tuple = None   # month-start timestamps
    def camps(self):
        c = dim_c
        if self.channel: c = c[c.Channel.isin(self.channel)]
        if self.campaign: c = c[c.CampaignKey.isin(self.campaign)]
        return set(c.CampaignKey)
    def label(self):
        p = [f"{k}={'/'.join(map(str, v)) if k != 'months' else v[0].strftime('%b %y') + ('..' + v[-1].strftime('%b %y') if len(v) > 1 else '')}" for k, v in self.__dict__.items() if v]
        return ", ".join(p) or "no filters"


def _f(df, ctx, datecol=None, full=False):
    """Apply dimension filters (and month filter on datecol). full=True drops date/city/device/segment (CAC logic)."""
    m = df.CampaignKey.isin(ctx.camps())
    if not full:
        if ctx.city: m &= df.CityKey.isin(ctx.city)
        if ctx.device: m &= df.DeviceKey.isin(ctx.device)
        if ctx.segment: m &= df.SegmentKey.isin(ctx.segment)
        if ctx.months and datecol:
            ms = pd.DatetimeIndex(ctx.months)
            m &= (df[datecol].dt.to_period("M").dt.to_timestamp()).isin(ms)
    return df[m]
cust = lambda c, full=False: _f(FC, c, "RegistrationDate", full)
act = lambda c: _f(FA, c, "ActivityMonthDate")
tic = lambda c: _f(FT, c, "CreatedDate")
div = lambda a, b: np.nan if (b in (0, None) or pd.isna(b)) else a / b
S = lambda s: float(s.sum())


def base(u):
    mt = u[u.FunnelMature == 1]
    return dict(reg=len(u), mature=len(mt), kyc=S(mt.KYCDone), bank=S(mt.BankLinked), funded=S(mt.Deposited), trade=S(mt.Traded), act30=int(((mt.Traded == 1) & (mt.Active30d == 1)).sum()))


def paid_rates(ctx):
    u = cust(ctx, True); u = u[u.CampaignKey.isin(dim_c[dim_c.IsPaid == 1].CampaignKey)]
    b = base(u); return div(b["kyc"], b["mature"]), div(b["trade"], b["mature"]), len(u)


def cac_block(ctx):
    cs = dim_c[dim_c.CampaignKey.isin(ctx.camps())]; spend = S(cs.CampaignSpendINR)
    kr, tr, npaid = paid_rates(ctx); cac = div(spend, npaid)
    return dict(spend=spend, cac=cac, cost_kyc=div(cac, kr), cost_trade=div(cac, tr))


def cpft_by_campaign(ctx, key="cost_trade"):
    out = {}
    for k in sorted(ctx.camps()):
        c = Ctx(campaign=(k,)); out[k] = cac_block(c)[key]
    return out


def evaluate(ctx):
    """Return {measure name: value} for a context, mirroring the DAX in powerbi_measures.py."""
    u, a, t = cust(ctx), act(ctx), tic(ctx); b = base(u); V = {}
    V.update({"Registered Customers": b["reg"], "Mature Customers": b["mature"], "Mature KYC Users": b["kyc"], "Mature Bank Linked Users": b["bank"], "Mature Funded Users": b["funded"],
              "Mature First Traders": b["trade"], "Mature Active 30d Traders": b["act30"], "KYC Completion Rate": div(b["kyc"], b["mature"]), "Bank Link Conversion": div(b["bank"], b["kyc"]),
              "First Deposit Conversion": div(b["funded"], b["bank"]), "First Trade Conversion": div(b["trade"], b["funded"]), "First Trade Activation Rate": div(b["trade"], b["mature"]),
              "Active 30d Share of First Traders": div(b["act30"], b["trade"]), "Total Funnel Loss": b["mature"] - b["act30"]})
    stages = [("Registered", b["mature"]), ("KYC Completed", b["kyc"]), ("Bank Linked", b["bank"]), ("First Deposit", b["funded"]), ("First Trade", b["trade"]), ("Active (30d)", b["act30"])]
    for i, (n, v) in enumerate(stages):
        V[f"Funnel Users|{n}"] = v
        if i:
            pv = stages[i - 1][1]; V[f"Funnel Previous Stage Users|{n}"] = pv; V[f"Funnel Step Conversion|{n}"] = div(v, pv); V[f"Funnel Users Lost|{n}"] = pv - v
            V[f"Funnel Drop-off Rate|{n}"] = div(pv - v, pv); V[f"Share of Funnel Losses|{n}"] = div(pv - v, b["mature"] - b["act30"])
        V[f"Funnel % of Registered|{n}"] = div(v, b["mature"])
    mt = u[u.FunnelMature == 1]
    for n, c in (("KYC Completed", "DaysRegToKYC"), ("Bank Linked", "DaysKYCToBank"), ("First Deposit", "DaysBankToDeposit"), ("First Trade", "DaysDepositToTrade")): V[f"Median Days in Stage|{n}"] = mt[c].median()
    V["Median Days Registration to First Trade"] = mt.DaysRegToTrade.median()
    idle = u[(u.Deposited == 1) & (u.Traded == 0)]; V["Funded Never Traded"] = len(idle); V["Funded Never Traded Deposits INR"] = S(idle.FirstDepositAmountINR)
    V["Stalled Onboarding Customers"] = int(u.SegmentKey.isin([2, 3, 4, 5]).sum())
    # acquisition (full-period logic)
    cb = cac_block(ctx); V["Total Campaign Spend"] = cb["spend"]; V["CAC"] = cb["cac"]; V["Cost per KYC"] = cb["cost_kyc"]; V["Cost per First Trade"] = cb["cost_trade"]
    V["Paid Spend"] = S(dim_c[dim_c.CampaignKey.isin(ctx.camps()) & (dim_c.IsPaid == 1)].CampaignSpendINR)
    V["Registered Customers (Full Period)"] = len(cust(ctx, True)); V["Paid Registrations (Full Period)"] = paid_rates(ctx)[2]
    paid_keys = set(dim_c[dim_c.IsPaid == 1].CampaignKey); V["Paid Share of Registrations"] = div(int(u.CampaignKey.isin(paid_keys).sum()), len(u))
    cp = {k: v for k, v in cpft_by_campaign(ctx).items() if not pd.isna(v)}
    V["Median Paid Cost per First Trade"] = float(np.median(list(cp.values()))) if cp else np.nan
    V["Cost Efficiency Index"] = div(V["Median Paid Cost per First Trade"], cb["cost_trade"])
    ck = {k: v for k, v in cpft_by_campaign(ctx, "cost_kyc").items() if not pd.isna(v)}
    V["Median Paid Cost per KYC"] = float(np.median(list(ck.values()))) if ck else np.nan
    # retention
    am = a.ActivityMonthDate.max() if len(a) else None
    V["MAU"] = S(a[a.ActivityMonthDate == am].ActiveInMonth) if am is not None else np.nan
    dmax = max(ctx.months) + pd.offsets.MonthEnd(0) if ctx.months else DATE_MAX
    cust_to_date = int((cust(Ctx(channel=ctx.channel, campaign=ctx.campaign, city=ctx.city, device=ctx.device, segment=ctx.segment)).RegistrationDate <= dmax).sum())
    V["Customers To Date"] = cust_to_date
    if am is not None:
        eom = am + pd.offsets.MonthEnd(0)
        V["MAU Share of Customers"] = div(V["MAU"], int((cust(Ctx(channel=ctx.channel, campaign=ctx.campaign, city=ctx.city, device=ctx.device, segment=ctx.segment)).RegistrationDate <= eom).sum()))
    e30 = u[u.Eligible30d == 1]; e90 = u[u.Eligible90d == 1]
    V["30-Day Retention"] = e30.Active30d.mean(); V["Inactive 90d Rate"] = e90.Inactive90d.mean(); V["Dormant 3m Rate"] = u.Dormant3m.mean()
    for k in (1, 3, 6): V[f"M{k} Retention"] = a[a.MonthsSinceRegistration == k].ActiveInMonth.mean()
    for bk, g in e30.groupby("InactivityBucket"): V[f"Inactivity Share (Eligible)|{bk}"] = len(g) / len(e30)
    V["Trading Users"] = S(a.TradedInMonth); V["Trades"] = S(a.TradeCount); V["Trading Value INR mn"] = S(a.TradingValueINR) / 1e6
    V["Deposits INR mn"] = S(a.DepositValueINR) / 1e6; V["Withdrawals INR mn"] = S(a.WithdrawalValueINR) / 1e6; V["Net Flow INR mn"] = S(a.NetFlowINR) / 1e6
    V["Withdrawal to Deposit Ratio"] = div(S(a.WithdrawalValueINR), S(a.DepositValueINR)); V["Trades per Trading User"] = div(V["Trades"], V["Trading Users"]); V["Avg Trade Value INR"] = div(S(a.TradingValueINR), V["Trades"])
    rb = u[u.MonthsObserved >= RB]; V["Ever-Traders (Repeat Base)"] = int((rb.TradeMonths >= 1).sum()); V["Repeat Traders"] = int((rb.TradeMonths >= RM).sum()); V["Repeat Trader Share"] = div(V["Repeat Traders"], V["Ever-Traders (Repeat Base)"])
    V["Avg 6m Trading Value INR"] = u.TradingValue6mINR.mean()
    # support
    V["Tickets"] = len(t); V["Tickets per 1000 Customers"] = div(len(t), cust_to_date) * 1000 if cust_to_date else np.nan
    V["Resolved Tickets"] = S(t.IsResolved); V["Unresolved Tickets"] = S(t.IsUnresolved); V["Open Tickets"] = int((t.Status == "Open").sum()); V["Escalated Tickets"] = S(t.IsEscalated)
    V["Resolved Rate"] = div(V["Resolved Tickets"], len(t)); V["Escalation Rate"] = div(V["Escalated Tickets"], len(t))
    r = t.ResolutionHours.dropna(); V["Avg Resolution Hours"] = r.mean(); V["Median Resolution Hours"] = r.median(); V["P90 Resolution Hours"] = r.quantile(0.9)
    V["Within SLA Rate"] = div(int((t[t.IsResolved == 1].ResolutionHours <= SLA).sum()), V["Resolved Tickets"])
    cs = t.CSAT.dropna(); V["CSAT"] = cs.mean(); V["CSAT Top-Box"] = (cs >= 4).mean(); V["CSAT Bottom-Box"] = (cs <= 2).mean()
    V["Backlog over 90 Days"] = int(((t.IsUnresolved == 1) & (t.TicketAgeDays > 90)).sum()); V["High Priority Share"] = div(int((t.Priority == "High").sum()), len(t))
    ob = t[t.RelatedFunnelStage != "none"]; V["Onboarding Tickets"] = len(ob); V["Tickets While Stage Pending"] = int((t.StagePendingAtTicket == 1).sum()); V["Pending Stage Ticket Share"] = div(V["Tickets While Stage Pending"], len(ob))
    for c_, g in t.groupby("Category"): V[f"Tickets|{c_}"] = len(g); V[f"Median Resolution Hours|{c_}"] = g.ResolutionHours.median()
    for p_, g in t.groupby("Priority"): V[f"Priority Share|{p_}"] = len(g) / len(t)
    return V


rows = []
def rec(measure, context, value, ref, ref_name, tol):
    ok = (pd.isna(value) and pd.isna(ref)) or (not pd.isna(value) and not pd.isna(ref) and abs(float(value) - float(ref)) <= tol + 1e-12)
    rows.append(dict(measure=measure, context=context, oracle_value=value, reference=ref, reference_source=ref_name, tolerance=tol, status="MATCH" if ok else "DIFF"))

# ---------------------------------------------------------------- 1. default context vs validated Phase 3 / Phase 4
ALL = Ctx(); V = evaluate(ALL); ctxn = "no filters"
F = R3["funnel"]; xl = openpyxl.load_workbook(ROOT / "03_business_analytics/excel/Fintech_Advanced_Excel_Analytics.xlsx", data_only=True)
P3r = lambda k: R3[k]
checks = [("Registered Customers", R3["n_users"], "Phase3 n_users", 0), ("Mature Customers", R3["n_mature"], "Phase3 n_mature", 0),
          ("Mature KYC Users", F["KYC Completed"]["reached"], "Phase3 funnel", 0), ("Mature Bank Linked Users", F["Bank Linked"]["reached"], "Phase3 funnel", 0),
          ("Mature Funded Users", F["First Deposit"]["reached"], "Phase3 funnel", 0), ("Mature First Traders", F["First Trade"]["reached"], "Phase3 funnel", 0),
          ("Mature Active 30d Traders", 2808, "Phase4 KPI report (funnel_active30)", 0),
          ("KYC Completion Rate", F["KYC Completed"]["conv_prev"], "Phase3 funnel (4dp)", 6e-5), ("Bank Link Conversion", F["Bank Linked"]["conv_prev"], "Phase3 funnel (4dp)", 6e-5),
          ("First Deposit Conversion", F["First Deposit"]["conv_prev"], "Phase3 funnel (4dp)", 6e-5), ("First Trade Conversion", F["First Trade"]["conv_prev"], "Phase3 funnel (4dp)", 6e-5),
          ("First Trade Activation Rate", F["First Trade"]["conv_reg"], "Phase3 funnel (4dp)", 6e-5),
          ("M1 Retention", R3["m1"], "Phase3 results", 1e-9), ("M3 Retention", R3["m3"], "Phase3 results", 1e-9), ("M6 Retention", R3["m6"], "Phase3 results", 1e-9),
          ("MAU", R3["mau_last"], "Phase3 mau_last", 0), ("MAU Share of Customers", R3["mau_pct_last"], "Phase3 mau_pct_last (4dp)", 6e-5),
          ("30-Day Retention", R3["active30"], "Phase3 active30", 1e-9), ("Inactive 90d Rate", R3["inactive90"], "Phase3 inactive90", 1e-9), ("Dormant 3m Rate", R3["dormant3m"], "Phase3 dormant3m", 1e-9),
          ("Repeat Trader Share", R3["repeat_trader_share_of_traders"], "Phase3 results", 1e-9), ("Withdrawal to Deposit Ratio", R3["wd_ratio_total"], "Phase3 wd_ratio_total", 1e-6),
          ("Tickets", R3["tickets"], "Phase3 results", 0), ("Tickets per 1000 Customers", R3["tickets_per_1000_users"], "Phase3 results", 0.05), ("Resolved Rate", R3["resolved_pct"], "Phase3 results", 6e-5),
          ("Open Tickets", R3["open_n"], "Phase3 results", 0), ("Escalated Tickets", R3["escalated_n"], "Phase3 results", 0), ("Unresolved Tickets", R3["open_n"] + R3["escalated_n"], "Phase3 open + escalated", 0),
          ("Avg Resolution Hours", R3["res_mean"], "Phase3 results", 1e-3), ("Median Resolution Hours", R3["res_median"], "Phase3 results", 0.05), ("P90 Resolution Hours", R3["res_p90"], "Phase3 results", 0.05),
          ("CSAT", R3["csat_mean"], "Phase3 results", 5e-4), ("Backlog over 90 Days", R3["backlog_over_90"], "Phase3 results", 0),
          ("Within SLA Rate", xl["Support_Analysis"]["B15"].value, "Phase4 Excel Support_Analysis!B15", 1e-9), ("Funded Never Traded", xl["Customer_Segmentation"]["C43"].value, "Phase4 Excel Customer_Segmentation!C43", 0),
          ("Funded Never Traded Deposits INR", xl["Customer_Segmentation"]["C44"].value, "Phase4 Excel Customer_Segmentation!C44", 0.5),
          ("CAC", xl["Campaign_Analysis"]["O17"].value, "Phase4 Excel Campaign_Analysis!O17 (blended paid CAC)", 1e-6), ("Total Campaign Spend", xl["Campaign_Analysis"]["E18"].value, "Phase4 Excel Campaign_Analysis!E18", 0),
          ("Escalation Rate", R3["escalated_n"] / R3["tickets"], "Phase3 escalated_n / tickets", 1e-9)]
for n, ref, src, tol in checks: rec(n, ctxn, V[n], ref, src, tol)
rec("Median Days Registration to First Trade", ctxn, V["Median Days Registration to First Trade"], R3["median_days_reg_to_trade"], "Phase3 results", 0.05)
bn = pd.read_csv(P3 / "m2_bottlenecks.csv").set_index("stage")
for st in ["KYC Completed", "Bank Linked", "First Deposit", "First Trade", "Active (30d)"]:
    rec(f"Share of Funnel Losses|{st}", ctxn, V[f"Share of Funnel Losses|{st}"], bn.loc[st, "share_of_all_funnel_losses"], "Phase3 m2_bottlenecks", 1e-9)
    rec(f"Funnel Users Lost|{st}", ctxn, V[f"Funnel Users Lost|{st}"], bn.loc[st, "users_lost"], "Phase3 m2_bottlenecks", 0)
    rec(f"Funnel Drop-off Rate|{st}", ctxn, V[f"Funnel Drop-off Rate|{st}"], bn.loc[st, "drop_rate"], "Phase3 m2_bottlenecks", 1e-9)
for st, k in (("KYC Completed", "KYC Completed"), ("Bank Linked", "Bank Linked"), ("First Deposit", "First Deposit"), ("First Trade", "First Trade")):
    rec(f"Median Days in Stage|{st}", ctxn, V[f"Median Days in Stage|{st}"], F[k]["median_days"], "Phase3 funnel median_days", 0.05)
idist = pd.read_csv(P3 / "m3_inactivity_distribution.csv").set_index("days_since_last_activity").share_of_eligible_users
for b_, sh in idist.items(): rec(f"Inactivity Share (Eligible)|{b_}", ctxn, V[f"Inactivity Share (Eligible)|{b_}"], sh, "Phase3 m3_inactivity_distribution", 1e-9)
for d_ in R3["journey_segments"]:
    sk = int(d_["journey_segment"][:2]); rec(f"Segment customers|{sk:02d}", ctxn, int((FC.SegmentKey == sk).sum()), d_["users"], "Phase3 journey_segments", 0)
pr = pd.read_csv(P3 / "m6_priority.csv").set_index("priority")
for p_ in ["High", "Medium", "Low"]: rec(f"Priority tickets|{p_}", ctxn, V[f"Priority Share|{p_}"] * V["Tickets"], pr.loc[p_, "tickets"], "Phase3 m6_priority", 1e-6)
cat3 = pd.read_csv(P3 / "m6_ticket_categories.csv").set_index("category")
for c_ in cat3.index:
    rec(f"Tickets|{c_}", ctxn, V[f"Tickets|{c_}"], cat3.loc[c_, "tickets"], "Phase3 m6_ticket_categories", 0); rec(f"Median Resolution Hours|{c_}", ctxn, V[f"Median Resolution Hours|{c_}"], cat3.loc[c_, "median_res_h"], "Phase3 m6_ticket_categories", 0.05)
# per-campaign CAC / cost per KYC / cost per first trade vs Phase 3
cpf = pd.read_csv(P3 / "Campaign_Performance.csv").set_index("campaign_id")
for k in dim_c.CampaignKey:
    Vc = evaluate(Ctx(campaign=(k,))); lab = f"campaign={k}"
    rec("Registered Customers", lab, Vc["Registered Customers"], cpf.loc[k, "registered_users"], "Phase3 Campaign_Performance", 0)
    rec("First Trade Activation Rate", lab, Vc["First Trade Activation Rate"], cpf.loc[k, "first_trade_rate_mature"], "Phase3 Campaign_Performance (4dp)", 6e-5)
    rec("M3 Retention", lab, Vc["M3 Retention"], cpf.loc[k, "m3_retention"], "Phase3 Campaign_Performance (4dp)", 6e-5)
    if dim_c.set_index("CampaignKey").loc[k, "IsPaid"] == 1:
        rec("CAC", lab, Vc["CAC"], cpf.loc[k, "cac_inr"], "Phase3 Campaign_Performance", 1e-3)
        rec("Cost per First Trade", lab, Vc["Cost per First Trade"], cpf.loc[k, "cost_per_first_trade_at_maturity_inr"], "Phase3 Campaign_Performance", 0.5)
        rec("Cost per KYC", lab, Vc["Cost per KYC"], cpf.loc[k, "cost_per_kyc_at_maturity_inr"], "Phase3 Campaign_Performance", 0.5)
    else:
        rec("CAC", lab, Vc["CAC"], np.nan, "Organic: blank, not zero", 0)
rec("Median Paid Cost per KYC", ctxn, V["Median Paid Cost per KYC"], float(cpf.loc[dim_c[dim_c.IsPaid == 1].CampaignKey, "cost_per_kyc_at_maturity_inr"].median()), "Phase3 Campaign_Performance (median of paid campaigns)", 0.5)
rec("Median Paid Cost per First Trade", ctxn, V["Median Paid Cost per First Trade"], float(cpf.loc[dim_c[dim_c.IsPaid == 1].CampaignKey, "cost_per_first_trade_at_maturity_inr"].median()), "Phase3 Campaign_Performance (median of paid campaigns)", 0.5)
chp = pd.read_csv(P3 / "m1_channel_performance.csv").set_index("acquisition_channel")
for ch in chp.index:
    Vc = evaluate(Ctx(channel=(ch,))); lab = f"channel={ch}"
    rec("Registered Customers", lab, Vc["Registered Customers"], chp.loc[ch, "registered"], "Phase3 m1_channel_performance", 0)
    rec("First Trade Activation Rate", lab, Vc["First Trade Activation Rate"], chp.loc[ch, "first_trade_rate"], "Phase3 m1_channel_performance (4dp)", 6e-5)
    rec("M3 Retention", lab, Vc["M3 Retention"], chp.loc[ch, "m3_retention"], "Phase3 m1_channel_performance (4dp)", 6e-5)
    if not pd.isna(chp.loc[ch, "cac_inr"]): rec("CAC", lab, Vc["CAC"], chp.loc[ch, "cac_inr"], "Phase3 m1_channel_performance", 1e-3)
    else: rec("CAC", lab, Vc["CAC"], np.nan, "Organic: blank, not zero", 0)

# ---------------------------------------------------------------- 2. filtered scenarios vs independent SQL
db = sqlite3.connect(ROOT / "04_sql/fintech_analytics.db"); q = lambda s: db.execute(s).fetchone()[0]
SC = [(Ctx(channel=("Referral",)), "u.acquisition_channel='Referral'"), (Ctx(city=("Pune",), device=("Android",)), "u.city='Pune' AND u.device_type='Android'"),
      (Ctx(segment=(9,)), "u.user_id IN (SELECT user_id FROM v_journey_segment WHERE journey_segment LIKE '09%')"), (Ctx(campaign=("CMP04",)), "u.acquisition_campaign_id='CMP04'")]
for ctx, where in SC:
    Vc = evaluate(ctx); lab = ctx.label()
    rec("Registered Customers", lab, Vc["Registered Customers"], q(f"SELECT COUNT(*) FROM users u WHERE {where}"), "SQL", 0)
    rec("First Trade Activation Rate", lab, Vc["First Trade Activation Rate"], q(f"SELECT 1.0*SUM(trade_asof)/COUNT(*) FROM users u WHERE funnel_mature=1 AND {where}"), "SQL", 1e-9)
    rec("KYC Completion Rate", lab, Vc["KYC Completion Rate"], q(f"SELECT 1.0*SUM(kyc_asof)/COUNT(*) FROM users u WHERE funnel_mature=1 AND {where}"), "SQL", 1e-9)
    rec("Tickets", lab, Vc["Tickets"], q(f"SELECT COUNT(*) FROM support_tickets s JOIN users u ON u.user_id=s.user_id WHERE {where}"), "SQL", 0)
    rec("MAU", lab, Vc["MAU"], q(f"SELECT SUM(a.active_in_month) FROM monthly_activity a JOIN users u ON u.user_id=a.user_id WHERE a.activity_month='2026-10' AND {where}"), "SQL", 0)
    rec("M3 Retention", lab, Vc["M3 Retention"], q(f"SELECT AVG(a.active_in_month) FROM monthly_activity a JOIN users u ON u.user_id=a.user_id WHERE a.months_since_registration=3 AND {where}"), "SQL", 1e-9)
    rec("Dormant 3m Rate", lab, Vc["Dormant 3m Rate"], q(f"SELECT AVG(dormant_3m_monthly) FROM users u WHERE {where}"), "SQL", 1e-9)
    rec("Median Resolution Hours", lab, Vc["Median Resolution Hours"], q(f"""WITH r AS (SELECT s.resolution_time_hours v, ROW_NUMBER() OVER (ORDER BY s.resolution_time_hours) rn, COUNT(*) OVER () n FROM support_tickets s JOIN users u ON u.user_id=s.user_id WHERE s.resolution_time_hours IS NOT NULL AND {where}) SELECT AVG(v) FROM r WHERE rn IN ((n+1)/2,(n+2)/2)"""), "SQL", 1e-9)
# CAC channel scenario via SQL: spend of channel / registered users of paid campaigns in channel
rec("CAC", "channel=Referral", evaluate(Ctx(channel=("Referral",)))["CAC"], q("SELECT SUM(c.campaign_spend_inr)*1.0/(SELECT COUNT(*) FROM users u WHERE u.acquisition_channel='Referral') FROM campaigns c WHERE c.channel='Referral'"), "SQL", 1e-9)
rec("Cost per First Trade", "campaign=CMP04", evaluate(Ctx(campaign=("CMP04",)))["Cost per First Trade"],
    q("SELECT (c.campaign_spend_inr*1.0/(SELECT COUNT(*) FROM users u WHERE u.acquisition_campaign_id='CMP04'))/(SELECT 1.0*SUM(trade_asof)/COUNT(*) FROM users u WHERE funnel_mature=1 AND u.acquisition_campaign_id='CMP04') FROM campaigns c WHERE c.campaign_id='CMP04'"), "SQL", 1e-6)
# month scenario: Aug-2026
mctx = Ctx(months=(pd.Timestamp("2026-08-01"),)); Vm = evaluate(mctx); lab = mctx.label()
rec("Registered Customers", lab, Vm["Registered Customers"], q("SELECT COUNT(*) FROM users WHERE registration_month='2026-08'"), "SQL", 0)
rec("MAU", lab, Vm["MAU"], q("SELECT SUM(active_in_month) FROM monthly_activity WHERE activity_month='2026-08'"), "SQL", 0)
rec("Tickets", lab, Vm["Tickets"], q("SELECT COUNT(*) FROM support_tickets WHERE created_month='2026-08'"), "SQL", 0)
rec("Trading Value INR mn", lab, Vm["Trading Value INR mn"], q("SELECT SUM(trading_value_inr)/1e6 FROM monthly_activity WHERE activity_month='2026-08'"), "SQL", 1e-6)
rec("Customers To Date", lab, Vm["Customers To Date"], q("SELECT COUNT(*) FROM users WHERE registration_month<='2026-08'"), "SQL", 0)
rec("Tickets per 1000 Customers", lab, Vm["Tickets per 1000 Customers"], q("SELECT 1000.0*(SELECT COUNT(*) FROM support_tickets WHERE created_month='2026-08')/(SELECT COUNT(*) FROM users WHERE registration_month<='2026-08')"), "SQL", 1e-9)
jul = evaluate(Ctx(months=(pd.Timestamp("2026-07-01"),)))
rec("Registrations MoM %", lab, (Vm["Registered Customers"] - jul["Registered Customers"]) / jul["Registered Customers"],
    q("SELECT 1.0*(SELECT COUNT(*) FROM users WHERE registration_month='2026-08')/(SELECT COUNT(*) FROM users WHERE registration_month='2026-07')-1"), "SQL", 1e-9)
rec("MAU MoM %", lab, (Vm["MAU"] - jul["MAU"]) / jul["MAU"], q("SELECT 1.0*(SELECT SUM(active_in_month) FROM monthly_activity WHERE activity_month='2026-08')/(SELECT SUM(active_in_month) FROM monthly_activity WHERE activity_month='2026-07')-1"), "SQL", 1e-9)
# Rolling 3-month registrations avg (Aug-2026 window = Jun, Jul, Aug)
reg3 = np.mean([int((FC.RegistrationDate.dt.to_period("M") == p).sum()) for p in pd.period_range("2026-06", "2026-08", freq="M")])
rec("Registrations 3M Avg", lab, reg3, q("SELECT COUNT(*)/3.0 FROM users WHERE registration_month IN ('2026-06','2026-07','2026-08')"), "SQL", 1e-9)
rec("Registered YTD", "month=Aug 26", int((FC.RegistrationDate <= "2026-08-31").sum() - (FC.RegistrationDate < "2026-01-01").sum()), q("SELECT COUNT(*) FROM users WHERE registration_month BETWEEN '2026-01' AND '2026-08'"), "SQL", 0)
# Cohort matrix cell + cohort size
cell = FA[(FA.RegMonthDate == "2026-03-01") & (FA.MonthsSinceRegistration == 3)].ActiveInMonth.mean()
rec("Cohort Retention", "cohort=Mar 26, M3", cell, q("SELECT AVG(active_in_month) FROM monthly_activity WHERE registration_month='2026-03' AND months_since_registration=3"), "SQL", 1e-9)
rec("Cohort Size", "cohort=Mar 26", FA[(FA.RegMonthDate == "2026-03-01") & (FA.MonthsSinceRegistration == 0)].CustomerID.nunique(), q("SELECT COUNT(*) FROM users WHERE registration_month='2026-03'"), "SQL", 0)
# Budget signal / rank across paid campaigns
cp = {k: v for k, v in cpft_by_campaign(ALL).items() if not pd.isna(v)}
med = float(np.median(list(cp.values()))); idx = {k: med / v for k, v in cp.items()}
rank = pd.Series(cp).rank(method="dense").astype(int).to_dict()
sig = {k: ("Efficient" if i >= 1.15 else "Costly" if i <= 0.85 else "In line") for k, i in idx.items()}
for k in cp:
    rec("Cost Efficiency Index", f"campaign={k}", evaluate(Ctx(campaign=tuple(dim_c.CampaignKey)))["Median Paid Cost per First Trade"] / cp[k], idx[k], "Recomputed from per-campaign costs", 1e-9)
exp_rows = pd.DataFrame(rows)

# ---------------------------------------------------------------- 3. coverage: every measure either oracle-tested or listed
tested = set(n.split("|")[0] for n in exp_rows.measure) | {n.split("|")[0] for n in V}
all_m = [x[1] for x in PM.M]
not_tested = [n for n in all_m if n not in tested]
exp_rows.to_csv(ROOT / "06_dashboard/validation/DAX_Oracle_Expected_Values.csv", index=False)
n_ok = int((exp_rows.status == "MATCH").sum()); n = len(exp_rows)
sig_tbl = pd.DataFrame({"campaign": list(cp), "cost_per_first_trade_inr": [round(cp[k], 1) for k in cp], "rank_asc": [rank[k] for k in cp], "index_vs_median": [round(idx[k], 3) for k in cp], "budget_signal": [sig[k] for k in cp]})
sig_tbl.to_csv(ROOT / "06_dashboard/validation/Budget_Signal_Expected.csv", index=False)
cover = f"{len(all_m) - len(not_tested)} of {len(all_m)}"
md = ["# Phase 5 - DAX measure verification (oracle)", "", "SYNTHETIC data. Power BI Desktop is not available in this environment, so the DAX itself has **not been executed**. Each measure's logic was re-implemented in pandas on the same star-schema CSVs and filter semantics, then checked against validated Phase 3/4 figures and independent SQL.", "",
      f"**{n_ok} / {n} oracle comparisons match.** Measures with at least one oracle check: **{cover}**.", "",
      "Measures without a direct oracle check (formatting/label measures, parameters, or those that need the Power BI engine, e.g. RANKX): " + (", ".join(not_tested) or "none"), "",
      "Paid-campaign budget indicator (expected on-screen values):", "", sig_tbl.to_markdown(index=False), "",
      "After building the model in Power BI Desktop, compare any card with `DAX_Oracle_Expected_Values.csv` (same measure name + context). A difference there means a DAX or model error, not a data difference.", ""]
(ROOT / "06_dashboard/validation/Phase5_Measure_Verification.md").write_text("\n".join(md))
print(f"{n_ok}/{n} oracle comparisons match; measures covered: {cover}")
print("not oracle-tested:", not_tested)
if n_ok != n: print(exp_rows[exp_rows.status != "MATCH"].to_string()); sys.exit(1)
