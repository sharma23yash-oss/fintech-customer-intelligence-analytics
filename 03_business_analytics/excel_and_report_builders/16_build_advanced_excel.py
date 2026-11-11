"""Phase 4 / Module A - builds 03_business_analytics/excel/Fintech_Advanced_Excel_Analytics.xlsx (SYNTHETIC DATA).
Stage 1 (this file): openpyxl authoring - Excel Tables, structured references, formulas, conditional formatting, charts.
Stage 2: LibreOffice recalculation (recalc.py) computes cached values.  Stage 3: 17_finalize_excel.py injects live XLOOKUP cells.
Run: python3 16_build_advanced_excel.py
"""
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import openpyxl
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.formatting.rule import CellIsRule, ColorScaleRule, DataBarRule, FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as CL
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.formula import ArrayFormula
from openpyxl.worksheet.table import Table, TableStyleInfo

ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "05_python")); from fintech_analytics import config as CFG
CLEAN, P3 = CFG.CLEAN_TABLES, CFG.P3_TABLES
OUT = ROOT / "03_business_analytics" / "excel" / "Fintech_Advanced_Excel_Analytics.xlsx"
OUT.parent.mkdir(exist_ok=True)

# ----------------------------------------------------------------------------------------------- styles
FN = "Arial"
NAVY, SOFT, GREYF, YEL = "1F3864", "D9E2F3", "F2F2F2", "FFF2CC"
f_n = Font(name=FN, size=10); f_b = Font(name=FN, size=10, bold=True); f_t = Font(name=FN, size=15, bold=True, color=NAVY)
f_sub = Font(name=FN, size=10, italic=True, color="595959"); f_h = Font(name=FN, size=10, bold=True, color="FFFFFF")
f_in = Font(name=FN, size=10, color="0000FF"); f_lnk = Font(name=FN, size=10, color="008000"); f_sec = Font(name=FN, size=11, bold=True, color=NAVY)
fill_h = PatternFill("solid", fgColor=NAVY); fill_s = PatternFill("solid", fgColor=SOFT); fill_g = PatternFill("solid", fgColor=GREYF); fill_y = PatternFill("solid", fgColor=YEL)
thin = Side(style="thin", color="BFBFBF"); box = Border(left=thin, right=thin, top=thin, bottom=thin)
wrap = Alignment(wrap_text=True, vertical="top"); ctr = Alignment(horizontal="center", vertical="center", wrap_text=True)
PCT, PCT2, INT, DEC1, DEC2, DATE, INR = "0.0%", "0.00%", "#,##0", "#,##0.0", "#,##0.00", "yyyy-mm-dd", "#,##0"

wb = openpyxl.Workbook(); wb.remove(wb.active)
SN = ["README", "Raw_Data_Reference", "Cleaned_Users", "Campaign_Analysis", "Funnel_Analysis", "Retention_Analysis", "Customer_Segmentation",
      "Support_Analysis", "KPI_Summary", "Phase3_Check", "Assumptions", "Formula_Guide", "XLOOKUP_Demo", "PivotTable_Guide", "Monthly_Activity_Data", "Support_Tickets_Data"]
WS = {n: wb.create_sheet(n) for n in SN}
TAB = {"README": "7F7F7F", "Raw_Data_Reference": "7F7F7F", "Cleaned_Users": "2E75B6", "Campaign_Analysis": "ED7D31", "Funnel_Analysis": "ED7D31",
       "Retention_Analysis": "ED7D31", "Customer_Segmentation": "ED7D31", "Support_Analysis": "ED7D31", "KPI_Summary": "00B050", "Phase3_Check": "00B050",
       "Assumptions": "FFC000", "Formula_Guide": "7F7F7F", "XLOOKUP_Demo": "7F7F7F", "PivotTable_Guide": "7F7F7F", "Monthly_Activity_Data": "2E75B6", "Support_Tickets_Data": "2E75B6"}
for n, c in TAB.items(): WS[n].sheet_properties.tabColor = c


def put(ws, ref, v=None, font=f_n, fmt=None, fill=None, al=None, border=None):
    c = ws[ref]
    if v is not None: c.value = v
    c.font = font
    if fmt: c.number_format = fmt
    if fill: c.fill = fill
    if al: c.alignment = al
    if border: c.border = border
    return c


def title(ws, text, sub, width=14):
    put(ws, "A1", text, f_t); put(ws, "A2", sub, f_sub)
    ws.sheet_view.showGridLines = False


def section(ws, row, text, ncols=12):
    for c in range(1, ncols + 1): ws.cell(row, c).fill = fill_s
    put(ws, f"A{row}", text, f_sec, fill=fill_s)


def header(ws, row, labels, col=1, height=30):
    for i, t in enumerate(labels):
        put(ws, f"{CL(col + i)}{row}", t, f_h, fill=fill_h, al=ctr, border=box)
    ws.row_dimensions[row].height = height


def widths(ws, spec):
    for k, v in spec.items(): ws.column_dimensions[k].width = v


def text_cell(ws, ref, text, font=f_n, **kw):
    """Store literal text even when it starts with '=' (formula documentation)."""
    c = put(ws, ref, text, font, **kw); c.data_type = "s"; return c


def add_table(ws, name, ref, style="TableStyleMedium2"):
    t = Table(displayName=name, ref=ref); t.tableStyleInfo = TableStyleInfo(name=style, showRowStripes=True); ws.add_table(t)


# ----------------------------------------------------------------------------------------------- data
U0 = pd.read_csv(CLEAN / "Cleaned_Users.csv", parse_dates=["registration_date", "kyc_date_asof", "bank_date_asof", "deposit_date_asof", "trade_date_asof"])
A0 = pd.read_csv(CLEAN / "Cleaned_Monthly_Activity.csv")
T0 = pd.read_csv(CLEAN / "Cleaned_Support_Tickets.csv", parse_dates=["created_date"])
C0 = pd.read_csv(CLEAN / "Cleaned_Campaigns.csv")
R3 = json.loads((P3 / "results.json").read_text())

U_SRC = ["user_id", "registration_date", "acquisition_campaign_id", "acquisition_channel", "city", "age_group", "device_type", "risk_profile", "furthest_stage_asof",
         "kyc_asof", "bank_asof", "deposit_asof", "trade_asof", "kyc_date_asof", "bank_date_asof", "deposit_date_asof", "trade_date_asof", "first_deposit_amount_asof_inr",
         "funnel_mature", "eligible_30d", "eligible_90d", "days_reg_to_kyc", "days_kyc_to_bank", "days_bank_to_deposit", "days_deposit_to_trade", "days_reg_to_trade",
         "active_30d_adj", "inactive_90d_adj", "tenure_days", "months_observed", "trade_months", "trade_months_6m", "trading_value_6m_inr", "activity_ratio",
         "dormant_3m_monthly", "m1_retained", "m3_retained", "m6_retained", "ticket_count", "unresolved_ticket_count"]
TR = lambda c: f"tblUsers[[#This Row],[{c}]]"
U_CALC = {
    "reg_month_key": lambda: f"=YEAR({TR('registration_date')})*100+MONTH({TR('registration_date')})",
    "campaign_name": lambda: f"=INDEX(tblCampaigns[campaign_name],MATCH({TR('acquisition_campaign_id')},tblCampaigns[campaign_id],0))",
    "reg_weekday": lambda: f'=CHOOSE(WEEKDAY({TR("registration_date")},2),"Mon","Tue","Wed","Thu","Fri","Sat","Sun")',
    "days_since_registration": lambda: f"=Snapshot-{TR('registration_date')}",
    "tenure_months": lambda: f'=DATEDIF({TR("registration_date")},Snapshot,"m")',
    "last_stage_event_date": lambda: f"=MAX({TR('registration_date')},{TR('kyc_date_asof')},{TR('bank_date_asof')},{TR('deposit_date_asof')})",
    "days_since_last_stage_event": lambda: f"=Snapshot-{TR('last_stage_event_date')}",
    "days_since_first_trade": lambda: f'=IF({TR("trade_asof")}=1,Snapshot-{TR("trade_date_asof")},"")',
    "journey_segment": lambda: (
        f'=_xlfn.IFS(OR(AND({TR("furthest_stage_asof")}="Registered",{TR("days_since_last_stage_event")}<=Lag_Reg),'
        f'AND({TR("furthest_stage_asof")}="KYC Completed",{TR("days_since_last_stage_event")}<=Lag_KYC),'
        f'AND({TR("furthest_stage_asof")}="Bank Linked",{TR("days_since_last_stage_event")}<=Lag_Bank),'
        f'AND({TR("furthest_stage_asof")}="Funded",{TR("days_since_last_stage_event")}<=Lag_Funded)),"01 New / in-flight onboarding",'
        f'{TR("furthest_stage_asof")}="Registered","02 KYC-pending (stalled)",{TR("furthest_stage_asof")}="KYC Completed","03 Bank-link pending (stalled)",'
        f'{TR("furthest_stage_asof")}="Bank Linked","04 Deposit-pending (stalled)",{TR("furthest_stage_asof")}="Funded","05 Deposited, never traded (stalled)",'
        f'{TR("days_since_first_trade")}<=FirstTradeWindow,"06 First-time trader (<=30d since first trade)",'
        f'{TR("dormant_3m_monthly")}=1,"09 Inactive trader (no activity Aug-Oct)",'
        f'{TR("trade_months_6m")}>=High_Min,"08 High-engagement trader (>=4 trading months of last 6)",'
        f'{TR("trade_months_6m")}>=Rep_Min,"07 Repeat trader (2-3 trading months of last 6)",'
        f'TRUE,"10 Occasional trader (0-1 trading months of last 6)")'),
    "deposit_band": lambda: (f'=IF({TR("deposit_asof")}=0,"No deposit",IF({TR("first_deposit_amount_asof_inr")}<=DepBand1,"Under Rs3k",'
                             f'IF({TR("first_deposit_amount_asof_inr")}<=DepBand2,"Rs3-6.5k",IF({TR("first_deposit_amount_asof_inr")}<=DepBand3,"Rs6.5-11.4k","Rs11.4k and above (top quartile)"))))'),
    "tenure_bucket": lambda: (f'=_xlfn.IFS({TR("days_since_registration")}<=30,"0-30 d",{TR("days_since_registration")}<=90,"31-90 d",'
                              f'{TR("days_since_registration")}<=180,"91-180 d",TRUE,">180 d")'),
    "idle_deposit_key": lambda: f'=IF(AND({TR("deposit_asof")}=1,{TR("trade_asof")}=0),{TR("first_deposit_amount_asof_inr")}+ROW()/10000000,"")',
}
U_COLS = U_SRC + list(U_CALC)
NU, NA_, NT = len(U0), len(A0), len(T0)
UL = NU + 4                         # last row of tblUsers (header on row 4)

# ----------------------------------------------------------------------------------------------- Assumptions
ws = WS["Assumptions"]; title(ws, "Assumptions & parameters", "Blue cells on yellow are inputs; every formula in the workbook reads them through the named ranges shown in column D. All data are SYNTHETIC.")
header(ws, 3, ["Parameter", "Value", "Why / source", "Named range"])
AS = [("Snapshot date", datetime(2026, 10, 31), DATE, "Data cut-off. All *_asof columns count only events on/before this date.", "Snapshot"),
      ("Max KYC-pending lag in-flight (days)", 11, INT, "Max historical registration->KYC lag in mature data (Phase 3). Beyond this a Registered user is 'stalled'.", "Lag_Reg"),
      ("Max bank-link lag after KYC (days)", 7, INT, "Max historical KYC->bank lag.", "Lag_KYC"),
      ("Max deposit lag after bank link (days)", 14, INT, "Max historical bank->deposit lag.", "Lag_Bank"),
      ("Max first-trade lag after deposit (days)", 11, INT, "Max historical deposit->trade lag.", "Lag_Funded"),
      ("'First-time trader' window (days since first trade)", 30, INT, "Journey-segment rule 06.", "FirstTradeWindow"),
      ("Repeat trader: min trading months of last 6", 2, INT, "Journey-segment rule 07.", "Rep_Min"),
      ("High-engagement: min trading months of last 6", 4, INT, "Journey-segment rule 08.", "High_Min"),
      ("Repeat-trading base: min observed months", 4, INT, "Users need >= 4 observed months to be judged on repetition (Phase 3).", "RepBaseMonths"),
      ("Support SLA threshold (hours)", 24, INT, "Illustrative internal SLA for the 'within SLA' share. Not a regulatory figure.", "SLA_Hours"),
      ("Deposit band 1 upper limit (INR)", 3000, INR, "Phase 3 deposit bands.", "DepBand1"),
      ("Deposit band 2 upper limit (INR)", 6500, INR, "Phase 3 deposit bands.", "DepBand2"),
      ("Deposit band 3 upper limit (INR) = top-quartile cut", 11352, INR, "Phase 3: 75th percentile of first deposits.", "DepBand3"),
      ("Idle-deposit threshold (days)", 14, INT, "Beyond the historical deposit->trade lag, a funded-never-traded user is stalled (SQL Q24).", "IdleDays"),
      ("Repeat-contactor threshold (tickets)", 3, INT, "Users with this many tickets or more.", "TicketRepeatMin"),
      ("z for 95% confidence interval", 1.96, DEC2, "Wilson interval on step conversions.", "Z95"),
      ("First registration month start", datetime(2025, 11, 1), DATE, "Start of the 12-month observation window (calendar tables).", "WindowStart")]
for i, (p, v, fm, why, nm) in enumerate(AS):
    r = 4 + i
    put(ws, f"A{r}", p, f_n, border=box); put(ws, f"B{r}", v, f_in, fm, fill_y, border=box); put(ws, f"C{r}", why, f_n, al=wrap, border=box); put(ws, f"D{r}", nm, f_n, border=box)
    wb.defined_names[nm] = DefinedName(nm, attr_text=f"Assumptions!$B${r}")
widths(ws, {"A": 50, "B": 16, "C": 88, "D": 18})

