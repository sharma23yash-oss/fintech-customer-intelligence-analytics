"""
Phase 3 - assembles the management-report content (12 sections) as JSON for the docx renderer (14_build_report_docx.js)
and the executive-summary PDF builder (15_build_exec_summary_pdf.py). All numbers are pulled from the Phase 3 tables.
Output: reports/_build/report_content.json (git-ignored intermediate)
All data are synthetic.
"""
import json
from pathlib import Path
import pandas as pd

import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "05_python")); from fintech_analytics import config as CFG
BUILD = ROOT / "reports" / "_build"; BUILD.mkdir(parents=True, exist_ok=True)   # git-ignored intermediate (holds absolute image paths)
T, CH = CFG.P3_TABLES, CFG.CHARTS_DIR
R = json.load(open(T / "results.json"))
rd = lambda n: pd.read_csv(T / f"{n}.csv", keep_default_na=not n.startswith("m8_"))
pct = lambda x, d=1: f"{x*100:.{d}f}%"
inr = lambda x: f"Rs {x:,.0f}"

F = R["funnel"]; bn = {b["stage"]: b for b in R["bottlenecks"]}
ch = rd("m1_channel_performance"); cp = rd("Campaign_Performance").set_index("campaign_id")
fin = rd("m8_findings"); rec = rd("m8_prioritisation"); ex = rd("m7_experiments")
cat = rd("m6_ticket_categories"); js = rd("m4_journey_segment_profile")
B = []
add = lambda **k: B.append(k)
H1 = lambda t: add(type="h1", text=t)
H2 = lambda t: add(type="h2", text=t)
P = lambda t: add(type="p", text=t)
BL = lambda items: add(type="bullets", items=items)
NOTE = lambda t: add(type="note", text=t)
IMG = lambda f, cap, w=6.3: add(type="img", file=str(CH / ("phase3_" + f)), caption=cap, width=w)


def TAB(header, rows, widths, caption=None, align=None):
    add(type="table", header=header, rows=rows, widths=widths, caption=caption, align=align or [])


SYN = "All data in this report are synthetic (a fictional Indian retail-brokerage dataset of 10,000 users, Nov 2025 - Oct 2026, INR). Nothing here describes real customers, a real company, or real market performance."

