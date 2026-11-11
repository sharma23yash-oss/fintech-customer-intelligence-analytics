"""Builds and EXECUTES the five Phase 4 Jupyter notebooks (SYNTHETIC DATA). Run: python3 build_notebooks.py"""
import sys
from pathlib import Path
import nbformat as nbf
from nbconvert.preprocessors import ExecutePreprocessor

HERE = Path(__file__).resolve().parent
NB = HERE.parent / "notebooks"; NB.mkdir(exist_ok=True)   # 05_python/notebooks
md = nbf.v4.new_markdown_cell; code = nbf.v4.new_code_cell
SETUP = ("import sys, warnings; sys.path.insert(0, '..'); warnings.filterwarnings('ignore')\n"
         "import pandas as pd, numpy as np, matplotlib.pyplot as plt\n"
         "from fintech_analytics import config as C, loading, cleaning, eda, funnel, campaign, cohort, segmentation, support, kpi_report\n"
         "%matplotlib inline\npd.set_option('display.width', 160); pd.set_option('display.max_columns', 30)\n"
         "d = loading.load_all(); users, act, tix, camp = d['users'], d['activity'], d['tickets'], d['campaigns']\n"
         "print(f'users={len(users):,}  monthly rows={len(act):,}  tickets={len(tix):,}  campaigns={len(camp)}  (ALL DATA SYNTHETIC)')")
BANNER = "> **All data in this notebook are synthetic** (fictional Indian retail brokerage, 10,000 users, Nov 2025 - Oct 2026, INR, snapshot 2026-10-31). No real company data are used.\n\n"