# ----------------------------------------------------------------------------------------------- Cleaned_Users (tblUsers)
ws = WS["Cleaned_Users"]; title(ws, "Cleaned_Users - Excel Table tblUsers (10,000 synthetic users)", "Source columns (left, black) come from data/cleaned/Cleaned_Users.csv; calculated columns (right, header tinted) are live formulas using structured references and named ranges.")
for j, c in enumerate(U_COLS, 1):
    put(ws, f"{CL(j)}4", c, f_h, fill=PatternFill("solid", fgColor="C55A11" if c in U_CALC else NAVY), al=ctr)
ws.row_dimensions[4].height = 42
DATECOLS = {"registration_date", "kyc_date_asof", "bank_date_asof", "deposit_date_asof", "trade_date_asof", "last_stage_event_date"}
vals = U0[U_SRC].astype(object).where(U0[U_SRC].notna(), None)
for i, row in enumerate(vals.itertuples(index=False), start=5):
    for j, v in enumerate(row, 1):
        if isinstance(v, pd.Timestamp): v = v.to_pydatetime()
        elif isinstance(v, (np.integer,)): v = int(v)
        elif isinstance(v, (np.floating,)): v = float(v)
        if v is not None: ws.cell(i, j, v)
    for k, (nm, fn) in enumerate(U_CALC.items(), len(U_SRC) + 1):
        ws.cell(i, k, fn())
col_idx = {c: j for j, c in enumerate(U_COLS, 1)}
for c in DATECOLS:
    for r in range(5, UL + 1): ws.cell(r, col_idx[c]).number_format = DATE
for c in ("activity_ratio", "first_deposit_amount_asof_inr", "trading_value_6m_inr", "idle_deposit_key"):
    for r in range(5, UL + 1): ws.cell(r, col_idx[c]).number_format = DEC2 if c != "activity_ratio" else "0.000"
for j in range(1, len(U_COLS) + 1): ws.column_dimensions[CL(j)].width = 15
widths(ws, {"A": 11, "AU": 20, "AX": 30, "AY": 30, "AZ": 28, "BA": 32})
ws.column_dimensions[CL(col_idx["journey_segment"])].width = 52; ws.column_dimensions[CL(col_idx["campaign_name"])].width = 20
ws.column_dimensions[CL(col_idx["deposit_band"])].width = 24
add_table(ws, "tblUsers", f"A4:{CL(len(U_COLS))}{UL}", "TableStyleLight9"); ws.freeze_panes = "B5"

# ----------------------------------------------------------------------------------------------- Monthly_Activity_Data (tblActivity)
ws = WS["Monthly_Activity_Data"]; title(ws, "Monthly_Activity_Data - Excel Table tblActivity (64,645 user-month rows)", "From data/cleaned/Cleaned_Monthly_Activity.csv. *_key columns are yyyymm integers derived from the text month (avoids ambiguous 'yyyy-mm' criteria in COUNTIFS).")
A_COLS = ["user_id", "activity_month", "activity_month_key", "months_since_registration", "registration_month_key", "active_in_month", "traded_in_month", "trade_count",
          "trading_value_inr", "deposit_value_inr", "withdrawal_value_inr", "net_flow_inr"]
A1 = A0.copy(); A1["activity_month_key"] = A1.activity_month.str.replace("-", "").astype(int); A1["registration_month_key"] = A1.registration_month.str.replace("-", "").astype(int)
header(ws, 4, A_COLS, height=36)
for r in A1[A_COLS].itertuples(index=False): ws.append([x.item() if hasattr(x, "item") else x for x in r]) if False else None
rows = A1[A_COLS].values.tolist()
for i, r in enumerate(rows, start=5):
    for j, v in enumerate(r, 1): ws.cell(i, j, v)
widths(ws, {CL(j): 17 for j in range(1, 13)}); add_table(ws, "tblActivity", f"A4:L{NA_ + 4}", "TableStyleLight9"); ws.freeze_panes = "B5"

# ----------------------------------------------------------------------------------------------- Support_Tickets_Data (tblTickets)
ws = WS["Support_Tickets_Data"]; title(ws, "Support_Tickets_Data - Excel Table tblTickets (7,614 tickets)", "From data/cleaned/Cleaned_Support_Tickets.csv. 'sla_flag' is a calculated column (SLA hours on the Assumptions sheet).")
T1 = T0.copy(); T1["created_month_key"] = T1.created_month.astype(str).str.replace("-", "").astype(int)
T_SRC = ["ticket_id", "user_id", "created_date", "created_month_key", "category", "priority", "status", "resolution_time_hours", "csat_score", "is_resolved", "is_unresolved",
         "ticket_age_days", "backlog_age_bucket", "csat_band", "related_funnel_stage", "stage_pending_at_ticket"]
T_COLS = T_SRC + ["sla_flag"]
header(ws, 4, T_COLS, height=36); put(ws, f"{CL(len(T_COLS))}4", "sla_flag", f_h, fill=PatternFill("solid", fgColor="C55A11"), al=ctr)
tv = T1[T_SRC].astype(object).where(T1[T_SRC].notna(), None)
for i, row in enumerate(tv.itertuples(index=False), start=5):
    for j, v in enumerate(row, 1):
        if isinstance(v, pd.Timestamp): v = v.to_pydatetime()
        if v is not None: ws.cell(i, j, v)
    ws.cell(i, len(T_COLS), f'=IF(tblTickets[[#This Row],[is_resolved]]=1,IF(tblTickets[[#This Row],[resolution_time_hours]]<=SLA_Hours,"Within SLA","Over SLA"),"Unresolved")')
    ws.cell(i, 3).number_format = DATE
widths(ws, {CL(j): 18 for j in range(1, 18)}); add_table(ws, "tblTickets", f"A4:{CL(len(T_COLS))}{NT + 4}", "TableStyleLight9"); ws.freeze_panes = "B5"

# ----------------------------------------------------------------------------------------------- Campaign_Analysis (tblCampaigns + channel summary)
ws = WS["Campaign_Analysis"]; title(ws, "Campaign_Analysis - CAC, cost per first trader and campaign quality", "CAC = recorded spend / registered users. Cost per first trader = CAC / mature first-trade rate. Organic campaigns have no recorded spend, so CAC is 'n/a' (not zero). No revenue or ROI is modelled.")
section(ws, 4, "A. Campaign scorecard (Excel Table tblCampaigns - blue = input from Cleaned_Campaigns.csv, black = formula)", 22)
CT = ["campaign_id", "campaign_name", "channel", "source_platform", "campaign_spend_inr", "channel_group", "is_paid", "spend_basis",
      "registered_users", "mature_users", "mature_kyc_users", "mature_first_traders", "kyc_rate_mature", "first_trade_rate_mature", "cac_inr",
      "cost_per_first_trader_inr", "m3_retention", "dormant_3m_rate", "rank_first_trade", "rank_m3_retention", "rank_cost_efficiency_paid", "cost_flag"]
header(ws, 5, CT, height=44)
CR = lambda c: f"tblCampaigns[[#This Row],[{c}]]"
cf = {
    "registered_users": lambda: f"=COUNTIFS(tblUsers[acquisition_campaign_id],{CR('campaign_id')})",
    "mature_users": lambda: f"=COUNTIFS(tblUsers[acquisition_campaign_id],{CR('campaign_id')},tblUsers[funnel_mature],1)",
    "mature_kyc_users": lambda: f"=SUMIFS(tblUsers[kyc_asof],tblUsers[acquisition_campaign_id],{CR('campaign_id')},tblUsers[funnel_mature],1)",
    "mature_first_traders": lambda: f"=SUMIFS(tblUsers[trade_asof],tblUsers[acquisition_campaign_id],{CR('campaign_id')},tblUsers[funnel_mature],1)",
    "kyc_rate_mature": lambda: f'=IF({CR("mature_users")}=0,"",{CR("mature_kyc_users")}/{CR("mature_users")})',
    "first_trade_rate_mature": lambda: f'=IF({CR("mature_users")}=0,"",{CR("mature_first_traders")}/{CR("mature_users")})',
    "cac_inr": lambda: f'=IF({CR("is_paid")}=1,{CR("campaign_spend_inr")}/{CR("registered_users")},"n/a")',
    "cost_per_first_trader_inr": lambda: f'=IF(AND({CR("is_paid")}=1,{CR("first_trade_rate_mature")}>0),{CR("cac_inr")}/{CR("first_trade_rate_mature")},"n/a")',
    "m3_retention": lambda: f'=IFERROR(AVERAGEIFS(tblUsers[m3_retained],tblUsers[acquisition_campaign_id],{CR("campaign_id")}),"")',
    "dormant_3m_rate": lambda: f'=IFERROR(AVERAGEIFS(tblUsers[dormant_3m_monthly],tblUsers[acquisition_campaign_id],{CR("campaign_id")}),"")',
    "rank_first_trade": lambda: f'=RANK({CR("first_trade_rate_mature")},tblCampaigns[first_trade_rate_mature],0)',
    "rank_m3_retention": lambda: f'=RANK({CR("m3_retention")},tblCampaigns[m3_retention],0)',
    "rank_cost_efficiency_paid": lambda: f'=IF({CR("is_paid")}=1,RANK({CR("cost_per_first_trader_inr")},tblCampaigns[cost_per_first_trader_inr],1),"n/a")',
    "cost_flag": lambda: f'=IF({CR("is_paid")}=0,"Organic (no spend)",IF({CR("cost_per_first_trader_inr")}<=MEDIAN(tblCampaigns[cost_per_first_trader_inr]),"Below-median cost","Above-median cost"))',
}
for i, r in enumerate(C0.itertuples(index=False), start=6):
    for j, v in enumerate([r.campaign_id, r.campaign_name, r.channel, r.source_platform, int(r.campaign_spend_inr), r.channel_group, int(r.is_paid), r.spend_basis], 1):
        put(ws, f"{CL(j)}{i}", v, f_in if j == 5 else f_n)
    for j, nm in enumerate(CT[8:], 9): put(ws, f"{CL(j)}{i}", cf[nm](), f_n)
    for nm, fm in (("campaign_spend_inr", INR), ("registered_users", INT), ("mature_users", INT), ("mature_kyc_users", INT), ("mature_first_traders", INT), ("kyc_rate_mature", PCT),
                   ("first_trade_rate_mature", PCT), ("cac_inr", DEC1), ("cost_per_first_trader_inr", INR), ("m3_retention", PCT), ("dormant_3m_rate", PCT)):
        ws[f"{CL(CT.index(nm) + 1)}{i}"].number_format = fm
add_table(ws, "tblCampaigns", "A5:V15", "TableStyleMedium2")
put(ws, "A17", "Paid total / blended", f_b); put(ws, "E17", "=SUMIFS(tblCampaigns[campaign_spend_inr],tblCampaigns[is_paid],1)", f_b, INR)
put(ws, "I17", "=SUMIFS(tblCampaigns[registered_users],tblCampaigns[is_paid],1)", f_b, INT); put(ws, "O17", "=E17/I17", f_b, DEC1)
put(ws, "A18", "All campaigns", f_b); put(ws, "E18", "=SUM(tblCampaigns[campaign_spend_inr])", f_b, INR); put(ws, "I18", "=SUM(tblCampaigns[registered_users])", f_b, INT)
put(ws, "A19", "Blended paid CAC (O17) = paid spend / users registered by paid campaigns. Organic users are excluded because their cost is not recorded.", f_sub)
ws.conditional_formatting.add("N6:N15", DataBarRule(start_type="num", start_value=0, end_type="max", color="5B9BD5"))
ws.conditional_formatting.add("P6:P15", ColorScaleRule(start_type="min", start_color="C6EFCE", mid_type="percentile", mid_value=50, mid_color="FFEB9C", end_type="max", end_color="F8CBAD"))
ws.conditional_formatting.add("Q6:Q15", ColorScaleRule(start_type="min", start_color="F8CBAD", end_type="max", end_color="C6EFCE"))
ws.conditional_formatting.add("V6:V15", FormulaRule(formula=['V6="Above-median cost"'], fill=PatternFill("solid", bgColor="F8CBAD")))
section(ws, 22, "B. Channel summary (formulas by channel)", 22)
header(ws, 23, ["Channel", "Recorded spend (INR)", "Registrations", "Share", "Mature users", "KYC rate (mature)", "First-trade rate (mature)", "CAC (INR)", "Cost per first trader (INR)",
                "M3 retention", "Dormant 3m", "Tickets per 1,000 users"], height=44)
CHS = ["Organic", "Referral", "CRM", "Paid Search", "Paid Social", "Affiliate", "Partnerships"]
for i, ch in enumerate(CHS, start=24):
    put(ws, f"A{i}", ch)
    put(ws, f"B{i}", f"=SUMIFS(tblCampaigns[campaign_spend_inr],tblCampaigns[channel],A{i})", fmt=INR)
    put(ws, f"C{i}", f"=COUNTIFS(tblUsers[acquisition_channel],A{i})", fmt=INT)
    put(ws, f"D{i}", f"=C{i}/COUNTA(tblUsers[user_id])", fmt=PCT)
    put(ws, f"E{i}", f"=COUNTIFS(tblUsers[acquisition_channel],A{i},tblUsers[funnel_mature],1)", fmt=INT)
    put(ws, f"F{i}", f"=SUMIFS(tblUsers[kyc_asof],tblUsers[acquisition_channel],A{i},tblUsers[funnel_mature],1)/E{i}", fmt=PCT)
    put(ws, f"G{i}", f"=SUMIFS(tblUsers[trade_asof],tblUsers[acquisition_channel],A{i},tblUsers[funnel_mature],1)/E{i}", fmt=PCT)
    put(ws, f"H{i}", f'=IF(B{i}>0,B{i}/C{i},"n/a")', fmt=DEC1)
    put(ws, f"I{i}", f'=IF(B{i}>0,H{i}/G{i},"n/a")', fmt=INR)
    put(ws, f"J{i}", f"=AVERAGEIFS(tblUsers[m3_retained],tblUsers[acquisition_channel],A{i})", fmt=PCT)
    put(ws, f"K{i}", f"=AVERAGEIFS(tblUsers[dormant_3m_monthly],tblUsers[acquisition_channel],A{i})", fmt=PCT)
    put(ws, f"L{i}", f"=1000*SUMIFS(tblUsers[ticket_count],tblUsers[acquisition_channel],A{i})/C{i}", fmt=INT)
