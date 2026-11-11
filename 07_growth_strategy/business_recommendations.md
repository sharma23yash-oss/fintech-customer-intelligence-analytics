# Business recommendations

> **All data are synthetic** (a fictional Indian retail brokerage: 10,000 users, Nov 2025 - Oct 2026, INR, snapshot 2026-10-31). No revenue, ROI or lifetime value is computed because the dataset contains none of those fields. Nothing below has been tested in a real business; experiments are **proposed, not run**.

Fifteen recommendations in four themes (Growth, Customer experience, Retention, Operations). Each has the problem, the evidence, the action, an owner, a planning estimate of resources, KPIs with baselines, a review frequency, risks and any linked experiment. Resource lines are **planning estimates, not costs from the data**. Evidence tags such as `[Phase 3 F05]` point to the finding IDs in [`phase3_findings/m8_findings.csv`](phase3_findings/m8_findings.csv).

## Evidence base

### Channel scorecard (mature cohort for rates)

| Channel | Registrations | Share | CAC | First-trade rate (mature) | Cost per first trade | M3 retention |
|---|---|---|---|---|---|---|
| Referral | 1,036 | 10.4% | Rs 232 | 52.9% | Rs 438 | 61.2% |
| Organic | 1,878 | 18.8% | n/a | 47.2% | n/a | 60.4% |
| Paid Search | 2,644 | 26.4% | Rs 390 | 36.6% | Rs 1,065 | 54.6% |
| CRM | 561 | 5.6% | Rs 160 | 34.0% | Rs 472 | 56.0% |
| Affiliate | 757 | 7.6% | Rs 410 | 33.7% | Rs 1,216 | 54.4% |
| Partnerships | 580 | 5.8% | Rs 328 | 31.1% | Rs 1,052 | 50.8% |
| Paid Social | 2,544 | 25.4% | Rs 326 | 30.3% | Rs 1,075 | 54.1% |

CAC = spend / registrations. Cost per first trade = CAC / mature first-trade rate. Organic has no recorded spend, so its cost is undefined (not zero).

### Where onboarding loses customers (mature cohort, n = 9,116)

| Last stage reached | Users at risk | Users lost | Drop rate | Share of all losses | Median days to next stage |
|---|---|---|---|---|---|
| KYC Completed | 9,116 | 2,687 | 29.5% | 42.6% | 6 |
| Bank Linked | 6,429 | 784 | 12.2% | 12.4% | 4 |
| First Deposit | 5,645 | 1,305 | 23.1% | 20.7% | 7 |
| First Trade | 4,340 | 878 | 20.2% | 13.9% | 6 |
| Active (30d) | 3,462 | 654 | 18.9% | 10.4% | n/a |

Support is the earliest sensor of this friction: tickets are raised while the related stage is still pending (see recommendation D01).

### Budget-shift arithmetic (not a forecast)

| Scenario | Budget moved | Net first traders (at observed efficiency) | % of paid first traders | Break-even cost penalty |
|---|---|---|---|---|
| S1 Stage 1: move 10% of CMP04+CMP06 to CMP05+CMP10 | Rs 76,000 | 106 | 3.6% | +172% |
| S2 Stage 2: move 25% of CMP04+CMP06 to CMP05+CMP10 | Rs 190,000 | 265 | 9.1% | +172% |
| S3 Tier-C sweep: move 15% of CMP04+CMP06+CMP09 to CMP05+CMP10 | Rs 142,500 | 194 | 6.7% | +163% |

These rows apply each source campaign's *average* cost per first trade to the moved budget and assume the destination keeps its average cost. Real campaigns rarely keep average cost as spend grows, so the break-even column shows how much the destination's cost could rise before the shift stops adding first traders. The full grid (cost penalties from +0% to +150%) is in [`tables/p6_budget_scenarios.csv`](tables/p6_budget_scenarios.csv).

## Recommendations

### Growth

