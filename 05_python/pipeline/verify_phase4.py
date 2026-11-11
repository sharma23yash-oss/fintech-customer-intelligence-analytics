"""Phase 4 verification: SQL database  vs  Python pipeline  vs  Excel workbook  vs  validated Phase 3 results (SYNTHETIC data).
Run after build_database.py, run_pipeline.py and build_excel_all.sh.   python3 verify_phase4.py   -> exit code 1 on any mismatch."""
import json, sqlite3, sys, warnings
from pathlib import Path
import pandas as pd, openpyxl
warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # 05_python/
from fintech_analytics import config as CFG
ROOT = CFG.ROOT
P3 = json.loads(CFG.p3_path("results.json").read_text())
PY = json.loads((CFG.OUT_DIR / "kpi_values.json").read_text())
XL = openpyxl.load_workbook(CFG.BA_DIR / "excel" / "Fintech_Advanced_Excel_Analytics.xlsx", data_only=True)
db = sqlite3.connect(CFG.DB_PATH)
q = lambda s: db.execute(s).fetchone()[0]
x = lambda sh, ref: XL[sh][ref].value
F = P3["funnel"]

# SQL medians by window function (no MEDIAN in SQLite)
def sql_median(col, where="1=1"):
    return q(f"""WITH r AS (SELECT {col} v, ROW_NUMBER() OVER (ORDER BY {col}) rn, COUNT(*) OVER () n FROM support_tickets WHERE {where} AND {col} IS NOT NULL)
                 SELECT AVG(v) FROM r WHERE rn IN ((n+1)/2, (n+2)/2)""")

M = "funnel_mature=1"
rows = []   # kpi, sql, python, excel, phase3, tolerance
def add(k, s, p, e, p3, tol=0.0): rows.append((k, s, p, e, p3, tol))

add("Total registrations", q("SELECT COUNT(*) FROM users"), PY["total_registrations"], x("KPI_Summary", "B28"), P3["n_users"])
add("Mature users", q(f"SELECT SUM(funnel_mature) FROM users"), PY["mature_users"], x("Funnel_Analysis", "B6"), P3["n_mature"])
for i, (lab, col, key, pk) in enumerate([("KYC completed", "kyc_asof", "funnel_kyc", "KYC Completed"), ("Bank linked", "bank_asof", "funnel_bank", "Bank Linked"),
                                         ("First deposit", "deposit_asof", "funnel_deposit", "First Deposit"), ("First trade", "trade_asof", "funnel_trade", "First Trade")]):
    add(f"Funnel reached: {lab}", q(f"SELECT SUM({col}) FROM users WHERE {M}"), PY[key], x("Funnel_Analysis", f"B{7 + i}"), F[pk]["reached"])
add("Funnel: Active (30d) first traders", q(f"SELECT COUNT(*) FROM users WHERE {M} AND trade_asof=1 AND active_30d_adj=1"), PY["funnel_active30"], x("Funnel_Analysis", "B11"), None)
prev = ["1", "kyc_asof", "bank_asof", "deposit_asof"]; cur = ["kyc_asof", "bank_asof", "deposit_asof", "trade_asof"]
for i, (lab, pk) in enumerate([("KYC completion", "KYC Completed"), ("Bank-link conversion", "Bank Linked"), ("First-deposit conversion", "First Deposit"), ("First-trade activation", "First Trade")]):
    den = f"SUM({prev[i]})" if prev[i] != "1" else "COUNT(*)"
    add(f"Step conversion: {lab}", q(f"SELECT 1.0*SUM({cur[i]})/{den} FROM users WHERE {M}"), PY[["conv_kyc_pct", "conv_bank_pct", "conv_deposit_pct", "conv_trade_pct"][i]] / 100, x("Funnel_Analysis", f"D{7 + i}"), F[pk]["conv_prev"], 6e-5)
add("Registered -> first trade (mature)", q(f"SELECT 1.0*SUM(trade_asof)/COUNT(*) FROM users WHERE {M}"), PY["reg_to_trade_pct"] / 100, x("Funnel_Analysis", "C10"), F["First Trade"]["conv_reg"], 6e-5)
for k, kk in ((1, "m1"), (3, "m3"), (6, "m6")):
    add(f"{kk.upper()} retention (pooled)", q(f"SELECT AVG(active_in_month) FROM monthly_activity WHERE months_since_registration={k}"), PY[f"{kk}_retention_pct"] / 100, x("Retention_Analysis", f"B{39 + k if k == 1 else (41 if k == 3 else 42)}"), P3[kk], 1e-9)