put(ws, "A31", "All channels", f_b); put(ws, "B31", "=SUM(B24:B30)", f_b, INR); put(ws, "C31", "=SUM(C24:C30)", f_b, INT); put(ws, "D31", "=SUM(D24:D30)", f_b, PCT)
put(ws, "E31", "=SUM(E24:E30)", f_b, INT)
ws.conditional_formatting.add("G24:G30", ColorScaleRule(start_type="min", start_color="F8CBAD", end_type="max", end_color="C6EFCE"))
ws.conditional_formatting.add("J24:J30", ColorScaleRule(start_type="min", start_color="F8CBAD", end_type="max", end_color="C6EFCE"))
ws.conditional_formatting.add("C24:C30", DataBarRule(start_type="num", start_value=0, end_type="max", color="5B9BD5"))
put(ws, "A32", "Differences between channels are often small; Phase 3 tested significance (chi-square, Holm-adjusted) before any reallocation advice.", f_sub)
ch = BarChart(); ch.type = "bar"; ch.title = "Cost per first trader by campaign (paid, INR)"; ch.style = 10; ch.legend = None
ch.add_data(Reference(ws, min_col=16, min_row=5, max_row=15), titles_from_data=True); ch.set_categories(Reference(ws, min_col=2, min_row=6, max_row=15))
ch.y_axis.title = "INR per first trader"; ch.x_axis.delete = False; ch.y_axis.delete = False; ch.height, ch.width = 11, 17; ch.gapWidth = 60; ch.y_axis.majorGridlines = None
ch.series[0].graphicalProperties.solidFill = "2E75B6"; ws.add_chart(ch, "A35")
widths(ws, {"A": 20, "B": 20, "C": 16, "D": 17, "E": 16, "F": 17, "G": 15, "H": 14, "I": 15, "J": 14, "K": 15, "L": 15, "M": 14, "N": 15, "O": 12, "P": 16, "Q": 13, "R": 13, "S": 12, "T": 14, "U": 16, "V": 20})
ws.freeze_panes = "C6"

# ----------------------------------------------------------------------------------------------- Funnel_Analysis
ws = WS["Funnel_Analysis"]; title(ws, "Funnel_Analysis - onboarding funnel, conversion and timing (mature cohort)", "Mature cohort = registered before 2026-10 (funnel_mature = 1, n = 9,116). Users table is the source of truth for funnel metrics. Step conversion = reached / previous stage.")
section(ws, 4, "A. Overall funnel with Wilson 95% interval on step conversion", 12)
header(ws, 5, ["Stage", "Users reached", "% of registered", "Step conversion", "Users lost", "Share of all losses", "Step conv. CI low", "Step conv. CI high"])
STG = ["Registered", "KYC Completed", "Bank Linked", "First Deposit", "First Trade", "Active (30d)"]
RF = ["=COUNTIFS(tblUsers[funnel_mature],1)", "=SUMIFS(tblUsers[kyc_asof],tblUsers[funnel_mature],1)", "=SUMIFS(tblUsers[bank_asof],tblUsers[funnel_mature],1)",
      "=SUMIFS(tblUsers[deposit_asof],tblUsers[funnel_mature],1)", "=SUMIFS(tblUsers[trade_asof],tblUsers[funnel_mature],1)",
      "=COUNTIFS(tblUsers[funnel_mature],1,tblUsers[trade_asof],1,tblUsers[active_30d_adj],1)"]
for i, (s, f) in enumerate(zip(STG, RF)):
    r = 6 + i
    put(ws, f"A{r}", s); put(ws, f"B{r}", f, fmt=INT); put(ws, f"C{r}", f"=B{r}/$B$6", fmt=PCT)
    if i:
        put(ws, f"D{r}", f"=B{r}/B{r - 1}", fmt=PCT); put(ws, f"E{r}", f"=B{r - 1}-B{r}", fmt=INT); put(ws, f"F{r}", f"=E{r}/($B$6-$B$11)", fmt=PCT)
        put(ws, f"G{r}", f"=(D{r}+Z95^2/(2*B{r - 1})-Z95*SQRT(D{r}*(1-D{r})/B{r - 1}+Z95^2/(4*B{r - 1}^2)))/(1+Z95^2/B{r - 1})", fmt=PCT)
        put(ws, f"H{r}", f"=(D{r}+Z95^2/(2*B{r - 1})+Z95*SQRT(D{r}*(1-D{r})/B{r - 1}+Z95^2/(4*B{r - 1}^2)))/(1+Z95^2/B{r - 1})", fmt=PCT)
    else:
        for c in "DEFGH": put(ws, f"{c}{r}", "-", al=Alignment(horizontal="center"))
put(ws, "A12", "Total lost (registered - active 30d)", f_b); put(ws, "E12", "=SUM(E7:E11)", f_b, INT); put(ws, "F12", "=SUM(F7:F11)", f_b, PCT)
ws.conditional_formatting.add("B6:B11", DataBarRule(start_type="num", start_value=0, end_type="max", color="5B9BD5"))
ws.conditional_formatting.add("F7:F11", ColorScaleRule(start_type="min", start_color="FFFFFF", end_type="max", end_color="F4B183"))
ws.conditional_formatting.add("D7:D11", ColorScaleRule(start_type="min", start_color="F8CBAD", end_type="max", end_color="C6EFCE"))


def dim_block(ws, row, label, col, values):
    section(ws, row, f"{label}", 12)
    header(ws, row + 1, [label.split("by ")[-1].title(), "Mature users", "KYC rate", "Bank-link conv.", "Deposit conv.", "First-trade conv.", "Reg -> first trade"], height=34)
    r0 = row + 2
    all_ = ["All"] + values
    for i, v in enumerate(all_):
        r = r0 + i; crit = "" if v == "All" else f"tblUsers[{col}],$A{r},"
        put(ws, f"A{r}", v, f_b if v == "All" else f_n)
        put(ws, f"B{r}", f"=COUNTIFS({crit}tblUsers[funnel_mature],1)", fmt=INT)
        sm = lambda c: f"SUMIFS(tblUsers[{c}],{crit}tblUsers[funnel_mature],1)"
        put(ws, f"C{r}", f"={sm('kyc_asof')}/B{r}", fmt=PCT); put(ws, f"D{r}", f"={sm('bank_asof')}/{sm('kyc_asof')}", fmt=PCT)
        put(ws, f"E{r}", f"={sm('deposit_asof')}/{sm('bank_asof')}", fmt=PCT); put(ws, f"F{r}", f"={sm('trade_asof')}/{sm('deposit_asof')}", fmt=PCT)
        put(ws, f"G{r}", f"={sm('trade_asof')}/B{r}", fmt=PCT)
    ws.conditional_formatting.add(f"G{r0 + 1}:G{r0 + len(values)}", ColorScaleRule(start_type="min", start_color="F8CBAD", end_type="max", end_color="C6EFCE"))
    ws.conditional_formatting.add(f"C{r0 + 1}:C{r0 + len(values)}", ColorScaleRule(start_type="min", start_color="F8CBAD", end_type="max", end_color="C6EFCE"))
    return r0 + len(all_)


nxt = dim_block(ws, 15, "B. Funnel by channel", "acquisition_channel", CHS)
nxt = dim_block(ws, nxt + 1, "C. Funnel by device", "device_type", ["Android", "iOS", "Web"])
CITIES = sorted(U0.city.unique().tolist(), key=lambda s: (s == "Other", s))
nxt = dim_block(ws, nxt + 1, "D. Funnel by city", "city", CITIES)
r = nxt + 1; section(ws, r, "E. Time between stages (days, users who reached the stage; mature cohort; array formulas)", 12)
header(ws, r + 1, ["Stage transition", "Users", "Mean days", "Median days", "75th percentile"])
TS = [("Registration -> KYC", "days_reg_to_kyc"), ("KYC -> bank link", "days_kyc_to_bank"), ("Bank link -> first deposit", "days_bank_to_deposit"), ("Deposit -> first trade", "days_deposit_to_trade")]
for i, (lab, col) in enumerate(TS):
    rr = r + 2 + i; put(ws, f"A{rr}", lab)
    put(ws, f"B{rr}", f"=COUNTIFS(tblUsers[funnel_mature],1,tblUsers[{col}],\">=0\")", fmt=INT)
    put(ws, f"C{rr}", f"=AVERAGEIFS(tblUsers[{col}],tblUsers[funnel_mature],1)", fmt=DEC1)
    core = f"IF((tblUsers[funnel_mature]=1)*(tblUsers[{col}]<>\"\"),tblUsers[{col}])"
    ws[f"D{rr}"] = ArrayFormula(f"D{rr}", f"=MEDIAN({core})"); ws[f"D{rr}"].font = f_n; ws[f"D{rr}"].number_format = DEC1
    ws[f"E{rr}"] = ArrayFormula(f"E{rr}", f"=PERCENTILE({core},0.75)"); ws[f"E{rr}"].font = f_n; ws[f"E{rr}"].number_format = DEC1
TS_ROW = r + 2
r = r + 8; section(ws, r, "F. Acquisition calendar - registrations by month (date arithmetic with EDATE) and by weekday", 12)
header(ws, r + 1, ["Month start", "Registrations", "MoM change", "Became traders (as-of)", "Trader rate (as-of)"])
for i in range(12):
    rr = r + 2 + i
    put(ws, f"A{rr}", "=WindowStart" if i == 0 else f"=EDATE(A{rr - 1},1)", fmt="mmm-yy")
    put(ws, f"B{rr}", f'=COUNTIFS(tblUsers[registration_date],">="&A{rr},tblUsers[registration_date],"<"&EDATE(A{rr},1))', fmt=INT)
    put(ws, f"C{rr}", f"=B{rr}/B{rr - 1}-1" if i else "-", fmt=PCT)
    put(ws, f"D{rr}", f'=SUMIFS(tblUsers[trade_asof],tblUsers[registration_date],">="&A{rr},tblUsers[registration_date],"<"&EDATE(A{rr},1))', fmt=INT)
    put(ws, f"E{rr}", f"=D{rr}/B{rr}", fmt=PCT)
CAL_ROW = r + 2
put(ws, f"A{r + 14}", "Total", f_b); put(ws, f"B{r + 14}", f"=SUM(B{r + 2}:B{r + 13})", f_b, INT)
header(ws, r + 1, ["Weekday", "Registrations", "Share"], col=7)
for i, d in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
    rr = r + 2 + i; put(ws, f"G{rr}", d); put(ws, f"H{rr}", f"=COUNTIFS(tblUsers[reg_weekday],G{rr})", fmt=INT); put(ws, f"I{rr}", f"=H{rr}/COUNTA(tblUsers[user_id])", fmt=PCT)
ws.conditional_formatting.add(f"B{r + 2}:B{r + 13}", DataBarRule(start_type="num", start_value=0, end_type="max", color="9DC3E6"))
fc = BarChart(); fc.type = "bar"; fc.title = "Onboarding funnel - users reached (mature cohort, synthetic)"; fc.style = 10; fc.legend = None
fc.add_data(Reference(ws, min_col=2, min_row=5, max_row=11), titles_from_data=True); fc.set_categories(Reference(ws, min_col=1, min_row=6, max_row=11))
fc.x_axis.scaling.orientation = "maxMin"; fc.x_axis.delete = False; fc.y_axis.delete = False; fc.height, fc.width = 8.5, 16; fc.series[0].graphicalProperties.solidFill = "2E75B6"
fc.dataLabels = DataLabelList(); fc.dataLabels.showVal = True; fc.dataLabels.showSerName = False; fc.dataLabels.showCatName = False; fc.dataLabels.showLegendKey = False; fc.dataLabels.showPercent = False; ws.add_chart(fc, "K4")
widths(ws, {"A": 34, "B": 15, "C": 14, "D": 16, "E": 16, "F": 17, "G": 16, "H": 16, "I": 12})
FUN = dict(reached={s: f"Funnel_Analysis!$B${6 + i}" for i, s in enumerate(STG)}, conv={s: f"Funnel_Analysis!$D${6 + i}" for i, s in enumerate(STG) if i}, share={s: f"Funnel_Analysis!$F${6 + i}" for i, s in enumerate(STG) if i},
           ts=TS_ROW)

# ----------------------------------------------------------------------------------------------- Retention_Analysis
ws = WS["Retention_Analysis"]; title(ws, "Retention_Analysis - cohort retention, MAU, repeat trading and inactivity", "Monthly_Activity is the source of truth for activity. M_k = share active in calendar month k after the registration month (a proxy, not exact 30/90/180 days). Blank = not yet observable.")
section(ws, 4, "A. Cohort retention matrix (% of cohort active; AVERAGEIFS on tblActivity)", 14)
header(ws, 5, ["Cohort", "Cohort users"] + [None] * 7, height=24)
for k in range(7): put(ws, f"{CL(3 + k)}5", k, f_h, '"M"0', fill_h, ctr, box)
cohorts = [202511, 202512, 202601, 202602, 202603, 202604, 202605, 202606, 202607, 202608, 202609, 202610]
for i, ck in enumerate(cohorts):
    r = 6 + i; put(ws, f"A{r}", ck, f_n, '0000"-"00'); put(ws, f"B{r}", f"=COUNTIFS(tblUsers[reg_month_key],$A{r})", fmt=INT)
    for k in range(7):
        c = CL(3 + k)
        put(ws, f"{c}{r}", f'=IFERROR(AVERAGEIFS(tblActivity[active_in_month],tblActivity[registration_month_key],$A{r},tblActivity[months_since_registration],{c}$5),"")', fmt=PCT)
put(ws, "A18", "POOLED", f_b); put(ws, "B18", "=SUM(B6:B17)", f_b, INT)
for k in range(7):
    c = CL(3 + k); put(ws, f"{c}18", f"=AVERAGEIFS(tblActivity[active_in_month],tblActivity[months_since_registration],{c}$5)", f_b, PCT2)