| ID | Priority | Window | Recommendation | Owner / contributors |
|---|---|---|---|---|
| A01 | P1 | Days 1-30 | Make cost per first trade the headline campaign KPI | Marketing (owner); Data Analytics |
| A02 | P1 | Days 31-90 | Stage the shift of budget from the weakest to the strongest paid campaigns | Marketing (owner); Finance (approves); Data Analytics |
| A03 | P1 | Days 31-90 | Scale referral with a prompt at the first-trade moment | Product (owner); Marketing; Compliance (reward terms) |
| A04 | P2 | Days 61-90 | Put Video Awareness (CMP04) and Finance Affiliate (CMP06) on improvement plans | Marketing (owner); Partnerships; Data Analytics |
| A05 | P3 | Days 61-90 | Make organic a tracked, costed channel | Marketing (owner); Finance |

<details>
<summary><b>A01 · Make cost per first trade the headline campaign KPI</b> (P1, Days 1-30)</summary>

* **Problem.** Budget reviews rank campaigns on CAC, which ignores whether the customer ever trades.
* **Evidence.** CMP04 CAC (Rs 385) is below CMP02 (Rs 393) yet its cost per first trade is Rs 1,252 vs Rs 1,051 (+19%). First-trade rate ranges from 30.3% (Paid Social) to 52.9% (Referral). [Phase 3 F05, F07]
* **Action.** Publish one monthly campaign scorecard: cost per first trade (spend / registrations / mature first-trade rate), CAC, cost per KYC, M3 retention by channel. Reuse the Phase 5 Power BI measures.
* **Resources.** Planning estimate: about 1 analyst-week; no media spend.
* **KPI.** Share of paid budget reviewed on cost per first trade (target 100%); blended paid cost per first trade (baseline Rs 923)
* **Review frequency.** Monthly
* **Risks.** Newest cohorts are immature (Oct-26 cohort excluded), so use 60-90 day cohort windows. A single metric can be gamed; keep M3 retention beside it.
* **Linked experiment.** -

</details>

<details>
<summary><b>A02 · Stage the shift of budget from the weakest to the strongest paid campaigns</b> (P1, Days 31-90)</summary>

* **Problem.** 28% of paid spend (CMP04 Rs 450,000 + CMP06 Rs 310,000 = Rs 760,000 of Rs 2.69M) buys first traders at Rs 1,216-1,252 each vs Rs 438-472 for CMP05 and CMP10.
* **Evidence.** Arithmetic at observed efficiency: moving 10% (Rs 76,000) adds about 106 first traders (+3.6%); 25% adds about 265 (+9.1%); break-even only if destination cost rises about 172%. The 25% step needs CMP10 spend to roughly double (+106%), so capacity is the binding risk. [p6_budget_scenarios.csv, Phase 3 F08]
* **Action.** Stage 1: move 10% in two weekly tranches. Re-measure marginal cost per first trade per campaign. Stage 2 (25%) only if destination cost stays within +50% of observed. Bias the shift to CMP05 where capacity allows.
* **Resources.** Budget-neutral. Needs spend logged by date (not in the dataset today).
* **KPI.** Marginal cost per first trade of destination campaigns (decision rule: at most Rs 682, i.e. +50% on the observed Rs 454); blended paid cost per first trade
* **Review frequency.** Weekly during the shift; monthly after
* **Risks.** Diminishing returns. Referral volume depends on the active base. CMP06 gap is not significant after correction (Holm p=0.061), so it is the weaker case; CMP04 is significant (p<0.001). Campaign differences are associations, not causal.
* **Linked experiment.** -

</details>

<details>
<summary><b>A03 · Scale referral with a prompt at the first-trade moment</b> (P1, Days 31-90)</summary>

* **Problem.** The highest-quality channel supplies only 10.4% of registrations.
* **Evidence.** Referral: first-trade rate 52.9%, M3 retention 61.2%, 3-month dormancy 15.5%, CAC Rs 232. Referral registrations run at about 2.95 per 100 active users per month (approximate; referrer IDs are not recorded). [Phase 3 F05, F10]
* **Action.** Run EXP-06: share sheet and invite prompt after a user's first trade; reward structure identical in both arms. Track quality of referred users.
* **Resources.** Planning estimate: 1 designer and 1 engineer for 2-3 weeks.
* **KPI.** Referred registrations per 100 exposed users in 30 days (baseline 2.95); guardrail: first-trade rate of referred cohort stays at or above 45%
* **Review frequency.** Weekly in test; monthly after
* **Risks.** Referral abuse and duplicate accounts; reward cost not in the data; incentive rules need Compliance review.
* **Linked experiment.** EXP-06

</details>

