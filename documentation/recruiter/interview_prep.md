# Interview preparation

Sixty questions with model answers based on what this project actually did. Numbers come from the repository; check them against [`../KPI_definitions.md`](../KPI_definitions.md) before an interview. Everything is **synthetic data**: say so early, and never present it as a real company's data.

**Use the answers as a spine, not a script.** If you did not do something (for example, run an experiment or build the Power BI file), say so plainly: the project is stronger for being honest about it.

---

## A. Technical (20)

**1. Why did you restrict funnel rates to a "mature cohort"?**
Users who registered in October 2026 had no time to convert. On the source flags that cohort showed 40.0 % first-trade conversion, but those flags included future events; as of the snapshot it was 8.4 %. Mixing them in would distort every rate, so funnel rates use the 9,116 users registered Nov 2025 – Sep 2026.

**2. How did you deal with events dated after the snapshot?**
388 users had KYC, bank, deposit or trade dates after 2026-10-31 while flagged as completed. I created `*_asof` flags and dates that count only events up to the snapshot, kept the original columns, and checked that zero post-snapshot events remained. The change is logged (CL04).

**3. How did you know your numbers were right?**
I computed the headline KPIs independently in SQL (34 queries), Python (a package and pipeline) and Excel (live formulas), then compared them: 71 of 71 KPI comparisons agree, and an Excel check sheet reconciles 114 of 114 values to the Python results. For the dashboard I found one real defect this way (an inactivity measure used the wrong eligible base) and fixed it.

**4. Why SQLite, and how did you get a median without `MEDIAN()`?**
SQLite needs no server and ships with Python, so anyone can reproduce the queries. For medians I used window functions: `ROW_NUMBER` over the ordered values and the average of the middle one or two. Date arithmetic uses `julianday`.

**5. How is retention defined?**
Calendar-month retention: active in calendar month *k* after the registration month, divided by cohort users old enough to observe month *k* (month 0 is the registration month). That gives M1 67.6 %, M3 56.0 %, M6 40.7 %. It is a proxy for retention because the data has no confirmed churn.

**6. How did you compute CAC, and why is organic CAC blank?**
CAC is recorded campaign spend divided by registrations (blended paid ≈ Rs 331). Organic has no recorded spend, but organic activity has hidden costs, so I left its CAC undefined rather than showing zero, which would make it look free. Cost per first trade is CAC divided by the mature first-trade rate.

**7. Why Wilson confidence intervals?**
For proportions, especially with smaller groups or rates near 0 or 1, the Wilson interval has much better coverage than the simple normal approximation. I used it for all rates, for example referral's cost per first trade of Rs 438 (CI Rs 413–466).

**8. Why a Holm correction?**
I compared each of ten campaigns with the rest, which inflates false positives. Holm controls the family-wise error rate and is never less powerful than Bonferroni. It changed a conclusion: Finance Affiliate looked weak (raw p = 0.015) but is not significant after correction (p = 0.061), while Video Awareness stays significant.

**9. How did you size the experiments?**
With the two-proportion sample-size formula at α = 0.05 (two-sided) and 80 % power. Baselines come from the data; the expected lifts are assumptions. I also show the requirement if the effect is halved. For the KYC checklist test: baseline 70.5 %, assumed +5 points → 1,236 users per arm, rising to 5,088 if the true lift is 2.5 points.

**10. What is the Mantel–Haenszel odds ratio doing in the support analysis?**
Tenure plausibly affects both raising a ticket and going dormant, so I stratified by registration cohort to keep that from distorting the comparison. The cohort-adjusted odds ratio for three-month dormancy is 1.15 (95 % CI 1.03–1.30): a weak association, not evidence that support causes churn.

**11. How did you choose the segmentation approach?**
I built ten rule-based journey segments and compared them with k-means and RFM. K-means gave weakly separated clusters (k = 4 silhouette 0.33; the silhouette-best k = 2 scores 0.37), so I used the explainable rule-based segments for action. They show 58.6 % of users stalled in onboarding.

**12. Tell me about the early-warning model.**
A logistic regression predicting month-3 retention from early behaviour and profile features: cross-validated AUC 0.57, temporal test 0.58. That is barely better than chance, so I reported it as weak and did not use it. Trading in months 0–1 is the strongest signal (odds ratio 1.44), which supports an onboarding action but not a prediction tool.