ws.conditional_formatting.add("C6:I17", ColorScaleRule(start_type="num", start_value=0.3, start_color="F8CBAD", mid_type="num", mid_value=0.55, mid_color="FFEB9C", end_type="num", end_value=0.8, end_color="63BE7B"))
put(ws, "A19", "Pooled M_k divides all active user-months at offset k by all user-months at offset k, which is why it can differ slightly from a simple average of cohort rows.", f_sub)
lc = LineChart(); lc.title = "Pooled retention curve (% of cohort active, synthetic)"; lc.style = 12; lc.legend = None
lc.add_data(Reference(ws, min_col=3, max_col=9, min_row=18), from_rows=True, titles_from_data=False); lc.set_categories(Reference(ws, min_col=3, max_col=9, min_row=5))
lc.y_axis.number_format = "0%"; lc.y_axis.scaling.min = 0; lc.y_axis.scaling.max = 0.9; lc.x_axis.delete = False; lc.y_axis.delete = False; lc.height, lc.width = 7.5, 13
lc.series[0].graphicalProperties.line.solidFill = "2E75B6"; lc.series[0].graphicalProperties.line.width = 28000; ws.add_chart(lc, "K4")
section(ws, 22, "B. Monthly active users (SUMIFS on tblActivity) and new vs existing", 14)
header(ws, 23, ["Month", "MAU", "of which new (registration month)", "of which existing", "Registered to date", "MAU % of registered", "Trading users", "Trades", "Trading value (INR mn)"], height=44)
for i, ck in enumerate(cohorts):
    r = 24 + i; put(ws, f"A{r}", ck, f_n, '0000"-"00')
    put(ws, f"B{r}", f"=SUMIFS(tblActivity[active_in_month],tblActivity[activity_month_key],$A{r})", fmt=INT)
    put(ws, f"C{r}", f"=SUMIFS(tblActivity[active_in_month],tblActivity[activity_month_key],$A{r},tblActivity[months_since_registration],0)", fmt=INT)
    put(ws, f"D{r}", f"=B{r}-C{r}", fmt=INT); put(ws, f"E{r}", f'=COUNTIFS(tblUsers[reg_month_key],"<="&$A{r})', fmt=INT); put(ws, f"F{r}", f"=B{r}/E{r}", fmt=PCT)
    put(ws, f"G{r}", f"=SUMIFS(tblActivity[traded_in_month],tblActivity[activity_month_key],$A{r})", fmt=INT)
    put(ws, f"H{r}", f"=SUMIFS(tblActivity[trade_count],tblActivity[activity_month_key],$A{r})", fmt=INT)
    put(ws, f"I{r}", f"=SUMIFS(tblActivity[trading_value_inr],tblActivity[activity_month_key],$A{r})/1000000", fmt=DEC2)
ws.conditional_formatting.add("B24:B35", DataBarRule(start_type="num", start_value=0, end_type="max", color="5B9BD5"))
mc = BarChart(); mc.type = "col"; mc.title = "Monthly active users (synthetic)"; mc.style = 10; mc.legend = None
mc.add_data(Reference(ws, min_col=2, min_row=23, max_row=35), titles_from_data=True); mc.set_categories(Reference(ws, min_col=1, min_row=24, max_row=35))
mc.x_axis.number_format = '0000"-"00'; mc.x_axis.delete = False; mc.y_axis.delete = False; mc.height, mc.width = 7.5, 13; mc.series[0].graphicalProperties.solidFill = "2E75B6"; ws.add_chart(mc, "K22")
section(ws, 38, "C. Headline retention, inactivity and repeat-trading metrics (all proxies, none confirmed churn)", 14)
header(ws, 39, ["Metric", "Value", "Eligible base", "Definition"], height=24)
HM = [("M1 retention (pooled)", "=D18", "=COUNTIFS(tblActivity[months_since_registration],1)", "Active in the calendar month after the registration month", PCT2),
      ("M3 retention (pooled)", "=F18", "=COUNTIFS(tblActivity[months_since_registration],3)", "Active 3 calendar months after the registration month", PCT2),
      ("M6 retention (pooled)", "=I18", "=COUNTIFS(tblActivity[months_since_registration],6)", "Active 6 calendar months after the registration month", PCT2),
      ("Active in last 30 days", "=AVERAGEIFS(tblUsers[active_30d_adj],tblUsers[eligible_30d],1)", "=COUNTIFS(tblUsers[eligible_30d],1)", "Days since last activity <= 30; tenure >= 31 days", PCT2),
      ("Inactive > 90 days (proxy)", "=AVERAGEIFS(tblUsers[inactive_90d_adj],tblUsers[eligible_90d],1)", "=COUNTIFS(tblUsers[eligible_90d],1)", "Days since last activity > 90 (bounded at 120); tenure >= 91 days", PCT2),
      ("Dormant 3 months (proxy)", "=AVERAGE(tblUsers[dormant_3m_monthly])", "=COUNT(tblUsers[dormant_3m_monthly])", "No active month Aug-Oct 2026; registered by Jul-2026", PCT2),
      ("Ever-traded users (>=4 observed months)", '=COUNTIFS(tblUsers[months_observed],">="&RepBaseMonths,tblUsers[trade_months],">=1")', '=COUNTIFS(tblUsers[months_observed],">="&RepBaseMonths)', "Traded in at least one calendar month (monthly source)", INT),
      ("Repeat traders, % of ever-traders", '=COUNTIFS(tblUsers[months_observed],">="&RepBaseMonths,tblUsers[trade_months],">="&Rep_Min)/B45', "=B45", "Traded in 2+ calendar months", PCT2),
      ("Traded in 3+ months, % of ever-traders", '=COUNTIFS(tblUsers[months_observed],">="&RepBaseMonths,tblUsers[trade_months],">=3")/B45', "=B45", "Traded in 3+ calendar months", PCT2)]
for i, (m, f, base, d, fm) in enumerate(HM):
    r = 40 + i; put(ws, f"A{r}", m); put(ws, f"B{r}", f, f_b, fm); put(ws, f"C{r}", base, fmt=INT); put(ws, f"D{r}", d, f_sub)
section(ws, 51, "D. Retention and inactivity by channel (AVERAGEIFS on tblUsers)", 14)
header(ws, 52, ["Channel", "M1", "M3", "M6", "Active 30d", "Inactive >90d", "Dormant 3m", "Repeat % of ever-traders"], height=34)
for i, chn in enumerate(CHS + ["All"], start=53):
    put(ws, f"A{i}", chn, f_b if chn == "All" else f_n)
    cr = "" if chn == "All" else f",tblUsers[acquisition_channel],$A{i}"
    cr1 = "" if chn == "All" else f"tblUsers[acquisition_channel],$A{i},"
    for col, c in (("B", "m1_retained"), ("C", "m3_retained"), ("D", "m6_retained"), ("G", "dormant_3m_monthly")):
        put(ws, f"{col}{i}", f"=AVERAGEIFS(tblUsers[{c}],tblUsers[{c}],\">=0\"{cr})", fmt=PCT)
    put(ws, f"E{i}", f"=AVERAGEIFS(tblUsers[active_30d_adj],tblUsers[eligible_30d],1{cr})", fmt=PCT)
    put(ws, f"F{i}", f"=AVERAGEIFS(tblUsers[inactive_90d_adj],tblUsers[eligible_90d],1{cr})", fmt=PCT)
    put(ws, f"H{i}", f'=COUNTIFS({cr1}tblUsers[months_observed],">="&RepBaseMonths,tblUsers[trade_months],">="&Rep_Min)/COUNTIFS({cr1}tblUsers[months_observed],">="&RepBaseMonths,tblUsers[trade_months],">=1")', fmt=PCT)
ws.conditional_formatting.add("C53:C59", ColorScaleRule(start_type="min", start_color="F8CBAD", end_type="max", end_color="C6EFCE"))
ws.conditional_formatting.add("G53:G59", ColorScaleRule(start_type="min", start_color="C6EFCE", end_type="max", end_color="F8CBAD"))
widths(ws, {"A": 36, "B": 14, "C": 16, "D": 14, "E": 15, "F": 15, "G": 14, "H": 20, "I": 16})
RET = dict(m1="Retention_Analysis!$B$40", m3="Retention_Analysis!$B$41", m6="Retention_Analysis!$B$42", a30="Retention_Analysis!$B$43", i90="Retention_Analysis!$B$44",
           dorm="Retention_Analysis!$B$45", rep="Retention_Analysis!$B$47", repbase="Retention_Analysis!$C$46", mau_last="Retention_Analysis!$B$35", mau_first="Retention_Analysis!$B$24")
# fix: rows - HM index 0..8 -> rows 40..48 ; ever-traded row = 46, repeat = 47, repeat3 = 48 ; dormant row = 45 ; base ref for repeat uses ever-traded count (row 46)
for i, (m, f, base, d, fm) in enumerate(HM):
    pass
ws["B47"] = '=COUNTIFS(tblUsers[months_observed],">="&RepBaseMonths,tblUsers[trade_months],">="&Rep_Min)/B46'; ws["B48"] = '=COUNTIFS(tblUsers[months_observed],">="&RepBaseMonths,tblUsers[trade_months],">=3")/B46'
ws["C47"] = "=B46"; ws["C48"] = "=B46"; ws["C46"] = '=COUNTIFS(tblUsers[months_observed],">="&RepBaseMonths)'
for a in ("B47", "B48"): ws[a].font = f_b; ws[a].number_format = PCT2
RET.update(rep="Retention_Analysis!$B$47", repbase="Retention_Analysis!$C$46")

# ----------------------------------------------------------------------------------------------- Customer_Segmentation
ws = WS["Customer_Segmentation"]; title(ws, "Customer_Segmentation - rule-based journey segments, deposit bands and high-potential list", "journey_segment is a calculated column in tblUsers (nested IFS using the lag limits on the Assumptions sheet). Segments are operational groupings for action, not statistical clusters.")
section(ws, 4, "A. Journey segments (COUNTIFS / AVERAGEIFS on tblUsers[journey_segment])", 12)
header(ws, 5, ["Journey segment", "Rule (plain English)", "Users", "Share", "Avg tenure (days)", "Avg 6m trading value (INR)", "Tickets per user", "Recommended operational action"], height=40)
SEGS = [("01 New / in-flight onboarding", "Still inside the historical max lag for their furthest stage", "Let the journey run; light nudges only"),
        ("02 KYC-pending (stalled)", "Registered, no KYC, pending longer than 11 days", "KYC rescue: reminders + assisted verification"),
        ("03 Bank-link pending (stalled)", "KYC done, no bank link, pending longer than 7 days", "Bank-link help content + UPI/net-banking prompts"),
        ("04 Deposit-pending (stalled)", "Bank linked, no deposit, pending longer than 14 days", "First-deposit nudge; small-ticket starter prompt"),
        ("05 Deposited, never traded (stalled)", "Funded, no trade, pending longer than 11 days", "Activation: guided first trade, education"),
        ("06 First-time trader (<=30d since first trade)", "First trade within the last 30 days", "Habit building: second-trade prompt"),
        ("07 Repeat trader (2-3 trading months of last 6)", "Traded in 2-3 of the last 6 months", "Frequency nudges; feature discovery"),
        ("08 High-engagement trader (>=4 trading months of last 6)", "Traded in 4+ of the last 6 months", "Retain and reward; service priority"),
        ("09 Inactive trader (no activity Aug-Oct)", "Traded before, no active month Aug-Oct 2026", "Win-back campaign (no pitch on first touch)"),
        ("10 Occasional trader (0-1 trading months of last 6)", "Trader with at most 1 trading month in last 6", "Re-engagement; relevance-based content")]
for i, (sg, rule, act) in enumerate(SEGS):
    r = 6 + i; put(ws, f"A{r}", sg); put(ws, f"B{r}", rule, al=wrap); put(ws, f"C{r}", f"=COUNTIFS(tblUsers[journey_segment],$A{r})", fmt=INT)
    put(ws, f"D{r}", f"=C{r}/$C$16", fmt=PCT); put(ws, f"E{r}", f"=IFERROR(AVERAGEIFS(tblUsers[tenure_days],tblUsers[journey_segment],$A{r}),0)", fmt=INT)
    put(ws, f"F{r}", f"=IFERROR(AVERAGEIFS(tblUsers[trading_value_6m_inr],tblUsers[journey_segment],$A{r}),0)", fmt=INR)
    put(ws, f"G{r}", f"=IFERROR(AVERAGEIFS(tblUsers[ticket_count],tblUsers[journey_segment],$A{r}),0)", fmt=DEC2); put(ws, f"H{r}", act, al=wrap); ws.row_dimensions[r].height = 28
put(ws, "A16", "Total", f_b); put(ws, "C16", "=SUM(C6:C15)", f_b, INT); put(ws, "D16", "=SUM(D6:D15)", f_b, PCT)
ws.conditional_formatting.add("C6:C15", DataBarRule(start_type="num", start_value=0, end_type="max", color="5B9BD5"))
section(ws, 19, "B. Segment x channel (user counts)", 12)
header(ws, 20, ["Journey segment"] + CHS, height=30)
for i, (sg, *_x) in enumerate(SEGS):
    r = 21 + i; put(ws, f"A{r}", f"=A{6 + i}")
    for j in range(7): put(ws, f"{CL(2 + j)}{r}", f"=COUNTIFS(tblUsers[journey_segment],$A{r},tblUsers[acquisition_channel],{CL(2 + j)}$20)", fmt=INT)
ws.conditional_formatting.add("B21:H30", ColorScaleRule(start_type="min", start_color="FFFFFF", end_type="max", end_color="5B9BD5"))
section(ws, 33, "C. First-deposit bands (depositors only)", 12)
header(ws, 34, ["Deposit band", "Users", "Share of depositors", "Avg trading value 6m (INR)", "First-trade rate"], height=30)
for i, b in enumerate(["Under Rs3k", "Rs3-6.5k", "Rs6.5-11.4k", "Rs11.4k and above (top quartile)"]):
    r = 35 + i; put(ws, f"A{r}", b); put(ws, f"B{r}", f"=COUNTIFS(tblUsers[deposit_band],A{r})", fmt=INT); put(ws, f"C{r}", f"=B{r}/SUM($B$35:$B$38)", fmt=PCT)
    put(ws, f"D{r}", f"=IFERROR(AVERAGEIFS(tblUsers[trading_value_6m_inr],tblUsers[deposit_band],A{r}),0)", fmt=INR)
    put(ws, f"E{r}", f"=SUMIFS(tblUsers[trade_asof],tblUsers[deposit_band],A{r})/B{r}", fmt=PCT)