# ---------------------------------------------------------------- 1 Executive summary
H1("1. Executive summary")
NOTE(SYN + " This is a portfolio project, not professional brokerage work. No revenue, profit or ROI is calculated because the dataset has no revenue data.")
P("The analysis follows 10,000 synthetic customers from registration to first trade and later activity. Mature cohorts (registered before Oct 2026, n=9,116) are used for conversion and retention so recent registrants are not penalised for not having had time to convert.")
TAB(["KPI (mature cohorts)", "Value", "Label"], [
    ["Registered -> KYC completed", pct(F["KYC Completed"]["conv_reg"]), "ACTUAL"],
    ["Registered -> first trade", pct(F["First Trade"]["conv_reg"]), "ACTUAL"],
    ["Registered -> 30-day active", pct(F["Active (30d)"]["conv_reg"]), "ACTUAL"],
    ["Median days registration -> first trade", f"{R['median_days_reg_to_trade']:.0f} days", "ACTUAL"],
    ["M1 / M3 / M6 retention", f"{pct(R['m1'])} / {pct(R['m3'])} / {pct(R['m6'])}", "ACTUAL"],
    ["Paid CAC (blended, recorded spend)", inr(2690000 / 8122), "ACTUAL"],
    ["Tickets per 1,000 users; median resolution; CSAT", f"{R['tickets_per_1000_users']:.0f}; {R['res_median']:.1f}h; {R['csat_mean']:.2f}", "ACTUAL"],
], [3.4, 2.0, 1.1], caption="Table 1. Headline KPIs", align=["l", "r", "l"])
H2("The five most important findings")
top5 = [
    f"KYC is the largest leak. Only {pct(F['KYC Completed']['conv_prev'])} of registrants complete KYC; {bn['KYC Completed']['users_lost']:,} users are lost there ({pct(bn['KYC Completed']['share_of_all_funnel_losses'])} of all stage losses).",
    f"Only {pct(F['First Trade']['conv_reg'])} of registrants place a first trade. Deposit ({pct(F['First Deposit']['conv_prev'])} of bank-linked users) and first trade ({pct(F['First Trade']['conv_prev'])} of depositors) leak a further {bn['First Deposit']['users_lost'] + bn['First Trade']['users_lost']:,} users.",
    f"Referral is the strongest channel: first-trade rate {pct(cp.loc['CMP05','first_trade_rate_mature'])} and cost per first trader {inr(cp.loc['CMP05','cost_per_first_trade_at_maturity_inr'])}, against {inr(cp.loc['CMP06','cost_per_first_trade_at_maturity_inr'])} for Finance Affiliate and {inr(cp.loc['CMP04','cost_per_first_trade_at_maturity_inr'])} for Video Awareness, the two weakest paid campaigns.",
    f"Retention decays steadily: {pct(R['m1'])} at M1, {pct(R['m3'])} at M3, {pct(R['m6'])} at M6. Referral and organic cohorts retain best (M3 {pct(R['retention_by_channel_m3']['Referral'])} and {pct(R['retention_by_channel_m3']['Organic'])}); partnerships worst ({pct(R['retention_by_channel_m3']['Partnerships'])}).",
    f"Support load is concentrated in onboarding: KYC, bank-link and deposit tickets are {pct(cat.share.iloc[[0,2,3]].sum())} of {R['tickets']:,} tickets; priority does not change resolution time and {R['backlog_over_90']:,} unresolved tickets are older than 90 days.",
]
BL(top5)
P("Recommended priorities: (1) fix KYC and the deposit/first-trade steps through guided flows and reminders; (2) scale referral in stages and put the two weakest campaigns on an improvement plan; (3) judge channels on cost per first trader and M3 retention, not CAC alone; (4) add priority-based service levels and clear the old ticket backlog. Ten experiments are proposed (not run) to test these ideas. Important caution: the funnel flags and the monthly activity log disagree for many users, so segment sizes are indicative (section 12).")

# ---------------------------------------------------------------- 2 Business context
H1("2. Business context")
P("A retail brokerage grows when new registrants complete onboarding (KYC, bank link, first deposit), place a first trade, and keep trading. Customer Operations touches each step through onboarding support, KYC and deposit processing, and trading support. The questions answered here are: where customers drop out, which channels bring customers who actually trade and stay, how efficient each campaign is, what the support data say about friction, and which experiments are worth running.")
P("The project is framed as an analytics exercise for a Retail Customer Operations role. It uses only the synthetic dataset and does not claim any employment, certification or real brokerage results.")

# ---------------------------------------------------------------- 3 Data & methodology
H1("3. Data and methodology")
BL([
    "Inputs: Phase 2 cleaned tables (users, monthly activity, support tickets, campaigns). Raw tables were used only for reconciliation and were never modified.",
    "Maturity: funnel and retention use cohorts registered before Oct 2026 (n=9,116). The Oct-2026 cohort (n=884) is excluded from conversion and retention rates. '30-day active' needs tenure of at least 31 days and 90-day proxies at least 91 days.",
    "Source of truth: the Users table for funnel, CAC and conversion; Monthly_Activity for MAU, retention, cohorts and repeat trading. The two sources contradict each other for a share of users (flagged in Phase 2), so mixed-source results are indicative.",
    "Inactivity is a proxy: flags such as 'dormant (no activity Aug-Oct 2026)' are not churn. True churn (account closure) cannot be observed, and users with short observation windows are never classed as churned.",
    "Statistics: Wilson 95% intervals for rates; chi-square tests for channel and segment differences; two-proportion z-tests with Holm correction for campaigns; Kruskal-Wallis for resolution time by priority; cohort-adjusted Mantel-Haenszel odds ratios for support vs inactivity; K-means with a pre-stated K rule (among k>=3 with bootstrap ARI>=0.85, highest silhouette); a logistic early-warning prototype with cross-validation.",
    "Labels: ACTUAL = calculated from the data; ASSUMPTION = analyst-chosen input; SCENARIO = arithmetic what-if; PROPOSED = design only. Correlation is never presented as causation.",
])
TAB(["KPI", "Formula"], [
    ["CAC", "Campaign spend / registered users (organic: not defined, not zero)"],
    ["Cost per KYC / first trader (at maturity)", "CAC / mature KYC rate; CAC / mature first-trade rate"],
    ["Stage conversion", "Users reaching the stage / users reaching the previous stage"],
    ["M1 / M3 / M6 retention", "Share active in calendar month k after the registration month, among cohorts old enough to observe it"],
    ["Tickets per 1,000 customer-months", "Tickets / observed customer-months x 1,000"],
], [2.6, 3.9], caption="Table 2. Key KPI formulas (full list in the Excel workbook, sheet KPI_Definitions)")