**13. How did you make the project reproducible?**
One path registry (`config.py`) derives everything from the repository root, so there are no hard-coded paths. The raw data is read-only, every cleaning change is logged, and the cleaning step reproduces the cleaned files byte for byte. I tested two library combinations (pandas 3.0 and pandas 2.2).

**14. Describe the Power BI data model.**
A star schema: three fact tables (customer, activity, ticket) and dimensions for campaign, city, device, segment, stage and date. Each fact carries the dimension keys, so slicers filter every fact directly and there are no fact-to-fact relationships (which would need bi-directional filtering). 15 one-to-many, single-direction relationships.

**15. You never opened Power BI. How can you trust the DAX?**
I can't claim it runs. I re-implemented each measure's logic in pandas under several filter contexts and compared with validated results: 231 of 231 comparisons match, covering 87 of 117 measures directly. That shows the logic is right; it doesn't prove the syntax executes in Power BI, and I say so in the documentation.

**16. How does the Friction Detector decide when to flag a customer?**
Per stage, a customer is flagged only after waiting longer than the 95th percentile of observed completion lags for that step (KYC 11 days, bank 7, deposit 14, trade 11). Customers still inside the window are labelled `WITHIN_WINDOW` (543), so new sign-ups aren't flagged too early.

**17. How is the priority score built?**
A transparent 0–100 heuristic with six components: tenure, funnel stage, inactivity, support history, recent activity and past transaction value. Bands are High ≥ 55, Medium ≥ 35. It is explicitly not a probability: there are no outcome labels to train or validate against.

**18. How did you test the Friction Detector?**
64 unit and integration tests plus 46 end-to-end checks. The key one compares the engine with an independent plain-Python re-implementation of the written rules for all 10,000 customers: zero mismatches. That catches coding errors, not wrong rules, and I state that limit.

**19. How did you handle the contradictions between tables?**
The monthly activity log conflicts with the funnel flags for a large share of users (for example, trade rows for users flagged as never having traded). I flagged and quantified them in the data-quality report rather than guessing which source is right, and used a data-confidence field in the Friction Detector so 66 % of its flagged customers are marked "verify first".

**20. What dependency or environment problems did you hit?**
Running the pipeline under pandas 2.2 failed on a missing `tabulate` dependency, which I added to requirements; a Streamlit app crashed on a freshly built database with no runs, so I added an empty-state message. Both were caught by running the project in a clean environment.

---

## B. Business and product analytics (20)

**21. Walk me through the funnel and the biggest leak.**
Of 9,116 mature registrants, 70.5 % complete KYC, 87.8 % of those link a bank, 76.9 % of those deposit, and 79.8 % of those trade, so 38.0 % reach a first trade. KYC loses the most users (2,687, 42.6 % of all losses), then first deposit (1,305).

**22. Why is cost per first trade a better metric than CAC?**
CAC counts registrations, but value starts at the first trade. Email Nurture is cheaper than Referral per registration (Rs 160 vs 232) but dearer per trader (Rs 472 vs 438) because fewer of its users trade. I'm clear it is a cost-efficiency measure, not ROI, since the data has no revenue.

**23. Which campaign would you cut?**
Video Awareness is the clearest case: Rs 1,252 per first trade and significantly below the others after Holm correction. Finance Affiliate has a high cost (Rs 1,216) but isn't significant after correction, so I'd put both on improvement plans with a cost guardrail before cutting.

**24. Referral performs best. Do you just scale it?**
Not blindly. Referred users may simply be more motivated (selection), and costs usually rise as spend grows. The plan adds a referral prompt at the first-trade moment and watches a guardrail: the referred cohort's first-trade rate must stay at or above 45 % (it's 52.9 % today).

**25. Would you move the budget?**
Stage it. Moving Rs 190,000 from the two weakest to the two strongest paid campaigns adds about 265 first traders at observed efficiency, but the gain disappears if the destination cost rises about 172 %. I'd set a decision rule (destination cost per first trade must stay under about Rs 682, i.e. +50 %) and expand only if it holds.

**26. How would you cut KYC drop-off?**
Three moves, each testable: a guided KYC checklist with auto-resume reminders (EXP-01), assisted-KYC outreach for stalled applicants (EXP-02), and an in-flow status tracker with contextual help (EXP-08). KYC also has the most support tickets (22.7 %), so help content and status clarity are likely levers. Compliance reviews all wording.

