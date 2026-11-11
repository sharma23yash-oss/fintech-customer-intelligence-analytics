"""Phase 6 evidence layer (synthetic data only).

Builds the tables that every Phase 6 deliverable quotes, so each number is traceable:
  p6_channel_scorecard.csv      channel quality + cost metrics (mature cohort for rates)
  p6_campaign_scorecard.csv     campaign cost per activated customer and budget share
  p6_budget_scenarios.csv       directional budget scenarios (cost per first trade only; NO revenue / ROI)
  p6_experiment_plan.csv        10 PROPOSED tests: sample size, duration, MDE sensitivity (re-computed and
                                reconciled with Phase 3 m7_experiments.csv)
  p6_friction_by_stage.csv      stage-level friction evidence: loss, timing, support linkage
  p6_missing_information.csv    data that does not exist in the synthetic dataset and blocks financial claims
  p6_verification.csv           reconciliation of every headline number against Phase 3 sources

Nothing here is a forecast. Scenario rows are arithmetic at observed efficiency.
"""
import json, math, sys
from pathlib import Path
import pandas as pd
from scipy import stats

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "05_python"))   # fintech_analytics package
from fintech_analytics import config as CFG
ROOT = CFG.ROOT
T3 = CFG.P3_TABLES
OUT = ROOT / "07_growth_strategy" / "tables"
OUT.mkdir(parents=True, exist_ok=True)
CL = CFG.CLEAN_TABLES

R = json.load(open(T3 / "results.json"))
CP = pd.read_csv(CL / "Campaign_Performance.csv")
U = pd.read_csv(CL / "Cleaned_Users.csv")
MU = U[U.funnel_mature == 1]

# ------------------------------------------------------------------ channel scorecard
rows = []
for ch, g in U.groupby("acquisition_channel"):
    m = g[g.funnel_mature == 1]
    cp = CP[CP.channel == ch]
    spend = cp.campaign_spend_inr.sum()
    reg = len(g)
    rows.append(dict(
        channel=ch, registrations=reg, share_of_registrations=reg / len(U),
        spend_inr=spend if spend > 0 else None,
        cac_inr=spend / reg if spend > 0 else None,
        mature_users=len(m),
        kyc_rate=m.kyc_asof.mean(), first_trade_rate=m.trade_asof.mean(),
        cost_per_first_trade_inr=(spend / reg) / m.trade_asof.mean() if spend > 0 else None,
        m3_retention=m.m3_retained.mean(),
        dormant_3m_rate=m.dormant_3m_monthly.mean(),
    ))
ch = pd.DataFrame(rows).sort_values("first_trade_rate", ascending=False)
ch.to_csv(OUT / "p6_channel_scorecard.csv", index=False)

# ------------------------------------------------------------------ campaign scorecard
cs = CP[["campaign_id", "campaign_name", "channel", "campaign_spend_inr", "registered_users", "cac_inr",
         "first_trade_rate_mature", "cost_per_first_trade_at_maturity_inr", "cost_per_kyc_at_maturity_inr",
         "m3_retention", "dormant_3m_rate", "share_of_spend"]].copy()
cs.to_csv(OUT / "p6_campaign_scorecard.csv", index=False)

# ------------------------------------------------------------------ budget scenarios (directional)
paid = CP[CP.is_paid == 1].set_index("campaign_id")
cpft = paid.cost_per_first_trade_at_maturity_inr
spend = paid.campaign_spend_inr
base_traders = float((spend / cpft).sum())            # first traders implied at mature rates, observed spend
assert abs(base_traders - R["realloc"]["base_traders"]) < 1e-6, "baseline differs from Phase 3"


def scenario(name, src, dst, pct, penalties):
    """Same arithmetic as Phase 3 m5: moved budget is split EQUALLY across destinations (Phase 3 convention)."""
    moved = spend[src].sum() * pct
    src_cost = float((spend[src] * pct).sum() / (spend[src] * pct / cpft[src]).sum())
    share = moved / len(dst)
    dst_cost = float(moved / (sum(share / cpft[d] for d in dst)))
    growth = {d: share / spend[d] for d in dst}          # extra spend as a share of the destination's current spend
    out = []
    for p in penalties:
        lost = moved / src_cost
        gained = moved / (dst_cost * (1 + p))
        out.append(dict(
            scenario=name, moved_budget_inr=moved, destination_cost_penalty=f"+{int(p*100)}%",
            source_cost_per_first_trade_inr=src_cost, destination_cost_per_first_trade_inr=dst_cost * (1 + p),
            first_traders_lost=lost, first_traders_gained=gained, net_change_first_traders=gained - lost,
            net_change_pct_of_paid_baseline=(gained - lost) / base_traders,
            cmp05_spend_growth_required=growth.get("CMP05"), cmp10_spend_growth_required=growth.get("CMP10"),
            blended_cost_per_first_trade_after_inr=spend.sum() / (base_traders - lost + gained)))
    return out


