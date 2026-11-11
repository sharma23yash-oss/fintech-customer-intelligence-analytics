"""
Phase 3 - Modules 7 & 8: PROPOSED growth experiments (power calculations) and data-driven findings.

Inputs : Phase 3 tables + results.json (written by 10_phase3_analysis.py), data/cleaned/*.csv
Outputs: 07_growth_strategy/phase3_experiments/m7_experiments.csv, m7_experiments_power_grid.csv,
         m8_findings.csv, m8_recommendations.csv, m8_prioritisation.csv, findings_numbers.json
Run    : python3 11_phase3_experiments_findings.py

LABELLING RULES
  ACTUAL      = computed from the synthetic cleaned data (baselines, funnel rates, counts).
  ASSUMPTION  = expected effect sizes / MDEs chosen by the analyst. They are NOT forecasts.
  PROPOSED    = every experiment below is a design only. None has been run.
Sample size: two-sided alpha=0.05, power=80%, normal approximation (proportions or Poisson-style rates).
All data are synthetic; no revenue or ROI is computed anywhere.
"""
import json
import math
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # 05_python/ (for fintech_analytics)
from fintech_analytics import config as CFG

ROOT = CFG.ROOT
T = CFG.P3_TABLES          # 03_business_analytics/<module>/ (see config.p3_path)
CL = CFG.CLEAN_TABLES      # data/cleaned (+ derived/)
R = json.load(open(T / "results.json"))

Z_A, Z_B = stats.norm.ppf(0.975), stats.norm.ppf(0.80)
WEEKS_PER_MONTH = 52 / 12
REG_PER_WEEK = R["reg_monthly_mean"] / WEEKS_PER_MONTH            # ACTUAL: ~192 registrations / week
F = R["funnel"]
c = {k: v["conv_prev"] for k, v in F.items()}                       # stage conversion vs previous stage
reach = {k: v["conv_reg"] for k, v in F.items()}                    # cumulative vs registered


def n_per_arm_prop(p0, delta):
    """Two-proportion z-test, equal arms; delta = absolute lift (treatment - control)."""
    p1 = p0 + delta
    pbar = (p0 + p1) / 2
    num = (Z_A * math.sqrt(2 * pbar * (1 - pbar)) + Z_B * math.sqrt(p0 * (1 - p0) + p1 * (1 - p1))) ** 2
    return math.ceil(num / delta ** 2)


def n_per_arm_rate(r0, r1):
    """Per-user event-count rate (Poisson-style variance = mean). Used for tickets / referrals per user."""
    return math.ceil((Z_A + Z_B) ** 2 * (r0 + r1) / (r0 - r1) ** 2)


# ---------- baselines that need the raw cleaned tables ----------
MA = pd.read_csv(CL / "Cleaned_Monthly_Activity.csv", usecols=["user_id", "activity_month", "active_in_month"])
MA["activity_month"] = MA["activity_month"].astype(str).str[:7]
piv = MA.pivot_table(index="user_id", columns="activity_month", values="active_in_month", aggfunc="max")
months = sorted(piv.columns)
# ACTUAL: reactivation base rate = P(active in month t | registered, no activity in t-3..t-1), pooled over t
hits = tot = 0
for i in range(3, len(months)):
    prev = piv[months[i - 3:i]]
    eligible = prev.notna().all(axis=1) & (prev.sum(axis=1) == 0)
    cur = piv.loc[eligible, months[i]].dropna()
    hits += int(cur.sum()); tot += int(len(cur))
REACT_RATE = hits / tot if tot else float("nan")
U = pd.read_csv(CL / "Cleaned_Users.csv", usecols=["user_id", "acquisition_channel", "acquisition_campaign_id", "funnel_mature",
                                                     "dormant_3m_monthly", "ticket_count", "kyc_asof", "bank_asof", "deposit_asof",
                                                     "trade_asof", "days_reg_to_kyc"])
MU = U[U.funnel_mature == 1]
N_DORMANT_POOL = int((MU.dormant_3m_monthly == 1).sum())
# ACTUAL: inflow of newly dormant users per month (active at t-4, none in t-3..t-1); mean of the last 3 observable months.
# (earlier months are depressed by the left edge of the window, so only the last 3 are used)
ent = []
for i in range(4, len(months)):
    prev = piv[months[i - 3:i]]
    ent.append(int((prev.notna().all(axis=1) & (prev.sum(axis=1) == 0) & (piv[months[i - 4]] == 1)).sum()))
DORMANT_INFLOW_WEEK = float(np.mean(ent[-3:])) / WEEKS_PER_MONTH
# ACTUAL: KYC pending at day 7 and later completion (history shows no KYC later than day 11)
PEND7 = MU[(MU.kyc_asof == 0) | (MU.days_reg_to_kyc > 7)]
PEND7_SHARE = len(PEND7) / len(MU)
PEND7_COMPLETE = float(PEND7.kyc_asof.mean())
# ACTUAL: backlogs (mature users stuck at each stage; conflict-flagged, see F12)
BK_KYC = int((MU.kyc_asof == 0).sum())
BK_BANK = int(((MU.kyc_asof == 1) & (MU.bank_asof == 0)).sum())
BK_DEP = int(((MU.bank_asof == 1) & (MU.deposit_asof == 0)).sum())
BK_TRADE = int(((MU.deposit_asof == 1) & (MU.trade_asof == 0)).sum())
MAU_MEAN = pd.read_csv(T / "m3_mau_and_flows_monthly.csv").mau.mean()
CH = pd.read_csv(T / "m1_channel_performance.csv").set_index("acquisition_channel")
REF_REG_PER_MONTH = CH.loc["Referral", "registered"] / 12
js_first_trader = next(j["users"] for j in R["journey_segments"] if j["journey_segment"].startswith("06"))
REF_PER_100_MAU_MONTH = REF_REG_PER_MONTH / MAU_MEAN * 100         # ACTUAL (approx.: all referrals attributed to active base)
CAT = pd.read_csv(T / "m6_ticket_categories.csv").set_index("category")
KYC_TKT_PER_USER = CAT.loc["KYC & verification", "tickets_per_1000_users"] / 1000
CMP = pd.read_csv(T / "Campaign_Performance.csv").set_index("campaign_id")
PS_FT = CH.loc["Paid Social", "first_trade_rate"]
PS_REG_WEEK = CH.loc["Paid Social", "registered"] / 52