put(ws, "A39", "Depositors total", f_b); put(ws, "B39", "=SUM(B35:B38)", f_b, INT)
section(ws, 42, "D. High-potential customers: funded but never traded, ranked by first-deposit size (top 25 via LARGE + INDEX/MATCH)", 12)
put(ws, "A43", "Idle depositors (funded, no trade)"); put(ws, "C43", "=COUNT(tblUsers[idle_deposit_key])", f_b, INT)
put(ws, "A44", "Idle first deposits, total (INR)"); put(ws, "C44", '=SUMIFS(tblUsers[first_deposit_amount_asof_inr],tblUsers[deposit_asof],1,tblUsers[trade_asof],0)', f_b, INR)
put(ws, "A45", "Idle longer than the idle threshold (stalled)"); put(ws, "C45", '=COUNTIFS(tblUsers[deposit_asof],1,tblUsers[trade_asof],0,tblUsers[days_since_registration],">0")-COUNTIFS(tblUsers[deposit_asof],1,tblUsers[trade_asof],0,tblUsers[deposit_date_asof],">"&(Snapshot-IdleDays))', f_b, INT)
header(ws, 47, ["Rank", "User ID", "Channel", "City", "Device", "First deposit (INR)", "Days since deposit", "Row key (helper)"], height=30)
for k in range(25):
    r = 48 + k; put(ws, f"A{r}", k + 1)
    put(ws, f"H{r}", f"=LARGE(tblUsers[idle_deposit_key],A{r})", fmt="0.0000000", font=Font(name=FN, size=9, color="7F7F7F"))
    mt = f"MATCH($H{r},tblUsers[idle_deposit_key],0)"
    put(ws, f"B{r}", f"=INDEX(tblUsers[user_id],{mt})"); put(ws, f"C{r}", f"=INDEX(tblUsers[acquisition_channel],{mt})"); put(ws, f"D{r}", f"=INDEX(tblUsers[city],{mt})")
    put(ws, f"E{r}", f"=INDEX(tblUsers[device_type],{mt})"); put(ws, f"F{r}", f"=INDEX(tblUsers[first_deposit_amount_asof_inr],{mt})", fmt=INR)
    put(ws, f"G{r}", f"=Snapshot-INDEX(tblUsers[deposit_date_asof],{mt})", fmt=INT)
ws.conditional_formatting.add("F48:F72", DataBarRule(start_type="num", start_value=0, end_type="max", color="F4B183"))
sc = BarChart(); sc.type = "bar"; sc.title = "Users by journey segment (synthetic)"; sc.style = 10; sc.legend = None
sc.add_data(Reference(ws, min_col=3, min_row=5, max_row=15), titles_from_data=True); sc.set_categories(Reference(ws, min_col=1, min_row=6, max_row=15))
sc.x_axis.scaling.orientation = "maxMin"; sc.x_axis.delete = False; sc.y_axis.delete = False; sc.height, sc.width = 9, 15; sc.series[0].graphicalProperties.solidFill = "2E75B6"; ws.add_chart(sc, "J19")
widths(ws, {"A": 52, "B": 42, "C": 15, "D": 16, "E": 16, "F": 20, "G": 15, "H": 42})

# ----------------------------------------------------------------------------------------------- Support_Analysis
ws = WS["Support_Analysis"]; title(ws, "Support_Analysis - ticket volume, resolution, CSAT, backlog and repeat contact", "Resolution time and CSAT exist only for resolved tickets. Unresolved = Open + Escalated. Medians are array formulas (MEDIAN(IF(...))).")
section(ws, 4, "A. Support KPIs", 12)
header(ws, 5, ["KPI", "Value", "Note"], height=24)
SK = [("Tickets", "=COUNTA(tblTickets[ticket_id])", INT, ""), ("Tickets per 1,000 users", "=1000*B6/COUNTA(tblUsers[user_id])", INT, "Per registered user, whole period"),
      ("Users with at least one ticket", '=COUNTIFS(tblUsers[ticket_count],">0")/COUNTA(tblUsers[user_id])', PCT, ""), ("Resolved share", "=SUM(tblTickets[is_resolved])/B6", PCT, ""),
      ("Open tickets", '=COUNTIFS(tblTickets[status],"Open")', INT, ""), ("Escalated tickets", '=COUNTIFS(tblTickets[status],"Escalated")', INT, ""),
      ("Unresolved tickets (open + escalated)", "=B10+B11", INT, "Backlog"), ("Mean resolution time (h)", "=AVERAGE(tblTickets[resolution_time_hours])", DEC1, "Resolved tickets only"),
      ("Median resolution time (h)", None, DEC1, "Typical wait; array formula"), ("Within-SLA share of resolved", '=COUNTIFS(tblTickets[sla_flag],"Within SLA")/SUM(tblTickets[is_resolved])', PCT, "SLA hours on Assumptions (illustrative)"),
      ("CSAT, mean (1-5)", "=AVERAGE(tblTickets[csat_score])", DEC2, "Rated (resolved) tickets only"), ("CSAT top-box (4-5)", '=COUNTIFS(tblTickets[csat_score],">=4")/COUNT(tblTickets[csat_score])', PCT, ""),
      ("CSAT bottom-box (1-2)", '=COUNTIFS(tblTickets[csat_score],"<=2")/COUNT(tblTickets[csat_score])', PCT, "")]
for i, (k, f, fm, n) in enumerate(SK):
    r = 6 + i; put(ws, f"A{r}", k)
    if f: put(ws, f"B{r}", f, f_b, fm)
    put(ws, f"C{r}", n, f_sub)
ws["B14"] = ArrayFormula("B14", '=MEDIAN(IF(tblTickets[resolution_time_hours]<>"",tblTickets[resolution_time_hours]))'); ws["B14"].font = f_b; ws["B14"].number_format = DEC1
section(ws, 21, "B. Ticket categories", 12)
header(ws, 22, ["Category", "Tickets", "Share", "High priority", "Escalated", "Unresolved", "Mean res. (h)", "Median res. (h)", "Avg CSAT", "CSAT top-box"], height=34)
CATS = ["KYC & verification", "Trading & orders", "Bank linking", "Deposits & withdrawals", "App navigation", "Account access", "Fees & charges"]
for i, c in enumerate(CATS):
    r = 23 + i; put(ws, f"A{r}", c); put(ws, f"B{r}", f"=COUNTIFS(tblTickets[category],$A{r})", fmt=INT); put(ws, f"C{r}", f"=B{r}/$B$30", fmt=PCT)
    put(ws, f"D{r}", f'=COUNTIFS(tblTickets[category],$A{r},tblTickets[priority],"High")', fmt=INT); put(ws, f"E{r}", f'=COUNTIFS(tblTickets[category],$A{r},tblTickets[status],"Escalated")', fmt=INT)
    put(ws, f"F{r}", f"=SUMIFS(tblTickets[is_unresolved],tblTickets[category],$A{r})", fmt=INT); put(ws, f"G{r}", f"=AVERAGEIFS(tblTickets[resolution_time_hours],tblTickets[category],$A{r})", fmt=DEC1)
    ws[f"H{r}"] = ArrayFormula(f"H{r}", f'=MEDIAN(IF((tblTickets[category]=$A{r})*(tblTickets[resolution_time_hours]<>""),tblTickets[resolution_time_hours]))'); ws[f"H{r}"].font = f_n; ws[f"H{r}"].number_format = DEC1
    put(ws, f"I{r}", f"=AVERAGEIFS(tblTickets[csat_score],tblTickets[category],$A{r})", fmt=DEC2)
    put(ws, f"J{r}", f'=COUNTIFS(tblTickets[category],$A{r},tblTickets[csat_score],">=4")/COUNTIFS(tblTickets[category],$A{r},tblTickets[csat_score],">0")', fmt=PCT)
put(ws, "A30", "Total", f_b)
for c in "BDEF": put(ws, f"{c}30", f"=SUM({c}23:{c}29)", f_b, INT)
put(ws, "C30", "=SUM(C23:C29)", f_b, PCT)
ws.conditional_formatting.add("B23:B29", DataBarRule(start_type="num", start_value=0, end_type="max", color="5B9BD5"))
ws.conditional_formatting.add("I23:I29", ColorScaleRule(start_type="min", start_color="F8CBAD", end_type="max", end_color="C6EFCE"))
section(ws, 33, "C. Backlog ageing - unresolved tickets by age bucket and priority (COUNTIFS)", 12)
header(ws, 34, ["Age bucket", "High", "Medium", "Low", "Total"], height=24)
for i, b in enumerate(["0-30d", "31-90d", "91-180d", ">180d"]):
    r = 35 + i; put(ws, f"A{r}", b)
    for j, p in enumerate(["High", "Medium", "Low"]): put(ws, f"{CL(2 + j)}{r}", f'=COUNTIFS(tblTickets[backlog_age_bucket],"="&$A{r},tblTickets[priority],{CL(2 + j)}$34,tblTickets[is_unresolved],1)', fmt=INT)
    put(ws, f"E{r}", f"=SUM(B{r}:D{r})", f_b, INT)
put(ws, "A39", "Total", f_b)
for c in "BCDE": put(ws, f"{c}39", f"=SUM({c}35:{c}38)", f_b, INT)
ws.conditional_formatting.add("B35:D38", ColorScaleRule(start_type="min", start_color="FFFFFF", end_type="max", end_color="F4B183"))
section(ws, 42, "D. Monthly ticket trend", 12)
header(ws, 43, ["Month", "Tickets", "Mean res. (h)", "Avg CSAT"], height=24)
for i, ck in enumerate(cohorts):
    r = 44 + i; put(ws, f"A{r}", ck, f_n, '0000"-"00'); put(ws, f"B{r}", f"=COUNTIFS(tblTickets[created_month_key],$A{r})", fmt=INT)
    put(ws, f"C{r}", f"=AVERAGEIFS(tblTickets[resolution_time_hours],tblTickets[created_month_key],$A{r})", fmt=DEC1); put(ws, f"D{r}", f"=AVERAGEIFS(tblTickets[csat_score],tblTickets[created_month_key],$A{r})", fmt=DEC2)
section(ws, 58, "E. Repeat contact and dormancy (descriptive screening only; not adjusted for cohort age or channel)", 12)
header(ws, 59, ["Group", "Users (dormancy-eligible)", "Dormant 3m rate", "Note"], height=34)
GR = [("0 tickets", '=COUNTIFS(tblUsers[ticket_count],0,tblUsers[dormant_3m_monthly],">=0")', '=AVERAGEIFS(tblUsers[dormant_3m_monthly],tblUsers[ticket_count],0)'),
      ("Has an unresolved ticket", '=COUNTIFS(tblUsers[unresolved_ticket_count],">0",tblUsers[dormant_3m_monthly],">=0")', '=AVERAGEIFS(tblUsers[dormant_3m_monthly],tblUsers[unresolved_ticket_count],">0")'),
      ("Tickets, all resolved", '=COUNTIFS(tblUsers[ticket_count],">0",tblUsers[unresolved_ticket_count],0,tblUsers[dormant_3m_monthly],">=0")', '=AVERAGEIFS(tblUsers[dormant_3m_monthly],tblUsers[ticket_count],">0",tblUsers[unresolved_ticket_count],0)'),
      ("Repeat contactors (>= threshold tickets)", '=COUNTIFS(tblUsers[ticket_count],">="&TicketRepeatMin,tblUsers[dormant_3m_monthly],">=0")', '=AVERAGEIFS(tblUsers[dormant_3m_monthly],tblUsers[ticket_count],">="&TicketRepeatMin)')]
for i, (g, n_, d_) in enumerate(GR):
    r = 60 + i; put(ws, f"A{r}", g); put(ws, f"B{r}", n_, fmt=INT); put(ws, f"C{r}", d_, fmt=PCT); put(ws, f"D{r}", "Association only - does not show that support caused disengagement.", f_sub)
put(ws, "A64", "Users with >= threshold tickets (all users)"); put(ws, "B64", '=COUNTIFS(tblUsers[ticket_count],">="&TicketRepeatMin)', f_b, INT)
tc = BarChart(); tc.type = "bar"; tc.title = "Support tickets by category (synthetic)"; tc.style = 10; tc.legend = None
tc.add_data(Reference(ws, min_col=2, min_row=22, max_row=29), titles_from_data=True); tc.set_categories(Reference(ws, min_col=1, min_row=23, max_row=29))
tc.x_axis.scaling.orientation = "maxMin"; tc.x_axis.delete = False; tc.y_axis.delete = False; tc.height, tc.width = 8, 14; tc.series[0].graphicalProperties.solidFill = "2E75B6"; ws.add_chart(tc, "L4")
widths(ws, {"A": 42, "B": 18, "C": 16, "D": 14, "E": 12, "F": 12, "G": 14, "H": 14, "I": 12, "J": 13})
SUP = dict(tickets="Support_Analysis!$B$6", per1000="Support_Analysis!$B$7", resolved="Support_Analysis!$B$9", open="Support_Analysis!$B$10", esc="Support_Analysis!$B$11",
           mean="Support_Analysis!$B$13", median="Support_Analysis!$B$14", csat="Support_Analysis!$B$16", cat0=23)