<details>
<summary><b>A04 · Put Video Awareness (CMP04) and Finance Affiliate (CMP06) on improvement plans</b> (P2, Days 61-90)</summary>

* **Problem.** Paid Social is 25.4% of registrations but has the lowest first-trade rate (30.3%).
* **Evidence.** CMP04 first-trade rate 30.8%, cost per first trade Rs 1,252 (significantly below the rest, Holm p<0.001). CMP06 cost per first trade Rs 1,216 but not significant after correction (p=0.061). [Phase 3 F07]
* **Action.** CMP04: pre-qualification page before sign-up (EXP-10, with click logging). CMP06: renegotiate payout toward qualified first trades once 90 days of dated data exist.
* **Resources.** Planning estimate: 1 landing-page build; partner negotiation time.
* **KPI.** First trades per 1,000 clicks (not per registrant); guardrail: CAC rises no more than 20%
* **Review frequency.** Fortnightly in test
* **Risks.** Lower registration volume can be mistaken for quality gain; click counts are not in the data and must be logged first; partner pushback.
* **Linked experiment.** EXP-10

</details>

<details>
<summary><b>A05 · Make organic a tracked, costed channel</b> (P3, Days 61-90)</summary>

* **Problem.** Organic delivers 18.8% of registrations and the second-best first-trade rate, but its cost is blank in the data.
* **Evidence.** Organic first-trade rate 47.2% vs 35.8% for paid; 30-day active 62.7% vs 52.0%. Organic CAC is undefined, not zero. [Phase 3 F06]
* **Action.** Record content and SEO cost separately; set up two content series aimed at the question new users stall on (KYC documents, first deposit amount); judge by first-trade rate and share of registrations.
* **Resources.** Planning estimate: content time already in the team; cost to be logged.
* **KPI.** Organic share of registrations (baseline 18.8%); organic first-trade rate (baseline 47.2%)
* **Review frequency.** Monthly
* **Risks.** Attribution is weak; effect takes months; cost unknown.
* **Linked experiment.** -

</details>

### Customer experience

| ID | Priority | Window | Recommendation | Owner / contributors |
|---|---|---|---|---|
| B01 | P1 | Days 1-90 | Fix the KYC step: checklist, status tracker and assisted KYC | Product (owner); Compliance (rules, vendor); Customer Support; Marketing CRM (reminders); Data Analytics |
| B02 | P3 | Days 61-90 | Offer UPI-first bank linking with a one-tap fallback | Product (owner); Compliance; Customer Support |
| B03 | P2 | Days 31-90 | Reduce first-deposit hesitation with quick-amount chips and reminders | Product (owner); CRM; Compliance |
| B04 | P2 | Days 31-90 | Convert funded-but-untraded users with a guided first trade | Product (owner); CRM; Compliance (practice-order disclosures) |
| B05 | P1 | Days 1-60 | Make support priority real and clear the ageing backlog | Customer Support (owner); Operations; Product (top ticket drivers) |
| B06 | P1 | Days 1-30 | Fix the data foundation: reconcile flags, log step events, spend and clicks | Data Analytics (owner); Engineering; Operations |

<details>
<summary><b>B01 · Fix the KYC step: checklist, status tracker and assisted KYC</b> (P1, Days 1-90)</summary>

* **Problem.** KYC is the largest leak: 29.5% of registrants do not complete it (2,687 users; 42.6% of all funnel losses). Median time to KYC is 6 days (p75 9).
* **Evidence.** KYC is also the largest ticket category (1,727 tickets, 22.7%); 43% of onboarding tickets about KYC are raised while KYC is still pending. Ticket raisers complete KYC at 7.5% vs 74.9% for non-raisers (association only). [Phase 3 F01, F02, F13]
* **Action.** EXP-01: document checklist, photo-quality check, resume reminders on day 2 and day 5. EXP-08: in-flow status tracker with inline rejection reasons. EXP-02: assisted-KYC offer for applicants pending beyond day 11, after the funnel flags are reconciled with the activity log.
* **Resources.** Planning estimate: 2 engineers and 1 designer for 4-6 weeks; Compliance review of copy and consent.
* **KPI.** Registration to KYC within 14 days (baseline 70.5% final completion); KYC tickets per registrant (baseline 0.173)
* **Review frequency.** Weekly in test
* **Risks.** KYC rigour must not be weakened (guardrail: rejection and fraud flags). Outreach needs consent. About 91% of the stalled KYC group shows source conflict, so the backlog size is uncertain.
* **Linked experiment.** EXP-01, EXP-02, EXP-08