PEN = [0, 0.25, 0.5, 1.0, 1.5]
sc = []
sc += scenario("S1 Stage 1: move 10% of CMP04+CMP06 to CMP05+CMP10", ["CMP04", "CMP06"], ["CMP05", "CMP10"], 0.10, PEN)
sc += scenario("S2 Stage 2: move 25% of CMP04+CMP06 to CMP05+CMP10", ["CMP04", "CMP06"], ["CMP05", "CMP10"], 0.25, PEN)
sc += scenario("S3 Tier-C sweep: move 15% of CMP04+CMP06+CMP09 to CMP05+CMP10",
               ["CMP04", "CMP06", "CMP09"], ["CMP05", "CMP10"], 0.15, PEN)
scn = pd.DataFrame(sc)
scn["breakeven_penalty_pct"] = scn.apply(
    lambda r: (r.source_cost_per_first_trade_inr / (r.destination_cost_per_first_trade_inr / (1 + float(r.destination_cost_penalty.strip('+%')) / 100)) - 1) * 100, axis=1)
scn.to_csv(OUT / "p6_budget_scenarios.csv", index=False)
# reconcile S2 with Phase 3
p3 = pd.read_csv(T3 / "m5_budget_reallocation_scenarios.csv")
s2 = scn[scn.scenario.str.startswith("S2")].reset_index(drop=True)
for a, b in zip(s2.net_change_first_traders, p3.net_change_first_traders):
    assert abs(a - b) < 1e-6, (a, b)

# ------------------------------------------------------------------ experiment plan
ZA, ZB = stats.norm.ppf(0.975), stats.norm.ppf(0.80)


def n_prop(p0, d):
    p1 = p0 + d; pb = (p0 + p1) / 2
    return math.ceil((ZA * math.sqrt(2 * pb * (1 - pb)) + ZB * math.sqrt(p0 * (1 - p0) + p1 * (1 - p1))) ** 2 / d ** 2)


def n_rate(r0, r1):
    return math.ceil((ZA + ZB) ** 2 * (r0 + r1) / (r0 - r1) ** 2)


m7 = pd.read_csv(T3 / "m7_experiments.csv")
eff = {  # experiment: (kind, assumed effect, label of metric) - effects are ASSUMPTIONS from Phase 3
    "EXP-01": ("prop", 0.05), "EXP-02": ("prop", 0.06), "EXP-03": ("prop", 0.04), "EXP-04": ("prop", 0.05),
    "EXP-05": ("prop", 0.05), "EXP-06": ("rate_rel", 0.50), "EXP-07": ("prop", 0.06), "EXP-08": ("rate_rel", -0.20),
    "EXP-09": ("prop", 0.06), "EXP-10": ("prop", 0.06)}
rows = []
for _, e in m7.iterrows():
    k, d = eff[e.experiment_id]
    b = float(e.baseline)
    if k == "prop":
        n = n_prop(b, d); n_half = n_prop(b, d / 2); n_150 = n_prop(b, d * 1.5)
    else:
        r1 = b * (1 + d)
        n = n_rate(b, r1) if d < 0 else n_rate(r1, b)
        n_half = n_rate(b, b * (1 + d / 2)) if d < 0 else n_rate(b * (1 + d / 2), b)
        n_150 = n_rate(b, b * (1 + d * 1.5)) if d < 0 else n_rate(b * (1 + d * 1.5), b)
    # Phase 3 used unrounded baselines; the CSV stores 4 dp, so allow 0.5% tolerance and keep Phase 3 n as authoritative
    assert abs(n - int(e.n_per_arm)) <= max(1, 0.005 * int(e.n_per_arm)), (e.experiment_id, n, e.n_per_arm)
    scale = int(e.n_per_arm) / n
    n_half = round(n_half * scale); n_150 = round(n_150 * scale); n = int(e.n_per_arm)
    per_wk = float(e.eligible_per_week)
    pool = float(e.launch_pool)
    # accrual weeks: launch pool drains first, then weekly inflow (Phase 3 convention)
    need = 2 * n
    accrual = 0 if need <= pool else math.ceil((need - pool) / per_wk) if per_wk > 0 else None
    if pool and need <= pool:
        accrual = max(1, math.ceil(need / max(per_wk, 1)))
    rows.append(dict(
        experiment_id=e.experiment_id, area=e.area, title=e.title, status="PROPOSED - NOT CONDUCTED",
        baseline=b, baseline_source=e.baseline_source, assumed_effect=e.assumed_effect,
        alpha=0.05, power=0.80, n_per_arm=n, n_total=2 * n, n_per_arm_if_effect_halved=n_half,
        n_per_arm_if_effect_1_5x=n_150, eligible_per_week=per_wk, launch_pool=int(pool),
        accrual_weeks_phase3=int(e.accrual_weeks), follow_up_weeks=int(e.follow_up_weeks),
        total_weeks_phase3=int(e.total_duration_weeks), feasibility_phase3=e.feasibility))
ep = pd.DataFrame(rows)
ep.to_csv(OUT / "p6_experiment_plan.csv", index=False)