# ---------- experiment definitions (each: design fields + baseline + assumed effect + traffic) ----------
# kind: 'prop' (absolute lift), 'rate' (relative reduction/increase in per-user rate)
EXP = []


def add(**k):
    EXP.append(k)


add(id="EXP-01", area="KYC completion",
    title="Guided KYC checklist + auto-resume reminder (D+2, D+5)",
    hypothesis="Many registrants stall at KYC because the document step is unclear; a pre-submission checklist with photo-quality checks and a resume reminder will raise KYC completion.",
    segment="New registrants, all channels (stratified by channel and device)",
    intervention="Show document checklist + capture-quality validation before upload; push/email/SMS resume reminder on day 2 and day 5 if KYC incomplete.",
    control="Current KYC screens and no reminder cadence beyond the existing default.",
    treatment="Guided checklist + reminders as described.",
    primary="KYC completion within 14 days of registration", guardrail="KYC rejection / resubmission rate; KYC support tickets per 100 registrants; unsubscribe/opt-out rate",
    kind="prop", baseline=c["KYC Completed"], baseline_src="ACTUAL: Registered->KYC conversion (mature cohorts)", mde=0.05,
    traffic=REG_PER_WEEK, follow_up_weeks=2, evaluation="Two-proportion z-test (or chi-square) on 14-day KYC completion; CUPED not needed; stratified by channel; report absolute lift with 95% CI.",
    expected="+5 pp in KYC completion is the ASSUMED target; at ~190 registrants/week this would add ~10 KYC-complete users/week.")

add(id="EXP-02", area="KYC completion (support-assisted)",
    title="Assisted-KYC outreach for stalled applicants (backlog + new)",
    hypothesis="Applicants still pending beyond the historic maximum KYC lag (11 days; no KYC later than day 11 is observed) will not complete unaided; an assisted contact offer can recover some. Ticket raisers are a visible high-risk group (7.5% completion vs 74.9%).",
    segment=f"Mature registrants with KYC incomplete beyond day 11 (backlog of {BK_KYC:,}) plus new registrants as they cross day 11. Enrol only after reconciling KYC status with the activity log (about 91% of this group has a source conflict)",
    intervention="One outbound message offering assisted KYC (call-back or in-app chat link).",
    control="No outbound contact.", treatment="Assisted-KYC offer.",
    primary="KYC completion within 30 days of the outreach date", guardrail="Support contacts per enrolled user; assisted-contact cost per completed KYC (operational cost only); complaint rate",
    kind="prop", baseline=0.02, baseline_src="ASSUMPTION: 2% unaided late recovery. The data show no KYC completions after day 11, so the true unaided rate is near 0 and cannot be estimated",
    mde=0.06, traffic=REG_PER_WEEK * (1 - c["KYC Completed"]) * 0.5, pool=BK_KYC, follow_up_weeks=4,
    evaluation="Two-proportion z-test (exact test if counts are small) on 30-day completion; ITT analysis; stratify backlog vs new.",
    expected="+6 pp recovery among stalled applicants is an ASSUMPTION. With a backlog of this size, even a small lift is detectable quickly, but the result applies to stalled users, not all registrants.")

add(id="EXP-03", area="Bank linking",
    title="UPI-first bank link with alternate-method fallback",
    hypothesis="Bank-link failure/abandonment is a method-specific friction; offering UPI-based verification first and a one-tap fallback to net-banking reduces drop-off.",
    segment="KYC-completed users who have not linked a bank",
    intervention="Default to UPI-first linking; on failure, show alternate method and a status message within the same screen.",
    control="Current bank-link flow.", treatment="UPI-first with fallback.",
    primary="Bank linked within 7 days of KYC", guardrail="Bank-link failure rate; bank-link tickets per 100 KYC-complete users; fraud/mismatch flags",
    kind="prop", baseline=c["Bank Linked"], baseline_src="ACTUAL: KYC->Bank conversion (mature cohorts)", mde=0.04,
    traffic=REG_PER_WEEK * reach["KYC Completed"], pool=BK_BANK, follow_up_weeks=1,
    evaluation="Two-proportion z-test on 7-day bank-link rate; stratified by device (iOS/Android/Web).",
    expected="+4 pp is ASSUMED. Bank-linking is the smallest bottleneck by users lost (784), so expected volume benefit is limited.")