</details>

<details>
<summary><b>B02 · Offer UPI-first bank linking with a one-tap fallback</b> (P3, Days 61-90)</summary>

* **Problem.** 12.2% of KYC-complete users never link a bank (784 users).
* **Evidence.** Bank linking is the smallest bottleneck by users lost (12.4% of funnel losses); bank-link tickets are 1,246 (16.4%). [Phase 3 F03, F13]
* **Action.** EXP-03: default to UPI-first linking; on failure show the alternate method on the same screen.
* **Resources.** Planning estimate: 1 engineer for 3 weeks plus bank-partner confirmation.
* **KPI.** Bank linked within 7 days of KYC (baseline 87.8%)
* **Review frequency.** Weekly in test
* **Risks.** Small volume benefit; fraud or mismatch flags; partner constraints.
* **Linked experiment.** EXP-03

</details>

<details>
<summary><b>B03 · Reduce first-deposit hesitation with quick-amount chips and reminders</b> (P2, Days 31-90)</summary>

* **Problem.** 23.1% of bank-linked users never fund the account (1,305 users, the second-largest leak).
* **Evidence.** Median first deposit is about Rs 6,400-6,500; deposit-pending is 13.3% of customers by journey segment. 13.8% of mature users who never deposited raised a related ticket. [Phase 3 F03, m4, m6]
* **Action.** EXP-04: chips anchored to observed amounts (for example Rs 2,000 / 5,000 / 10,000) and reminders on day 3 and day 7.
* **Resources.** Planning estimate: 1 engineer and 1 designer for 2-3 weeks.
* **KPI.** First deposit within 14 days of bank link (baseline 76.9%)
* **Review frequency.** Weekly in test
* **Risks.** Low-intent small deposits; guardrail is the withdrawal-to-deposit ratio (baseline 0.41) and opt-out rate.
* **Linked experiment.** EXP-04

</details>

<details>
<summary><b>B04 · Convert funded-but-untraded users with a guided first trade</b> (P2, Days 31-90)</summary>

* **Problem.** 20.2% of funded users never place a trade (878 mature users); 881 sit in the deposited-never-traded segment.
* **Evidence.** Deposit to first trade converts at 79.8%; median 6 days. Early trading (months 0-1) is associated with M3 retention of 60.7% vs 50.0% (association, not causal). [Phase 3 F03, F11]
* **Action.** EXP-05: walkthrough card, practice (paper) order, reminders on day 2 and day 5.
* **Resources.** Planning estimate: 1 engineer and 1 designer for 3-4 weeks.
* **KPI.** First trade within 14 days of deposit (baseline 79.8%)
* **Review frequency.** Weekly in test
* **Risks.** Hollow activation (tiny trades); guardrail: share of first trades under Rs 500 and order-error rate.
* **Linked experiment.** EXP-05

</details>

<details>
<summary><b>B05 · Make support priority real and clear the ageing backlog</b> (P1, Days 1-60)</summary>

* **Problem.** Priority does not change service: median resolution is 9.4-9.5 hours for High, Medium and Low alike. 563 unresolved tickets are older than 90 days.
* **Evidence.** 7,614 tickets (761 per 1,000 customers); 892 open; 479 escalated; High priority is 15.4% of tickets; Kruskal-Wallis p=0.59. Onboarding categories (KYC, bank, deposits) are 54.8% of tickets. Tickets per 1,000 customer-months rose from 36 (Nov-25) to 134 (Sep-26) and 218 (Oct-26). [Phase 3 F13, F14]
* **Action.** Define SLA tiers by priority with routing; weekly ageing review; clear the over-90-day backlog; trigger a proactive follow-up on open onboarding tickets older than 24 hours.
* **Resources.** Planning estimate: backlog sprint by existing agents for 2-3 weeks; staffing and cost per ticket are not in the data.
* **KPI.** Open tickets older than 90 days (baseline 563; proposed target 0 by Day 60); median resolution High vs Low (proposed: High at least 25% faster)
* **Review frequency.** Weekly
* **Risks.** Closing tickets without resolving them (guardrail: reopen rate and CSAT, baseline 3.83); the Oct-26 volume spike should be validated before staffing decisions.
* **Linked experiment.** -

