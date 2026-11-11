"""Phase 6 - renders the three Markdown strategy documents from the Phase 6 evidence tables (SYNTHETIC data).

Inputs : 07_growth_strategy/tables/p6_*.csv   (written by 24_phase6_evidence.py and p6_content.py)
Outputs: 07_growth_strategy/business_recommendations.md, experiment_design.md, 30_60_90_day_roadmap.md
Run    : python3 07_growth_strategy/build_scripts/26_build_strategy_markdown.py

Every number is read from a CSV, not typed. No revenue, ROI or incremental revenue appears anywhere because the dataset has no
revenue, fee, lifetime-value or cost-to-serve field. No experiment has been run: all effects are ASSUMPTIONS used only to size tests.
"""
from pathlib import Path
import re
import sys
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
T = ROOT / "07_growth_strategy" / "tables"
sys.path.insert(0, str(HERE))
from p6_content import PLAN  # noqa: E402  (importing rewrites p6_recommendations.csv with identical content)

rec = pd.read_csv(T / "p6_recommendations.csv", keep_default_na=False)
exp = pd.read_csv(T / "p6_experiment_plan.csv")
chan = pd.read_csv(T / "p6_channel_scorecard.csv")
camp = pd.read_csv(T / "p6_campaign_scorecard.csv")
scn = pd.read_csv(T / "p6_budget_scenarios.csv")
fric = pd.read_csv(T / "p6_friction_by_stage.csv")
miss = pd.read_csv(T / "p6_missing_information.csv")
ver = pd.read_csv(T / "p6_verification.csv")

NOTICE = ("> **All data are synthetic** (a fictional Indian retail brokerage: 10,000 users, Nov 2025 - Oct 2026, INR, snapshot 2026-10-31). "
          "No revenue, ROI or lifetime value is computed because the dataset contains none of those fields. "
          "Nothing below has been tested in a real business; experiments are **proposed, not run**.\n")


def md_table(df, fmts=None):
    fmts = fmts or {}
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for r in df.itertuples(index=False):
        cells = []
        for c, v in zip(cols, r):
            if isinstance(v, float) and pd.isna(v):
                cells.append("n/a")
            elif c in fmts:
                cells.append(fmts[c](v))
            else:
                cells.append(str(v))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


pct = lambda v: f"{v * 100:.1f}%"
rs = lambda v: f"Rs {v:,.0f}"

# ============================================================== business_recommendations.md
c = chan.rename(columns={"channel": "Channel", "registrations": "Registrations", "share_of_registrations": "Share", "cac_inr": "CAC",
                         "first_trade_rate": "First-trade rate (mature)", "cost_per_first_trade_inr": "Cost per first trade", "m3_retention": "M3 retention"})
c = c[["Channel", "Registrations", "Share", "CAC", "First-trade rate (mature)", "Cost per first trade", "M3 retention"]]
chan_tbl = md_table(c, {"Registrations": lambda v: f"{v:,.0f}", "Share": pct, "CAC": rs, "First-trade rate (mature)": pct,
                        "Cost per first trade": rs, "M3 retention": pct})

f = fric.rename(columns={"stage_reached": "Last stage reached", "users_at_risk": "Users at risk", "users_lost": "Users lost", "drop_rate": "Drop rate",
                         "share_of_all_funnel_losses": "Share of all losses", "median_days": "Median days to next stage"})
fric_tbl = md_table(f[["Last stage reached", "Users at risk", "Users lost", "Drop rate", "Share of all losses", "Median days to next stage"]],
                    {"Users at risk": lambda v: f"{v:,.0f}", "Users lost": lambda v: f"{v:,.0f}", "Drop rate": pct, "Share of all losses": pct,
                     "Median days to next stage": lambda v: f"{v:.0f}"})

s = scn[scn.destination_cost_penalty == "+0%"].copy()
s["Scenario"] = s.scenario
s = s.rename(columns={"moved_budget_inr": "Budget moved", "net_change_first_traders": "Net first traders (at observed efficiency)",
                      "net_change_pct_of_paid_baseline": "% of paid first traders", "breakeven_penalty_pct": "Break-even cost penalty"})