# ---------------------------------------------------------------- 4 Acquisition
H1("4. Acquisition")
P(f"Registrations are flat at about {R['reg_monthly_mean']:.0f} a month (range {R['reg_monthly_min']}-{R['reg_monthly_max']}; trend not significant, p={R['reg_trend_p']:.2f}). Monthly active users climb because the active base accumulates, not because acquisition is growing.")
IMG("c02_registrations_mau.png", "Figure 1. Registrations are flat; MAU grows as the active base accumulates")
rows = []
for r in ch.itertuples():
    rows.append([r.acquisition_channel, f"{r.registered:,}", pct(r.share_of_registrations), "n/a" if pd.isna(r.cac_inr) else f"{r.cac_inr:,.0f}", pct(r.kyc_rate), pct(r.first_trade_rate),
                 "n/a" if pd.isna(r.cost_per_first_trade_at_maturity_inr) else f"{r.cost_per_first_trade_at_maturity_inr:,.0f}", pct(r.m3_retention)])
TAB(["Channel", "Regs", "Share", "CAC (Rs)", "KYC", "First trade", "Cost / first trader (Rs)", "M3 ret."], rows, [1.2, 0.65, 0.6, 0.75, 0.6, 0.8, 1.05, 0.65],
    caption="Table 3. Channel performance (mature cohorts; organic has no recorded spend)", align=["l"] + ["r"] * 7)
IMG("c03_channel_first_trade.png", "Figure 2. First-trade rate by channel with 95% intervals")
H2("Answers to the five acquisition questions")
BL([
    f"Which channels acquire the most customers? Paid Search ({ch.set_index('acquisition_channel').loc['Paid Search','registered']:,}, {pct(ch.set_index('acquisition_channel').loc['Paid Search','share_of_registrations'])}) and Paid Social ({ch.set_index('acquisition_channel').loc['Paid Social','registered']:,}, {pct(ch.set_index('acquisition_channel').loc['Paid Social','share_of_registrations'])}).",
    f"Which acquire the highest-quality customers? Referral (first-trade {pct(cp.loc['CMP05','first_trade_rate_mature'])}, M3 {pct(R['retention_by_channel_m3']['Referral'])}) and Organic (first-trade {pct(R['organic_trade_rate'])}). Paid/incentivised users trade at {pct(R['paid_trade_rate'])} (difference significant, p<0.001).",
    "Which campaigns are inefficient? Video Awareness (CMP04) and Finance Affiliate (CMP06) have the highest cost per first trader and score tier C; Campus Events (CMP09) is also tier C on quality. CMP06's quality gap is not statistically significant after correction (p=0.061).",
    "Where to allocate budget? Shift in stages from CMP04/CMP06 to Referral (CMP05) and Email Nurture (CMP10) while measuring marginal cost; section 8 shows the arithmetic.",
    "What acquisition experiments to run? Post-first-trade referral prompt (EXP-06), pre-qualification landing page for paid social (EXP-10), guided KYC at sign-up (EXP-01).",
])