add(id="EXP-04", area="First deposit",
    title="Low-ticket first-deposit prompt with quick-amount chips",
    hypothesis="Users who have linked a bank but not deposited face an amount-decision barrier; showing low-ticket quick amounts anchored to the observed median first deposit (about Rs 6,400-6,500) lowers friction.",
    segment="Bank-linked users with no deposit",
    intervention="Quick-amount chips (e.g. 2,000 / 5,000 / 10,000) and a deposit reminder on day 3 and day 7.",
    control="Free-text amount entry, standard reminders.", treatment="Quick-amount chips + reminders.",
    primary="First deposit within 14 days of bank link", guardrail="Withdrawal-to-deposit ratio in first 30 days (guard against low-intent deposits); deposit-related tickets; opt-out rate",
    kind="prop", baseline=c["First Deposit"], baseline_src="ACTUAL: Bank->Deposit conversion (mature cohorts)", mde=0.05,
    traffic=REG_PER_WEEK * reach["Bank Linked"], pool=BK_DEP, follow_up_weeks=2,
    evaluation="Two-proportion z-test on 14-day deposit rate; secondary: median deposit amount (Mann-Whitney).",
    expected="+5 pp is ASSUMED. First Deposit is the second-largest leak (1,305 users lost).")

add(id="EXP-05", area="First trade",
    title="Guided first-trade walkthrough with a practice order",
    hypothesis="Funded-but-never-traded users lack confidence; an in-app walkthrough and a simulated/practice order will convert more deposits into first trades.",
    segment="Users with a deposit and no trade",
    intervention="Walkthrough card + practice (paper) order + day-2 and day-5 reminder.",
    control="Standard post-deposit home screen.", treatment="Walkthrough + practice order + reminders.",
    primary="First trade within 14 days of deposit", guardrail="Order-error/rejection rate; trading-support tickets; share of first trades that are very small (<Rs 500) to avoid hollow activation",
    kind="prop", baseline=c["First Trade"], baseline_src="ACTUAL: Deposit->First Trade conversion (mature cohorts)", mde=0.05,
    traffic=REG_PER_WEEK * reach["First Deposit"], pool=BK_TRADE, follow_up_weeks=2,
    evaluation="Two-proportion z-test on 14-day first-trade rate; check M1 activity as secondary to confirm that activation is not hollow.",
    expected="+5 pp is ASSUMED.")

add(id="EXP-06", area="Referral",
    title="Two-sided referral prompt at first-trade moment",
    hypothesis="Referral is the highest-quality, lowest-cost-per-trader channel (cost per first trader about Rs 438 vs Rs 1,050-1,250 elsewhere); surfacing the referral prompt right after a user's first trade will increase referred registrations.",
    segment=f"Active users (current MAU of {R['mau_last']:,}) at launch, plus new first-time traders as they arrive",
    intervention="Share sheet + invite-link prompt after first trade; reward structure kept identical in both arms (only prompt placement varies).",
    control="Existing referral entry in menu only.", treatment="Prompt after first trade.",
    primary="Referred registrations per 100 exposed users within 30 days", guardrail="Quality of referred users (first-trade rate of referred cohort must stay >= 45%); referral abuse/duplicate flags; opt-out rate",
    kind="rate", baseline=REF_PER_100_MAU_MONTH / 100, baseline_src="ACTUAL (approximate): mean monthly referral registrations / mean MAU. Referrer IDs are not in the dataset, so attribution is approximated",
    mde=0.50, mde_is_relative=True, traffic=REG_PER_WEEK * reach["First Trade"], pool=int(R["mau_last"]), follow_up_weeks=4,
    evaluation="Poisson/negative-binomial rate comparison per exposed user; guardrail on the first-trade rate of referred users.",
    expected="+50% relative lift in the referral rate is ASSUMED (a small baseline requires a large relative effect to be detectable).")

add(id="EXP-07", area="Retention",
    title="Week-2 / month-1 habit nudges for first-time traders",
    hypothesis="Users who trade within months 0-1 retain better at month 3 (60.7% vs 50.0%, an association, not proven causal); a structured nudge after first trade can lift engagement.",
    segment="Users who have placed their first trade (launch pool = current first-time traders, then new first traders weekly)",
    intervention="Contextual, non-promotional nudges at day 7, 14, 21 after first trade (watch-list suggestions, goal reminders).",
    control="Standard notifications only.", treatment="Habit-nudge sequence.",
    primary="Active in calendar month 3 after registration (M3 retention)", guardrail="Notification opt-out rate; app-uninstall proxy; complaint tickets about notifications",
    kind="prop", baseline=R["m3"], baseline_src="ACTUAL: pooled M3 retention, all mature registrants (traders-only baseline is higher; not computed)",
    mde=0.06, traffic=REG_PER_WEEK * reach["First Trade"], pool=int(js_first_trader), follow_up_weeks=14,
    evaluation="Two-proportion z-test on M3 active flag; pre-register stratification by channel; difference-in-differences not needed under randomisation.",
    expected="+6 pp M3 retention is ASSUMED. Note the early-warning logistic model was weak (CV AUC about 0.57), so targeting by predicted risk is NOT proposed.")

add(id="EXP-08", area="Ticket reduction",
    title="In-flow KYC status tracker + contextual help",
    hypothesis="KYC & verification is the largest ticket category (22.7% of tickets, 17.3 tickets per 100 users) and 43% of KYC tickets are raised while KYC is still pending; a status tracker plus contextual help should deflect avoidable tickets.",
    segment="Registrants in KYC-pending state",
    intervention="KYC progress tracker with expected time, rejection reasons shown inline, and FAQ deflection before 'contact support'.",
    control="Current KYC status screen.", treatment="Tracker + inline help.",
    primary="KYC tickets per registrant within 30 days", guardrail="KYC completion rate must not fall; CSAT for tickets; escalation rate; backlog age",
    kind="rate", baseline=KYC_TKT_PER_USER, baseline_src="ACTUAL: KYC & verification tickets / registered users (all-time per user)",
    mde=-0.20, mde_is_relative=True, traffic=REG_PER_WEEK, follow_up_weeks=4,
    evaluation="Rate comparison (Poisson/NB) on tickets per user; co-primary guardrail on KYC completion (non-inferiority).",
    expected="-20% relative KYC ticket rate is ASSUMED.")