# ----------------------------------------------------------------------------------------------- KPI_Summary (dynamic)
ws = WS["KPI_Summary"]; title(ws, "KPI_Summary - dynamic KPI panel", "Change the yellow selectors (dropdowns / dates). Tiles recalculate through SUMIFS / COUNTIFS / AVERAGEIFS with wildcard criteria. All data are SYNTHETIC.")
section(ws, 4, "1. Selectors", 8)
put(ws, "A5", "Acquisition channel", f_b); put(ws, "B5", "All", f_in, fill=fill_y, border=box); put(ws, "C5", '=IF(B5="All","*",B5)', Font(name=FN, size=9, color="7F7F7F"))
put(ws, "A6", "Device type", f_b); put(ws, "B6", "All", f_in, fill=fill_y, border=box); put(ws, "C6", '=IF(B6="All","*",B6)', Font(name=FN, size=9, color="7F7F7F"))
put(ws, "A7", "Registered from", f_b); put(ws, "B7", datetime(2025, 11, 1), f_in, DATE, fill_y, border=box)
put(ws, "A8", "Registered to", f_b); put(ws, "B8", datetime(2026, 10, 31), f_in, DATE, fill_y, border=box)
put(ws, "D5", "(C5:C6 hold the wildcard criteria: 'All' becomes '*')", f_sub)
dv1 = DataValidation(type="list", formula1='"All,Organic,Referral,CRM,Paid Search,Paid Social,Affiliate,Partnerships"', allow_blank=False); dv2 = DataValidation(type="list", formula1='"All,Android,iOS,Web"', allow_blank=False)
dv3 = DataValidation(type="date", operator="between", formula1="DATE(2025,11,1)", formula2="DATE(2026,10,31)")
for dv, rng in ((dv1, "B5"), (dv2, "B6"), (dv3, "B7:B8")): ws.add_data_validation(dv); dv.add(rng)
section(ws, 10, "2. Dynamic KPIs for the selection", 8)
header(ws, 11, ["KPI", "Value", "Eligible base", "Definition"], height=24)
FLT = 'tblUsers[acquisition_channel],$C$5,tblUsers[device_type],$C$6,tblUsers[registration_date],">="&$B$7,tblUsers[registration_date],"<="&$B$8'
DK = [("Registrations", f"=COUNTIFS({FLT})", "", INT, "Users registered in the window"),
      ("Mature registrations", f"=COUNTIFS({FLT},tblUsers[funnel_mature],1)", "", INT, "Registered before 2026-10; used for funnel rates"),
      ("KYC completion rate", f"=IFERROR(SUMIFS(tblUsers[kyc_asof],{FLT},tblUsers[funnel_mature],1)/B13,\"n/a\")", "=B13", PCT, "KYC completed / mature registered"),
      ("Bank-link conversion", f"=IFERROR(SUMIFS(tblUsers[bank_asof],{FLT},tblUsers[funnel_mature],1)/SUMIFS(tblUsers[kyc_asof],{FLT},tblUsers[funnel_mature],1),\"n/a\")", "", PCT, "Bank linked / KYC completed"),
      ("First-deposit conversion", f"=IFERROR(SUMIFS(tblUsers[deposit_asof],{FLT},tblUsers[funnel_mature],1)/SUMIFS(tblUsers[bank_asof],{FLT},tblUsers[funnel_mature],1),\"n/a\")", "", PCT, "Funded / bank linked"),
      ("First-trade conversion (of funded)", f"=IFERROR(SUMIFS(tblUsers[trade_asof],{FLT},tblUsers[funnel_mature],1)/SUMIFS(tblUsers[deposit_asof],{FLT},tblUsers[funnel_mature],1),\"n/a\")", "", PCT, "First traders / funded"),
      ("Registered -> first trade", f"=IFERROR(SUMIFS(tblUsers[trade_asof],{FLT},tblUsers[funnel_mature],1)/B13,\"n/a\")", "=B13", PCT, "End-to-end activation, mature cohort"),
      ("M3 retention (calendar-month proxy)", f"=IFERROR(AVERAGEIFS(tblUsers[m3_retained],{FLT}),\"n/a\")", f"=COUNTIFS({FLT},tblUsers[m3_retained],\">=0\")", PCT, "Active 3 calendar months after registration month"),
      ("Dormant 3 months (churn proxy)", f"=IFERROR(AVERAGEIFS(tblUsers[dormant_3m_monthly],{FLT}),\"n/a\")", f"=COUNTIFS({FLT},tblUsers[dormant_3m_monthly],\">=0\")", PCT, "No active month Aug-Oct 2026"),
      ("Tickets per 1,000 users", f"=IFERROR(1000*SUMIFS(tblUsers[ticket_count],{FLT})/B12,\"n/a\")", "=B12", INT, "Support contacts per 1,000 registered"),
      ("Avg first deposit (depositors, INR)", f"=IFERROR(AVERAGEIFS(tblUsers[first_deposit_amount_asof_inr],{FLT},tblUsers[deposit_asof],1),\"n/a\")", "", INR, "Mean over users with a deposit"),
      ("Channel CAC, full period (INR)", '=IFERROR(IF(SUMIFS(tblCampaigns[campaign_spend_inr],tblCampaigns[channel],$C$5)=0,"n/a",SUMIFS(tblCampaigns[campaign_spend_inr],tblCampaigns[channel],$C$5)/COUNTIFS(tblUsers[acquisition_channel],$C$5)),"n/a")', "", DEC1,
       "Spend is not dated, so this ignores the date and device filters; 'n/a' for All/Organic")]
for i, (k, f, base, fm, d) in enumerate(DK):
    r = 12 + i; put(ws, f"A{r}", k, f_b); put(ws, f"B{r}", f, f_n, fm, fill=fill_g, border=box); put(ws, f"C{r}", base if base else None, fmt=INT); put(ws, f"D{r}", d, f_sub)
section(ws, 26, "3. Headline KPIs (links to the analysis sheets - green = cross-sheet link)", 8)
header(ws, 27, ["KPI", "Value", "", "Source sheet"], height=24)
HL = [("Total registrations", "=COUNTA(tblUsers[user_id])", INT, "Cleaned_Users"), ("Mature cohort users", "=Funnel_Analysis!B6", INT, "Funnel_Analysis"),
      ("Mature registered -> first trade", "=Funnel_Analysis!C10", PCT, "Funnel_Analysis"), ("Biggest funnel leak: KYC share of all losses", "=Funnel_Analysis!F7", PCT, "Funnel_Analysis"),
      ("M1 retention", f"={RET['m1']}", PCT2, "Retention_Analysis"), ("M3 retention", f"={RET['m3']}", PCT2, "Retention_Analysis"), ("M6 retention", f"={RET['m6']}", PCT2, "Retention_Analysis"),
      ("MAU, latest month (Oct-2026)", f"={RET['mau_last']}", INT, "Retention_Analysis"), ("Dormant 3 months (proxy)", f"={RET['dorm']}", PCT2, "Retention_Analysis"),
      ("Repeat traders, % of ever-traders", f"={RET['rep']}", PCT2, "Retention_Analysis"), ("Blended paid CAC (INR)", "=Campaign_Analysis!O17", DEC1, "Campaign_Analysis"),
      ("Support tickets", f"={SUP['tickets']}", INT, "Support_Analysis"), ("Median resolution time (h)", f"={SUP['median']}", DEC1, "Support_Analysis"),
      ("Unresolved tickets", "=Support_Analysis!B12", INT, "Support_Analysis"), ("CSAT, mean", f"={SUP['csat']}", DEC2, "Support_Analysis"),
      ("Phase 3 verification: KPIs matching", '=Phase3_Check!H3', None, "Phase3_Check")]
for i, (k, f, fm, src) in enumerate(HL):
    r = 28 + i; put(ws, f"A{r}", k, f_b); put(ws, f"B{r}", f, f_lnk, fm, fill=fill_g, border=box); put(ws, f"D{r}", src, f_sub)
widths(ws, {"A": 44, "B": 18, "C": 16, "D": 70})
fk = BarChart(); fk.type = "bar"; fk.title = "Funnel (mature cohort)"; fk.style = 10; fk.legend = None
fk.add_data(Reference(WS["Funnel_Analysis"], min_col=2, min_row=5, max_row=11), titles_from_data=True); fk.set_categories(Reference(WS["Funnel_Analysis"], min_col=1, min_row=6, max_row=11))
fk.x_axis.scaling.orientation = "maxMin"; fk.x_axis.delete = False; fk.y_axis.delete = False; fk.height, fk.width = 7.5, 13; fk.series[0].graphicalProperties.solidFill = "2E75B6"; ws.add_chart(fk, "F4")
rk = LineChart(); rk.title = "Pooled retention curve"; rk.style = 12; rk.legend = None
rk.add_data(Reference(WS["Retention_Analysis"], min_col=3, max_col=9, min_row=18), from_rows=True, titles_from_data=False); rk.set_categories(Reference(WS["Retention_Analysis"], min_col=3, max_col=9, min_row=5))
rk.y_axis.number_format = "0%"; rk.y_axis.scaling.min = 0; rk.y_axis.scaling.max = 0.9; rk.x_axis.delete = False; rk.y_axis.delete = False; rk.height, rk.width = 7.5, 13
rk.series[0].graphicalProperties.line.solidFill = "ED7D31"; rk.series[0].graphicalProperties.line.width = 28000; ws.add_chart(rk, "F20")

# ----------------------------------------------------------------------------------------------- Phase3_Check
ws = WS["Phase3_Check"]; title(ws, "Phase3_Check - live Excel results vs validated Phase 3 results", "Excel value = live formula pulling from this workbook (green). Phase 3 value = input from 03_business_analytics/summary/results.json/tables (blue). Status = MATCH when |difference| <= tolerance.")
put(ws, "G3", "KPIs matching:", f_b)
header(ws, 5, ["Check", "Excel value (live)", "Phase 3 value", "Difference", "Tolerance", "Status", "Phase 3 source"], height=30)
CK = []
f = R3["funnel"]
for s_, k_ in zip(STG[:5], ["Registered", "KYC Completed", "Bank Linked", "First Deposit", "First Trade"]):
    CK.append((f"Funnel users reached: {s_}", f"={FUN['reached'][s_]}", f[k_]["reached"], 0, INT, "results.json funnel"))
for s_, k_ in zip(STG[1:5], ["KYC Completed", "Bank Linked", "First Deposit", "First Trade"]):
    CK.append((f"Step conversion: {s_}", f"={FUN['conv'][s_]}", f[k_]["conv_prev"], 0.0006, PCT2, "results.json funnel (4 dp)"))
CK += [("Total registrations", "=COUNTA(tblUsers[user_id])", R3["n_users"], 0, INT, "results.json n_users"), ("Mature users", "=COUNTIFS(tblUsers[funnel_mature],1)", R3["n_mature"], 0, INT, "results.json n_mature"),
       ("M1 retention", f"={RET['m1']}", R3["m1"], 0.00005, PCT2, "results.json m1"), ("M3 retention", f"={RET['m3']}", R3["m3"], 0.00005, PCT2, "results.json m3"), ("M6 retention", f"={RET['m6']}", R3["m6"], 0.00005, PCT2, "results.json m6"),
       ("MAU latest month (Oct-2026)", f"={RET['mau_last']}", R3["mau_last"], 0, INT, "results.json mau_last"), ("MAU first month (Nov-2025)", f"={RET['mau_first']}", R3["mau_first"], 0, INT, "results.json mau_first"),
       ("Active in last 30 days", f"={RET['a30']}", R3["active30"], 0.00005, PCT2, "results.json active30"), ("Inactive > 90 days (proxy)", f"={RET['i90']}", R3["inactive90"], 0.00005, PCT2, "results.json inactive90"),
       ("Dormant 3 months (proxy)", f"={RET['dorm']}", R3["dormant3m"], 0.00005, PCT2, "results.json dormant3m"), ("Repeat-trading base users", f"={RET['repbase'].replace('$C$46','$C$46')}", R3["repeat_base_n"], 0, INT, "results.json repeat_base_n"),
       ("Repeat traders % of ever-traders", f"={RET['rep']}", R3["repeat_trader_share_of_traders"], 0.00005, PCT2, "results.json"),
       ("Tickets", f"={SUP['tickets']}", R3["tickets"], 0, INT, "results.json tickets"), ("Tickets per 1,000 users", f"={SUP['per1000']}", R3["tickets_per_1000_users"], 0.05, DEC1, "results.json"),
       ("Resolved share", f"={SUP['resolved']}", R3["resolved_pct"], 0.00005, PCT2, "results.json resolved_pct"), ("Open tickets", f"={SUP['open']}", R3["open_n"], 0, INT, "results.json open_n"),
       ("Escalated tickets", f"={SUP['esc']}", R3["escalated_n"], 0, INT, "results.json escalated_n"), ("Mean resolution (h)", f"={SUP['mean']}", R3["res_mean"], 0.001, DEC2, "results.json res_mean"),
       ("Median resolution (h)", f"={SUP['median']}", R3["res_median"], 0.05, DEC1, "results.json res_median"), ("CSAT mean", f"={SUP['csat']}", R3["csat_mean"], 0.0005, "0.000", "results.json csat_mean")]
chp = pd.read_csv(P3 / "m1_channel_performance.csv").set_index("acquisition_channel")
for i, chn in enumerate(CHS):
    r_ = 24 + i
    CK.append((f"Registrations: {chn}", f"=Campaign_Analysis!C{r_}", int(chp.loc[chn, "registered"]), 0, INT, "m1_channel_performance"))
    CK.append((f"First-trade rate (mature): {chn}", f"=Campaign_Analysis!G{r_}", float(chp.loc[chn, "first_trade_rate"]), 0.00005, PCT2, "m1_channel_performance"))
    CK.append((f"M3 retention: {chn}", f"=Campaign_Analysis!J{r_}", float(chp.loc[chn, "m3_retention"]), 0.00005, PCT2, "m1_channel_performance"))
cpf = pd.read_csv(P3 / "Campaign_Performance.csv").set_index("campaign_id")
for i, cid in enumerate(C0.campaign_id):
    r_ = 6 + i
    CK.append((f"First-trade rate (mature): {cid}", f"=Campaign_Analysis!N{r_}", float(cpf.loc[cid, "first_trade_rate_mature"]), 0.00005, PCT2, "Campaign_Performance"))
    if C0.is_paid.iloc[i] == 1:
        CK.append((f"CAC (INR): {cid}", f"=Campaign_Analysis!O{r_}", float(cpf.loc[cid, "cac_inr"]), 0.01, DEC2, "Campaign_Performance"))
        CK.append((f"Cost per first trader (INR): {cid}", f"=Campaign_Analysis!P{r_}", float(cpf.loc[cid, "cost_per_first_trade_at_maturity_inr"]), 0.5, DEC1, "Campaign_Performance"))