</details>

<details>
<summary><b>B06 · Fix the data foundation: reconcile flags, log step events, spend and clicks</b> (P1, Days 1-30)</summary>

* **Problem.** Funnel flags disagree with the activity log: 91-98% of users in the stalled segments also show activity, so the true onboarding backlog is unknown. Spend, clicks and in-app steps are not logged at the grain tests need.
* **Evidence.** Source-conflict share by stalled segment: KYC-pending 91.2%, bank-pending 92.7%, deposit-pending 93.2%, deposited-never-traded 97.8%. Spend exists only as one total per campaign. [Phase 3 F12, m4]
* **Action.** Agree a source-of-truth rule; log step-level KYC, bank, deposit and trade events; log spend by date and click counts; add stage-lag KPIs (median registration to first trade 23 days, p75 28).
* **Resources.** Planning estimate: 1 data engineer for 3-4 weeks.
* **KPI.** Share of stalled-segment users with an unresolved source conflict (baseline 91-98%; proposed target under 5%); median days registration to first trade
* **Review frequency.** Monthly
* **Risks.** Engineering capacity; privacy review of new event logs.
* **Linked experiment.** Enabler for all

</details>

### Retention

| ID | Priority | Window | Recommendation | Owner / contributors |
|---|---|---|---|---|
| C01 | P2 | Days 31-90 | Build onboarding around an early first-trade milestone | Marketing CRM (owner); Product; Compliance (communication rules) |
| C02 | P2 | Days 31-90 | Run a value-led win-back sequence with a holdout | Marketing CRM (owner); Compliance; Finance (incentive cost) |
| C03 | P3 | Days 61-90 | Protect repeat and high-engagement traders | Product; Customer Support; Marketing CRM |

<details>
<summary><b>C01 · Build onboarding around an early first-trade milestone</b> (P2, Days 31-90)</summary>

* **Problem.** Retention decays steadily: M1 67.6%, M3 56.0%, M6 40.7%.
* **Evidence.** M3 retention is 60.7% for users who traded in months 0-1 vs 50.0% for those who did not; 49.9% for users without KYC in 14 days vs 58.6% with it. Early deposit alone shows no difference. The early-warning model is weak (AUC 0.57), so risk-score targeting is not proposed. [Phase 3 F09, F11]
* **Action.** Day-based reminders at each stage; EXP-07: contextual habit nudges on day 7, 14 and 21 after the first trade.
* **Resources.** Planning estimate: CRM journey build of 2-3 weeks.
* **KPI.** Share of new users who trade in months 0-1 (baseline 56.3% of the eligible base); M1 and M3 retention
* **Review frequency.** Monthly
* **Risks.** Opt-out and notification fatigue; association not proven causal; long follow-up (EXP-07 is 40 weeks as scoped).
* **Linked experiment.** EXP-07

</details>

<details>
<summary><b>C02 · Run a value-led win-back sequence with a holdout</b> (P2, Days 31-90)</summary>

* **Problem.** 21.95% of eligible users are dormant for the last 3 months (a pool of 1,632 mature users); a further 19.2% have been inactive for 31-60 days.
* **Evidence.** Inactivity of 31-60 days 19.2%, 61-90 days 14.6%, 91-120 days 12.2% of eligible users. Reactivation base rate is 34.7% (high for a dormant group; treat cautiously). [Phase 3 F09, m3]
* **Action.** EXP-09: three touches seven days apart (product updates, a learning resource), with a no-contact holdout; test value-led message vs a small incentive only if Finance supplies the incentive cost.
* **Resources.** Planning estimate: 1 CRM journey; incentive budget not defined.
* **KPI.** Reactivation in 30 days after last touch (baseline 34.7%); guardrail: unsubscribe rate and trading in the following month
* **Review frequency.** Fortnightly in test
* **Risks.** Empty logins without trading; unsubscribes; incentive cost unknown.
* **Linked experiment.** EXP-09

</details>

<details>
<summary><b>C03 · Protect repeat and high-engagement traders</b> (P3, Days 61-90)</summary>