add(id="EXP-09", area="Re-engagement of inactive users",
    title="Dormant-user win-back sequence (value-led, no incentive vs small incentive)",
    hypothesis="Users with no activity for 3+ months reactivate at a low base rate; a tailored win-back message can lift reactivation.",
    segment=f"Dormant users: no active month Aug-Oct 2026 (pool of {N_DORMANT_POOL:,} mature users), plus new entrants (about {DORMANT_INFLOW_WEEK:.0f}/week, ASSUMED to continue)",
    intervention="3-touch win-back (email/push, 7 days apart) with product updates and a learning resource.",
    control="No outreach (holdout).", treatment="3-touch win-back sequence.",
    primary="Reactivation: active in the 30 days after the last touch", guardrail="Unsubscribe rate; complaint rate; reactivated users' trading in the following month (to avoid empty logins)",
    kind="prop", baseline=REACT_RATE, baseline_src="ACTUAL: pooled P(active in month t | no activity in t-3..t-1) from Monthly_Activity",
    mde=0.06, traffic=DORMANT_INFLOW_WEEK, follow_up_weeks=4, pool=N_DORMANT_POOL,
    evaluation="Two-proportion z-test on 30-day reactivation; stratified by channel; ITT.",
    expected="+6 pp reactivation is ASSUMED. NOTE: the 34.7% base rate is high for a group labelled dormant; it reflects the synthetic activity pattern, so treat the baseline cautiously.")

add(id="EXP-10", area="Acquisition quality (paid social)",
    title="Pre-qualification landing page for Paid Social (CMP03 + CMP04)",
    hypothesis="Video Awareness (CMP04) has the weakest scorecard result (first-trade rate 30.8%, cost per first trader about Rs 1,250) and Education Social (CMP03) is also below average; intent-setting content before sign-up may filter low-intent registrants and raise first-trade yield per rupee.",
    segment="Paid Social click-throughs (CMP03 and CMP04 pooled so that traffic is sufficient)",
    intervention="Insert a short 'what you will need to start' page (KYC documents, bank, minimum amounts) before registration.",
    control="Direct-to-registration landing page.", treatment="Pre-qualification page first.",
    primary="First trade within 45 days of registration", guardrail="Registrations per rupee (CAC must not rise by more than 20%); KYC completion; organic spill-over",
    kind="prop", baseline=PS_FT, baseline_src="ACTUAL: Paid Social mature first-trade rate (CMP03 + CMP04)",
    mde=0.06, traffic=PS_REG_WEEK, follow_up_weeks=7,
    evaluation="Compare first trades per 1,000 click-throughs (not per registrant) so that lower registration volume is not mistaken for higher quality. Click-through counts are not in the dataset and must be logged.",
    expected="+6 pp first-trade rate per registrant is ASSUMED; the volume trade-off must be evaluated per click.")


rows = []
for e in EXP:
    if e["kind"] == "prop":
        n_arm = n_per_arm_prop(e["baseline"], e["mde"]); eff = f"+{e['mde']*100:.0f} pp (ASSUMED)"
        tgt = e["baseline"] + e["mde"]
    else:
        r1 = e["baseline"] * (1 + e["mde"])
        n_arm = n_per_arm_rate(e["baseline"], r1); eff = f"{e['mde']*100:+.0f}% relative (ASSUMED)"
        tgt = r1
    n_total = 2 * n_arm
    pool = e.get("pool", 0)
    # accrual weeks: launch pool is enrolled in week 1, remainder arrives at the weekly inflow
    wk_accrual = 1 if n_total <= pool else 1 + (n_total - pool) / e["traffic"]
    if wk_accrual <= 13:
        feas = "Feasible (<= 13 weeks accrual)"
    elif wk_accrual <= 26:
        feas = "Slow (14-26 weeks accrual): run concurrently with other tests or accept a larger MDE"
    else:
        feas = "Traffic-constrained (> 26 weeks): needs larger MDE, pooling, or a longer run"
    total_weeks = wk_accrual + e["follow_up_weeks"]
    rows.append(dict(
        experiment_id=e["id"], area=e["area"], title=e["title"], status="PROPOSED - NOT CONDUCTED",
        hypothesis=e["hypothesis"], target_segment=e["segment"], intervention=e["intervention"],
        control_group=e["control"], treatment_group=e["treatment"], primary_metric=e["primary"], guardrail_metrics=e["guardrail"],
        baseline=round(e["baseline"], 4), baseline_source=e["baseline_src"], assumed_effect=eff,
        target_value=round(tgt, 4), alpha=0.05, power=0.80,
        n_per_arm=n_arm, n_total=n_total, launch_pool=pool, eligible_per_week=round(e["traffic"], 1),
        accrual_weeks=math.ceil(wk_accrual), follow_up_weeks=e["follow_up_weeks"],
        total_duration_weeks=math.ceil(total_weeks), feasibility=feas,
        expected_benefit=e["expected"], evaluation_method=e["evaluation"]))
EX = pd.DataFrame(rows)
EX.to_csv(T / "m7_experiments.csv", index=False)

# sensitivity grid: n per arm if the true MDE is half / full / 1.5x the assumption
grid = []
for e in EXP:
    for mult in (0.5, 1.0, 1.5):
        if e["kind"] == "prop":
            n = n_per_arm_prop(e["baseline"], e["mde"] * mult)
        else:
            n = n_per_arm_rate(e["baseline"], e["baseline"] * (1 + e["mde"] * mult))
        grid.append(dict(experiment_id=e["id"], effect_multiplier=mult, n_per_arm=n, n_total=2 * n,
                         weeks_to_accrue=round(1 if 2 * n <= e.get("pool", 0) else 1 + (2 * n - e.get("pool", 0)) / e["traffic"], 1)))