js = {d["journey_segment"]: d["users"] for d in R3["journey_segments"]}
for i, (sg, *_x) in enumerate(SEGS): CK.append((f"Journey segment users: {sg[:2]}", f"=Customer_Segmentation!C{6 + i}", js[sg], 0, INT, "results.json journey_segments"))
cat3 = pd.read_csv(P3 / "m6_ticket_categories.csv").set_index("category")
for i, c in enumerate(CATS):
    CK.append((f"Tickets: {c}", f"=Support_Analysis!B{23 + i}", int(cat3.loc[c, "tickets"]), 0, INT, "m6_ticket_categories"))
    CK.append((f"Median resolution h: {c}", f"=Support_Analysis!H{23 + i}", float(cat3.loc[c, "median_res_h"]), 0.05, DEC1, "m6_ticket_categories"))
mx = pd.read_csv(P3 / "m3_cohort_retention_matrix.csv").set_index("registration_month")
ck_ = ["2025-11", "2026-03", "2026-06"]
for cohort_ in ck_:
    rr_ = 6 + cohorts.index(int(cohort_.replace("-", "")))
    for k in (1, 3):
        v = mx.loc[cohort_, str(k)]
        if not np.isnan(v): CK.append((f"Cohort {cohort_} M{k}", f"=Retention_Analysis!{CL(3 + k)}{rr_}", float(v), 0.00006, PCT2, "m3_cohort_retention_matrix (4 dp)"))
for i, (lab, key) in enumerate([("Median days reg->KYC", 0), ("Median days KYC->bank", 1), ("Median days bank->deposit", 2), ("Median days deposit->trade", 3)]):
    st = ["KYC Completed", "Bank Linked", "First Deposit", "First Trade"][i]
    CK.append((lab, f"=Funnel_Analysis!D{TS_ROW + i}", float(f[st]["median_days"]), 0.05, DEC1, "results.json funnel median_days"))
    CK.append((lab.replace("Median", "P75"), f"=Funnel_Analysis!E{TS_ROW + i}", float(f[st]["p75_days"]), 0.05, DEC1, "results.json funnel p75_days"))
for i, (chk_, ex, tg, tol, fm, src) in enumerate(CK):
    r = 6 + i
    put(ws, f"A{r}", chk_); put(ws, f"B{r}", ex, f_lnk, fm); put(ws, f"C{r}", tg, f_in, fm); put(ws, f"D{r}", f"=B{r}-C{r}", f_n, "0.0000"); put(ws, f"E{r}", tol, f_in, "0.00000")
    put(ws, f"F{r}", f'=IF(ABS(D{r})<=E{r}+0.0000001,"MATCH","DIFF")', f_b, al=Alignment(horizontal="center")); put(ws, f"G{r}", src, f_sub)
last = 5 + len(CK)
put(ws, "H3", f'=COUNTIF(F6:F{last},"MATCH")&" / "&COUNTA(F6:F{last})', Font(name=FN, size=12, bold=True, color="008000"))
put(ws, "H4", f'=IF(COUNTIF(F6:F{last},"DIFF")=0,"All checks pass","Review DIFF rows")', f_b)
ws.conditional_formatting.add(f"F6:F{last}", CellIsRule(operator="equal", formula=['"MATCH"'], fill=PatternFill("solid", bgColor="C6EFCE")))
ws.conditional_formatting.add(f"F6:F{last}", CellIsRule(operator="equal", formula=['"DIFF"'], fill=PatternFill("solid", bgColor="F8CBAD")))
widths(ws, {"A": 46, "B": 18, "C": 16, "D": 14, "E": 12, "F": 10, "G": 36, "H": 22}); ws.freeze_panes = "A6"
N_CHECKS = len(CK)

# ----------------------------------------------------------------------------------------------- XLOOKUP_Demo (placeholders; finalised by 17_finalize_excel.py)
ws = WS["XLOOKUP_Demo"]; title(ws, "XLOOKUP_Demo - XLOOKUP beside the equivalent INDEX/MATCH", "Column D is the INDEX/MATCH formula used throughout this workbook (works in every Excel version). Column E is the same lookup written as XLOOKUP (Excel 2021 / Microsoft 365 only).")
put(ws, "A3", "Build note: the verification engine used to build this file (LibreOffice 24.2) cannot evaluate XLOOKUP, so the XLOOKUP cells in column E were added after recalculation with cached values equal to the INDEX/MATCH result in column D. Excel 365 recalculates them on open; older Excel and LibreOffice show a name error in those cells.", f_sub, al=wrap)
ws.merge_cells("A3:F3"); ws.row_dimensions[3].height = 44
header(ws, 5, ["#", "Lookup key (input)", "Question answered", "INDEX / MATCH (live)", "XLOOKUP (Excel 365)", "Equivalent XLOOKUP text"], height=30)
XD = [("CMP05", "Campaign name for a campaign id", "=INDEX(tblCampaigns[campaign_name],MATCH(B6,tblCampaigns[campaign_id],0))", '=XLOOKUP(B6,tblCampaigns[campaign_id],tblCampaigns[campaign_name],"not found")'),
      ("CMP02", "Recorded spend (INR) for a campaign id", "=INDEX(tblCampaigns[campaign_spend_inr],MATCH(B7,tblCampaigns[campaign_id],0))", '=XLOOKUP(B7,tblCampaigns[campaign_id],tblCampaigns[campaign_spend_inr],"not found")'),
      ("U100001", "Acquisition channel of a user", "=INDEX(tblUsers[acquisition_channel],MATCH(B8,tblUsers[user_id],0))", '=XLOOKUP(B8,tblUsers[user_id],tblUsers[acquisition_channel],"not found")'),
      ("Referral", "First-trade rate of a channel (Campaign_Analysis!A24:G30)", "=INDEX(Campaign_Analysis!$G$24:$G$30,MATCH(B9,Campaign_Analysis!$A$24:$A$30,0))", '=XLOOKUP(B9,Campaign_Analysis!$A$24:$A$30,Campaign_Analysis!$G$24:$G$30,"not found")'),
      ("CMP99", "Missing key - shows the fallback (if_not_found)", '=IFERROR(INDEX(tblCampaigns[campaign_name],MATCH(B10,tblCampaigns[campaign_id],0)),"not found")', '=XLOOKUP(B10,tblCampaigns[campaign_id],tblCampaigns[campaign_name],"not found")')]
for i, (key, q, im, xl) in enumerate(XD):
    r = 6 + i; put(ws, f"A{r}", i + 1); put(ws, f"B{r}", key, f_in, fill=fill_y); put(ws, f"C{r}", q, al=wrap); put(ws, f"D{r}", im, f_n, PCT2 if key == "Referral" else None)
    put(ws, f"E{r}", "xl", f_n, PCT2 if key == "Referral" else None); text_cell(ws, f"F{r}", xl, Font(name=FN, size=9, color="595959"))
widths(ws, {"A": 5, "B": 20, "C": 52, "D": 26, "E": 26, "F": 90})
XDEMO = dict(rows=list(range(6, 6 + len(XD))), formulas=[x[3] for x in XD])

# ----------------------------------------------------------------------------------------------- Raw_Data_Reference
ws = WS["Raw_Data_Reference"]; title(ws, "Raw_Data_Reference - data lineage, inventory and cleaning log", "How this workbook's data relate to the original (raw) file. The raw file is never modified: data/raw/Fintech_Users_10000_Synthetic.csv. All data are SYNTHETIC.")
section(ws, 4, "A. Lineage", 8)
LIN = ["1. RAW: data/raw/Fintech_Users_10000_Synthetic.csv (25 columns, 10,000 synthetic users) + the project workbook's campaign, monthly-activity and support sheets.",
       "2. CLEAN (Phase 2): 02_data_cleaning/01_phase2_clean_validate_transform.py -> data/cleaned/Cleaned_*.csv. 13 documented changes (table below); originals preserved; no row deleted.",
       "3. ANALYSE (Phase 3): validated findings in 03_business_analytics/ (summary/results.json and the module folders) - the targets used on the Phase3_Check sheet.",
       "4. THIS WORKBOOK (Phase 4): Cleaned_* data loaded as Excel Tables (tblUsers, tblActivity, tblTickets, tblCampaigns); every analysis cell is a live formula.",
       "Source-of-truth rule: Users table -> funnel / CAC / conversion; Monthly_Activity -> MAU / retention / repeat trading. The two disagree for many users, so mixed-source results are indicative only."]
for i, t in enumerate(LIN): put(ws, f"A{5 + i}", t, al=wrap); ws.merge_cells(f"A{5 + i}:H{5 + i}"); ws.row_dimensions[5 + i].height = 30
section(ws, 11, "B. Dataset inventory and reconciliation (live row counts vs expected)", 8)
header(ws, 12, ["Dataset", "Excel Table", "Sheet", "Source file", "Rows (live)", "Rows expected", "Status", "Grain"], height=30)
INV = [("Users", "tblUsers", "Cleaned_Users", "data/cleaned/Cleaned_Users.csv", "=ROWS(tblUsers[user_id])", 10000, "One row per registered user"),
       ("Monthly activity", "tblActivity", "Monthly_Activity_Data", "data/cleaned/Cleaned_Monthly_Activity.csv", "=ROWS(tblActivity[user_id])", 64645, "One row per user per calendar month since registration"),
       ("Support tickets", "tblTickets", "Support_Tickets_Data", "data/cleaned/Cleaned_Support_Tickets.csv", "=ROWS(tblTickets[ticket_id])", 7614, "One row per ticket"),
       ("Campaigns", "tblCampaigns", "Campaign_Analysis", "data/cleaned/Cleaned_Campaigns.csv", "=ROWS(tblCampaigns[campaign_id])", 10, "One row per acquisition campaign")]
for i, (d, t, s, src, f_, exp, g) in enumerate(INV):
    r = 13 + i; put(ws, f"A{r}", d); put(ws, f"B{r}", t); put(ws, f"C{r}", s); put(ws, f"D{r}", src); put(ws, f"E{r}", f_, fmt=INT); put(ws, f"F{r}", exp, f_in, INT)
    put(ws, f"G{r}", f'=IF(E{r}=F{r},"MATCH","DIFF")', f_b, al=Alignment(horizontal="center")); put(ws, f"H{r}", g)
put(ws, "A17", "Raw file rows (not loaded here; shown for reconciliation)"); put(ws, "F17", 10000, f_in, INT)
put(ws, "G17", '=IF(E13=F17,"MATCH","DIFF")', f_b, al=Alignment(horizontal="center"))
ws.conditional_formatting.add("G13:G17", CellIsRule(operator="equal", formula=['"MATCH"'], fill=PatternFill("solid", bgColor="C6EFCE")))
section(ws, 20, "C. Phase 2 cleaning log (from 02_data_cleaning/cleaning_log.csv)", 8)
LG = pd.read_csv(ROOT / "02_data_cleaning" / "cleaning_log.csv")
header(ws, 21, ["Change", "Table", "Column(s)", "Issue", "Action", "Records affected", "Rationale"], height=26)
for i, r_ in enumerate(LG.itertuples(index=False), start=22):
    for j, v in enumerate([r_.change_id, r_.table, r_.column, r_.issue, r_.action, int(r_.records_affected), r_.rationale], 1):
        put(ws, f"{CL(j)}{i}", v, al=wrap, border=box, fmt=INT if j == 6 else None)
    ws.row_dimensions[i].height = 62
r0 = 22 + len(LG) + 2; section(ws, r0, "D. Column dictionary for tblUsers (calculated columns show their formula logic)", 8)
header(ws, r0 + 1, ["Column", "Type", "Origin", "Description / logic"], height=24)
dd = pd.read_csv(ROOT / "data" / "data_dictionary.csv"); dd = dd[dd.table == "Cleaned_Users"].set_index("column")
CALC_DESC = {"reg_month_key": "YEAR*100+MONTH of registration_date (yyyymm integer cohort key)", "campaign_name": "INDEX/MATCH on tblCampaigns by acquisition_campaign_id",
             "reg_weekday": "CHOOSE(WEEKDAY(date,2),...) - weekday label", "days_since_registration": "Snapshot - registration_date", "tenure_months": "DATEDIF(registration_date, Snapshot, \"m\")",
             "last_stage_event_date": "MAX of registration/KYC/bank/deposit dates", "days_since_last_stage_event": "Snapshot - last_stage_event_date",
             "days_since_first_trade": "Snapshot - trade_date_asof for first traders, else blank", "journey_segment": "Nested IFS implementing the Phase 3 rule (lag limits on Assumptions)",
             "deposit_band": "Nested IF on first deposit vs DepBand1-3", "tenure_bucket": "IFS on days_since_registration", "idle_deposit_key": "Funded-never-traded: deposit + ROW()/1e7 (unique sort key for LARGE)"}
for i, c in enumerate(U_COLS):
    r = r0 + 2 + i; calc = c in U_CALC
    put(ws, f"A{r}", c, f_b if calc else f_n); put(ws, f"B{r}", "calculated" if calc else str(dd.loc[c, "dtype"]) if c in dd.index else "")
    put(ws, f"C{r}", "Excel formula" if calc else (str(dd.loc[c, "origin"]) if c in dd.index else "Source")); put(ws, f"D{r}", CALC_DESC[c] if calc else (str(dd.loc[c, "description"]) if c in dd.index else ""), al=wrap)
widths(ws, {"A": 40, "B": 16, "C": 26, "D": 46, "E": 44, "F": 14, "G": 52, "H": 52})