**27. Why is the first trade your activation event?**
Registration and KYC cost the brokerage money without creating usage; the first trade is when the customer actually uses the product. Early trading also associates with better M3 retention (60.7 % vs 50.0 %), though that's an association.

**28. What retention metrics would you track for a brokerage?**
Cohort M1/M3/M6 retention, MAU and its new/existing split, repeat-trader share (69.3 % of ever-traders), and a dormancy proxy, each with its denominator stated. I'd add confirmed churn (closures, transfers-out) if the data existed.

**29. What does "22 % dormant" mean for the business?**
Among mature users, 22.0 % had no active month from Aug to Oct 2026. It's a proxy, not churn, and it varies by channel: 15.5 % for referral vs 25.2 % for affiliate, which says where to look first.

**30. Does support cause customers to leave?**
The data doesn't show that. Ticket-raisers are only slightly more likely to be dormant (adjusted OR 1.15), and tickets are raised while a step is pending, so support is better read as a sensor of onboarding friction. The actionable findings are operational: priority doesn't change resolution time (p = 0.59) and 563 tickets are older than 90 days.

**31. How did you prioritise the recommendations?**
Each idea was scored on impact, ease, cost and speed to benefit (a priority index), then grouped into P1–P3 and into 30-60-90 windows. The measurement foundation (an experiment review cadence and the data fixes) goes first because everything else depends on trustworthy numbers; then the KYC, campaign-KPI and backlog fixes. The scores are analyst judgements, labelled as such.

**32. What would be on the executive dashboard?**
Four pages: Executive Overview (registrations, funnel, MAU), Acquisition & Marketing (CAC, cost per first trade, budget signal with evidence strength), Retention & Segmentation (cohort heatmap, journey segments) and Customer Operations (tickets, resolution, CSAT, backlog). I designed and specified it but have not built it in Power BI.

**33. Which experiment would you run first?**
EXP-02, assisted-KYC outreach for stalled applicants. Only about 28 customers a week are eligible, but the assumed lift is large, so it needs 206 per arm and reads out in about five weeks, the only test that fully reads out inside the 90-day plan.

**34. Design the referral experiment.**
EXP-06: randomise users at the first-trade moment to a two-sided referral prompt or none. Baseline referred registrations are about 2.9 per 100 exposed users; I assumed +50 % relative, which needs about 2,657 users per arm (about 15 weeks). Guardrail: first-trade rate of referred users stays ≥ 45 %; compliance reviews reward terms.

**35. How would you use the journey segments operationally?**
Each stalled segment maps to an owner and an action: KYC-pending to assisted KYC, deposit-pending to quick-amount prompts, deposited-never-traded to a guided first trade. The Friction Detector turns these into a daily ranked list for operations.

**36. What would you do about the 563 old tickets?**
Triage them first (proposed target: none older than 90 days by Day 60), then make priority real, for example High-priority tickets at least 25 % faster, so the SLA means something. I'd measure median resolution by priority weekly.

**37. How does onboarding friction connect to acquisition cost?**
Every user lost at KYC is spend that bought nothing. With 42.6 % of losses at KYC, fixing it lowers cost per first trade for every channel without changing media spend.

**38. What data would you ask stakeholders for?**
Revenue and fee data (to turn cost per first trade into a return), dated spend and click data, a step-level onboarding event log, ticket-to-stage linkage, and confirmed churn. They're the eleven gaps listed in the strategy tables.

**39. How would you explain the findings to a non-technical leader?**
"Four in ten new customers make a first trade. The biggest loss is at identity verification. Referral customers are the best and cheapest per trader; video campaigns are the worst. Support doesn't triage by priority, and 563 tickets are over three months old. Fix verification first, test it, and measure cost per trader, not sign-ups."

**40. What would you do in the first 30 days in a real role?**
Stand up the experiment-review cadence, reconcile the activity and funnel data, make cost per first trade the headline campaign KPI, start clearing the ageing backlog and ship the KYC improvements as tests. That's the Days 1–30 block of the roadmap.

---

## C. Project decisions (10)

**41. Why a synthetic dataset?**
It lets me show the whole analyst workflow without privacy or confidentiality issues, and I can publish it. The trade-off is that findings demonstrate method, not real-world truth, and I label everything accordingly.