books = {}
books["01_data_loading_cleaning_eda"] = [
    md("# 01 · Data loading, validation and exploratory analysis\n\n" + BANNER +
       "**Purpose:** load the Phase 2 cleaned tables, re-run integrity checks, and explore the data before any business metric is computed.\n\n"
       "**Source-of-truth rule:** the *Users* table drives funnel / CAC / conversion; *Monthly_Activity* drives MAU / retention / repeat trading. They disagree for many users (shown below), so mixed-source results are indicative only."),
    code(SETUP),
    md("## 1 · Integrity checks on the cleaned tables\nEvery run re-validates keys, foreign keys, date bounds, nested funnel flags and value ranges. The raw file is never modified."),
    code("chk = cleaning.validate_cleaned(d)\nprint(f'{int(chk.passed.sum())}/{len(chk)} checks passed')\nchk"),
    md("## 2 · Column profile (missing values, ranges)\nMissing values in date/duration columns are *structural* (a user who never reached a stage has no stage date) - they are not data errors."),
    code("prof = pd.concat([eda.profile(users,'users'), eda.profile(act,'monthly_activity'), eda.profile(tix,'support_tickets'), eda.profile(camp,'campaigns')])\nprof[prof.missing_pct>0].sort_values('missing_pct', ascending=False).head(15)"),
    code("eda.plot_missingness(users); plt.tight_layout(); plt.show()"),
    md("## 3 · Acquisition shape"),
    code("fig, ax = plt.subplots(1, 2, figsize=(12, 3.4)); eda.plot_registrations(users, ax[0]); eda.plot_channel_mix(users, ax[1]); plt.tight_layout(); plt.show()\neda.channel_mix(users)"),
    md("Registrations are fairly flat across months (no strong seasonality), and Paid Search + Paid Social bring about half of all users; Organic is ~19%."),
    code("eda.plot_deposit_hist(users); plt.tight_layout(); plt.show()\nusers.first_deposit_amount_asof_inr.describe().round(0)"),
    md("## 4 · Known data property: the two sources disagree\nThe table below crosses *'ever traded' per the Users table* with *'ever traded' per Monthly_Activity*. The large off-diagonal is a documented property of the synthetic data (Phase 2 flags `flag_*_conflict`). That is why each metric family is tied to one source."),
    code("cleaning.source_conflict_summary(users, act)"),
]
books["02_funnel_and_campaign_analytics"] = [
    md("# 02 · Funnel and campaign analytics\n\n" + BANNER + "All conversion metrics use the **mature cohort** (registered before 2026-10, n = 9,116) so every user had at least 31 days to progress."),
    code(SETUP),
    md("## 1 · Onboarding funnel"),
    code("ft = funnel.funnel_table(users); ft"),
    code("funnel.plot_funnel(users); plt.tight_layout(); plt.show()"),
    md("**Reading it:** KYC is the largest leak in absolute terms (about 43% of all lost users), First Deposit is second. Step conversions and Wilson 95% intervals are in the table."),
    md("## 2 · Funnel by channel and device"),
    code("funnel.funnel_by(users, 'acquisition_channel')"),
    code("funnel.funnel_by(users, 'device_type')"),
    md("## 3 · Time between stages (days, users who reached the stage)"),
    code("funnel.time_to_stage(users)"),
    md("## 4 · Campaign scorecard\n**CAC** = recorded spend / registered users. **Cost per first trader** = CAC / mature first-trade rate. Organic campaigns have no recorded spend, so CAC is undefined (NaN), not zero. No revenue or ROI is computed anywhere in this project."),
    code("sc = campaign.campaign_scorecard(users, camp)\nsc[['campaign_id','campaign_name','channel','campaign_spend_inr','registered_users','cac_inr','first_trade_rate_mature_pct','cost_per_first_trader_inr','m3_retention_pct','rank_first_trade']]"),
    code("campaign.plot_cost_vs_quality(sc); plt.tight_layout(); plt.show()"),
    md("Cheap registrations are not the same as cheap traders: Education Social has a moderate CAC but the lowest activation, so its cost per first trader is among the highest. Treat small gaps with caution - Phase 3 tested them statistically."),
    code("campaign.channel_scorecard(users)"),
]
books["03_cohort_retention_and_segmentation"] = [
    md("# 03 · Cohort retention, MAU, repeat trading and segmentation\n\n" + BANNER +
       "Retention uses **calendar-month proxies** (M1 = active in the month after the registration month), not exact 30/90/180-day retention. 'Dormant 3m' and 'inactive 90d' are churn **proxies**."),
    code(SETUP),
    md("## 1 · Cohort retention matrix"),
    code("mat = cohort.retention_matrix(act); mat"),
    code("fig, ax = plt.subplots(1, 2, figsize=(13, 4)); cohort.plot_retention_heatmap(mat, ax[0]); cohort.plot_retention_curve(act, ax[1]); plt.tight_layout(); plt.show()\ncohort.retention_summary(act)"),
    md("## 2 · MAU"),
    code("mau = cohort.mau_table(users, act); mau"),
    md("## 3 · Repeat trading and dormancy"),
    code("print(cohort.repeat_trading(users)); print(cohort.dormancy_rate(users))"),
    md("## 4 · Rule-based journey segments (Phase 3 rule)"),
    code("segmentation.journey_summary(users)"),
    md("## 5 · K-means behavioural clusters (scikit-learn)\nFeatures are standardised; the number of clusters follows a rule fixed *before* looking at results (k >= 3 with bootstrap stability ARI >= 0.85, then best silhouette). Cluster labels are descriptive, not causal."),
    code("km_u, sel, prof, K = segmentation.kmeans_segments(users)\nprint('chosen k =', K, '| users clustered =', len(km_u))\nsel"),
    code("prof"),
    code("fig, ax = plt.subplots(figsize=(6, 3.4)); ax.plot(sel.k, sel.silhouette, marker='o', color='#2563EB', label='silhouette'); ax.set_xlabel('k'); ax.set_ylabel('silhouette'); ax2 = ax.twiny(); ax.set_title('K selection (silhouette)'); ax2.set_visible(False)\nax.axvline(K, color='#D97706', ls='--'); ax.legend(); plt.tight_layout(); plt.show()"),
]
books["04_support_operations_analytics"] = [
    md("# 04 · Support operations analytics\n\n" + BANNER + "Resolution time and CSAT exist only for **resolved** tickets. Unresolved = Open + Escalated."),
    code(SETUP),
    code("pd.Series(support.ticket_kpis(tix, len(users))).round(2).to_frame('value')"),
    md("## Categories"),
    code("support.plot_category(tix); plt.tight_layout(); plt.show()\nsupport.category_table(tix)"),
    md("## Backlog ageing (unresolved tickets)"),
    code("support.backlog_table(tix)"),
    md("## Monthly trend"),
    code("support.monthly_ticket_trend(tix)"),
    md("## Repeat contactors (3+ tickets)"),
    code("rc = support.repeat_contactors(tix); print(len(rc), 'users with 3+ tickets'); rc.groupby('tickets').agg(users=('user_id','size'), avg_csat=('avg_csat','mean')).round(2)"),
    md("## Support exposure vs dormancy (descriptive only)\nThis does not adjust for cohort age or channel mix. Phase 3 used a cohort-adjusted test for the formal claim; here it is only a screening view."),
    code("x = users[users.dormant_3m_monthly.notna()].assign(support_status=lambda d: np.select([d.ticket_count==0, d.unresolved_ticket_count>0], ['0 tickets','Has unresolved ticket'], 'Tickets all resolved'))\nx.groupby('support_status').agg(users=('user_id','size'), dormant_3m_pct=('dormant_3m_monthly', lambda s: 100*s.mean())).round(1)"),
]
books["05_automated_kpi_report"] = [
    md("# 05 · Automated KPI report and cross-checks\n\n" + BANNER +
       "Computes every headline KPI, compares it with the validated Phase 3 results, and reconciles Python against the SQLite database."),
    code(SETUP),
    code("k, cmp_, text = kpi_report.build_report(d)\nprint(f\"{(cmp_.status=='MATCH').sum()}/{len(cmp_)} KPIs match Phase 3 within tolerance\")\ncmp_"),
    md("## Python vs SQL reconciliation\nThe same KPIs recomputed with SQL on `fintech_analytics.db` (build it first with `04_sql/build_database.py`)."),
    code("import sqlite3\ncon = sqlite3.connect(C.DB_PATH)\nsql_funnel = pd.read_sql_query('''SELECT COUNT(*) reg, SUM(kyc_asof) kyc, SUM(bank_asof) bank, SUM(deposit_asof) dep, SUM(trade_asof) trd FROM users WHERE funnel_mature=1''', con).iloc[0].tolist()\npy_funnel = [k['funnel_registered'], k['funnel_kyc'], k['funnel_bank'], k['funnel_deposit'], k['funnel_trade']]\nsql_m3 = pd.read_sql_query('SELECT 100*AVG(active_in_month) v FROM monthly_activity WHERE months_since_registration=3', con).v[0]\nprint('funnel  SQL:', sql_funnel, '\\nfunnel  PY :', py_funnel, '\\nidentical:', sql_funnel == py_funnel)\nprint(f\"M3 retention  SQL {sql_m3:.2f}%  PY {k['m3_retention_pct']:.2f}%  identical: {abs(sql_m3-k['m3_retention_pct'])<1e-9}\")"),
    md("## Report text (also saved to `05_python/outputs/KPI_Report.md`)"),
    code("from IPython.display import Markdown\nMarkdown(text.split('## Verification detail')[0])"),
]

ok = True
for name, cells in books.items():
    nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}})
    try:
        ExecutePreprocessor(timeout=600, kernel_name="python3").preprocess(nb, {"metadata": {"path": str(NB)}})
        status = "executed"
    except Exception as e:  # keep going so every failure is reported
        status = f"FAILED: {str(e)[:300]}"; ok = False
    nbf.write(nb, NB / f"{name}.ipynb")
    n_err = sum(1 for c in nb.cells if c.cell_type == "code" for o in c.get("outputs", []) if o.output_type == "error")
    print(f"{name}.ipynb  {status}  cells={len(nb.cells)} errors={n_err}")
sys.exit(0 if ok else 1)