add("MAU, Oct-2026", q("SELECT SUM(active_in_month) FROM monthly_activity WHERE activity_month='2026-10'"), PY["mau_latest"], x("Retention_Analysis", "B35"), P3["mau_last"])
add("MAU, Nov-2025", q("SELECT SUM(active_in_month) FROM monthly_activity WHERE activity_month='2025-11'"), PY["mau_first"], x("Retention_Analysis", "B24"), P3["mau_first"])
add("Active in last 30 days", q("SELECT AVG(active_30d_adj) FROM users WHERE eligible_30d=1"), PY["active_30d_pct"] / 100, x("Retention_Analysis", "B43"), P3["active30"], 1e-9)
add("Inactive > 90 days (proxy)", q("SELECT AVG(inactive_90d_adj) FROM users WHERE eligible_90d=1"), PY["inactive_90d_proxy_pct"] / 100, x("Retention_Analysis", "B44"), P3["inactive90"], 1e-9)
add("Dormant 3 months (proxy)", q("SELECT AVG(dormant_3m_monthly) FROM users"), PY["dormant_3m_pct"] / 100, x("Retention_Analysis", "B45"), P3["dormant3m"], 1e-9)
add("Repeat-trading base users", q("SELECT COUNT(*) FROM users WHERE months_observed>=4"), PY["repeat_base_users"], x("Retention_Analysis", "C46"), P3["repeat_base_n"])
add("Repeat traders % of ever-traders", q("SELECT 1.0*SUM(trade_months>=2)/SUM(trade_months>=1) FROM users WHERE months_observed>=4"), PY["repeat_pct_of_traders"] / 100, x("Retention_Analysis", "B47"), P3["repeat_trader_share_of_traders"], 1e-9)
add("Tickets", q("SELECT COUNT(*) FROM support_tickets"), PY["tickets"], x("Support_Analysis", "B6"), P3["tickets"])
add("Tickets per 1,000 users", q("SELECT 1000.0*(SELECT COUNT(*) FROM support_tickets)/(SELECT COUNT(*) FROM users)"), PY["tickets_per_1000_users"], x("Support_Analysis", "B7"), P3["tickets_per_1000_users"], 0.05)
add("Resolved share", q("SELECT AVG(is_resolved) FROM support_tickets"), PY["resolved_pct"] / 100, x("Support_Analysis", "B9"), P3["resolved_pct"], 6e-5)
add("Open tickets", q("SELECT COUNT(*) FROM support_tickets WHERE status='Open'"), PY["open_tickets"], x("Support_Analysis", "B10"), P3["open_n"])
add("Escalated tickets", q("SELECT COUNT(*) FROM support_tickets WHERE status='Escalated'"), PY["escalated_tickets"], x("Support_Analysis", "B11"), P3["escalated_n"])
add("Mean resolution (h)", q("SELECT AVG(resolution_time_hours) FROM support_tickets"), PY["mean_resolution_h"], x("Support_Analysis", "B13"), P3["res_mean"], 1e-3)
add("Median resolution (h)", sql_median("resolution_time_hours"), PY["median_resolution_h"], x("Support_Analysis", "B14"), P3["res_median"], 0.05)
add("CSAT mean", q("SELECT AVG(csat_score) FROM support_tickets"), PY["csat_mean"], x("Support_Analysis", "B16"), P3["csat_mean"], 5e-4)
add("Unresolved tickets (open + escalated)", q("SELECT SUM(is_unresolved) FROM support_tickets"), PY["open_tickets"] + PY["escalated_tickets"], x("Support_Analysis", "B12"), P3["open_n"] + P3["escalated_n"])
add("Backlog ageing total (Excel table) = unresolved", q("SELECT COUNT(*) FROM support_tickets WHERE is_unresolved=1"), PY["open_tickets"] + PY["escalated_tickets"], x("Support_Analysis", "E39"), P3["open_n"] + P3["escalated_n"])
cmp = pd.read_csv(CFG.p3_path("m1_channel_performance.csv")).set_index("acquisition_channel")
for chn in cmp.index:
    add(f"Registrations: {chn}", q(f"SELECT COUNT(*) FROM users WHERE acquisition_channel='{chn}'"), PY[f"registrations_{chn}"], None, int(cmp.loc[chn, "registered"]))
for chn, r_ in zip(["Organic", "Referral", "CRM", "Paid Search", "Paid Social", "Affiliate", "Partnerships"], range(24, 31)):
    add(f"First-trade rate (mature): {chn}", q(f"SELECT 1.0*SUM(trade_asof)/COUNT(*) FROM users WHERE {M} AND acquisition_channel='{chn}'"), None, x("Campaign_Analysis", f"G{r_}"), float(cmp.loc[chn, "first_trade_rate"]), 6e-5)
    add(f"M3 retention: {chn}", q(f"SELECT AVG(m3_retained) FROM users WHERE acquisition_channel='{chn}'"), None, x("Campaign_Analysis", f"J{r_}"), float(cmp.loc[chn, "m3_retention"]), 6e-5)