**42. Why SQL, Python and Excel?**
Each serves a different audience (analysts, data teams, business users), and doing all three let me cross-validate: if three independent implementations agree, the numbers are right.

**43. Why five notebooks instead of one?**
Each notebook answers one question (cleaning/EDA, funnel and campaigns, cohorts and segmentation, support, automated KPI report) and runs in minutes; one giant notebook is harder to read and review.

**44. Why didn't you finish Power BI?**
Power BI Desktop wasn't available in my build environment, and a `.pbix` can't be produced without it. Rather than fake screenshots, I delivered a build kit (data, DAX, Power Query, themes, specs), verified the DAX logic in pandas, labelled the images as mockups and documented the screenshots to export once it's built.

**45. Why a rule-based Friction Detector instead of machine learning?**
There are no friction or outcome labels, so an ML model couldn't be trained or validated, and my one prediction attempt reached AUC 0.57. Rules are transparent, testable against the written definitions, and explainable to operations.

**46. Why leave organic CAC undefined?**
Zero would imply organic acquisition is free; the data just doesn't record its costs. Undefined forces the question of what organic really costs (recommendation A05 makes it a tracked, costed channel).

**47. Why include the raw data in the repository?**
It's synthetic, small, and nothing sensitive, and including it lets anyone reproduce the whole pipeline from the original file. The original is never modified.

**48. What would you do differently?**
Start with a step-level event model to avoid the activity/funnel conflicts, run the Power BI build earlier, keep one set of folder names from the start (the Excel workbooks still carry earlier folder names in descriptive text), and test on macOS.

**49. How did you keep numbers consistent across so many files?**
Single sources of truth: one results file from the analysis step, one path registry, generated documents (the strategy Markdown is rendered from CSV tables, not typed), and cross-tool verification scripts.

**50. What was the hardest decision?**
Not over-claiming. It would have been easy to present budget scenarios as forecasts, the heuristic score as a prediction, or mockups as a dashboard. Each is labelled for what it is.

---

## D. Limitations and synthetic data (10)

**51. Aren't the findings meaningless because the data is synthetic?**
They don't describe a real business, and I don't claim they do. What they demonstrate is the method: defining cohorts correctly, choosing the right cost metric, controlling for multiple testing, separating proxies from facts, and turning results into testable actions. Some patterns (like priority not affecting resolution time) are as the generator made them.

**52. Could you calculate ROI?**
No. There is no revenue, fee or lifetime-value field, and spend is undated. Cost per first trade is an efficiency measure. Adding revenue and cost-to-serve data is the first improvement I list.

**53. How reliable is the 22 % dormancy figure?**
As a proxy, moderately. It depends on the activity log, which conflicts with the funnel record for many users. I'd call it a screening number to compare channels, not a churn rate.

**54. What's the biggest data-quality problem?**
Monthly activity rows contradict the funnel flags (for instance, trade activity for users flagged as never having traded). I quantified the conflicts rather than silently choosing a side, and the Friction Detector carries a data-confidence field because of it.

**55. Did you try to improve the AUC?**
I didn't tune to chase a number. With weak signal and no labelled outcome beyond retention, a higher score would risk overfitting. Reporting 0.57 honestly is the point: early behaviour is a useful *segment* signal but a poor predictor.

**56. What did you not test?**
The DAX and Power Query in Power BI, the TMDL scaffold, a live call to the optional LLM wording step, and running on macOS. The documentation lists them.

**57. Are the experiments real?**
No. All ten are proposed. Baselines are actual rates from the data; the lifts are assumptions used only to size the tests. None has been run, and I don't report results for any.

**58. Are the assumed effect sizes credible?**
They're plausible planning values (for example +5 percentage points on a funnel step), not forecasts. That's why each test shows the sample needed if the effect is half as big: it's the honest way to show how sensitive the plan is.

**59. Do the results transfer to a real broker such as Groww or Zerodha?**
I make no such claim. The method transfers; the numbers don't. A real analysis would start from the real event data and rerun the same pipeline.

**60. An interviewer says "this is just toy data". How do you respond?**
"Yes, it's synthetic by design, and I say so on the first line of the README. What I'd like you to judge is the workflow: how I audited and corrected the data, verified numbers in three tools, separated proxies from facts, and wrote recommendations and experiments that don't over-claim. I'd run the same process on your data."