scn_tbl = md_table(s[["Scenario", "Budget moved", "Net first traders (at observed efficiency)", "% of paid first traders", "Break-even cost penalty"]],
                   {"Budget moved": rs, "Net first traders (at observed efficiency)": lambda v: f"{v:,.0f}", "% of paid first traders": pct,
                    "Break-even cost penalty": lambda v: f"+{v:.0f}%"})

doc = [f"# Business recommendations\n", NOTICE,
       "Fifteen recommendations in four themes (Growth, Customer experience, Retention, Operations). Each has the problem, the evidence, the action, an owner, "
       "a planning estimate of resources, KPIs with baselines, a review frequency, risks and any linked experiment. Resource lines are **planning "
       "estimates, not costs from the data**. Evidence tags such as `[Phase 3 F05]` point to the finding IDs in "
       "[`phase3_findings/m8_findings.csv`](phase3_findings/m8_findings.csv).\n",
       "## Evidence base\n", "### Channel scorecard (mature cohort for rates)\n", chan_tbl,
       "\nCAC = spend / registrations. Cost per first trade = CAC / mature first-trade rate. Organic has no recorded spend, so its cost is undefined (not zero).\n",
       "### Where onboarding loses customers (mature cohort, n = 9,116)\n", fric_tbl,
       "\nSupport is the earliest sensor of this friction: tickets are raised while the related stage is still pending (see recommendation D01).\n",
       "### Budget-shift arithmetic (not a forecast)\n", scn_tbl,
       "\nThese rows apply each source campaign's *average* cost per first trade to the moved budget and assume the destination keeps its average cost. "
       "Real campaigns rarely keep average cost as spend grows, so the break-even column shows how much the destination's cost could rise before the shift stops "
       "adding first traders. The full grid (cost penalties from +0% to +150%) is in [`tables/p6_budget_scenarios.csv`](tables/p6_budget_scenarios.csv).\n",
       "## Recommendations\n"]
for theme in ["Growth", "Customer experience", "Retention", "Operations"]:
    sub = rec[rec.theme == theme]
    doc.append(f"### {theme}\n")
    doc.append(md_table(sub[["id", "priority", "window", "title", "department"]].rename(
        columns={"id": "ID", "priority": "Priority", "window": "Window", "title": "Recommendation", "department": "Owner / contributors"})) + "\n")
    for r in sub.itertuples():
        doc += [f"<details>\n<summary><b>{r.id} · {r.title}</b> ({r.priority}, {r.window})</summary>\n",
                f"* **Problem.** {r.problem}", f"* **Evidence.** {r.evidence}", f"* **Action.** {r.action}",
                f"* **Resources.** {r.resources}", f"* **KPI.** {r.kpi}", f"* **Review frequency.** {r.frequency}",
                f"* **Risks.** {r.risks}", f"* **Linked experiment.** {r.experiment}\n", "</details>\n"]
doc += ["## What the data cannot support\n", md_table(miss.rename(columns={"missing_item": "Missing item", "status_in_synthetic_data": "Status",
                                                                        "consequence_for_Phase6": "Consequence", "owner_to_provide": "Who could supply it"})),
        f"\n## Verification\n\nThe evidence tables were reconciled to the Phase 3 results with {len(ver)} checks ({int(ver.ok.sum())} pass): "
        "[`tables/p6_verification.csv`](tables/p6_verification.csv). Regenerate with `24_phase6_evidence.py`, then this script.\n"]
(ROOT / "07_growth_strategy" / "business_recommendations.md").write_text("\n".join(doc))

# ============================================================== experiment_design.md
e = exp.copy()
e["Experiment"] = e.experiment_id + " " + e.title
e = e.rename(columns={"assumed_effect": "Assumed effect", "n_per_arm": "Users per arm", "n_per_arm_if_effect_halved": "Per arm if effect halved",
                      "total_weeks_phase3": "Weeks to read out", "area": "Area"})
e["Baseline"] = [f"{b * 100:.1f}%" if b < 1 else f"{b:.3g}" for b in exp.baseline]
tbl = md_table(e[["Experiment", "Area", "Baseline", "Assumed effect", "Users per arm", "Per arm if effect halved", "Weeks to read out"]],
               {"Users per arm": lambda v: f"{v:,.0f}", "Per arm if effect halved": lambda v: f"{v:,.0f}", "Weeks to read out": lambda v: f"{v:.0f}"})