# ---------------------------------------------------------------- 5 Conversion
H1("5. Conversion funnel")
IMG("c01_funnel.png", "Figure 3. Overall funnel, mature cohorts")
rows = [[s, f"{F[s]['reached']:,}", pct(F[s]["conv_prev"]), pct(F[s]["conv_reg"]), f"{int(F[s]['lost']):,}", "-" if F[s]["median_days"] is None else f"{F[s]['median_days']:.0f}"] for s in F]
TAB(["Stage", "Users", "Step conv.", "Cumulative", "Users lost", "Median days"], rows, [1.7, 0.9, 1.0, 1.0, 0.9, 1.0], caption="Table 4. Funnel (mature cohorts, n=9,116)", align=["l"] + ["r"] * 5)
P(f"Segment differences are small: city and age do not significantly change first-trade rates, and device differs only for KYC (iOS highest). Median time from registration to first trade is {R['median_days_reg_to_trade']:.0f} days and no channel is materially faster (spread about {R['timing_channel_spread_days']:.0f} days), so speed is a product issue rather than a channel issue.")
H2("Three bottlenecks")
TAB(["Bottleneck", "Evidence (ACTUAL)", "Likely reasons (hypotheses)", "Intervention", "Success KPI"], [
    ["KYC", f"{pct(F['KYC Completed']['conv_prev'])} complete; {bn['KYC Completed']['users_lost']:,} lost; ticket raisers complete at {pct(bn['KYC Completed']['completion_rate_ticket_raisers'])} vs {pct(bn['KYC Completed']['completion_rate_non_raisers'])}", "Unclear documents, rejections, no status visibility", "Guided KYC, reminders, assisted KYC (EXP-01/02)", "Registration->KYC, 14-day completion"],
    ["First deposit", f"{pct(F['First Deposit']['conv_prev'])} of linked users deposit; {bn['First Deposit']['users_lost']:,} lost; ticket raisers {pct(bn['First Deposit']['completion_rate_ticket_raisers'])} vs {pct(bn['First Deposit']['completion_rate_non_raisers'])}", "Amount-decision friction, funding delays, low intent", "Quick-amount prompt + reminders (EXP-04)", "Bank->deposit conversion"],
    ["First trade", f"{pct(F['First Trade']['conv_prev'])} of depositors trade; {bn['First Trade']['users_lost']:,} lost; ticket raisers {pct(bn['First Trade']['completion_rate_ticket_raisers'])} vs {pct(bn['First Trade']['completion_rate_non_raisers'])}", "Low confidence, order friction", "Guided first trade with practice order (EXP-05)", "Deposit->first-trade conversion"],
], [0.9, 1.9, 1.3, 1.3, 1.1], caption="Table 5. Top three bottlenecks. Ticket evidence is an association (blocked users raise tickets), not proof that tickets cause drop-off")

# ---------------------------------------------------------------- 6 Retention
H1("6. Retention")
IMG("c05_retention.png", "Figure 4. Pooled retention curve and M3 retention by channel")
P(f"Retention is measured in calendar months after the registration month. It falls from {pct(R['m1'])} at M1 to {pct(R['m3'])} at M3 and {pct(R['m6'])} at M6. Among mature users, {pct(R['active30'])} were active in the 30 days after registration (eligible users only), {pct(R['inactive90'])} show a 90-day inactivity proxy, and {pct(R['dormant3m'])} had no active month Aug-Oct 2026. These are inactivity proxies, not churn.")
IMG("c07_cohort_heatmap.png", "Figure 5. Cohort retention matrix (blank cells are not yet observable)", 5.8)
BL([
    f"Loyal channels: Referral and Organic (M3 {pct(R['retention_by_channel_m3']['Referral'])} / {pct(R['retention_by_channel_m3']['Organic'])}; 3-month dormancy {pct(R['retention_by_channel_dormant']['Referral'])} / {pct(R['retention_by_channel_dormant']['Organic'])}).",
    f"Highest inactivity: Affiliate ({pct(R['retention_by_channel_dormant']['Affiliate'])} dormant), Paid Social ({pct(R['retention_by_channel_dormant']['Paid Social'])}) and Partnerships ({pct(R['retention_by_channel_dormant']['Partnerships'])}).",
    f"Repeat trading: {pct(R['repeat_trader_share_of_traders'])} of traders trade in 2 or more months and {pct(R['repeat3_share_of_traders'])} in 3 or more; {pct(R['traded_again_next_month'])} of trading months are followed by trading the next month.",
    f"Early disengagement: users who traded in months 0-1 are retained at M3 {pct(R['signals']['Traded in months 0-1']['present'])} vs {pct(R['signals']['Traded in months 0-1']['absent'])} for those who did not (association). A logistic early-warning model is weak (CV AUC {R['ew_model']['cv_auc']:.2f}), so risk-score targeting is not recommended yet.",
    "Possible churn reasons (hypotheses, not in the data): onboarding friction that never turns into a first trade, low-ticket accounts with little reason to return, channel mismatch for incentive-led sign-ups.",
])