pd.DataFrame(grid).to_csv(T / "m7_experiments_power_grid.csv", index=False)

# ---------- Module 8: findings (numbers pulled from results) ----------
fn = {}
bn = {b["stage"]: b for b in R["bottlenecks"]}
sc = {s["campaign_id"]: s for s in R["campaign_scorecard"]}
js = {s["journey_segment"][:2]: s for s in R["journey_segments"]}
pct = lambda x, d=1: f"{x*100:.{d}f}%"
inr = lambda x: f"Rs {x:,.0f}"
kyc_lost = bn["KYC Completed"]; dep_lost = bn["First Deposit"]
tot_lost = sum(b["users_lost"] for b in R["bottlenecks"])
ret_c = R["retention_by_channel_m3"]; dor_c = R["retention_by_channel_dormant"]
sig = R["signals"]
real = R["realloc"]
rt = pd.read_csv(T / "m5_budget_reallocation_scenarios.csv")
sup = pd.read_csv(T / "m6_support_vs_inactivity.csv").iloc[0]
cat_kyc = CAT.loc["KYC & verification"]
cat_trd = CAT.loc["Trading & orders"]
dev = pd.read_csv(T / "m2_dimension_significance_tests.csv")
dev_kyc = dev[(dev.dimension == "device_type") & (dev.outcome == "kyc_asof")].iloc[0]
city_t = dev[(dev.dimension == "city") & (dev.outcome == "trade_asof")].iloc[0]

