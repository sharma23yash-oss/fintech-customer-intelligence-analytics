# 07 · Growth strategy and operational optimisation

> **Synthetic data only.** Everything here is built on a fictional Indian retail brokerage (10,000 users, Nov 2025 – Oct 2026, INR, snapshot 2026-10-31). It is not data from any real broker.
> **No experiment has been run.** **No revenue, ROI or incremental revenue is computed**: the dataset has no revenue, fee, lifetime-value or cost-to-serve fields.

## Read these first

| Document | What it is |
|---|---|
| [`business_recommendations.md`](business_recommendations.md) | 15 recommendations (Growth, Customer experience, Retention, Operations) with problem, evidence, action, owner, KPI, risks; channel scorecard; budget-shift arithmetic; data gaps |
| [`experiment_design.md`](experiment_design.md) | 10 proposed A/B tests (EXP-01 to EXP-10): baselines are actual, lifts are assumptions, sample-size sensitivity, feasibility at observed traffic |
| [`30_60_90_day_roadmap.md`](30_60_90_day_roadmap.md) | The 15 recommendations sequenced into Foundation, Pilot, Scale and decide, with decision gates |

These three files are **generated from the evidence tables** in [`tables/`](tables/); no number is typed by hand.

## Evidence tables (`tables/`)

| File | Content |
|---|---|
| `p6_channel_scorecard.csv`, `p6_campaign_scorecard.csv` | Channel and campaign CAC, first-trade rate, cost per first trade |
| `p6_budget_scenarios.csv` | S1/S2/S3 budget shifts × destination cost penalties (+0 % to +150 %); arithmetic at observed efficiency, not a forecast |
| `p6_friction_by_stage.csv` | Funnel friction by stage (mature cohort) |
| `p6_experiment_plan.csv` | Ten proposed experiments, sample sizes, sensitivity, feasibility |
| `p6_recommendations.csv` | The fifteen recommendations in full |
| `p6_missing_information.csv` | Eleven data gaps that block any ROI statement |
| `p6_verification.csv` | 14 reconciliation checks against the Phase 3 results (all pass) |

`phase3_findings/` and `phase3_experiments/` hold the earlier Phase 3 findings, prioritisation and experiment/power-grid tables that the evidence builds on.

## Rebuild

From the repository root:

```bash
python3 07_growth_strategy/build_scripts/24_phase6_evidence.py      # evidence tables + 14 checks
python3 07_growth_strategy/build_scripts/26_build_strategy_markdown.py   # the three Markdown documents
```

`p6_content.py` holds the recommendation text and the 30-60-90 grouping (importing it rewrites `p6_recommendations.csv` with identical content).
`25_phase6_build_deck.py` generated the source files for a 12-slide management deck; it is kept for completeness and needs Node, so it is not part of the normal rebuild.

## What exists only in the original app session

The original Phase 6 deliverables (a report, action plan, campaign framework, customer-experience plan, executive summary, an experiment-tracker sheet and a 12-slide deck) were produced as in-app documents, not files. They are **not part of this repository**. The Markdown documents above carry the same content and numbers.

## Key limits

* Cost per first trade uses recorded marketing spend only; organic has no spend, so its cost is undefined.
* Inactivity and dormancy are proxies, not churn.
* Assumed lifts size the tests; they are not predictions.
* Traffic is about 190 registrations a week, so most tests need many weeks; with pilots starting in Days 31–60, only EXP-02 fully reads out by Day 90 and EXP-09 about Day 93.