# ----------------------------------------------------------------------------------------------- Formula_Guide
ws = WS["Formula_Guide"]; title(ws, "Formula_Guide - the working formulas and how they work", "Each row documents a formula used in the workbook (stored as text). 'Where' says which sheet/cell holds the live version.")
header(ws, 4, ["Technique", "Where", "Formula (as used)", "How it works", "Business use"], height=26)
FG = [
 ("Excel Table + structured reference", "All sheets", "=SUMIFS(tblUsers[trade_asof],tblUsers[acquisition_channel],A24,tblUsers[funnel_mature],1)", "tblUsers[col] always means the whole column of the table, so ranges grow automatically when rows are added and formulas stay readable.", "Channel first-trader counts that never need range edits."),
 ("This-row reference in a calculated column", "Cleaned_Users", "=Snapshot-tblUsers[[#This Row],[registration_date]]", "[#This Row] picks the cell in the same row (Excel's UI shows it as [@registration_date]).", "Per-user tenure in days."),
 ("Named range", "Assumptions", "Snapshot, Lag_Reg, High_Min ... (see Assumptions col D)", "A name replaces a cell address, so thresholds live in one place and formulas read like sentences.", "Change a lag limit once and every segment updates."),
 ("INDEX-MATCH", "Cleaned_Users[campaign_name]", "=INDEX(tblCampaigns[campaign_name],MATCH(tblUsers[[#This Row],[acquisition_campaign_id]],tblCampaigns[campaign_id],0))", "MATCH(...,0) finds the row of an exact key; INDEX returns the value from that row of another column.", "Attach the campaign name to each user."),
 ("XLOOKUP", "XLOOKUP_Demo", '=XLOOKUP(B6,tblCampaigns[campaign_id],tblCampaigns[campaign_name],"not found")', "One function: lookup array, return array, fallback text. Excel 2021/365 only.", "Same lookup as INDEX-MATCH; shown side by side."),
 ("SUMIFS", "Campaign_Analysis", "=SUMIFS(tblUsers[trade_asof],tblUsers[acquisition_campaign_id],[@campaign_id],tblUsers[funnel_mature],1)", "Sums a 0/1 flag where all criteria are true, i.e. counts traders in the mature cohort.", "Mature first traders per campaign."),
 ("COUNTIFS", "Funnel_Analysis", '=COUNTIFS(tblUsers[registration_date],">="&A60,tblUsers[registration_date],"<"&EDATE(A60,1))', "Counts rows meeting every criterion; comparison operators are joined to a value with &.", "Registrations per calendar month."),
 ("AVERAGEIFS", "Retention_Analysis", "=AVERAGEIFS(tblActivity[active_in_month],tblActivity[registration_month_key],$A6,tblActivity[months_since_registration],C$5)", "Mean of a 0/1 flag = share active. Averages ignore blank cells.", "Cohort retention cell (cohort x offset)."),
 ("Wildcard 'All' selector", "KPI_Summary", '=IF(B5="All","*",B5)', "A criterion of * matches any text, so 'All' turns a filter off without changing the SUMIFS.", "Dynamic KPI panel."),
 ("IF / nested IF", "Cleaned_Users[deposit_band]", '=IF(deposit=0,"No deposit",IF(amt<=DepBand1,"Under Rs3k",IF(amt<=DepBand2,"Rs3-6.5k",...)))', "Tests in order; the first true branch wins.", "Deposit-size banding."),
 ("IFS (multi-branch)", "Cleaned_Users[journey_segment]", '=IFS(OR(AND(stage="Registered",lag<=Lag_Reg),...),"01 ...",stage="Registered","02 ...", ... ,TRUE,"10 ...")', "Evaluates condition/result pairs in order; TRUE at the end is the default. Order mirrors the Phase 3 Python rule.", "Operational customer segments."),
 ("AND / OR inside IF", "Cleaned_Users[journey_segment]", 'OR(AND(stage="KYC Completed",lag<=Lag_KYC), AND(stage="Bank Linked",lag<=Lag_Bank))', "Combines tests: any in-flight condition makes the user 'new / in-flight'.", "Separates in-flight from stalled onboarding."),
 ("Date arithmetic", "Cleaned_Users", "=Snapshot-tblUsers[[#This Row],[deposit_date_asof]]  |  =DATEDIF(reg_date,Snapshot,\"m\")", "Dates are serial numbers, so subtraction gives days; DATEDIF counts whole months.", "Tenure and idle-deposit ageing."),
 ("EDATE / WEEKDAY / CHOOSE", "Funnel_Analysis", '=EDATE(A59,1)  |  =CHOOSE(WEEKDAY(date,2),"Mon",...,"Sun")', "EDATE moves a date by whole months; WEEKDAY(...,2) numbers Mon=1; CHOOSE maps numbers to labels (locale independent).", "Calendar and weekday views."),
 ("Wilson 95% interval", "Funnel_Analysis", "=(p+z^2/(2n)-z*SQRT(p*(1-p)/n+z^2/(4n^2)))/(1+z^2/n)", "Confidence interval for a proportion that behaves well for rates near 0 or 1.", "Shows how precise each step conversion is."),
 ("Array MEDIAN(IF())", "Funnel_Analysis, Support_Analysis", '=MEDIAN(IF((tblUsers[funnel_mature]=1)*(tblUsers[days_reg_to_kyc]<>""),tblUsers[days_reg_to_kyc]))', "IF filters the column inside the array; MEDIAN then ignores the FALSE values. Entered as an array (CSE) formula.", "Median days / median resolution time."),
 ("RANK", "Campaign_Analysis", "=RANK([@first_trade_rate_mature],tblCampaigns[first_trade_rate_mature],0)", "Rank 1 = highest (order 0). Text such as 'n/a' is ignored.", "Campaign leaderboard."),
 ("LARGE + INDEX/MATCH", "Customer_Segmentation", "=LARGE(tblUsers[idle_deposit_key],A48)  then  =INDEX(tblUsers[user_id],MATCH(H48,tblUsers[idle_deposit_key],0))", "The helper key (deposit + ROW()/1e7) is unique, so LARGE gives the n-th biggest idle deposit and MATCH finds its row - a top-N list without dynamic arrays.", "High-potential activation list."),
 ("IFERROR", "Retention_Analysis", '=IFERROR(AVERAGEIFS(...),"")', "Returns blank when the cohort/offset has no rows yet (not yet observable).", "Keeps the retention triangle clean."),
 ("Conditional formatting", "Several", "Color scales, data bars, icon-free status fills", "Colour scale on retention/conversion; data bars on volumes; green/red fill on MATCH/DIFF.", "Reads patterns at a glance."),
 ("Data validation", "KPI_Summary", "List: All,Organic,Referral,...", "Dropdowns restrict the selectors to valid values.", "Prevents typos in the dynamic panel."),
 ("CAC and cost per first trader", "Campaign_Analysis", '=IF(is_paid=1,spend/registered,"n/a")  |  =cac/first_trade_rate_mature', "CAC uses all registered users; the second step divides by the mature first-trade rate to give cost per first trader. Organic spend is unrecorded so the result is n/a, not 0.", "Compare campaigns on cost per activated customer."),
]
for i, row in enumerate(FG):
    r = 5 + i
    for j, v in enumerate(row, 1):
        c = put(ws, f"{CL(j)}{r}", None, f_b if j == 1 else f_n, al=wrap, border=box)
        c.value = v; c.data_type = "s"
    ws.row_dimensions[r].height = 58
widths(ws, {"A": 30, "B": 26, "C": 70, "D": 66, "E": 36}); ws.freeze_panes = "A5"

# ----------------------------------------------------------------------------------------------- PivotTable_Guide
ws = WS["PivotTable_Guide"]; title(ws, "PivotTable_Guide - building PivotTables and PivotCharts from the Excel Tables", "The analysis sheets use formula-driven cross-tabs that update automatically. For interactive PivotTables, insert them from the four Excel Tables below (Insert > PivotTable > 'Table/Range' = table name).")
put(ws, "A3", "Real PivotTables are delivered in the companion file 03_business_analytics/excel/Fintech_PivotTables_Demo.xlsx (five PivotTables on the same cleaned data, built with LibreOffice because openpyxl cannot author PivotTable caches). PivotCharts are NOT embedded - insert them from those PivotTables (steps below). The recipes here reproduce numbers already verified in this workbook, so every PivotTable can be checked against a live formula. Note: the demo file was inspected in LibreOffice and by script; it has not been opened in desktop Excel.", f_sub, al=wrap)
ws.merge_cells("A3:H3"); ws.row_dimensions[3].height = 58
header(ws, 5, ["#", "PivotTable", "Source table", "Rows", "Columns", "Values", "Filters / slicers", "Check against (live formula)"], height=30)
PV = [("1 Funnel by channel", "tblUsers", "acquisition_channel", "-", "Sum of kyc_asof, bank_asof, deposit_asof, trade_asof", "funnel_mature = 1 (slicer)", "Funnel_Analysis section B counts"),
      ("2 Registrations by month x channel", "tblUsers", "reg_month_key", "acquisition_channel", "Count of user_id", "-", "Campaign_Analysis!C24:C30 totals"),
      ("3 Cohort retention", "tblActivity", "registration_month_key", "months_since_registration", "Average of active_in_month (format %)", "months_since_registration <= 6", "Retention_Analysis!C6:I17"),
      ("4 Journey segment x channel", "tblUsers", "journey_segment", "acquisition_channel", "Count of user_id", "-", "Customer_Segmentation!B21:H30"),
      ("5 Support category x priority", "tblTickets", "category", "priority", "Count of ticket_id; Average of csat_score", "status (slicer)", "Support_Analysis section B"),
      ("6 Monthly trading volume", "tblActivity", "activity_month_key", "-", "Sum of trading_value_inr; Sum of trade_count", "-", "Retention_Analysis!H24:I35")]
for i, row in enumerate(PV):
    r = 6 + i; put(ws, f"A{r}", i + 1)
    for j, v in enumerate(row, 2): put(ws, f"{CL(j)}{r}", v, al=wrap, border=box)
    ws.row_dimensions[r].height = 40
put(ws, "A14", "PivotCharts: select any cell in a PivotTable > Insert > PivotChart (clustered bar for 1, 4 and 5; line for 3 and 6). Add Slicers for Channel and Device: PivotTable Analyze > Insert Slicer.", al=wrap); ws.merge_cells("A14:H14"); ws.row_dimensions[14].height = 34
widths(ws, {"A": 5, "B": 34, "C": 16, "D": 26, "E": 26, "F": 40, "G": 28, "H": 40})

# ----------------------------------------------------------------------------------------------- README
ws = WS["README"]; title(ws, "Fintech Growth Analytics - Advanced Excel Workbook (Phase 4)", "Project data: SYNTHETIC. Fictional Indian retail brokerage - 10,000 users, Nov 2025 - Oct 2026, INR, snapshot 2026-10-31. Not real Groww / moomoo / Zerodha data.")
RM = [("What this is", "A formula-driven analytics workbook built on the Phase 2 cleaned tables. Every figure on the analysis sheets is a live formula and is reconciled to the validated Phase 3 results (see Phase3_Check)."),
      ("Sheets (required eight)", "Raw_Data_Reference | Cleaned_Users | Campaign_Analysis | Funnel_Analysis | Retention_Analysis | Customer_Segmentation | Support_Analysis | KPI_Summary"),
      ("Supporting sheets", "Phase3_Check (verification) | Assumptions (inputs, named ranges) | Formula_Guide | XLOOKUP_Demo | PivotTable_Guide | Monthly_Activity_Data and Support_Tickets_Data (Excel Tables used by formulas)"),
      ("Excel Tables", "tblUsers (Cleaned_Users) | tblActivity (Monthly_Activity_Data) | tblTickets (Support_Tickets_Data) | tblCampaigns (Campaign_Analysis)"),
      ("Colour code", "Blue text = input / hardcoded Phase 3 target | Black = formula | Green = cross-sheet link | Yellow fill = editable input | Orange header = calculated column"),
      ("How to use", "KPI_Summary: pick a channel, device and date window in the yellow cells. Assumptions: change a lag limit or threshold and the segments recompute. Phase3_Check: shows MATCH / DIFF for every reconciled KPI."),
      ("Definitions", "Mature cohort = registered before 2026-10 (n = 9,116). CAC = recorded spend / registered users (organic = n/a). Retention M1/M3/M6 = active k calendar months after the registration month (proxy). Dormant 3m, inactive 90d = churn proxies, not confirmed churn."),
      ("Source of truth", "Users table for funnel/CAC/conversion; Monthly_Activity for MAU/retention/repeat trading. The two sources conflict for many users, so mixed-source results are indicative only."),
      ("Limits (honest notes)", "1) No revenue, ROI or lifetime value is modelled - the data contain none. 2) PivotTables are in the companion file Fintech_PivotTables_Demo.xlsx; PivotCharts are not embedded (see PivotTable_Guide). 3) XLOOKUP cells exist only on XLOOKUP_Demo and need Excel 2021/365. 4) Group differences can be small and statistically insignificant; Phase 3 holds the tests."),
      ("Refreshing", "Paste new rows under any Excel Table (it expands); structured references pick them up. Update the Snapshot date on Assumptions.")]
for i, (k, v) in enumerate(RM):
    r = 4 + i; put(ws, f"A{r}", k, f_b, al=wrap, border=box); put(ws, f"B{r}", v, f_n, al=wrap, border=box); ws.row_dimensions[r].height = 48
widths(ws, {"A": 26, "B": 130})

# ----------------------------------------------------------------------------------------------- finish

from openpyxl.worksheet.properties import PageSetupProperties
for _n in ["README", "Raw_Data_Reference", "Campaign_Analysis", "Funnel_Analysis", "Retention_Analysis", "Customer_Segmentation", "Support_Analysis", "KPI_Summary",
           "Phase3_Check", "Assumptions", "Formula_Guide", "XLOOKUP_Demo", "PivotTable_Guide"]:
    _w = WS[_n]; _w.page_setup.orientation = "landscape"; _w.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    _w.page_setup.fitToWidth = 1; _w.page_setup.fitToHeight = 0
wb.calculation.fullCalcOnLoad = True
wb.save(OUT)
json.dump(dict(xdemo=XDEMO, n_checks=N_CHECKS, ts_row=TS_ROW), open(ROOT / "03_business_analytics" / "excel" / "_build_meta.json", "w"))
print("saved", OUT, f"| size {OUT.stat().st_size/1e6:.1f} MB | checks {N_CHECKS}")