# ---------------------------------------------------------------- 7 Segmentation
H1("7. Customer segmentation")
IMG("c08_journey_segments.png", "Figure 6. Journey segments (share of all 10,000 users)", 5.9)
rows = [[r.journey_segment[3:], f"{r.users:,}", pct(r.share), "-" if pd.isna(r.avg_trading_value_6m_inr) else f"{r.avg_trading_value_6m_inr:,.0f}", pct(r.pct_frequent_support_issues), pct(r.pct_source_conflict)] for r in js.itertuples()]
TAB(["Journey segment", "Users", "Share", "Avg 6m trading value (Rs)", "Frequent support", "Source conflict"], rows, [2.6, 0.6, 0.6, 1.1, 0.8, 0.8], caption="Table 6. Journey segments", align=["l"] + ["r"] * 5)
P(f"By the funnel flags, {pct(js.share.iloc[1:5].sum())} of users are in a stalled onboarding state, but 91-98% of them also appear in the activity log, so the backlog is smaller than it looks; reconcile before targeting. K-means (k={R['kmeans']['k']}, silhouette {R['kmeans']['silhouette']:.2f}) finds four behavioural groups: engaged regulars, non-trading partly-onboarded users, lapsed users, and a group that has no funnel funding record but trades in the activity log (a data conflict, not a real segment). Silhouette is modest, so these are partitions of a continuum.")
TAB(["Segment", "Business value", "Engagement strategy"], [
    ["KYC / bank / deposit pending (stalled)", "Largest pool of unconverted registrants", "Stage-specific reminders, assisted completion, in-flow help"],
    ["Deposited, never traded", "Funded but inactive; cheapest to convert", "Guided first trade, practice order, small-ticket ideas"],
    ["First-time traders", "Habit formation window", "Day 7/14/21 nudges, watch-list set-up"],
    ["Repeat and high-engagement traders", "Core active base (25.8% of users)", "Protect service quality; referral prompts"],
    ["Inactive / dormant traders", "Previously active, now lapsed", "Win-back sequence with holdout"],
    ["Frequent-support-issue users", "High cost-to-serve", "Root-cause fixes in KYC/bank/deposit flows"],
], [2.0, 2.0, 2.5], caption="Table 7. Value and strategy by segment (strategy is a recommendation)")

# ---------------------------------------------------------------- 8 Campaigns
H1("8. Campaign performance")
rows = []
for cid, r in cp.iterrows():
    rows.append([f"{cid} {r.campaign_name}", "n/a" if r.campaign_spend_inr == 0 else f"{r.campaign_spend_inr:,.0f}", f"{r.registered_users:,}", "n/a" if pd.isna(r.cac_inr) else f"{r.cac_inr:,.0f}",
                 pct(r.kyc_rate_mature), pct(r.first_trade_rate_mature), "n/a" if pd.isna(r.cost_per_first_trade_at_maturity_inr) else f"{r.cost_per_first_trade_at_maturity_inr:,.0f}",
                 "-" if pd.isna(r.overall_score) else f"{r.overall_score:.0f}", r.scorecard_tier.split(" ")[0] if r.scorecard_tier[0] in "ABC" else "Org."])
