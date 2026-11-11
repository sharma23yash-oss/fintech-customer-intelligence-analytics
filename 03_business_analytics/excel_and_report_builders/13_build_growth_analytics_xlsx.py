"""
Phase 3 - builds Fintech_Growth_Analytics_Report.xlsx (module tables, KPI definitions, live formulas, charts)
and Growth_Experiments.xlsx (proposed experiments with formula-driven sample-size calculator).
Inputs : Phase 3 tables (03_business_analytics/*), assets/charts/phase3_*.png        Outputs: 03_business_analytics/summary/*.xlsx
Run    : python3 -I 13_build_growth_analytics_xlsx.py   then recalc with the xlsx skill's recalc.py
All data are synthetic. Blue font = hard-coded input from the analysis tables; black = formula.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as L

import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "05_python")); from fintech_analytics import config as CFG
P3 = ROOT / "03_business_analytics" / "summary"      # output folder for the two .xlsx files
T, CH = CFG.P3_TABLES, CFG.CHARTS_DIR
R = json.load(open(T / "results.json"))

FONT = "Arial"
HDR_FILL = PatternFill("solid", fgColor="1C5CAB")
NOTE_FILL = PatternFill("solid", fgColor="FFF4CC")
BAND = PatternFill("solid", fgColor="F3F6FA")
thin = Side(style="thin", color="D5D9DE")
BORDER = Border(bottom=thin)
BLUE = Font(name=FONT, size=10, color="0000FF")
BLACK = Font(name=FONT, size=10)
BOLD = Font(name=FONT, size=10, bold=True)
WHITE_B = Font(name=FONT, size=10, bold=True, color="FFFFFF")
TITLE = Font(name=FONT, size=14, bold=True, color="0D366B")
SUB = Font(name=FONT, size=9, italic=True, color="52514E")
SYN = "SYNTHETIC DATA - fictional brokerage dataset for portfolio purposes. Not real customer, company or market data. No revenue or ROI is calculated."


def fmt_for(col):
    c = col.lower()
    if any(k in c for k in ("rate", "share", "conv", "retention", "dropoff", "pct", "ratio_pct", "_ci_")) and "score" not in c and "inr" not in c and "per_" not in c:
        return "0.0%"
    if "inr" in c or "spend" in c or c.startswith("cac") or "cost_per" in c:
        return "#,##0"
    if c in ("p_value", "first_trade_p_holm", "chi2_p") or c.endswith("_p"):
        return "0.0000"
    return None


def title(ws, text, sub=None, row=1):
    ws.cell(row, 1, text).font = TITLE
    ws.cell(row + 1, 1, sub or SYN).font = SUB
    ws.sheet_view.showGridLines = False


def write_df(ws, df, r0, c0=1, formats=None, name=None, input_cols=True, widths=None, wrap_cols=()):
    """Write df with styled header; returns (first_data_row, last_row)."""
    if name:
        ws.cell(r0, c0, name).font = BOLD
        r0 += 1
    for j, col in enumerate(df.columns):
        c = ws.cell(r0, c0 + j, col.replace("_", " "))
        c.font, c.fill = WHITE_B, HDR_FILL
        c.alignment = Alignment(wrap_text=True, vertical="center")
    ws.row_dimensions[r0].height = 32
    for i, row in enumerate(df.itertuples(index=False)):
        for j, v in enumerate(row):
            col = df.columns[j]
            if isinstance(v, float) and np.isnan(v):
                v = None
            if isinstance(v, (np.integer,)):
                v = int(v)
            if isinstance(v, (np.floating,)):
                v = float(v)
            c = ws.cell(r0 + 1 + i, c0 + j, v)
            numeric = isinstance(v, (int, float)) and not isinstance(v, bool)
            c.font = BLUE if (numeric and input_cols) else BLACK
            c.border = BORDER
            f = (formats or {}).get(col) or (fmt_for(col) if numeric else None)
            if f:
                c.number_format = f
            if col in wrap_cols or (isinstance(v, str) and len(v) > 60):
                c.alignment = Alignment(wrap_text=True, vertical="top")
    return r0 + 1, r0 + len(df)


def set_widths(ws, widths):
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[L(i)].width = w


def add_img(ws, name, anchor, width=720):
    img = XLImage(str(CH / name))
    ratio = img.height / img.width
    img.width, img.height = width, int(width * ratio)
    ws.add_image(img, anchor)
    return int(width * ratio / 20) + 2     # approx rows consumed


rd = lambda n: pd.read_csv(T / f"{n}.csv", keep_default_na=not n.startswith("m8_"))

# ======================================================================================
wb = Workbook()
ws = wb.active; ws.title = "README"
title(ws, "Fintech Growth Analytics Report (Phase 3)", SYN)
rows = [
    ("Project", "Retail brokerage customer analytics - synthetic dataset, 10,000 users, Nov 2025 - Oct 2026, INR"),
    ("Snapshot date", "2026-10-31. Mature cohorts = registered before Oct 2026 (n=9,116); Oct-2026 cohort (884) is excluded from funnel/retention rates."),
    ("Purpose", "Portfolio project for a Retail Customer Operations / growth analytics application. Not professional brokerage work."),
    ("Source tables", "Phase 2 cleaned tables only (Cleaned_Users, Cleaned_Monthly_Activity, Cleaned_Support_Tickets, Cleaned_Campaigns). Raw data used only for reconciliation."),
    ("Source-of-truth rule", "Users table -> funnel, CAC, conversion. Monthly_Activity -> MAU, retention, cohorts, repeat trading. The two sources conflict for some users (flagged); mixed-source results are indicative."),
    ("Labels used", "ACTUAL = calculated from the synthetic data. ASSUMPTION = analyst-chosen input (effect sizes, baselines not in data). SCENARIO = arithmetic what-if, not a forecast. PROPOSED = experiment design, not conducted."),
    ("Colour code", "Blue font = value from the analysis tables (hard-coded input). Black font = formula calculated in this workbook. Yellow fill = assumption / caution."),
    ("Churn caveat", "'Inactive' and 'dormant' flags are inactivity PROXIES. Genuine churn (account closure) is not observable. Users with insufficient observation window are never treated as churned."),
    ("Not included", "Revenue, profitability, ROI, LTV. The dataset has no revenue data, so none is invented. Costs are recorded campaign spend only."),
    ("Reproducibility", "05_python/pipeline/10_phase3_analysis.py -> 11_phase3_experiments_findings.py -> 12_phase3_charts.py -> 03_business_analytics/excel_and_report_builders/13_build_growth_analytics_xlsx.py (seed 42)."),
]
for i, (k, v) in enumerate(rows):
    ws.cell(4 + i, 1, k).font = BOLD
    c = ws.cell(4 + i, 2, v); c.font = BLACK; c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[4 + i].height = 44
r = 4 + len(rows) + 1
ws.cell(r, 1, "Sheet index").font = BOLD
idx = [("KPI_Definitions", "Every KPI formula, source and caveat"), ("1_Acquisition", "Registrations, channel quality, CAC and cost per first trader (live formulas)"),
       ("2_Funnel", "Six-stage funnel with live conversion formulas, bottlenecks"), ("3_Retention", "Retention curve, cohorts, channel retention, repeat trading"),
       ("4_Segmentation", "Journey segments and K-means profile"), ("5_Campaigns", "Campaign scorecard (CAC and cost per trader as live formulas) and budget scenario"),
       ("6_Support", "Ticket categories, priority, backlog, support vs inactivity"), ("7_Insights", "15 findings, recommendations, prioritisation"), ("Charts", "Report charts")]
for i, (a, b) in enumerate(idx):
    ws.cell(r + 1 + i, 1, a).font = BLACK; ws.cell(r + 1 + i, 2, b).font = BLACK
set_widths(ws, [24, 130])

# ---------------- KPI definitions
ws = wb.create_sheet("KPI_Definitions"); title(ws, "KPI definitions and formulas")
kpis = pd.DataFrame([
    ("Registrations", "Count of users by registration month", "Users", "ACTUAL", "-"),
    ("CAC (INR)", "Campaign spend / registered users", "Campaigns x Users", "ACTUAL", "Spend is recorded campaign spend only. Organic has no recorded spend, so CAC is 'not defined' (NULL), not zero."),
    ("Cost per KYC (at maturity)", "CAC / mature KYC rate", "Users", "ACTUAL", "Mature cohorts only, so the Oct-2026 cohort does not understate conversion."),
    ("Cost per first trader (at maturity)", "CAC / mature first-trade rate", "Users", "ACTUAL", "Not ROI. Confidence interval reflects conversion uncertainty only (CAC treated as fixed)."),
    ("Stage conversion", "Users reaching stage n / users reaching stage n-1 (as-of snapshot)", "Users (*_asof)", "ACTUAL", "As-of columns count only events on or before 2026-10-31."),
    ("Cumulative conversion", "Users reaching stage n / registered users (mature cohorts)", "Users", "ACTUAL", ""),
    ("Drop-off / users lost", "1 - stage conversion; users lost = reached(n-1) - reached(n)", "Users", "ACTUAL", ""),
    ("30-day active rate", "Active in 30 days after registration / users with tenure >= 31 days", "Users (active_30d_adj)", "ACTUAL", "Users with shorter tenure are excluded, not counted as inactive."),
    ("M1 / M3 / M6 retention", "Active in calendar month k after registration month / cohort users old enough to observe month k", "Monthly_Activity", "ACTUAL", "Calendar-month definition. Month 0 = registration month."),
    ("Dormant (3 months)", "No active month Aug-Oct 2026, among mature users", "Monthly_Activity", "ACTUAL (proxy)", "Inactivity proxy, not churn."),
    ("Repeat trader", "Traded in >= 2 distinct months", "Monthly_Activity", "ACTUAL", ""),
    ("Tickets per 1,000 users", "Tickets / users x 1000", "Support tickets", "ACTUAL", ""),
    ("Tickets per 1,000 customer-months", "Tickets / sum of observed customer-months x 1000", "Support, Monthly_Activity", "ACTUAL", "Normalises for tenure."),
    ("Wilson 95% CI", "Wilson score interval for a proportion", "-", "ACTUAL", "Used for all rates."),
    ("Mantel-Haenszel odds ratio", "Odds of 3-month dormancy for ticket-raisers vs others, stratified by registration cohort", "Users", "ACTUAL (association)", "Association only; support exposure may be a symptom of onboarding friction."),
    ("Scorecard quality score", "Mean of rank-scores on KYC rate, first-trade rate, 30-day active rate and M3 retention (0-100)", "Campaigns", "ANALYST-DEFINED", "A transparent ranking, not a statistical model."),
    ("Scorecard cost-efficiency score", "Mean of rank-scores on cost per KYC and cost per first trader (0-100)", "Campaigns", "ANALYST-DEFINED", "Paid campaigns only."),
    ("Budget scenario", "Moved budget / cost per first trader at source vs destination (x (1 + penalty))", "Campaigns", "SCENARIO", "Arithmetic what-if; not a forecast."),
    ("Experiment sample size", "n per arm = [z(a/2)*sqrt(2*pbar*(1-pbar)) + z(b)*sqrt(p0(1-p0)+p1(1-p1))]^2 / (p1-p0)^2", "-", "ASSUMPTION (effect)", "alpha 0.05 two-sided, power 80%. Baselines from data; effects are assumed."),
], columns=["KPI", "Formula / definition", "Source", "Label", "Notes / caveat"])
a, b = write_df(ws, kpis, 4, input_cols=False)
for rr in range(a, b + 1):
    for cc in range(1, 6):
        ws.cell(rr, cc).alignment = Alignment(wrap_text=True, vertical="top")
set_widths(ws, [32, 70, 24, 20, 70])

# ---------------- 1 Acquisition
ws = wb.create_sheet("1_Acquisition"); title(ws, "Module 1 - Acquisition analytics")
ch = rd("m1_channel_performance")
base = ch[["acquisition_channel", "registered", "mature_users", "spend", "kyc_rate", "first_trade_rate", "active_30d_rate", "m3_retention"]].copy()
a, b = write_df(ws, base, 4, name="Channel performance (inputs in blue; CAC, cost per first trader and cost per KYC are live formulas)", formats={"spend": "#,##0"})
hdr = 5
for j, h in enumerate(["CAC (INR)", "Cost per KYC at maturity (INR)", "Cost per first trader at maturity (INR)", "Share of registrations"]):
    c = ws.cell(hdr, 9 + j, h); c.font, c.fill = WHITE_B, HDR_FILL; c.alignment = Alignment(wrap_text=True, vertical="center")
for rr in range(a, b + 1):
    ws.cell(rr, 9, f'=IF(D{rr}=0,"n/a",D{rr}/B{rr})').number_format = "#,##0"
    ws.cell(rr, 10, f'=IF(D{rr}=0,"n/a",I{rr}/E{rr})').number_format = "#,##0"
    ws.cell(rr, 11, f'=IF(D{rr}=0,"n/a",I{rr}/F{rr})').number_format = "#,##0"
    ws.cell(rr, 12, f"=B{rr}/SUM($B${a}:$B${b})").number_format = "0.0%"
    for cc in range(9, 13):
        ws.cell(rr, cc).font = BLACK; ws.cell(rr, cc).border = BORDER
tot = b + 1
ws.cell(tot, 1, "Total / blended paid").font = BOLD
ws.cell(tot, 2, f"=SUM(B{a}:B{b})").number_format = "#,##0"; ws.cell(tot, 4, f"=SUM(D{a}:D{b})").number_format = "#,##0"
ws.cell(tot, 9, f'=D{tot}/SUMIF(D{a}:D{b},">0",B{a}:B{b})').number_format = "#,##0"
ws.cell(tot + 1, 1, "Blended paid CAC = total spend / registrations of channels with spend. Organic CAC is not defined (no recorded spend).").font = SUB
for cc in (2, 4, 9):
    ws.cell(tot, cc).font = BOLD
r = tot + 3
po = rd("m1_paid_vs_organic")
a2, b2 = write_df(ws, po, r, name="Paid vs organic and channel groups")
r = b2 + 3
rm = rd("m1_registrations_monthly")
a3, b3 = write_df(ws, rm, r, name="Monthly registrations by channel", formats={"mom_change_pct": "0.0%"})
ws.cell(b3 + 1, 1, "Mean / month").font = BOLD
ws.cell(b3 + 1, 2, f"=AVERAGE(B{a3}:B{b3})").number_format = "#,##0.0"
ws.cell(b3 + 2, 1, f"Registration trend: slope {R['reg_trend_slope_per_month']:+.2f} users/month, p={R['reg_trend_p']:.2f} (not significant). Channel mix differences in first-trade rate: chi-square p<0.001.").font = SUB
set_widths(ws, [24, 14, 14, 14, 12, 14, 14, 14, 14, 16, 18, 14, 12, 12, 12])

# ---------------- 2 Funnel
ws = wb.create_sheet("2_Funnel"); title(ws, "Module 2 - Funnel analytics (mature cohorts)")
fn = rd("Funnel_Analysis"); fo = fn[fn.cut_type == "Overall"].copy()
ws.cell(4, 1, "Overall funnel - users reached are inputs; conversions are live formulas").font = BOLD
heads = ["Stage", "Users reached", "Step conversion", "Cumulative conversion", "Drop-off from previous", "Users lost", "Median days from previous", "p75 days from previous"]
for j, h in enumerate(heads):
    c = ws.cell(5, 1 + j, h); c.font, c.fill = WHITE_B, HDR_FILL; c.alignment = Alignment(wrap_text=True, vertical="center")
ws.row_dimensions[5].height = 32
for i, rw in enumerate(fo.itertuples()):
    rr = 6 + i
    ws.cell(rr, 1, rw.stage_name).font = BLACK
    c = ws.cell(rr, 2, float(rw.users_reached)); c.font = BLUE; c.number_format = "#,##0"
    if i == 0:
        ws.cell(rr, 3, 1).number_format = "0.0%"; ws.cell(rr, 5, 0).number_format = "0.0%"; ws.cell(rr, 6, 0)
    else:
        ws.cell(rr, 3, f"=B{rr}/B{rr-1}").number_format = "0.0%"; ws.cell(rr, 5, f"=1-C{rr}").number_format = "0.0%"; ws.cell(rr, 6, f"=B{rr-1}-B{rr}").number_format = "#,##0"
    ws.cell(rr, 4, f"=B{rr}/$B$6").number_format = "0.0%"
    for cc, v in ((7, rw.median_days_from_previous), (8, rw.p75_days_from_previous)):
        if not pd.isna(v):
            x = ws.cell(rr, cc, float(v)); x.font = BLUE
    for cc in (3, 4, 5, 6):
        ws.cell(rr, cc).font = BLACK
    for cc in range(1, 9):
        ws.cell(rr, cc).border = BORDER
ws.cell(12, 1, "Share of all stage losses").font = BOLD
for i in range(1, 6):
    rr = 6 + i
    ws.cell(rr, 9, f"=F{rr}/SUM($F$7:$F$11)").number_format = "0.0%"; ws.cell(rr, 9).font = BLACK
c = ws.cell(5, 9, "Share of losses (stages 2-5)"); c.font, c.fill = WHITE_B, HDR_FILL; c.alignment = Alignment(wrap_text=True)
ws.cell(12, 1, "Active (30d) uses a different eligibility rule (tenure >= 31 days); it is shown for completeness and excluded from the loss share.").font = SUB
r = 15
bn = rd("m2_bottlenecks")
a, b = write_df(ws, bn, r, name="Bottleneck evidence (ticket evidence is an association, not causation)", formats={"users_at_risk": "#,##0", "users_lost": "#,##0"})
r = b + 3
# bottleneck narrative
bt = pd.DataFrame([
    ("1. KYC completion", "70.5% completion; 2,687 users lost (largest single leak). Ticket raisers complete at 7.5% vs 74.9% for non-raisers.",
     "Unclear document steps, rejections, no status visibility (hypotheses; reasons are not in the data).", "Losing a third of the funnel at the top compounds through every later stage.",
     "Guided KYC, reminders, assisted KYC (EXP-01, EXP-02)", "Registration->KYC conversion; 14-day KYC completion"),
    ("2. First deposit", "76.9% of bank-linked users deposit; 1,305 lost; median 7 days. Ticket raisers 27.1% vs 78.9%.",
     "Amount decision friction, funding-source delays, low intent (hypotheses).", "Second largest leak; linked users who never fund cannot trade.",
     "Quick-amount deposit prompt and reminders (EXP-04)", "Bank->deposit conversion; median first deposit amount"),
    ("3. First trade", "79.8% of depositors trade; 878 lost; median 6 days. Ticket raisers 34.2% vs 81.5%.",
     "Lack of confidence / product familiarity, order friction (hypotheses).", "Funded customers who never trade are the cheapest to convert.",
     "Guided first trade with practice order (EXP-05)", "Deposit->first trade conversion; share of non-trivial first trades"),
], columns=["Bottleneck", "Evidence (ACTUAL)", "Possible reasons (HYPOTHESIS)", "Business impact", "Intervention", "Success KPI"])
a, b = write_df(ws, bt, r, name="Top three bottlenecks", input_cols=False)
for rr in range(a, b + 1):
    ws.row_dimensions[rr].height = 62
    for cc in range(1, 7):
        ws.cell(rr, cc).alignment = Alignment(wrap_text=True, vertical="top")
r = b + 3
sig = rd("m2_dimension_significance_tests")
a, b = write_df(ws, sig, r, name="Segment differences (chi-square): device is the only dimension with a significant KYC difference", formats={"chi2": "0.00", "p_value": "0.000", "spread_pp": "0.0"})
r = b + 3
tc = rd("m2_stage_timing_by_channel")
a, b = write_df(ws, tc, r, name="Median days by stage and channel (spread of about 2 days = no channel is materially faster)", input_cols=False)
set_widths(ws, [30, 18, 18, 18, 18, 16, 18, 18, 18, 14, 14, 14, 14])

# ---------------- 3 Retention
ws = wb.create_sheet("3_Retention"); title(ws, "Module 3 - Retention analytics (inactivity proxies, not churn)")
rc = rd("m3_retention_curve_pooled").rename(columns={"a": "active_users", "c": "cohort_users_observable"})
a, b = write_df(ws, rc[["months_since_registration", "active_users", "cohort_users_observable"]], 4, name="Pooled retention curve (rate is a live formula)")
c = ws.cell(5, 4, "Retention rate"); c.font, c.fill = WHITE_B, HDR_FILL
for rr in range(a, b + 1):
    ws.cell(rr, 4, f"=B{rr}/C{rr}").number_format = "0.0%"; ws.cell(rr, 4).font = BLACK; ws.cell(rr, 4).border = BORDER
r = b + 3
cm = rd("m3_cohort_retention_matrix")
a, b = write_df(ws, cm, r, name="Cohort retention matrix (blank = not yet observable, not churn)", formats={str(i): "0.0%" for i in range(12)})
r = b + 3
inact = rd("m3_inactivity_by_channel")
a, b = write_df(ws, inact, r, name="Inactivity by channel")
r = b + 3
rep = rd("m3_repeat_trading_by_channel")
a, b = write_df(ws, rep, r, name="Repeat trading by channel")
r = b + 3
sg = rd("m3_early_disengagement_signals")
a, b = write_df(ws, sg, r, name=f"Early signals vs M3 retention (association). Early-warning model CV AUC {R['ew_model']['cv_auc']:.2f} = weak")
r = b + 3
ra = rd("Retention_Analysis")
a, b = write_df(ws, ra.head(60), r, name="Retention_Analysis.csv (first 60 rows; full file delivered as CSV)")
set_widths(ws, [28, 16, 16, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14])

# ---------------- 4 Segmentation
ws = wb.create_sheet("4_Segmentation"); title(ws, "Module 4 - Segmentation")
js = rd("m4_journey_segment_profile")
a, b = write_df(ws, js, 4, name="Journey segments (rule-based, mutually exclusive). High source-conflict share means funnel flags and activity log disagree.",
                formats={"users": "#,##0", "share": "0.0%", "avg_tenure_days": "0.0", "pct_frequent_support_issues": "0.0%", "median_first_deposit_inr": "#,##0", "avg_trading_value_6m_inr": "#,##0", "pct_source_conflict": "0.0%"})
ws.cell(b + 1, 1, "Total").font = BOLD; ws.cell(b + 1, 2, f"=SUM(B{a}:B{b})").number_format = "#,##0"; ws.cell(b + 1, 3, f"=SUM(C{a}:C{b})").number_format = "0.0%"
r = b + 4
km = rd("m4_kmeans_profile")
a, b = write_df(ws, km, r, name=f"K-means profile (k={R['kmeans']['k']}, silhouette {R['kmeans']['silhouette']:.2f}, bootstrap ARI {R['kmeans']['ari']:.2f}; clusters are partitions of a continuum)")
r = b + 3
a, b = write_df(ws, rd("m4_kmeans_selection"), r, name="K selection rule: among k>=3 with ARI>=0.85 choose highest silhouette")
r = b + 3
a, b = write_df(ws, rd("m4_rfm_profile"), r, name="RFM profile")
set_widths(ws, [52, 16, 14, 14, 16, 16, 18, 16, 14, 14, 14, 14, 14, 14])

# ---------------- 5 Campaigns
ws = wb.create_sheet("5_Campaigns"); title(ws, "Module 5 - Campaign performance scorecard (no ROI: no revenue data)")
cp = rd("Campaign_Performance")
cols = ["campaign_id", "campaign_name", "channel", "campaign_spend_inr", "registered_users", "mature_users", "kyc_rate_mature", "first_trade_rate_mature",
        "active_30d_rate", "m3_retention", "tickets_per_1000_customer_months"]
base = cp[cols]
a, b = write_df(ws, base, 4, name="Campaign inputs (blue) and live formulas for CAC / cost per KYC / cost per first trader", formats={"tickets_per_1000_customer_months": "0.0"})
for j, h in enumerate(["CAC (INR)", "Cost per KYC at maturity (INR)", "Cost per first trader at maturity (INR)"]):
    c = ws.cell(5, 12 + j, h); c.font, c.fill = WHITE_B, HDR_FILL; c.alignment = Alignment(wrap_text=True, vertical="center")
for rr in range(a, b + 1):
    ws.cell(rr, 12, f'=IF(D{rr}=0,"n/a",D{rr}/E{rr})').number_format = "#,##0"
    ws.cell(rr, 13, f'=IF(D{rr}=0,"n/a",L{rr}/G{rr})').number_format = "#,##0"
    ws.cell(rr, 14, f'=IF(D{rr}=0,"n/a",L{rr}/H{rr})').number_format = "#,##0"
    for cc in (12, 13, 14):
        ws.cell(rr, cc).font = BLACK; ws.cell(rr, cc).border = BORDER
r = b + 3
sc = cp[["campaign_id", "campaign_name", "quality_score", "cost_efficiency_score", "overall_score", "scorecard_tier", "first_trade_diff_vs_others_pp", "first_trade_p_holm",
         "significant_at_5pct_holm", "cost_per_first_trade_ci_low", "cost_per_first_trade_ci_high", "revenue_data_available"]].copy()
for c_ in ("quality_score", "cost_efficiency_score", "overall_score", "first_trade_diff_vs_others_pp"):
    sc[c_] = sc[c_].round(1)
a, b = write_df(ws, sc, r, name="Scorecard (analyst-defined rank score, not a statistical model). Holm-corrected p-values vs all other campaigns.",
                formats={"quality_score": "0.0", "cost_efficiency_score": "0.0", "overall_score": "0.0", "first_trade_diff_vs_others_pp": "0.0", "first_trade_p_holm": "0.0000"})
for rr in range(a, b + 1):
    t = ws.cell(rr, 6).value or ""
    ws.cell(rr, 6).fill = PatternFill("solid", fgColor={"A": "D5EFD9", "B": "FFF4CC", "C": "FBD9D3"}.get(t[:1], "FFFFFF"))
ws.cell(b + 1, 1, "Tier colour is paired with the text label (A/B/C). CMP06 is tier C but its first-trade difference is not significant after Holm correction (p=0.061); CMP07/CMP08 are organic (quality score only).").font = SUB
r = b + 4
rb = rd("m5_budget_reallocation_scenarios")
ws.cell(r, 1, "Budget reallocation - SCENARIO (arithmetic, not a forecast). Live formulas below use the source/destination costs per first trader.").font = BOLD
ws.cell(r + 1, 1, "Budget moved (INR)").font = BLACK; x = ws.cell(r + 1, 2, float(R["realloc"]["moved"])); x.font = BLUE; x.number_format = "#,##0"
ws.cell(r + 2, 1, "Source cost per first trader (INR)").font = BLACK; x = ws.cell(r + 2, 2, float(R["realloc"]["src_cost"])); x.font = BLUE; x.number_format = "#,##0"
ws.cell(r + 3, 1, "Destination cost at observed efficiency (INR)").font = BLACK; x = ws.cell(r + 3, 2, float(R["realloc"]["dst_cost"])); x.font = BLUE; x.number_format = "#,##0"
heads = ["Destination cost penalty", "Destination cost (INR)", "First traders lost at source", "First traders gained at destination", "Net change in first traders"]
for j, h in enumerate(heads):
    c = ws.cell(r + 5, 1 + j, h); c.font, c.fill = WHITE_B, HDR_FILL; c.alignment = Alignment(wrap_text=True, vertical="center")
for i, pen in enumerate([0, 0.25, 0.5, 1.0, 1.5, 1.72]):
    rr = r + 6 + i
    x = ws.cell(rr, 1, pen); x.font = BLUE; x.number_format = "0%"
    ws.cell(rr, 2, f"=$B${r+3}*(1+A{rr})").number_format = "#,##0"
    ws.cell(rr, 3, f"=$B${r+1}/$B${r+2}").number_format = "#,##0"
    ws.cell(rr, 4, f"=$B${r+1}/B{rr}").number_format = "#,##0"
    ws.cell(rr, 5, f"=D{rr}-C{rr}").number_format = "#,##0"
    for cc in range(2, 6):
        ws.cell(rr, cc).font = BLACK
ws.cell(r + 12, 1, "The last row (+172%) is the break-even penalty: net change is approximately zero.").font = SUB
set_widths(ws, [34, 22, 18, 18, 16, 16, 16, 16, 14, 14, 14, 14, 16, 18])

# ---------------- 6 Support
ws = wb.create_sheet("6_Support"); title(ws, "Module 6 - Support analytics")
a, b = write_df(ws, rd("m6_ticket_categories"), 4, name="Ticket categories", formats={"tickets_per_1000_users": "0.0", "tickets_per_1000_customer_months": "0.0", "csat": "0.00", "mean_res_h": "0.0", "median_res_h": "0.0", "p90_res_h": "0.0"})
ws.cell(b + 1, 1, "Total").font = BOLD; ws.cell(b + 1, 2, f"=SUM(B{a}:B{b})").number_format = "#,##0"
ws.cell(b + 1, 3, f"=SUM(C{a}:C{b})").number_format = "0.0%"
r = b + 4
a, b = write_df(ws, rd("m6_priority"), r, name=f"Priority: no service-level difference (Kruskal-Wallis p={R['priority_res_kruskal_p']:.2f})", formats={"csat": "0.00", "median_res_h": "0.0", "mean_res_h": "0.0"})
r = b + 3
a, b = write_df(ws, rd("m6_backlog_ageing"), r, name="Unresolved ticket backlog by age")
r = b + 3
a, b = write_df(ws, rd("m6_support_vs_inactivity"), r, name="Support vs 3-month dormancy (cohort-adjusted Mantel-Haenszel; association only)", formats={"mantel_haenszel_odds_ratio_cohort_adjusted": "0.00", "or_ci_low": "0.00", "or_ci_high": "0.00", "crude_diff_pp": "0.0"})
r = b + 3
a, b = write_df(ws, rd("m6_csat_vs_dormancy"), r, name="CSAT vs dormancy", formats={"user_dormant_rate": "0.0%"})
r = b + 3
a, b = write_df(ws, rd("m6_stuck_users_and_tickets"), r, name="Users stuck at each stage and whether they raised a related ticket", formats={"raised_related_ticket_pct": "0.0%", "tickets_unresolved_among_raisers": "0.0%"})
r = b + 3
a, b = write_df(ws, rd("m6_tickets_monthly"), r, name="Tickets by month")
set_widths(ws, [30, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 16, 18, 18])

# ---------------- 7 Insights
ws = wb.create_sheet("7_Insights"); title(ws, "Module 8 - Insights, recommendations and prioritisation")
fi = rd("m8_findings")[["id", "module", "observation", "evidence", "implication", "recommendation", "kpi", "label"]]
a, b = write_df(ws, fi, 4, name="15 findings: Observation -> Evidence -> Business implication -> Recommendation -> KPI", input_cols=False)
for rr in range(a, b + 1):
    ws.row_dimensions[rr].height = 96
    for cc in range(1, 9):
        ws.cell(rr, cc).alignment = Alignment(wrap_text=True, vertical="top")
r = b + 3
pr = rd("m8_prioritisation")[["priority_rank", "category", "id", "recommendation", "impact", "complexity", "cost", "time_to_benefit", "linked_findings", "label", "priority_index"]]
pr["priority_index"] = pr.priority_index.round(2)
a, b = write_df(ws, pr, r, name="Recommendations ranked by priority index = (2 x impact + ease + cost-ease + speed) / 5. Weights are analyst-defined. Scores come from High/Medium/Low ratings that are judgements, not measurements.",
                input_cols=False, formats={"priority_index": "0.00"})
for rr in range(a, b + 1):
    ws.row_dimensions[rr].height = 42
    for cc in range(1, 12):
        ws.cell(rr, cc).alignment = Alignment(wrap_text=True, vertical="top")
set_widths(ws, [10, 20, 32, 56, 46, 40, 28, 22, 18, 24, 12])

# ---------------- Charts
ws = wb.create_sheet("Charts"); title(ws, "Charts")
row = 4
for nm in ["c01_funnel.png", "c02_registrations_mau.png", "c03_channel_first_trade.png", "c04_cost_per_first_trader.png", "c05_retention.png",
           "c07_cohort_heatmap.png", "c08_journey_segments.png", "c09_support.png", "c10_experiment_power.png", "c11_budget_reallocation.png"]:
    ws.add_image(XLImage(str(CH / ("phase3_" + nm))), f"A{row}")
    img = ws._images[-1]; ratio = img.height / img.width; img.width, img.height = 760, int(760 * ratio)
    row += int(760 * ratio / 20) + 3

for w in wb.worksheets:
    w.freeze_panes = None
wb.save(P3 / "Fintech_Growth_Analytics_Report.xlsx")

# ======================================================================================
# Growth_Experiments.xlsx
wb = Workbook(); ws = wb.active; ws.title = "README"
title(ws, "Growth Experiments Backlog (PROPOSED - none conducted)", SYN)
for i, (k, v) in enumerate([
    ("Status", "Every experiment is a PROPOSED design. No experiment has been run and no result is claimed."),
    ("Baselines", "ACTUAL values from the synthetic data (see 'baseline source' column)."),
    ("Effects", "Assumed minimum detectable effects (MDE) are ASSUMPTIONS chosen by the analyst, not forecasts."),
    ("Sample size", "Two-sided alpha 0.05, power 80%. The 'Calculator' sheet recomputes n per arm with live formulas; change the blue cells to test other effects."),
    ("Duration", "Accrual weeks = 1 + max(0, total sample - launch pool) / weekly eligible inflow; follow-up weeks are added for the outcome window."),
    ("Traffic constraint", "At about 190 registrations a week several tests are slow. Run independent levers concurrently (users randomised at registration), accept larger MDEs, or pool similar campaigns."),
    ("Randomisation", "Randomise at user level, stratify by channel and device, pre-register the primary metric, analyse intention-to-treat."),
]):
    ws.cell(4 + i, 1, k).font = BOLD
    c = ws.cell(4 + i, 2, v); c.font = BLACK; c.alignment = Alignment(wrap_text=True, vertical="top"); ws.row_dimensions[4 + i].height = 34
set_widths(ws, [22, 120])

ex = rd("m7_experiments")
ws = wb.create_sheet("Experiments"); title(ws, "Experiment backlog (10 proposed experiments)")
cols = ["experiment_id", "area", "title", "status", "hypothesis", "target_segment", "intervention", "control_group", "treatment_group", "primary_metric", "guardrail_metrics",
        "baseline", "baseline_source", "assumed_effect", "n_per_arm", "n_total", "launch_pool", "eligible_per_week", "accrual_weeks", "follow_up_weeks", "total_duration_weeks",
        "feasibility", "expected_benefit", "evaluation_method"]
a, b = write_df(ws, ex[cols], 4, input_cols=False, formats={"baseline": "0.0%", "n_per_arm": "#,##0", "n_total": "#,##0", "launch_pool": "#,##0", "eligible_per_week": "0.0"})
for rr in range(a, b + 1):
    ws.row_dimensions[rr].height = 120
    for cc in range(1, len(cols) + 1):
        ws.cell(rr, cc).alignment = Alignment(wrap_text=True, vertical="top")
    # baseline for rate experiments is per-user count, not a percentage
    if ws.cell(rr, 1).value in ("EXP-06", "EXP-08"):
        ws.cell(rr, 12).number_format = "0.0000"
ws.cell(b + 2, 1, "EXP-06 and EXP-08 baselines are event rates per user (not percentages). EXP-02 baseline (2%) and the EXP-09 reactivation base rate are cautioned in the 'baseline source' column.").font = SUB
set_widths(ws, [11, 20, 34, 16, 50, 40, 44, 28, 28, 34, 40, 10, 44, 18, 10, 10, 10, 12, 10, 10, 10, 34, 40, 44])
ws.freeze_panes = "D5"

ws = wb.create_sheet("Calculator"); title(ws, "Sample-size calculator (live formulas) - proportion experiments")
ws["A4"] = "Significance level (two-sided alpha)"; ws["B4"] = 0.05
ws["A5"] = "Power"; ws["B5"] = 0.80
ws["A6"] = "z (alpha/2)"; ws["B6"] = "=NORMSINV(1-B4/2)"
ws["A7"] = "z (power)"; ws["B7"] = "=NORMSINV(B5)"
for rr in (4, 5):
    ws.cell(rr, 2).font = BLUE; ws.cell(rr, 2).fill = NOTE_FILL
for rr in range(4, 8):
    ws.cell(rr, 1).font = BLACK
ws["B6"].font = BLACK; ws["B7"].font = BLACK
heads = ["Experiment", "Baseline rate p0 (ACTUAL)", "Assumed absolute lift (ASSUMPTION)", "p1 = p0 + lift", "n per arm", "Total sample", "Eligible per week", "Launch pool", "Accrual weeks", "Follow-up weeks", "Total weeks"]
for j, h in enumerate(heads):
    c = ws.cell(9, 1 + j, h); c.font, c.fill = WHITE_B, HDR_FILL; c.alignment = Alignment(wrap_text=True, vertical="center")
ws.row_dimensions[9].height = 44
prop = ex[ex.assumed_effect.str.contains("pp")]
for i, rw in enumerate(prop.itertuples()):
    rr = 10 + i
    ws.cell(rr, 1, f"{rw.experiment_id} {rw.area}").font = BLACK
    x = ws.cell(rr, 2, float(rw.baseline)); x.font = BLUE; x.number_format = "0.0%"
    x = ws.cell(rr, 3, float(rw.target_value) - float(rw.baseline)); x.font = BLUE; x.number_format = "0.0%"; x.fill = NOTE_FILL
    ws.cell(rr, 4, f"=B{rr}+C{rr}").number_format = "0.0%"
    ws.cell(rr, 5, f"=ROUNDUP((($B$6*SQRT(2*((B{rr}+D{rr})/2)*(1-(B{rr}+D{rr})/2))+$B$7*SQRT(B{rr}*(1-B{rr})+D{rr}*(1-D{rr})))^2)/(C{rr}^2),0)").number_format = "#,##0"
    ws.cell(rr, 6, f"=2*E{rr}").number_format = "#,##0"
    x = ws.cell(rr, 7, float(rw.eligible_per_week)); x.font = BLUE; x.number_format = "0.0"
    x = ws.cell(rr, 8, int(rw.launch_pool)); x.font = BLUE; x.number_format = "#,##0"
    ws.cell(rr, 9, f"=ROUNDUP(IF(F{rr}<=H{rr},1,1+(F{rr}-H{rr})/G{rr}),0)").number_format = "0"
    x = ws.cell(rr, 10, int(rw.follow_up_weeks)); x.font = BLUE
    ws.cell(rr, 11, f"=I{rr}+J{rr}").number_format = "0"
    for cc in (4, 5, 6, 9, 11):
        ws.cell(rr, cc).font = BLACK
    for cc in range(1, 12):
        ws.cell(rr, cc).border = BORDER
last = 10 + len(prop)
ws.cell(last + 1, 1, "Rate experiments (EXP-06 referral, EXP-08 tickets) use a Poisson-style variance and are computed in the analysis script; see the Experiments sheet.").font = SUB
ws.cell(last + 2, 1, "Check: the n per arm above should match the Experiments sheet for the same experiment (tolerance +/- 1 from rounding).").font = SUB
set_widths(ws, [40, 18, 20, 14, 12, 12, 14, 12, 12, 12, 12])

ws = wb.create_sheet("Sensitivity"); title(ws, "Sample size if the true effect is 0.5x / 1.0x / 1.5x the assumed effect")
sg = rd("m7_experiments_power_grid")
write_df(ws, sg, 4, input_cols=False, formats={"n_per_arm": "#,##0", "n_total": "#,##0", "weeks_to_accrue": "0.0", "effect_multiplier": "0.0x"})
set_widths(ws, [16, 16, 14, 14, 16])
wb.save(P3 / "Growth_Experiments.xlsx")
print("saved")