cpf = pd.read_csv(CFG.p3_path("Campaign_Performance.csv")).set_index("campaign_id")
camp = pd.read_csv(CFG.DATA_CLEAN / "Cleaned_Campaigns.csv")
for i, r in enumerate(camp.itertuples(), start=6):
    if r.is_paid:
        s_cac = q(f"SELECT c.campaign_spend_inr*1.0/(SELECT COUNT(*) FROM users u WHERE u.acquisition_campaign_id=c.campaign_id) FROM campaigns c WHERE campaign_id='{r.campaign_id}'")
        add(f"CAC (INR): {r.campaign_id}", s_cac, None, x("Campaign_Analysis", f"O{i}"), float(cpf.loc[r.campaign_id, "cac_inr"]), 0.01)
js = {d["journey_segment"]: d["users"] for d in P3["journey_segments"]}
seg = {r[0]: r[1] for r in db.execute("SELECT journey_segment, COUNT(*) FROM v_journey_segment GROUP BY 1")}
for i, (name, n) in enumerate(js.items()):
    add(f"Journey segment: {name[:34]}", seg.get(name), None, x("Customer_Segmentation", f"C{6 + i}") if name[:2] == f"{i + 1:02d}" else None, n)

res = []
for k, s, p, e, p3, tol in rows:
    vals = {"sql": s, "python": p, "excel": e}
    present = {n: v for n, v in vals.items() if v is not None}
    ref = p3 if p3 is not None else present.get("sql")
    diffs = {n: abs(float(v) - float(ref)) for n, v in present.items()}
    ok = all(d <= tol + 1e-12 for d in diffs.values())
    res.append(dict(kpi=k, sql=s, python=p, excel=e, phase3=p3, tolerance=tol, max_abs_diff=max(diffs.values()), sources_compared=len(present) + (p3 is not None), status="MATCH" if ok else "DIFF"))
df = pd.DataFrame(res)
out = ROOT / "documentation" / "verification"; out.mkdir(parents=True, exist_ok=True)
df.to_csv(out / "Phase4_Verification.csv", index=False)
n_ok = int((df.status == "MATCH").sum()); n = len(df)
p3chk = XL["Phase3_Check"]["H3"].value
runlog = json.loads((ROOT / "04_sql/query_run_log.json").read_text()) if (ROOT / "04_sql/query_run_log.json").exists() else None
md = ["# Phase 4 verification report (SYNTHETIC data)", "",
      "Three independent implementations of the same KPIs - SQL (SQLite), Python (pandas) and Excel (live formulas, LibreOffice-recalculated) - are compared with each other and with the validated Phase 3 results.", "",
      f"**Result: {n_ok} / {n} KPI comparisons match** (tolerances shown; integers must match exactly).",
      f"Excel's own Phase3_Check sheet reports **{p3chk}** reconciled cells.", ""]
if runlog: md.append(f"SQL query library: {len(runlog) if isinstance(runlog, list) else runlog.get('queries', '?')} queries executed - see `04_sql/query_run_log.json`.\n")
md += ["| KPI | SQL | Python | Excel | Phase 3 | Max abs diff | Tol. | Status |", "|---|---:|---:|---:|---:|---:|---:|:--:|"]
f = lambda v: "-" if v is None or (isinstance(v, float) and pd.isna(v)) else (f"{v:,.0f}" if float(v).is_integer() and abs(v) > 1.5 else f"{v:,.4f}")
for r in res: md.append(f"| {r['kpi']} | {f(r['sql'])} | {f(r['python'])} | {f(r['excel'])} | {f(r['phase3'])} | {r['max_abs_diff']:.6f} | {r['tolerance']:g} | {r['status']} |")
md += ["", "Notes", "- Phase 3 stored some step conversions and rates rounded to 4 decimals, hence tolerances of 6e-5.",
       "- '-' means that implementation does not report that figure (e.g. Python pipeline has no per-channel M3 in kpi_values; the full Python tables are in `05_python/outputs/tables`).",
       "- Funnel 'Active (30d)' has no stored Phase 3 reference in results.json; SQL/Python/Excel are compared with each other (loss shares are verified in Phase 3's Funnel_Analysis.csv by the SQL Q09/Q30 outputs)."]
(out / "Phase4_Verification_Report.md").write_text("\n".join(md))
print(f"{n_ok}/{n} match; Excel Phase3_Check: {p3chk}")
print(df[df.status != "MATCH"].to_string() if n_ok != n else "all match")
sys.exit(0 if n_ok == n else 1)
