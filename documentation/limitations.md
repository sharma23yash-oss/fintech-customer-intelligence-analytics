# Limitations

This page lists what the project does **not** show and what has **not** been done. It is meant to be read before any number is quoted.

## 1. The data are synthetic

* All records describe a fictional Indian retail brokerage. No real customer, broker or market data is used, and nothing here represents Groww, Zerodha, moomoo, Futu or any other company.
* Patterns in synthetic data reflect how it was generated. Findings show that the *method* works, not that any real business behaves this way.
* Several relationships are weak or absent by construction (for example, resolution time barely relates to CSAT, r = 0.02; priority does not change resolution time, Kruskal–Wallis p = 0.59). They are reported as found, not forced into a story.

## 2. What the dataset cannot support

| Missing | Consequence |
|---|---|
| Revenue, brokerage fees, interest income, lifetime value, cost to serve | **No revenue, ROI, payback or profit is calculated anywhere.** "Cost per first trade" is a cost-efficiency measure, not a return |
| Dated marketing spend, impressions, clicks | Spend cannot be allocated by month; funnel-before-registration analysis is impossible |
| Confirmed churn (account closure, transfer-out, zero balance) | Inactivity and dormancy are **proxies** |
| Step-level event log | Funnel timing relies on single dates per stage |
| Ticket-to-funnel-stage link | Support friction is associated with onboarding, not attributed to a stage |
| Consent and compliance fields | Nothing here establishes that any outreach is permissible |

The eleven data gaps are listed in [`../07_growth_strategy/tables/p6_missing_information.csv`](../07_growth_strategy/tables/p6_missing_information.csv).

## 3. Data-quality caveats

* The monthly activity log **conflicts with the funnel record** for a large share of users (flagged, not corrected). This is the main reason 66 % of customers flagged by the AI Friction Detector are marked low data confidence.
* `last_active_date` is truncated and unreliable; the cleaned data uses an adjusted version and keeps the original column.
* 388 users from the October 2026 cohort had completion flags that included events after the snapshot; an as-of version was created.
* Ticket resolution time and CSAT exist only for resolved tickets (survivorship).
* Full list: [`data_quality_report.md`](data_quality_report.md), [`../01_data_audit/data_audit_report.md`](../01_data_audit/data_audit_report.md).

## 4. Analytical limits

* **Association, not causation.** Campaign, channel and segment differences are observational. Referral's higher first-trade rate may reflect who gets referred.
* **Proxies.** Retention uses a calendar-month definition; "Inactive 90d" and "Dormant 3m" are not churn.
* **Weak prediction.** The early-warning model reaches AUC 0.57 (cross-validated 0.57, temporal test 0.58); it is reported as weak and not used for decisions.
* **Budget scenarios are arithmetic.** They assume the destination campaign keeps its average cost as spend grows; the break-even column shows how fragile that is.
* **Experiments are proposed, not run.** Baselines are actual rates; the expected lifts are assumptions used only to size tests. With about 190 registrations a week most tests need many weeks.
* **Replay is approximate.** The Friction Detector's daily history was reconstructed by replaying the same data for earlier dates.
* **The Friction Detector priority score is a heuristic**, not a probability, and the "AI" layer is rule-based text with an optional LLM re-wording step that has **not been exercised against a live model**.

## 5. Deliverables that do not exist

| Item | Status |
|---|---|
| Power BI `.pbix` | **Not built.** Power BI Desktop was unavailable. A build kit (data, 117 DAX measures, Power Query, themes, specifications) and matplotlib mockups exist |
| Power BI screenshots | None. The mockups are labelled as mockups |
| DAX / Power Query execution | Never run in Power BI. DAX logic was checked with a pandas re-implementation (231 of 231 comparisons; 87 of 117 measures directly) |
| TMDL semantic-model scaffold | Untested |
| Phase 6 slide deck and in-app documents | Existed only inside the original app session; the Markdown strategy documents carry the same content |
| Live LLM call in the Friction Detector | Untested |
| macOS run | Everything was built and tested on Linux; not run on macOS |
| Excel workbooks regenerated after folder renames | Committed as built; some descriptive text inside uses earlier folder names (mapping in [`../03_business_analytics/README.md`](../03_business_analytics/README.md)) |

## 6. Scope

This is an analytics portfolio project. It is not an official project of any company, not investment advice, and not a production system.