FIND = [
    dict(id="F01", module="Funnel", observation="KYC is the largest single leak in the onboarding funnel.",
         evidence=f"{pct(c['KYC Completed'])} of mature registrants complete KYC; {kyc_lost['users_lost']:,} of {tot_lost:,} users lost across all stages ({pct(kyc_lost['share_of_all_funnel_losses'])}). Median time to KYC is {F['KYC Completed']['median_days']:.0f} days (p75 {F['KYC Completed']['p75_days']:.0f}).",
         implication="Fixing KYC has more headroom than any other stage because it sits at the top and compounds through every later stage.",
         recommendation="Run EXP-01 (guided KYC + reminders) and EXP-02 (assisted KYC for stalled applicants).",
         kpi="Registration->KYC conversion (14-day and final)", label="ACTUAL"),
    dict(id="F02", module="Funnel", observation="Users who contact support while a stage is pending are far less likely to complete it.",
         evidence=f"KYC completion: {pct(kyc_lost['completion_rate_ticket_raisers'])} for ticket raisers vs {pct(kyc_lost['completion_rate_non_raisers'])} for non-raisers; deposit {pct(dep_lost['completion_rate_ticket_raisers'])} vs {pct(dep_lost['completion_rate_non_raisers'])}. Only {pct(kyc_lost['pct_of_at_risk_who_raised_ticket'])} of at-risk users raised a related ticket.",
         implication="A ticket is a visible signal of a blocked user. Association only (blocked users raise tickets); it does not prove that tickets cause drop-off.",
         recommendation="Prioritise first-contact resolution on onboarding tickets; trigger a proactive follow-up for open onboarding tickets older than 24h.",
         kpi="Stage completion within 14 days of an onboarding ticket", label="ACTUAL (association)"),
    dict(id="F03", module="Funnel", observation="First deposit is the second-largest bottleneck, and deposit-to-trade is the third.",
         evidence=f"Bank->deposit {pct(c['First Deposit'])} ({dep_lost['users_lost']:,} lost); deposit->trade {pct(c['First Trade'])} ({bn['First Trade']['users_lost']:,} lost). Registered->first trade is {pct(reach['First Trade'])}; registered->30-day active is {pct(reach['Active (30d)'])}.",
         implication="Even after the bank is linked, about 1 in 4 users never funds the account, and about 1 in 5 funded users never trades.",
         recommendation="Run EXP-04 (low-ticket deposit prompt) and EXP-05 (guided first trade with practice order).",
         kpi="Bank->deposit, deposit->first trade conversion", label="ACTUAL"),
    dict(id="F04", module="Funnel", observation="Time from registration to first trade is long relative to the stage lags.",
         evidence=f"Median registration->first trade is {R['median_days_reg_to_trade']:.0f} days (p75 {R['p75_days_reg_to_trade']:.0f}); stage medians KYC {F['KYC Completed']['median_days']:.0f}d, bank {F['Bank Linked']['median_days']:.0f}d, deposit {F['First Deposit']['median_days']:.0f}d, trade {F['First Trade']['median_days']:.0f}d. Channel spread in timing is only about {R['timing_channel_spread_days']:.0f} days.",
         implication="Lag is spread across all four steps rather than concentrated in one; no channel is materially faster, so onboarding speed is a product issue, not a channel issue.",
         recommendation="Add day-based reminders at each stage; track time-to-first-trade as an onboarding KPI.",
         kpi="Median days registration->first trade", label="ACTUAL"),
    dict(id="F05", module="Acquisition", observation="Referral and organic channels deliver the highest-quality users; paid social and partnerships the lowest.",
         evidence=f"First-trade rate (mature): Referral {pct(CH.loc['Referral','first_trade_rate'])}, Organic {pct(CH.loc['Organic','first_trade_rate'])}, Paid Search {pct(CH.loc['Paid Search','first_trade_rate'])}, Paid Social {pct(CH.loc['Paid Social','first_trade_rate'])}, Partnerships {pct(CH.loc['Partnerships','first_trade_rate'])}. Channel differences are significant (chi-square p<0.001).",
         implication="Registration volume and quality are decoupled: paid social is 25% of registrations but has the lowest first-trade rate among the large channels.",
         recommendation="Judge channels on cost per first trader, not CAC alone.",
         kpi="Cost per first trader at maturity, by channel", label="ACTUAL"),
    dict(id="F06", module="Acquisition", observation="Organic traffic is only a minority of registrations but is the best-performing large source.",
         evidence=f"Organic is {pct(R['organic_share'])} of registrations; first-trade rate {pct(R['organic_trade_rate'])} vs {pct(R['paid_trade_rate'])} for paid/incentivised; 30-day active {pct(R['organic_active'])} vs {pct(R['paid_active'])} (p<0.001).",
         implication="Organic cannot be bought with budget, but its quality sets a benchmark; no CAC is recorded for it (shown as not defined, not zero).",
         recommendation="Invest in organic search/social content and referral loops; track organic spend separately if content costs are available.",
         kpi="Organic share of registrations; organic first-trade rate", label="ACTUAL"),
    dict(id="F07", module="Campaigns", observation="Customer Referral (CMP05) is the most cost-efficient campaign; Video Awareness (CMP04) and Finance Affiliate (CMP06) are the least.",
         evidence=f"Cost per first trader at maturity: CMP05 {inr(sc['CMP05']['cost_per_first_trade_at_maturity_inr'])} (CI {inr(sc['CMP05']['cost_per_first_trade_ci_low'])}-{inr(sc['CMP05']['cost_per_first_trade_ci_high'])}); CMP04 {inr(sc['CMP04']['cost_per_first_trade_at_maturity_inr'])}; CMP06 {inr(sc['CMP06']['cost_per_first_trade_at_maturity_inr'])}. CMP04 first-trade rate is significantly below the rest (Holm p<0.001); CMP06 is not significant after correction (p={sc['CMP06']['first_trade_p_holm']:.3f}) although its cost per trader is high.",
         implication="CMP05 and CMP04/CMP06 sit at opposite ends of the scorecard; CMP06 needs more data before a firm conclusion. CI reflects conversion-rate uncertainty only (CAC treated as fixed).",
         recommendation="Scale CMP05 within its capacity; put CMP04 and CMP06 on a performance improvement plan.",
         kpi="Cost per first trader at maturity", label="ACTUAL (scorecard is analyst-defined, not a model)"),
    dict(id="F08", module="Campaigns", observation="Moving budget from the two weakest to the two strongest paid campaigns is arithmetically attractive but highly sensitive to diminishing returns.",
         evidence=f"Scenario: move 25% of CMP04 and CMP06 budgets ({inr(real['moved'])}) to CMP05 and CMP10. At observed efficiency the net gain is about {rt.net_change_first_traders.iloc[0]:.0f} first traders ({pct(rt.net_change_pct_of_paid_baseline.iloc[0])} of the paid baseline); it falls to {rt.net_change_first_traders.iloc[3]:.0f} if destination costs double and reaches break-even only when destination cost per first trader is about +{real['breakeven_penalty']*100:.0f}% above observed.",
         implication="Not a forecast: referral and CRM have limited absorptive capacity, so incremental spend will likely cost more than the average.",
         recommendation="Stage the shift (10%, then 25%) and re-measure marginal cost per first trader at each step.",
         kpi="Marginal cost per first trader by campaign", label="SCENARIO (arithmetic, not forecast)"),
    dict(id="F09", module="Retention", observation="Retention decays steadily rather than collapsing after onboarding.",
         evidence=f"Calendar-month retention (mature cohorts): M1 {pct(R['m1'])}, M3 {pct(R['m3'])}, M6 {pct(R['m6'])}. 30-day active {pct(R['active30'])} of eligible; 90-day inactivity proxy {pct(R['inactive90'])}; {pct(R['dormant3m'])} dormant for the last 3 months.",
         implication=f"About {(R['m1']-R['m3'])*100:.0f} points of retention are lost between M1 and M3 and a further {(R['m3']-R['m6'])*100:.0f} points by M6, so the retention plan must start in months 1-3.",
         recommendation="Run EXP-07 (habit nudges) and build a month-1 engagement milestone into onboarding.",
         kpi="M1, M3, M6 retention; dormant-3m rate", label="ACTUAL (inactivity PROXIES, not churn)"),
    dict(id="F10", module="Retention", observation="Referral and organic cohorts retain best; partnerships and affiliate retain worst.",
         evidence=f"M3 retention: Referral {pct(ret_c['Referral'])}, Organic {pct(ret_c['Organic'])}, Partnerships {pct(ret_c['Partnerships'])}, Paid Social {pct(ret_c['Paid Social'])}. 3-month dormancy: Referral {pct(dor_c['Referral'])} vs Affiliate {pct(dor_c['Affiliate'])}. Channel M3 differences significant (p<0.001).",
         implication="The channels that acquire cheaply are not the ones that keep customers.",
         recommendation="Include M3 retention in the campaign scorecard (already done) and review quarterly.",
         kpi="M3 retention by channel", label="ACTUAL"),
    dict(id="F11", module="Retention", observation="Early trading is associated with better later retention, but early signals are weak predictors.",
         evidence=f"M3 retained {pct(sig['Traded in months 0-1']['present'])} when traded in months 0-1 vs {pct(sig['Traded in months 0-1']['absent'])} when not. A logistic early-warning prototype has CV AUC {R['ew_model']['cv_auc']:.2f} (temporal test {R['ew_model']['temporal_test_auc']:.2f}).",
         implication="Activation timing matters, but the available features cannot reliably predict who will disengage; this is an association and not a causal estimate.",
         recommendation="Focus on universal onboarding improvements, not on risk-score targeting, until richer behavioural data exist.",
         kpi="Share of new users trading in months 0-1", label="ACTUAL (association; model weak)"),
    dict(id="F12", module="Segmentation", observation="A large share of customers are stalled in onboarding rather than inactive after trading.",
         evidence=f"Journey segments: KYC-pending {pct(js['02']['share'])}, deposit-pending {pct(js['04']['share'])}, bank-link pending {pct(js['03']['share'])}, deposited-never-traded {pct(js['05']['share'])}; high-engagement traders are only {pct(js['08']['share'])} and repeat traders {pct(js['07']['share'])}. K-means (k={R['kmeans']['k']}, silhouette {R['kmeans']['silhouette']:.2f}) shows continuous, weakly separated clusters.",
         implication=f"By the funnel flags, {pct(js['02']['share']+js['03']['share']+js['04']['share']+js['05']['share'])} of users sit in a stalled onboarding state. The high source-conflict share in those segments (91-98%) means many also appear active in the activity log, so the true size of the backlog is uncertain.",
         recommendation="Reconcile funnel flags with activity data before targeting; run stage-specific nudges for 'stalled' users.",
         kpi="Share of mature users in stalled segments", label="ACTUAL (conflict-flagged)"),
    dict(id="F13", module="Support", observation="Support volume is high and concentrated in onboarding and trading categories.",
         evidence=f"{R['tickets']:,} tickets ({R['tickets_per_1000_users']:.0f} per 1,000 users; {R['users_with_ticket_pct']*100:.0f}% of users raised at least one). KYC {pct(cat_kyc['share'])} of tickets ({cat_kyc['tickets_per_1000_customer_months']:.1f} per 1,000 customer-months), trading & orders {pct(cat_trd['share'])}. Median resolution {R['res_median']:.1f}h; CSAT {R['csat_mean']:.2f}; {R['open_n']:,} open and {R['escalated_n']:,} escalated.",
         implication="Onboarding-related tickets (KYC, bank, deposit) together account for over half of all tickets, so product fixes should reduce volume more efficiently than staffing.",
         recommendation="Run EXP-08; add in-flow help to KYC and bank-link screens.",
         kpi="Tickets per 1,000 customer-months; onboarding ticket share", label="ACTUAL"),
    dict(id="F14", module="Support", observation="Priority does not change service levels, and the backlog is ageing.",
         evidence=f"Median resolution is about 9.4-9.5h for High, Medium and Low priority alike (Kruskal-Wallis p={R['priority_res_kruskal_p']:.2f}); CSAT vs resolution time correlation {R['csat_corr_res_time']:.2f}. {R['backlog_over_90']:,} unresolved tickets are older than 90 days, {R['backlog_over_180']:,} older than 180 days.",
         implication="The priority field appears not to drive routing in this synthetic data, and old open tickets are unmanaged risk. Real operations may differ.",
         recommendation="Introduce SLA tiers by priority and a weekly backlog clearance for tickets older than 90 days.",
         kpi="Resolution time by priority; open tickets >90 days", label="ACTUAL"),
    dict(id="F15", module="Support", observation="Support contact is only weakly associated with later inactivity.",
         evidence=f"Cohort-adjusted odds ratio of 3-month dormancy for users who raised any ticket: {sup['mantel_haenszel_odds_ratio_cohort_adjusted']:.2f} (95% CI {sup['or_ci_low']:.2f}-{sup['or_ci_high']:.2f}); raising 3+ tickets: borderline (CI crosses 1). CSAT does not separate dormancy ({pd.read_csv(T/'m6_csat_vs_dormancy.csv').user_dormant_rate.min()*100:.0f}-{pd.read_csv(T/'m6_csat_vs_dormancy.csv').user_dormant_rate.max()*100:.0f}% across CSAT bands).",
         implication="Support experience is not a strong standalone driver of inactivity here; do not over-invest on that basis alone. Association, not causation.",
         recommendation="Keep support improvements justified by onboarding conversion and cost-to-serve rather than by a retention claim.",
         kpi="Dormancy rate by ticket exposure", label="ACTUAL (weak association)"),
]
FIN = pd.DataFrame(FIND)
FIN.to_csv(T / "m8_findings.csv", index=False)

