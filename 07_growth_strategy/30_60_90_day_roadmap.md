# 30-60-90 day roadmap

> **All data are synthetic** (a fictional Indian retail brokerage: 10,000 users, Nov 2025 - Oct 2026, INR, snapshot 2026-10-31). No revenue, ROI or lifetime value is computed because the dataset contains none of those fields. Nothing below has been tested in a real business; experiments are **proposed, not run**.

The plan sequences the fifteen recommendations: **Foundation** (fix measurement and the biggest known leaks), **Pilot** (run the first tests where pools already exist), **Scale and decide** (act on read-outs, slower tests, retention protection). Resource lines are planning estimates.

## Days 1-30: Foundation

| ID | Priority | Action | Owner / contributors | KPI (baseline) |
|---|---|---|---|---|
| D01 | P1 | Stand up a growth operating cadence and an experiment review board | Data Analytics (owner); all functions | Experiments with a pre-registered plan (target 100%); days from idea to decision; closed-loop feedback items resolved |
| B06 | P1 | Fix the data foundation: reconcile flags, log step events, spend and clicks | Data Analytics (owner); Engineering; Operations | Share of stalled-segment users with an unresolved source conflict (baseline 91-98%; proposed target under 5%); median days registration to first trade |
| A01 | P1 | Make cost per first trade the headline campaign KPI | Marketing (owner); Data Analytics | Share of paid budget reviewed on cost per first trade (target 100%); blended paid cost per first trade (baseline Rs 923) |
| B05 | P1 | Make support priority real and clear the ageing backlog | Customer Support (owner); Operations; Product (top ticket drivers) | Open tickets older than 90 days (baseline 563; proposed target 0 by Day 60); median resolution High vs Low (proposed: High at least 25% faster) |
| B01 | P1 | Fix the KYC step: checklist, status tracker and assisted KYC | Product (owner); Compliance (rules, vendor); Customer Support; Marketing CRM (reminders); Data Analytics | Registration to KYC within 14 days (baseline 70.5% final completion); KYC tickets per registrant (baseline 0.173) |

**Linked experiments:** EXP-01, EXP-02, EXP-08

## Days 31-60: Pilot

| ID | Priority | Action | Owner / contributors | KPI (baseline) |
|---|---|---|---|---|
| A02 | P1 | Stage the shift of budget from the weakest to the strongest paid campaigns | Marketing (owner); Finance (approves); Data Analytics | Marginal cost per first trade of destination campaigns (decision rule: at most Rs 682, i.e. +50% on the observed Rs 454); blended paid cost per first trade |
| A03 | P1 | Scale referral with a prompt at the first-trade moment | Product (owner); Marketing; Compliance (reward terms) | Referred registrations per 100 exposed users in 30 days (baseline 2.95); guardrail: first-trade rate of referred cohort stays at or above 45% |
| B03 | P2 | Reduce first-deposit hesitation with quick-amount chips and reminders | Product (owner); CRM; Compliance | First deposit within 14 days of bank link (baseline 76.9%) |
| B04 | P2 | Convert funded-but-untraded users with a guided first trade | Product (owner); CRM; Compliance (practice-order disclosures) | First trade within 14 days of deposit (baseline 79.8%) |
| C01 | P2 | Build onboarding around an early first-trade milestone | Marketing CRM (owner); Product; Compliance (communication rules) | Share of new users who trade in months 0-1 (baseline 56.3% of the eligible base); M1 and M3 retention |
| C02 | P2 | Run a value-led win-back sequence with a holdout | Marketing CRM (owner); Compliance; Finance (incentive cost) | Reactivation in 30 days after last touch (baseline 34.7%); guardrail: unsubscribe rate and trading in the following month |

**Linked experiments:** EXP-04, EXP-05, EXP-06, EXP-07, EXP-09

## Days 61-90: Scale and decide

| ID | Priority | Action | Owner / contributors | KPI (baseline) |
|---|---|---|---|---|
| A04 | P2 | Put Video Awareness (CMP04) and Finance Affiliate (CMP06) on improvement plans | Marketing (owner); Partnerships; Data Analytics | First trades per 1,000 clicks (not per registrant); guardrail: CAC rises no more than 20% |
| A05 | P3 | Make organic a tracked, costed channel | Marketing (owner); Finance | Organic share of registrations (baseline 18.8%); organic first-trade rate (baseline 47.2%) |
| B02 | P3 | Offer UPI-first bank linking with a one-tap fallback | Product (owner); Compliance; Customer Support | Bank linked within 7 days of KYC (baseline 87.8%) |
| C03 | P3 | Protect repeat and high-engagement traders | Product; Customer Support; Marketing CRM | Repeat-trader share of traders (baseline 69.3%); monthly migration from segment 08 to 09 |

**Linked experiments:** EXP-03, EXP-06, EXP-10

## Decision gates

* **Day 30:** the data foundation (B06) is reconciled enough to trust segment sizes; campaign scorecard (A01) is live; the experiment review board (D01) exists.
* **Day 60:** pilots have pre-registered plans and Compliance sign-off; the ageing backlog (B05) is being worked.
* **Day 90:** go / no-go on each pilot from its pre-set rule; the budget shift (A02) proceeds to its second stage only if the destination cost per first trade stays within the agreed limit.

Pilots start in Days 31-60, so only EXP-02 fully reads out by Day 90 and EXP-09 about Day 93; the Day 90 gate is judged on leading indicators plus those two reads. The other tests are started, not concluded (see the feasibility table in [`experiment_design.md`](experiment_design.md)).