TAB(["Campaign", "Spend (Rs)", "Regs", "CAC", "KYC", "First trade", "Cost / trader", "Score", "Tier"], rows, [1.7, 0.8, 0.5, 0.5, 0.55, 0.7, 0.8, 0.5, 0.45],
    caption="Table 8. Campaign scorecard (analyst-defined rank score, not a statistical model; no ROI)", align=["l"] + ["r"] * 7 + ["l"])
IMG("c04_cost_per_first_trader.png", "Figure 7. Cost per first trader at maturity, paid campaigns")
P("Best campaigns: Customer Referral (CMP05) and Email Nurture (CMP10). Worst: Video Awareness (CMP04) and Finance Affiliate (CMP06). Organic Search and Organic Social have high quality but no recorded spend, so they are scored on quality only. The interval on cost per trader reflects conversion uncertainty only (CAC is treated as fixed).")
IMG("c11_budget_reallocation.png", "Figure 8. Budget reallocation scenario (arithmetic, not a forecast)", 5.6)
P(f"Scenario: moving 25% of CMP04 and CMP06 budgets ({inr(R['realloc']['moved'])}) to CMP05 and CMP10 adds about {rd('m5_budget_reallocation_scenarios').net_change_first_traders.iloc[0]:.0f} first traders at observed efficiency, but referral and CRM have limited capacity; the gain shrinks to about {rd('m5_budget_reallocation_scenarios').net_change_first_traders.iloc[3]:.0f} if destination costs double. Shift in stages (10% then 25%) and re-measure.")
BL([
    "A/B ideas: pre-qualification page for paid social (EXP-10); pay-per-first-trade terms for affiliates; creative variants that state what is needed to start (KYC documents, bank, minimum amounts).",
    "Creative optimisation: for Video Awareness, test shorter intent-setting creatives and exclude audiences that register but never complete KYC.",
    "Referral programme: add a post-first-trade prompt (EXP-06); keep reward terms identical across arms so only placement is tested; monitor referred-user quality and duplicate flags.",
    "Organic improvements: invest in search and social content that mirrors organic quality; track any content cost separately so organic CAC can be defined.",
])

# ---------------------------------------------------------------- 9 Support
H1("9. Customer support")
IMG("c09_support.png", "Figure 9. Ticket intensity by category and unresolved backlog age")
rows = [[r.category, f"{r.tickets:,}", pct(r.share), f"{r.tickets_per_1000_customer_months:.1f}", f"{r.median_res_h:.1f}", f"{r.csat:.2f}", pct(r.unresolved_pct)] for r in cat.itertuples()]
TAB(["Category", "Tickets", "Share", "Per 1,000 cust-months", "Median res. (h)", "CSAT", "Unresolved"], rows, [1.7, 0.7, 0.6, 1.2, 0.9, 0.6, 0.8],
    caption="Table 9. Tickets by category", align=["l"] + ["r"] * 6)
BL([
    f"Volume: {R['tickets']:,} tickets ({R['tickets_per_1000_users']:.0f} per 1,000 users); {pct(R['users_with_ticket_pct'],0)} of users raised at least one; {pct(R['resolved_pct'])} resolved, {R['open_n']:,} open, {R['escalated_n']:,} escalated.",
    f"Service: median resolution {R['res_median']:.1f}h (p90 {R['res_p90']:.1f}h); CSAT {R['csat_mean']:.2f}, with {pct(R['csat_low_pct'])} low (1-2). Priority does not change resolution time (Kruskal-Wallis p={R['priority_res_kruskal_p']:.2f}) and resolution time barely relates to CSAT (r={R['csat_corr_res_time']:.2f}).",
    "Support vs inactivity: users who raised any ticket have a cohort-adjusted odds ratio of 1.15 (95% CI 1.03-1.30) for 3-month dormancy; three or more tickets is borderline. A weak association, not a driver.",
    "Recommendations - onboarding: in-flow help and a KYC status tracker. KYC support: assisted completion for stalled applicants. Deposit processing: status messages and quick-amount prompts. Trading support: order-error explanations and a first-trade guide. Operations: priority-based service levels and a weekly review of tickets older than 90 days.",
])