# ---------- recommendation lists + prioritisation ----------
REC = []


def rec(cat, rid, text, impact, complexity, cost, ttb, basis, hyp):
    REC.append(dict(category=cat, id=rid, recommendation=text, impact=impact, complexity=complexity, cost=cost,
                    time_to_benefit=ttb, linked_findings=basis, label="HYPOTHESIS / ESTIMATE (not measured)" if hyp else "DERIVED FROM ACTUALS"))


rec("Growth opportunity", "G1", "Scale the referral programme with a post-first-trade prompt (EXP-06) while monitoring referred-user quality.", "High", "Low", "Low", "1-3 months", "F05, F07, F10", True)
rec("Growth opportunity", "G2", "Close the KYC gap with guided KYC and assisted KYC for stalled applicants (EXP-01, EXP-02).", "High", "Medium", "Low-Medium", "1-2 months", "F01, F02", True)
rec("Growth opportunity", "G3", "Re-allocate part of the CMP04/CMP06 budget to CMP05/CMP10 in stages, measuring marginal cost.", "Medium", "Low", "None (budget-neutral)", "1-2 months", "F07, F08", True)
rec("Growth opportunity", "G4", "Convert funded-but-untraded users with a guided first trade and practice order (EXP-05).", "Medium", "Medium", "Low", "2-3 months", "F03", True)
rec("Growth opportunity", "G5", "Invest in organic content and SEO as the highest-quality non-paid source.", "Medium", "Medium", "Medium", "3-6 months", "F06", True)
rec("Operational improvement", "O1", "Add a KYC progress tracker and rejection reasons in-flow (EXP-08).", "High", "Medium", "Medium", "2-3 months", "F01, F13", True)
rec("Operational improvement", "O2", "Define priority-based SLA tiers (High/Medium/Low) with routing.", "Medium", "Low", "Low", "1 month", "F14", False)
rec("Operational improvement", "O3", "Clear the >90-day open-ticket backlog and set a weekly ageing review.", "Medium", "Low", "Low", "1 month", "F14", False)
rec("Operational improvement", "O4", "Reconcile funnel flags with the activity log (source-of-truth rules) before any segment-level targeting.", "High", "Medium", "Low", "1-2 months", "F12", False)
rec("Operational improvement", "O5", "Track time-to-first-trade and stage lags as standing onboarding KPIs.", "Medium", "Low", "Low", "1 month", "F04", False)
rec("Retention recommendation", "R1", "Month-1 habit nudges for first-time traders (EXP-07).", "Medium", "Medium", "Low", "3-4 months", "F09, F11", True)
rec("Retention recommendation", "R2", "Dormant-user win-back sequence with holdout (EXP-09).", "Medium", "Low", "Low", "1-2 months", "F09, F10", True)
rec("Retention recommendation", "R3", "Report M3 retention per channel quarterly and include it in the scorecard.", "Medium", "Low", "Low", "Immediate", "F10", False)
rec("Retention recommendation", "R4", "Prioritise early-activation milestones (trade in months 0-1) over risk scoring until better data exist.", "Medium", "Low", "Low", "1-2 months", "F11", True)
rec("Retention recommendation", "R5", "Add a stage-specific reminder cadence for stalled users (KYC, bank, deposit, first trade).", "High", "Medium", "Low", "1-2 months", "F03, F12", True)
rec("Campaign optimisation", "C1", "Place CMP04 (Video Awareness) on an improvement plan: pre-qualification page (EXP-10), creative refresh and audience exclusions.", "Medium", "Medium", "Low", "2-3 months", "F07", True)
rec("Campaign optimisation", "C2", "Review CMP06 (Finance Affiliate): renegotiate payout toward qualified first trades (pay-per-first-trade).", "Medium", "Medium", "Low", "2-4 months", "F07", True)
rec("Campaign optimisation", "C3", "Use cost per first trader (not CAC) as the primary campaign KPI in budget reviews.", "High", "Low", "None", "Immediate", "F05, F07", False)
rec("Customer experience", "X1", "Redesign KYC screens with a document checklist and photo-quality checks.", "High", "Medium", "Medium", "2-3 months", "F01", True)
rec("Customer experience", "X2", "Simplify first-deposit with quick-amount chips anchored to median first deposit (EXP-04).", "Medium", "Low", "Low", "1-2 months", "F03", True)
rec("Customer experience", "X3", "Add inline help and FAQ deflection at KYC, bank link and deposit screens.", "Medium", "Low", "Low", "1-2 months", "F02, F13", True)
RE = pd.DataFrame(REC)
RE.to_csv(T / "m8_recommendations.csv", index=False)

