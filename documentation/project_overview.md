# Project overview (one page for reviewers)

**Fintech Brokerage Customer Intelligence & Growth Analytics** is an end-to-end analytics portfolio project on a **fully synthetic** dataset: a fictional Indian retail brokerage with 10,000 users (Nov 2025 – Oct 2026, INR, snapshot 2026-10-31). It is not an official or company project and uses no real customer data.

## The business question

The brokerage acquires thousands of registrations but only about four in ten new users make a first trade. Where does onboarding lose people, which acquisition spend produces traders rather than sign-ups, who stays active, and what should the team do first?

## What was done

| Area | Output |
|---|---|
| Data audit and cleaning | 8 audit findings, 13 logged cleaning changes, data dictionary, data-quality report |
| Analytics | Funnel, acquisition, campaigns, retention/cohorts, segmentation, support operations |
| Tools | SQL (34 queries), Python (package, pipeline, 5 notebooks), Excel (live formulas) – cross-checked, 71 of 71 KPIs agree |
| BI | Power BI build kit: star schema, 117 DAX measures, Power Query, themes, design mockups (**no .pbix**) |
| Strategy | 15 recommendations, 10 proposed experiments, 30-60-90 roadmap, budget scenarios |
| Prototype | AI Friction Detector: rule engine, priority score, daily exception report, Streamlit app |

## Findings that matter (synthetic data)

* **KYC is the largest leak**: 42.6 % of all funnel losses; step conversion 70.5 %. Only 38.0 % of the 9,116 mature users reach a first trade.
* **Channel quality differs more than channel cost**: referral converts 52.9 % to first trade at Rs 438 per first trade, against roughly Rs 920–1,250 for most paid campaigns (blended paid ≈ Rs 923; the CRM email campaign is the exception at Rs 472).
* **Retention decays steadily**: M1 / M3 / M6 = 67.6 / 56.0 / 40.7 %; 22.0 % of mature users are dormant for three months (a proxy).
* **Support demand is concentrated in onboarding topics**: KYC and verification is the largest ticket category (22.7 %); 1,371 tickets are unresolved, 563 older than 90 days.
* **Early-warning prediction does not work here** (AUC 0.57) – reported honestly.

## What it deliberately does not claim

No revenue, ROI or lifetime value (the data has none); no confirmed churn; no experiment results (all 10 are proposed); no Power BI dashboard (kit and mockups only). See [`limitations.md`](limitations.md).

## Where to start

| If you have… | Read |
|---|---|
| 3 minutes | The main [`README`](../README.md) |
| 10 minutes | [`../reports/final_project_report.md`](../reports/final_project_report.md) |
| 30 minutes | [`methodology.md`](methodology.md), [`KPI_definitions.md`](KPI_definitions.md), [`../07_growth_strategy/business_recommendations.md`](../07_growth_strategy/business_recommendations.md) |
| To run something | [`../08_ai_friction_detector/README.md`](../08_ai_friction_detector/README.md) or [`../05_python/README.md`](../05_python/README.md) |