# ---------------------------------------------------------------- 10 Experiments
H1("10. Proposed growth experiments")
NOTE("These ten experiments are PROPOSED designs. None has been run and no result is claimed. Baselines are actual values from the synthetic data; effect sizes are assumptions. Alpha 0.05 two-sided, power 80%.")
rows = [[r.experiment_id, r.area, r.primary_metric[:55], f"{r.baseline:.1%}" if r.experiment_id not in ("EXP-06", "EXP-08") else f"{r.baseline:.3f}/user", r.assumed_effect.replace(" (ASSUMED)", ""), f"{r.n_total:,}", f"{r.total_duration_weeks}"] for r in ex.itertuples()]
TAB(["ID", "Area", "Primary metric", "Baseline", "Assumed effect", "Total n", "Weeks"], rows, [0.6, 1.3, 1.9, 0.9, 1.0, 0.65, 0.65],
    caption="Table 10. Experiment summary (full design in Growth_Experiments.xlsx)", align=["l", "l", "l", "r", "l", "r", "r"])
IMG("c10_experiment_power.png", "Figure 10. Required sample and duration")
P("Each experiment specifies a hypothesis, target segment, intervention, control and treatment groups, primary and guardrail metrics, duration, expected benefit and evaluation method in the workbook. At about 190 registrations a week the traffic constraint is real: stage tests are made feasible by enrolling the current backlog at launch, independent levers can run concurrently (randomised at registration), and the retention and paid-social tests need either a larger effect, pooling or 6-12 months.")

# ---------------------------------------------------------------- 11 Strategic recommendations
H1("11. Strategic recommendations")
rows = [[int(r.priority_rank), r.category, r.recommendation, r.impact, r.complexity, r.cost, r.time_to_benefit] for r in rec.head(12).itertuples()]
TAB(["#", "Type", "Recommendation", "Impact", "Complexity", "Cost", "Time"], rows, [0.3, 1.15, 2.5, 0.7, 0.9, 0.8, 0.8],
    caption="Table 11. Top 12 recommendations by priority index (impact, complexity, cost and time to benefit are analyst ratings, not measurements)")
BL(["Growth opportunities: referral scale-up, KYC closure, staged budget shift, guided first trade, organic content.",
    "Operational improvements: KYC tracker, priority-based service levels, backlog clearance, source-of-truth reconciliation, onboarding KPIs.",
    "Retention: month-1 habit nudges, win-back with holdout, quarterly channel M3 reporting, stage reminders.",
    "Campaign optimisation: improvement plans for CMP04 and CMP06, pay-per-first-trade affiliate terms, cost per first trader as the primary KPI.",
    "Customer experience: KYC redesign with checklist, quick-amount deposit, inline help at KYC/bank/deposit."])
P("The 15 findings with evidence, implication, recommendation and KPI are in the workbook (sheet 7_Insights) and summarised in the executive PDF.")

# ---------------------------------------------------------------- 12 Limitations
H1("12. Limitations and next steps")
BL([
    "Synthetic data: patterns reflect how the dataset was generated. For example, ticket priority has no effect on resolution time and activity looks less 'sticky' than real behaviour (about 35% of user-months that follow three inactive months are active).",
    "Source conflict: funnel flags and the activity log disagree for many users (91-98% in the stalled segments). Funnel results use the Users table; retention uses the activity log; mixed results are indicative.",
    "Right-censoring: recent cohorts are excluded or handled with eligibility rules, and late months have small denominators.",
    "No revenue or cost-to-serve data: cost per first trader is a cost metric, not ROI; no LTV is estimated.",
    "Weak models: the early-warning model (AUC about 0.57) and K-means (silhouette 0.33) are descriptive, not predictive.",
    "Association vs causation: ticket, early-trading and channel patterns are associations. Only the proposed experiments could test causal effects.",
    "Campaign intervals reflect conversion uncertainty only. Scenario and experiment effects are assumptions.",
    "Next steps: reconcile the source conflict, then (separately requested) build the Excel dashboard, SQL query set, Power BI model and AI prototype in later phases.",
])
json.dump(B, open(BUILD / "report_content.json", "w"), indent=1, default=str)
print(len(B), "blocks")