feas = md_table(exp[["experiment_id", "baseline_source", "eligible_per_week", "accrual_weeks_phase3", "follow_up_weeks", "feasibility_phase3"]].rename(
    columns={"experiment_id": "ID", "baseline_source": "Baseline source", "eligible_per_week": "Eligible per week", "accrual_weeks_phase3": "Accrual weeks",
             "follow_up_weeks": "Follow-up weeks", "feasibility_phase3": "Feasibility"}), {"Eligible per week": lambda v: f"{v:,.0f}"})
ed = [f"# Experiment design\n", NOTICE,
      "Ten A/B tests are **proposed**. **None has been run.** Baselines are actual rates from the synthetic data; every expected lift is an **assumption** "
      "chosen only to size the test. They are not forecasts.\n",
      "## Standards applied to every test\n",
      "* Two-sided test, 5% significance, 80% power, normal approximation (two proportions, or a rate comparison for count outcomes).",
      "* Random assignment of users, stratified by channel and device; analysis of all assigned users (intention to treat).",
      "* One primary KPI and at least one guardrail KPI written down **before** launch; no early stopping unless a sequential rule is written in advance.",
      "* Ship only when the confidence interval excludes zero and no guardrail is breached.",
      "* Compliance reviews KYC, consent and incentive wording before any test launches.\n",
      "## The ten tests\n", tbl,
      "\nSample sizes are very sensitive to the assumed effect: the *Per arm if effect halved* column shows how fast the requirement grows if the true lift is smaller than assumed.\n",
      "## Feasibility at observed traffic\n", feas,
      "\nTraffic is the binding constraint (about 190 registrations a week). *Weeks to read out* counts from launch. Slow tests should run concurrently, be designed as factorials where they touch the same screen, "
      "or accept a larger minimum detectable effect.\n",
      "## Linked recommendations\n",
      md_table(rec[rec.experiment.str.contains("EXP")][["id", "title", "experiment"]].rename(columns={"id": "Rec", "title": "Recommendation", "experiment": "Experiment(s)"})),
      "\nThe full machine-readable plan is [`tables/p6_experiment_plan.csv`](tables/p6_experiment_plan.csv); the earlier Phase 3 design with the power grid is in "
      "[`phase3_experiments/`](phase3_experiments/).\n"]
(ROOT / "07_growth_strategy" / "experiment_design.md").write_text("\n".join(ed))

# ============================================================== 30_60_90_day_roadmap.md
rd = [f"# 30-60-90 day roadmap\n", NOTICE,
      "The plan sequences the fifteen recommendations: **Foundation** (fix measurement and the biggest known leaks), **Pilot** (run the first tests where pools already exist), "
      "**Scale and decide** (act on read-outs, slower tests, retention protection). Resource lines are planning estimates.\n"]
for window, ids in PLAN.items():
    sub = rec.set_index("id").loc[ids].reset_index()
    rd.append(f"## {window}\n")
    rd.append(md_table(sub[["id", "priority", "title", "department", "kpi"]].rename(
        columns={"id": "ID", "priority": "Priority", "title": "Action", "department": "Owner / contributors", "kpi": "KPI (baseline)"})) + "\n")
    ids_ = sorted(set(re.findall(r"EXP-\d+", " ".join(sub.experiment.astype(str)))))
    rd.append("**Linked experiments:** " + (", ".join(ids_) if ids_ else "none") + "\n")
rd += ["## Decision gates\n",
       "* **Day 30:** the data foundation (B06) is reconciled enough to trust segment sizes; campaign scorecard (A01) is live; the experiment review board (D01) exists.",
       "* **Day 60:** pilots have pre-registered plans and Compliance sign-off; the ageing backlog (B05) is being worked.",
       "* **Day 90:** go / no-go on each pilot from its pre-set rule; the budget shift (A02) proceeds to its second stage only if the destination cost per first trade stays within the agreed limit.\n",
       "Pilots start in Days 31-60, so only EXP-02 fully reads out by Day 90 and EXP-09 about Day 93; the Day 90 gate is judged on leading indicators plus those two reads. The other tests are started, not concluded (see the feasibility table in [`experiment_design.md`](experiment_design.md)).\n"]
(ROOT / "07_growth_strategy" / "30_60_90_day_roadmap.md").write_text("\n".join(rd))
print("wrote business_recommendations.md, experiment_design.md, 30_60_90_day_roadmap.md")