* **Problem.** Repeat traders (16.8%) and high-engagement traders (9.0%) are about a quarter of customers and carry the highest trading value.
* **Evidence.** Average 6-month trading value is about Rs 36,700 for repeat and Rs 61,200 for high-engagement customers vs Rs 13,700 for occasional traders. Repeat traders are 69.3% of traders overall and 80.4% for referral. [Phase 3 m3, m4]
* **Action.** No discounting. Route them to the fastest support tier, add a referral prompt, and run a quarterly feedback panel; watch migration between segments 07, 08 and 09.
* **Resources.** Planning estimate: absorbed in A03, B05 and the CRM journey.
* **KPI.** Repeat-trader share of traders (baseline 69.3%); monthly migration from segment 08 to 09
* **Review frequency.** Monthly
* **Risks.** Over-contacting the best customers; segments overlap with the unreconciled flags.
* **Linked experiment.** EXP-06

</details>

### Operations

| ID | Priority | Window | Recommendation | Owner / contributors |
|---|---|---|---|---|
| D01 | P1 | Days 1-30 | Stand up a growth operating cadence and an experiment review board | Data Analytics (owner); all functions |

<details>
<summary><b>D01 · Stand up a growth operating cadence and an experiment review board</b> (P1, Days 1-30)</summary>

* **Problem.** Marketing, Product, Support, Compliance and Analytics each see one part of the funnel; no routine joins campaign cost, onboarding friction and ticket themes.
* **Evidence.** Onboarding tickets are raised while the related stage is still pending (KYC 43%, bank 54%, deposit 70%, first trade 78%), so support is the earliest signal of product friction. [Phase 3 m6]
* **Action.** Weekly growth-ops review (funnel, tickets, tests); monthly campaign review; quarterly planning. Experiments need a pre-registered plan, Compliance sign-off and a named decision owner before launch.
* **Resources.** Planning estimate: 1 hour per week per function; 1 coordinator.
* **KPI.** Experiments with a pre-registered plan (target 100%); days from idea to decision; closed-loop feedback items resolved
* **Review frequency.** Weekly / monthly
* **Risks.** Meeting overhead; the board becomes a bottleneck.
* **Linked experiment.** All

</details>

## What the data cannot support

| Missing item | Status | Consequence | Who could supply it |
|---|---|---|---|
| Revenue / brokerage fee per trade | Not in dataset | Cannot state revenue, ARPU, ROI or payback; all value expressed as cost per activated customer | Finance |
| Customer lifetime value (LTV) and margin | Not in dataset | Cannot rank channels by profit; quality proxies used (first-trade rate, M3 retention) | Finance / Data Analytics |
| Campaign spend by date | Spend is one total per campaign | Cannot measure marginal CAC, diminishing returns or pacing; scenarios use average cost | Marketing |
| Referral reward cost and referrer IDs | Reward cost not separated; referrer not recorded | Referral CAC (Rs 232) is recorded spend / registrations only; referral loop attribution is approximate | Marketing / Product |
| Organic channel cost (content, SEO) | Organic spend blank (not zero) | Organic CAC undefined; organic cannot be compared on cost | Marketing |
| Support cost per ticket and staffing | Not in dataset | Cannot cost ticket-deflection; benefit expressed as ticket volume only | Customer Support / Finance |
| KYC vendor cost per check and rejection reasons | Not in dataset | Cannot cost assisted KYC; cannot split drop-off by rejection vs abandonment | Compliance / Operations |
| Click and impression counts | Not in dataset | Cannot measure click-to-registration or landing-page conversion (needed for EXP-10) | Marketing / Analytics |
| In-app screen / event funnel | Only stage dates are recorded | Cannot see where inside a stage users abandon; tests must log step-level events | Product / Analytics |
| Incentive / bonus costs | Not in dataset | Cannot cost win-back or referral incentives | Marketing / Finance |
| Funnel flags vs activity log reconciliation | 78-98% of stalled-segment users also show activity (source conflict) | True size of the stalled-onboarding backlog is uncertain until reconciled | Data Analytics / Operations |

## Verification

The evidence tables were reconciled to the Phase 3 results with 14 checks (14 pass): [`tables/p6_verification.csv`](tables/p6_verification.csv). Regenerate with `24_phase6_evidence.py`, then this script.