score = {"High": 3, "Medium": 2, "Low": 1, "None": 0, "None (budget-neutral)": 0, "Low-Medium": 1.5, "Medium-High": 2.5}
ttb_months = {"Immediate": 0.5, "1 month": 1, "1-2 months": 1.5, "1-3 months": 2, "2-3 months": 2.5, "2-4 months": 3, "3-4 months": 3.5, "3-6 months": 4.5}
PR = RE.copy()
PR["impact_score"] = PR.impact.map(score)
PR["ease_score"] = 4 - PR.complexity.map(score)
PR["cost_score"] = 4 - PR.cost.map(score)
PR["speed_score"] = 4 - PR.time_to_benefit.map(ttb_months).clip(upper=4.5) / 4.5 * 3
# priority index: impact weighted 2x, ease/cost/speed 1x each (analyst-defined, transparent weights)
PR["priority_index"] = (2 * PR.impact_score + PR.ease_score + PR.cost_score + PR.speed_score) / 5
PR["priority_rank"] = PR.priority_index.rank(ascending=False, method="first").astype(int)
PR = PR.sort_values("priority_rank")
PR.to_csv(T / "m8_prioritisation.csv", index=False)

out = dict(reg_per_week=REG_PER_WEEK, react_rate=REACT_RATE, react_n=tot, dormant_pool=N_DORMANT_POOL, dormant_inflow_week=DORMANT_INFLOW_WEEK, pend7_share=PEND7_SHARE, pend7_complete=PEND7_COMPLETE, backlogs=dict(kyc=BK_KYC, bank=BK_BANK, deposit=BK_DEP, trade=BK_TRADE),
           ref_per_100_mau_month=REF_PER_100_MAU_MONTH, kyc_tickets_per_user=KYC_TKT_PER_USER, mau_mean=MAU_MEAN)
json.dump(out, open(T / "findings_numbers.json", "w"), indent=1, default=float)
print(EX[["experiment_id", "baseline", "assumed_effect", "n_per_arm", "n_total", "launch_pool", "eligible_per_week", "accrual_weeks", "total_duration_weeks", "feasibility"]].to_string())
print(out)
print(PR[["priority_rank", "id", "impact", "complexity", "cost", "time_to_benefit", "priority_index"]].head(10).to_string())
