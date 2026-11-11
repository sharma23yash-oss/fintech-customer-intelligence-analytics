"""Phase 5 - builds the Power BI star-schema source tables (SYNTHETIC data) -> 06_dashboard/data/*.csv, with integrity checks.
Star schema:  DimDate (DAX calculated table) | DimCampaign | DimCity | DimDevice | DimSegment | DimStage (disconnected)
              FactCustomer (grain: customer) | FactActivity (grain: customer x month) | FactTicket (grain: ticket)
Run: python3 19_build_powerbi_model_data.py"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1] / "05_python"))   # build_scripts + fintech_analytics package
from fintech_analytics import loading, segmentation, config as C

ROOT = HERE.parents[1]
OUT = ROOT / "06_dashboard" / "data"; OUT.mkdir(parents=True, exist_ok=True)
P3 = C.P3_TABLES                       # Phase 3 tables (03_business_analytics/<module>/)

d = loading.load_all(); U, A, T, CMP = d["users"], d["activity"], d["tickets"], d["campaigns"]
U = U.copy(); U["journey_segment"] = segmentation.journey_segment(U)
U["SegmentKey"] = U.journey_segment.str[:2].astype(int)

# ---------------------------------------------------------------- dimensions
perf = pd.read_csv(P3 / "Campaign_Performance.csv").set_index("campaign_id")
dc = CMP.copy()
dc["AcquisitionType"] = np.where(dc.is_paid == 1, "Paid (spend recorded)", "Organic (no spend recorded)")
dc["Phase3Tier"] = dc.campaign_id.map(perf.scorecard_tier)
dc["Phase3OverallScore"] = dc.campaign_id.map(perf.overall_score).round(2)
dc["Phase3FirstTradeP_Holm"] = dc.campaign_id.map(perf.first_trade_p_holm).round(6)
dc["Phase3SignificantAt5pct"] = dc.campaign_id.map(perf.significant_at_5pct_holm).map({True: "Yes", False: "No"})
dc["ChannelSort"] = dc.channel.map({c: i for i, c in enumerate(["Paid Search", "Paid Social", "Referral", "Affiliate", "Partnerships", "CRM", "Organic"], 1)})
dc = dc.rename(columns={"campaign_id": "CampaignKey", "campaign_name": "CampaignName", "channel": "Channel", "source_platform": "SourcePlatform", "campaign_spend_inr": "CampaignSpendINR",
                        "channel_group": "ChannelGroup", "is_paid": "IsPaid", "spend_basis": "SpendBasis"})
dc = dc[["CampaignKey", "CampaignName", "Channel", "ChannelSort", "SourcePlatform", "ChannelGroup", "AcquisitionType", "IsPaid", "CampaignSpendINR", "SpendBasis", "Phase3Tier", "Phase3OverallScore", "Phase3FirstTradeP_Holm", "Phase3SignificantAt5pct"]]
cities = sorted(U.city.unique(), key=lambda s: (s == "Other", s))
dcity = pd.DataFrame({"CityKey": cities, "CitySort": range(1, len(cities) + 1)})
ddev = pd.DataFrame({"DeviceKey": ["Android", "iOS", "Web"], "DeviceSort": [1, 2, 3]})
GROUP = {1: "Onboarding - in flight", 2: "Onboarding - stalled", 3: "Onboarding - stalled", 4: "Onboarding - stalled", 5: "Onboarding - stalled", 6: "Active trader - new",
         7: "Active trader - engaged", 8: "Active trader - engaged", 9: "Inactive / occasional", 10: "Inactive / occasional"}
ACTION = {1: "Let the journey run; light nudges only", 2: "KYC rescue: reminders + assisted verification", 3: "Bank-link help content + UPI/net-banking prompts",
          4: "First-deposit nudge; small-ticket starter prompt", 5: "Activation: guided first trade, education", 6: "Habit building: second-trade prompt",
          7: "Frequency nudges; feature discovery", 8: "Retain and reward; service priority", 9: "Win-back campaign (no pitch on first touch)", 10: "Re-engagement; relevance-based content"}
seg = U.groupby(["SegmentKey", "journey_segment"]).size().reset_index()[["SegmentKey", "journey_segment"]]
seg["SegmentName"] = seg.journey_segment; seg["SegmentGroup"] = seg.SegmentKey.map(GROUP); seg["RecommendedAction"] = seg.SegmentKey.map(ACTION)
seg = seg[["SegmentKey", "SegmentName", "SegmentGroup", "RecommendedAction"]]
dstage = pd.DataFrame({"StageOrder": range(1, 7), "StageName": C.STAGES})

# ---------------------------------------------------------------- fact tables
fc = pd.DataFrame({
    "CustomerID": U.user_id, "RegistrationDate": U.registration_date.dt.strftime("%Y-%m-%d"), "CampaignKey": U.acquisition_campaign_id, "CityKey": U.city, "DeviceKey": U.device_type,
    "SegmentKey": U.SegmentKey, "AgeGroup": U.age_group, "RiskProfile": U.risk_profile, "FurthestStage": U.furthest_stage_asof,
    "KYCDone": U.kyc_asof, "BankLinked": U.bank_asof, "Deposited": U.deposit_asof, "Traded": U.trade_asof,
    "KYCDate": U.kyc_date_asof.dt.strftime("%Y-%m-%d"), "BankDate": U.bank_date_asof.dt.strftime("%Y-%m-%d"), "DepositDate": U.deposit_date_asof.dt.strftime("%Y-%m-%d"), "FirstTradeDate": U.trade_date_asof.dt.strftime("%Y-%m-%d"),
    "FirstDepositAmountINR": U.first_deposit_amount_asof_inr, "FunnelMature": U.funnel_mature, "Eligible30d": U.eligible_30d, "Eligible90d": U.eligible_90d,
    "DaysRegToKYC": U.days_reg_to_kyc, "DaysKYCToBank": U.days_kyc_to_bank, "DaysBankToDeposit": U.days_bank_to_deposit, "DaysDepositToTrade": U.days_deposit_to_trade, "DaysRegToTrade": U.days_reg_to_trade,
    "Active30d": U.active_30d_adj, "Inactive90d": U.inactive_90d_adj, "TenureDays": U.tenure_days, "MonthsObserved": U.months_observed, "TradeMonths": U.trade_months,
    "TradeMonths6m": U.trade_months_6m, "TradingValue6mINR": U.trading_value_6m_inr, "Dormant3m": U.dormant_3m_monthly, "M1Retained": U.m1_retained, "M3Retained": U.m3_retained, "M6Retained": U.m6_retained,
    "TicketCount": U.ticket_count, "UnresolvedTicketCount": U.unresolved_ticket_count, "DaysSinceLastActivity": U.days_inactive_adj})
IB = ["0-7 d", "8-30 d", "31-60 d", "61-90 d", "91-120 d"]
fc["InactivityBucket"] = pd.cut(fc.DaysSinceLastActivity, [-1, 7, 30, 60, 90, 10_000], labels=IB).astype(str)
fc["InactivitySort"] = pd.cut(fc.DaysSinceLastActivity, [-1, 7, 30, 60, 90, 10_000], labels=range(1, 6)).astype(int)
keys = U.set_index("user_id")[["acquisition_campaign_id", "city", "device_type", "SegmentKey"]].rename(columns={"acquisition_campaign_id": "CampaignKey", "city": "CityKey", "device_type": "DeviceKey"})
fa = A.merge(keys, left_on="user_id", right_index=True, how="left")
fa = pd.DataFrame({"CustomerID": fa.user_id, "ActivityMonthDate": fa.activity_month_start, "RegMonthDate": fa.registration_month + "-01", "MonthsSinceRegistration": fa.months_since_registration,
                   "CampaignKey": fa.CampaignKey, "CityKey": fa.CityKey, "DeviceKey": fa.DeviceKey, "SegmentKey": fa.SegmentKey, "ActiveInMonth": fa.active_in_month, "TradedInMonth": fa.traded_in_month,
                   "DepositedInMonth": fa.deposited_in_month, "WithdrewInMonth": fa.withdrew_in_month, "TradeCount": fa.trade_count, "TradingValueINR": fa.trading_value_inr,
                   "DepositValueINR": fa.deposit_value_inr, "WithdrawalValueINR": fa.withdrawal_value_inr, "NetFlowINR": fa.net_flow_inr})
ft = T.merge(keys, left_on="user_id", right_index=True, how="left")
PR = {"High": 1, "Medium": 2, "Low": 3}; BK = {"0-30d": 1, "31-90d": 2, "91-180d": 3, ">180d": 4}
ft = pd.DataFrame({"TicketID": ft.ticket_id, "CustomerID": ft.user_id, "CreatedDate": ft.created_date.dt.strftime("%Y-%m-%d"), "CampaignKey": ft.CampaignKey, "CityKey": ft.CityKey, "DeviceKey": ft.DeviceKey,
                   "SegmentKey": ft.SegmentKey, "Category": ft.category, "Priority": ft.priority, "PrioritySort": ft.priority.map(PR), "Status": ft.status, "ResolutionHours": ft.resolution_time_hours,
                   "CSAT": ft.csat_score, "IsResolved": ft.is_resolved, "IsUnresolved": ft.is_unresolved, "IsEscalated": (ft.status == "Escalated").astype(int), "TicketAgeDays": ft.ticket_age_days,
                   "BacklogAgeBucket": ft.backlog_age_bucket, "BacklogSort": ft.backlog_age_bucket.map(BK), "RelatedFunnelStage": ft.related_funnel_stage.fillna("none"),
                   "StagePendingAtTicket": ft.stage_pending_at_ticket})

# ---------------------------------------------------------------- integrity checks
chk = []
def check(name, ok, detail=""): chk.append((name, bool(ok), detail)); assert ok, f"FAILED: {name} {detail}"
check("FactCustomer rows = 10,000", len(fc) == 10000, len(fc)); check("FactActivity rows = 64,645", len(fa) == 64645, len(fa)); check("FactTicket rows = 7,614", len(ft) == 7614, len(ft))
check("CustomerID unique in FactCustomer", fc.CustomerID.is_unique); check("TicketID unique", ft.TicketID.is_unique)
check("FactActivity (CustomerID, month) unique", not fa.duplicated(["CustomerID", "ActivityMonthDate"]).any())
for fname, f_ in (("FactCustomer", fc), ("FactActivity", fa), ("FactTicket", ft)):
    check(f"{fname}.CampaignKey in DimCampaign", f_.CampaignKey.isin(dc.CampaignKey).all()); check(f"{fname}.CityKey in DimCity", f_.CityKey.isin(dcity.CityKey).all())
    check(f"{fname}.DeviceKey in DimDevice", f_.DeviceKey.isin(ddev.DeviceKey).all()); check(f"{fname}.SegmentKey in DimSegment", f_.SegmentKey.isin(seg.SegmentKey).all())
check("FactActivity.CustomerID in FactCustomer", fa.CustomerID.isin(fc.CustomerID).all()); check("FactTicket.CustomerID in FactCustomer", ft.CustomerID.isin(fc.CustomerID).all())
lo, hi = pd.Timestamp("2025-11-01"), pd.Timestamp("2026-10-31")
for col, f_ in (("RegistrationDate", fc), ("ActivityMonthDate", fa), ("RegMonthDate", fa), ("CreatedDate", ft)):
    s = pd.to_datetime(f_[col]); check(f"{col} within DimDate range {lo.date()}..{hi.date()}", s.between(lo, hi).all(), f"{s.min().date()}..{s.max().date()}")
check("ActivityMonthDate and RegMonthDate are month starts", (pd.to_datetime(fa.ActivityMonthDate).dt.day == 1).all() and (pd.to_datetime(fa.RegMonthDate).dt.day == 1).all())
p3seg = {int(x["journey_segment"][:2]): x["users"] for x in json.loads(C.p3_path("results.json").read_text())["journey_segments"]}
mine = fc.SegmentKey.value_counts().to_dict(); check("Journey segment counts equal Phase 3", all(mine[k] == v for k, v in p3seg.items()), str(mine))
check("DimCampaign spend total = 2,690,000 (Rs 26.9 lakh)", dc.CampaignSpendINR.sum() == 2_690_000, dc.CampaignSpendINR.sum())

DATE_COLS = {"RegistrationDate", "KYCDate", "BankDate", "DepositDate", "FirstTradeDate", "ActivityMonthDate", "RegMonthDate", "CreatedDate"}
def tidy(t):
    t = t.copy()
    for c in t.columns:
        if pd.api.types.is_float_dtype(t[c]) and t[c].dropna().apply(float.is_integer).all(): t[c] = t[c].astype("Int64")
    return t
def ptype(t, c):
    if c in DATE_COLS: return "date"
    if pd.api.types.is_integer_dtype(t[c]): return "int"
    if pd.api.types.is_float_dtype(t[c]): return "number"
    return "text"
tables = {"DimCampaign": dc, "DimCity": dcity, "DimDevice": ddev, "DimSegment": seg, "DimStage": dstage, "FactCustomer": fc, "FactActivity": fa, "FactTicket": ft}
tables = {n: tidy(t) for n, t in tables.items()}
for n, t in tables.items(): t.to_csv(OUT / f"{n}.csv", index=False)
meta = {n: dict(rows=len(t), columns={c: ptype(t, c) for c in t.columns}) for n, t in tables.items()}
(ROOT / "06_dashboard" / "validation" / "model_tables_meta.json").write_text(json.dumps(meta, indent=1))
pd.DataFrame(chk, columns=["check", "passed", "detail"]).to_csv(ROOT / "06_dashboard" / "validation" / "model_integrity_checks.csv", index=False)
print(f"{sum(c[1] for c in chk)}/{len(chk)} integrity checks passed")
for n, t in tables.items(): print(f"  {n:13s} {len(t):>7,} rows x {t.shape[1]} cols")