# ------------------------------------------------------------------ friction by stage
b = pd.read_csv(T3 / "m2_bottlenecks.csv")
stuck = pd.read_csv(T3 / "m6_stuck_users_and_tickets.csv")
b = b.rename(columns={"stage": "stage_reached"})
b.to_csv(OUT / "p6_friction_by_stage.csv", index=False)

# ------------------------------------------------------------------ missing information
miss = pd.DataFrame([
    ("Revenue / brokerage fee per trade", "Not in dataset", "Cannot state revenue, ARPU, ROI or payback; all value expressed as cost per activated customer", "Finance"),
    ("Customer lifetime value (LTV) and margin", "Not in dataset", "Cannot rank channels by profit; quality proxies used (first-trade rate, M3 retention)", "Finance / Data Analytics"),
    ("Campaign spend by date", "Spend is one total per campaign", "Cannot measure marginal CAC, diminishing returns or pacing; scenarios use average cost", "Marketing"),
    ("Referral reward cost and referrer IDs", "Reward cost not separated; referrer not recorded", "Referral CAC (Rs 232) is recorded spend / registrations only; referral loop attribution is approximate", "Marketing / Product"),
    ("Organic channel cost (content, SEO)", "Organic spend blank (not zero)", "Organic CAC undefined; organic cannot be compared on cost", "Marketing"),
    ("Support cost per ticket and staffing", "Not in dataset", "Cannot cost ticket-deflection; benefit expressed as ticket volume only", "Customer Support / Finance"),
    ("KYC vendor cost per check and rejection reasons", "Not in dataset", "Cannot cost assisted KYC; cannot split drop-off by rejection vs abandonment", "Compliance / Operations"),
    ("Click and impression counts", "Not in dataset", "Cannot measure click-to-registration or landing-page conversion (needed for EXP-10)", "Marketing / Analytics"),
    ("In-app screen / event funnel", "Only stage dates are recorded", "Cannot see where inside a stage users abandon; tests must log step-level events", "Product / Analytics"),
    ("Incentive / bonus costs", "Not in dataset", "Cannot cost win-back or referral incentives", "Marketing / Finance"),
    ("Funnel flags vs activity log reconciliation", "78-98% of stalled-segment users also show activity (source conflict)", "True size of the stalled-onboarding backlog is uncertain until reconciled", "Data Analytics / Operations"),
], columns=["missing_item", "status_in_synthetic_data", "consequence_for_Phase6", "owner_to_provide"])
miss.to_csv(OUT / "p6_missing_information.csv", index=False)

# ------------------------------------------------------------------ verification
F = R["funnel"]
checks = []


def chk(name, got, want, tol=1e-6):
    ok = abs(got - want) <= tol
    checks.append(dict(check=name, phase6_value=got, source_value=want, ok=ok))
    return ok


chk("Registered users", len(U), 10000)
chk("Mature users", len(MU), 9116)
chk("Mature KYC rate", MU.kyc_asof.mean(), 0.7052, 5e-4)
chk("Mature first-trade rate", MU.trade_asof.mean(), 0.3798, 5e-4)
chk("Paid spend total", float(spend.sum()), 2690000)
chk("Blended paid CAC", float(spend.sum() / paid.registered_users.sum()), 331.2, 0.06)
chk("Referral first-trade rate", float(ch.set_index("channel").loc["Referral", "first_trade_rate"]), 0.529, 1e-3)
chk("Organic first-trade rate", float(ch.set_index("channel").loc["Organic", "first_trade_rate"]), 0.472, 1e-3)
chk("CMP05 cost per first trade", float(cpft["CMP05"]), 438, 0.6)
chk("CMP04 cost per first trade", float(cpft["CMP04"]), 1252, 0.6)
chk("Baseline paid first traders (P3)", base_traders, R["realloc"]["base_traders"])
chk("S2 net change @+0% (P3 264.55)", float(s2.net_change_first_traders.iloc[0]), 264.5516, 1e-3)
chk("S2 break-even penalty (P3 +172%)", float(s2.breakeven_penalty_pct.iloc[0]), 172.2466, 0.01)
chk("Experiments reconciled to Phase 3 n_per_arm", len(ep), 10)
v = pd.DataFrame(checks)
v.to_csv(OUT / "p6_verification.csv", index=False)
print(v.to_string(index=False))
print("ALL OK" if v.ok.all() else "FAILURES")
print(scn[["scenario", "destination_cost_penalty", "net_change_first_traders", "net_change_pct_of_paid_baseline",
           "cmp05_spend_growth_required", "cmp10_spend_growth_required", "blended_cost_per_first_trade_after_inr", "breakeven_penalty_pct"]].round(3).to_string(index=False))
print(ep[["experiment_id", "n_per_arm", "n_per_arm_if_effect_halved", "n_per_arm_if_effect_1_5x"]].to_string(index=False))
print(ch.round(3).to_string(index=False))
print("base first traders", base_traders, "blended cost per first trade", spend.sum() / base_traders)
sys.exit(0 if v.ok.all() else 1)
