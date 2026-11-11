"""SQL query library definitions (SYNTHETIC DATA). Each entry: id, title, topic, sql, logic, business, output.
Consumed by run_queries.py, which executes every query on fintech_analytics.db, writes CSV outputs,
analysis_queries.sql and SQL_Query_Library.md. Conventions: funnel/CAC/conversion -> users table;
MAU/retention/repeat trading -> monthly_activity (or users columns derived from it); mature = funnel_mature = 1."""

MATURE_NOTE = "Mature cohort = registered before 2026-10 (funnel_mature = 1, n = 9,116), so every user had >= 31 days to progress."

Q = []


def add(id, title, topic, sql, logic, business, output):
    Q.append(dict(id=id, title=title, topic=topic, sql=sql.strip("\n"), logic=logic, business=business, output=output))


add("Q01", "Total registrations", "total registrations",
"""SELECT COUNT(*)                                             AS total_registrations,
       SUM(funnel_mature = 1)                               AS mature_cohort_users,
       SUM(funnel_mature = 0)                               AS immature_oct26_users,
       MIN(registration_date)                               AS first_registration,
       MAX(registration_date)                               AS last_registration,
       COUNT(DISTINCT registration_month)                   AS months_covered,
       ROUND(1.0 * COUNT(*) / COUNT(DISTINCT registration_month), 1) AS avg_registrations_per_month
FROM users;""",
"Counts every row of users (one row per registered user). Booleans in SQLite are 0/1, so SUM(condition) counts rows. Splitting mature vs immature protects later conversion metrics from the Oct-2026 cohort that has not had time to convert.",
"Headline acquisition volume and the denominator for every rate on the platform. Mature/immature split tells analysts which users may be used for funnel conversion.",
"1 row: total_registrations, mature_cohort_users, immature_oct26_users, first/last_registration, months_covered, avg_registrations_per_month.")

add("Q02", "Monthly acquisition with month-over-month growth", "monthly acquisition",
"""WITH m AS (
    SELECT registration_month, COUNT(*) AS registrations
    FROM users GROUP BY registration_month
)
SELECT registration_month,
       registrations,
       LAG(registrations) OVER (ORDER BY registration_month)                       AS prev_month,
       ROUND(100.0 * (registrations - LAG(registrations) OVER (ORDER BY registration_month))
             / LAG(registrations) OVER (ORDER BY registration_month), 1)           AS mom_growth_pct,
       SUM(registrations) OVER (ORDER BY registration_month)                       AS cumulative_registrations
FROM m ORDER BY registration_month;""",
"Aggregates registrations per calendar month, then uses window functions: LAG for the previous month (MoM %), running SUM for cumulative base.",
"Shows whether acquisition is growing or seasonal; the cumulative base is the denominator for 'MAU as % of registered users'.",
"12 rows (2025-11 .. 2026-10): registration_month, registrations, prev_month, mom_growth_pct (NULL for first month), cumulative_registrations.")

add("Q03", "Channel-wise acquisition", "channel-wise acquisition",
"""SELECT acquisition_channel,
       COUNT(*)                                                         AS registrations,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)               AS share_pct,
       SUM(funnel_mature = 1)                                           AS mature_users,
       RANK() OVER (ORDER BY COUNT(*) DESC)                             AS volume_rank
FROM users
GROUP BY acquisition_channel
ORDER BY registrations DESC;""",
"Groups by acquisition_channel; SUM(COUNT(*)) OVER () turns the grouped counts into shares of the total without a self-join.",
"Shows channel mix (e.g. organic share) and dependence on paid channels; the starting point for budget conversations.",
"7 rows: acquisition_channel, registrations, share_pct, mature_users, volume_rank.")

add("Q04", "Campaign CAC and cost per first trader", "campaign CAC",
"""WITH c AS (
    SELECT u.acquisition_campaign_id AS campaign_id,
           COUNT(*)                                          AS registered_users,
           SUM(u.funnel_mature)                              AS mature_users,
           SUM(CASE WHEN u.funnel_mature = 1 AND u.trade_asof = 1 THEN 1 ELSE 0 END) AS mature_first_traders
    FROM users u GROUP BY u.acquisition_campaign_id
)
SELECT k.campaign_id, k.campaign_name, k.channel, k.campaign_spend_inr,
       c.registered_users,
       CASE WHEN k.is_paid = 1 THEN ROUND(1.0 * k.campaign_spend_inr / c.registered_users, 1) END AS cac_inr,
       ROUND(100.0 * c.mature_first_traders / c.mature_users, 2)                                  AS first_trade_rate_mature_pct,
       CASE WHEN k.is_paid = 1 THEN ROUND((1.0 * k.campaign_spend_inr / c.registered_users)
                                          / (1.0 * c.mature_first_traders / c.mature_users), 0) END AS cost_per_first_trader_inr
FROM campaigns k JOIN c ON c.campaign_id = k.campaign_id
ORDER BY cost_per_first_trader_inr;""",
"CAC = recorded campaign spend / users registered by that campaign (all 10,000 users). Cost per first trader divides CAC by the first-trade rate measured on the mature cohort only, so late campaigns are not flattered or penalised by immaturity. Organic campaigns have no recorded spend, so CAC is NULL (not zero).",
"The core efficiency metric for budget allocation: cheap registrations that never trade are not cheap. Feeds the campaign ranking in Q21.",
"10 rows: campaign_id, campaign_name, channel, campaign_spend_inr, registered_users, cac_inr (NULL for organic), first_trade_rate_mature_pct, cost_per_first_trader_inr.")

add("Q05", "KYC completion rate (registered -> KYC)", "KYC completion",
"""SELECT 'All channels' AS acquisition_channel,
       COUNT(*) AS mature_registered, SUM(kyc_asof) AS kyc_completed,
       ROUND(100.0 * SUM(kyc_asof) / COUNT(*), 2) AS kyc_completion_pct,
       ROUND(AVG(days_reg_to_kyc), 1) AS avg_days_to_kyc
FROM users WHERE funnel_mature = 1
UNION ALL
SELECT acquisition_channel, COUNT(*), SUM(kyc_asof),
       ROUND(100.0 * SUM(kyc_asof) / COUNT(*), 2), ROUND(AVG(days_reg_to_kyc), 1)
FROM users WHERE funnel_mature = 1
GROUP BY acquisition_channel
ORDER BY kyc_completion_pct DESC;""",
"Filters to the mature cohort, then divides KYC-completed users (kyc_asof = 1, event on/before the snapshot) by registered users. UNION ALL adds an overall row beside per-channel rows.",
"KYC is the largest single leak in the funnel; channel differences show whether the problem is traffic quality or the verification experience.",
"8 rows: acquisition_channel (incl. 'All channels'), mature_registered, kyc_completed, kyc_completion_pct, avg_days_to_kyc.")

add("Q06", "Bank-link conversion (KYC -> bank linked)", "bank-link conversion",
"""SELECT 'All channels' AS acquisition_channel,
       SUM(kyc_asof) AS kyc_completed, SUM(bank_asof) AS bank_linked,
       ROUND(100.0 * SUM(bank_asof) / SUM(kyc_asof), 2) AS bank_link_conv_pct,
       ROUND(AVG(days_kyc_to_bank), 1) AS avg_days_kyc_to_bank
FROM users WHERE funnel_mature = 1
UNION ALL
SELECT acquisition_channel, SUM(kyc_asof), SUM(bank_asof),
       ROUND(100.0 * SUM(bank_asof) / SUM(kyc_asof), 2), ROUND(AVG(days_kyc_to_bank), 1)
FROM users WHERE funnel_mature = 1
GROUP BY acquisition_channel
ORDER BY bank_link_conv_pct DESC;""",
"Step conversion = users who linked a bank / users who completed KYC (the prior stage), not / registered users. The funnel is nested so SUM(bank_asof) is already a subset of KYC completers.",
"Isolates friction at the bank-link step independent of the earlier KYC drop.",
"8 rows: acquisition_channel, kyc_completed, bank_linked, bank_link_conv_pct, avg_days_kyc_to_bank.")

add("Q07", "First-deposit conversion (bank linked -> funded)", "first deposit conversion",
"""SELECT 'All channels' AS acquisition_channel,
       SUM(bank_asof) AS bank_linked, SUM(deposit_asof) AS first_deposit,
       ROUND(100.0 * SUM(deposit_asof) / SUM(bank_asof), 2) AS deposit_conv_pct,
       ROUND(AVG(CASE WHEN deposit_asof = 1 THEN first_deposit_amount_asof_inr END), 0) AS avg_first_deposit_inr
FROM users WHERE funnel_mature = 1
UNION ALL
SELECT acquisition_channel, SUM(bank_asof), SUM(deposit_asof),
       ROUND(100.0 * SUM(deposit_asof) / SUM(bank_asof), 2),
       ROUND(AVG(CASE WHEN deposit_asof = 1 THEN first_deposit_amount_asof_inr END), 0)
FROM users WHERE funnel_mature = 1
GROUP BY acquisition_channel
ORDER BY deposit_conv_pct DESC;""",
"Deposit step conversion on the mature cohort; AVG over a CASE expression ignores non-depositors (NULL), giving the average first deposit among funded users only.",
"Shows where funding intent is lost after the user has done the hard KYC/bank work - the target for deposit nudges and first-deposit offers.",
"8 rows: acquisition_channel, bank_linked, first_deposit, deposit_conv_pct, avg_first_deposit_inr.")

add("Q08", "First-trade activation (funded -> first trade)", "first trade activation",
"""SELECT 'All channels' AS acquisition_channel,
       SUM(deposit_asof) AS funded, SUM(trade_asof) AS first_traders,
       ROUND(100.0 * SUM(trade_asof) / SUM(deposit_asof), 2)  AS activation_pct_of_funded,
       ROUND(100.0 * SUM(trade_asof) / COUNT(*), 2)            AS reg_to_first_trade_pct,
       ROUND(AVG(days_deposit_to_trade), 1)                    AS avg_days_deposit_to_trade
FROM users WHERE funnel_mature = 1
UNION ALL
SELECT acquisition_channel, SUM(deposit_asof), SUM(trade_asof),
       ROUND(100.0 * SUM(trade_asof) / SUM(deposit_asof), 2),
       ROUND(100.0 * SUM(trade_asof) / COUNT(*), 2), ROUND(AVG(days_deposit_to_trade), 1)
FROM users WHERE funnel_mature = 1
GROUP BY acquisition_channel
ORDER BY reg_to_first_trade_pct DESC;""",
"Two views of activation: step conversion (traders / funded) and end-to-end conversion (traders / registered). Both on the mature cohort.",
"First trade is the activation event. The gap between funded and traded users is money sitting idle and the cheapest group to re-engage.",
"8 rows: acquisition_channel, funded, first_traders, activation_pct_of_funded, reg_to_first_trade_pct, avg_days_deposit_to_trade.")

add("Q09", "Funnel drop-offs by stage", "funnel drop-offs",
"""WITH f AS (
    SELECT COUNT(*) AS registered, SUM(kyc_asof) AS kyc, SUM(bank_asof) AS bank,
           SUM(deposit_asof) AS deposit, SUM(trade_asof) AS trade,
           SUM(CASE WHEN trade_asof = 1 AND active_30d_adj = 1 THEN 1 ELSE 0 END) AS active30
    FROM users WHERE funnel_mature = 1
), s AS (
    SELECT 1 AS step, 'Registered'     AS stage, registered AS reached FROM f UNION ALL
    SELECT 2, 'KYC Completed', kyc FROM f UNION ALL
    SELECT 3, 'Bank Linked',   bank FROM f UNION ALL
    SELECT 4, 'First Deposit', deposit FROM f UNION ALL
    SELECT 5, 'First Trade',   trade FROM f UNION ALL
    SELECT 6, 'Active (30d)',  active30 FROM f
)
SELECT step, stage, reached,
       ROUND(100.0 * reached / FIRST_VALUE(reached) OVER (ORDER BY step), 1)               AS pct_of_registered,
       ROUND(100.0 * reached / LAG(reached) OVER (ORDER BY step), 1)                       AS step_conversion_pct,
       LAG(reached) OVER (ORDER BY step) - reached                                         AS users_lost_at_step,
       ROUND(100.0 * (LAG(reached) OVER (ORDER BY step) - reached)
             / (SELECT registered - active30 FROM f), 1)                                   AS share_of_all_losses_pct
FROM s ORDER BY step;""",
"Builds a six-row stage table from one pass over the mature cohort (Registered > KYC > Bank > Deposit > First Trade > Active in last 30 days), then uses LAG/FIRST_VALUE to get step conversion, absolute losses and each step's share of total leakage (registered minus users still active). Active (30d) = first traders whose days since last activity is <= 30.",
"Ranks where users are lost; KYC typically accounts for the largest share, so it gets priority in the experiment backlog.",
"6 rows: step, stage, reached, pct_of_registered, step_conversion_pct, users_lost_at_step, share_of_all_losses_pct.")

add("Q10", "City-wise performance", "city-wise",
"""SELECT city,
       COUNT(*)                                                        AS registrations,
       SUM(funnel_mature)                                              AS mature_users,
       ROUND(100.0 * SUM(CASE WHEN funnel_mature = 1 THEN kyc_asof END)
             / SUM(funnel_mature), 1)                                  AS kyc_pct,
       ROUND(100.0 * SUM(CASE WHEN funnel_mature = 1 THEN trade_asof END)
             / SUM(funnel_mature), 1)                                  AS first_trade_pct,
       ROUND(100.0 * AVG(m3_retained), 1)                              AS m3_retention_pct,
       ROUND(1000.0 * SUM(ticket_count) / COUNT(*), 0)                 AS tickets_per_1000_users
FROM users
GROUP BY city
ORDER BY first_trade_pct DESC;""",
"Per-city rates use the mature cohort for funnel metrics; AVG(m3_retained) ignores NULL (users too new to have an M3). Tickets per 1,000 users normalises for city size.",
"Checks for geographic variation worth localised action; city differences are usually small in this synthetic data and should be tested before acting.",
"11 rows: city, registrations, mature_users, kyc_pct, first_trade_pct, m3_retention_pct, tickets_per_1000_users.")

add("Q11", "Device-wise performance", "device-wise",
"""SELECT device_type,
       COUNT(*) AS registrations,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS share_pct,
       ROUND(100.0 * SUM(CASE WHEN funnel_mature = 1 THEN kyc_asof END) / SUM(funnel_mature), 1)   AS kyc_pct,
       ROUND(100.0 * SUM(CASE WHEN funnel_mature = 1 THEN trade_asof END) / SUM(funnel_mature), 1) AS first_trade_pct,
       ROUND(100.0 * AVG(m3_retained), 1) AS m3_retention_pct,
       ROUND(1000.0 * SUM(ticket_count) / COUNT(*), 0) AS tickets_per_1000_users
FROM users GROUP BY device_type ORDER BY registrations DESC;""",
"Same structure as Q10 grouped by device_type (Android, iOS, Web).",
"Shows whether a platform has a worse onboarding or support experience (e.g. app KYC flow vs web).",
"3 rows: device_type, registrations, share_pct, kyc_pct, first_trade_pct, m3_retention_pct, tickets_per_1000_users.")

add("Q12", "Monthly active users (MAU) with new vs existing split", "MAU",
"""WITH reg AS (
    SELECT registration_month AS m, COUNT(*) AS regs FROM users GROUP BY 1
), cum AS (
    SELECT m, SUM(regs) OVER (ORDER BY m) AS registered_to_date FROM reg
), act AS (
    SELECT activity_month AS m,
           SUM(active_in_month)                                            AS mau,
           SUM(CASE WHEN months_since_registration = 0 THEN active_in_month ELSE 0 END) AS mau_new,
           SUM(CASE WHEN months_since_registration > 0 THEN active_in_month ELSE 0 END) AS mau_existing
    FROM monthly_activity GROUP BY activity_month
)
SELECT a.m AS activity_month, a.mau, a.mau_new, a.mau_existing, c.registered_to_date,
       ROUND(100.0 * a.mau / c.registered_to_date, 1) AS mau_pct_of_registered
FROM act a JOIN cum c ON c.m = a.m ORDER BY a.m;""",
"MAU = users with active_in_month = 1 in the calendar month (monthly_activity is the source of truth for activity). months_since_registration = 0 identifies users in their registration month (new). Registered-to-date is a running sum of Q02.",
"MAU is the main engagement KPI; the share of registered users that are active shows whether growth in sign-ups translates to a bigger active base.",
"12 rows: activity_month, mau, mau_new, mau_existing, registered_to_date, mau_pct_of_registered.")

add("Q13", "Cohort retention matrix (M0-M6)", "cohort retention",
"""SELECT registration_month AS cohort,
       COUNT(CASE WHEN months_since_registration = 0 THEN 1 END)                              AS cohort_users,
       ROUND(100.0 * AVG(CASE WHEN months_since_registration = 0 THEN active_in_month END), 1) AS m0_pct,
       ROUND(100.0 * AVG(CASE WHEN months_since_registration = 1 THEN active_in_month END), 1) AS m1_pct,
       ROUND(100.0 * AVG(CASE WHEN months_since_registration = 2 THEN active_in_month END), 1) AS m2_pct,
       ROUND(100.0 * AVG(CASE WHEN months_since_registration = 3 THEN active_in_month END), 1) AS m3_pct,
       ROUND(100.0 * AVG(CASE WHEN months_since_registration = 4 THEN active_in_month END), 1) AS m4_pct,
       ROUND(100.0 * AVG(CASE WHEN months_since_registration = 5 THEN active_in_month END), 1) AS m5_pct,
       ROUND(100.0 * AVG(CASE WHEN months_since_registration = 6 THEN active_in_month END), 1) AS m6_pct
FROM monthly_activity
GROUP BY registration_month
UNION ALL
SELECT 'POOLED (all cohorts)',
       COUNT(CASE WHEN months_since_registration = 0 THEN 1 END),
       ROUND(100.0 * AVG(CASE WHEN months_since_registration = 0 THEN active_in_month END), 2),
       ROUND(100.0 * AVG(CASE WHEN months_since_registration = 1 THEN active_in_month END), 2),
       ROUND(100.0 * AVG(CASE WHEN months_since_registration = 2 THEN active_in_month END), 2),
       ROUND(100.0 * AVG(CASE WHEN months_since_registration = 3 THEN active_in_month END), 2),
       ROUND(100.0 * AVG(CASE WHEN months_since_registration = 4 THEN active_in_month END), 2),
       ROUND(100.0 * AVG(CASE WHEN months_since_registration = 5 THEN active_in_month END), 2),
       ROUND(100.0 * AVG(CASE WHEN months_since_registration = 6 THEN active_in_month END), 2)
FROM monthly_activity
ORDER BY cohort;""",
"Conditional aggregation pivots months_since_registration into columns. AVG(active_in_month) over rows at offset k is the share of cohort users active k calendar months after the registration month. Cells where the offset has not occurred yet are NULL because no row exists (no denominator). M1/M3/M6 are calendar-month retention proxies, not exact 30/90/180-day retention.",
"The classic retention triangle. Shows whether recent cohorts retain better or worse than older ones, and the pooled row gives the headline M1/M3/M6.",
"13 rows (12 cohorts + pooled): cohort, cohort_users, m0_pct ... m6_pct (NULL where not yet observable).")

add("Q14", "Customer inactivity (recency buckets)", "customer inactivity",
"""SELECT CASE WHEN days_inactive_adj <= 30 THEN '1. Active (0-30 d)'
            WHEN days_inactive_adj <= 60 THEN '2. Cooling (31-60 d)'
            WHEN days_inactive_adj <= 90 THEN '3. At risk (61-90 d)'
            ELSE '4. Inactive (>90 d, bounded at 120)' END AS recency_bucket,
       COUNT(*)                                  AS users,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS share_pct,
       ROUND(AVG(trading_value_6m_inr), 0)       AS avg_trading_value_6m_inr
FROM users
WHERE eligible_30d = 1            -- tenure >= 31 days, so recency is meaningful
GROUP BY recency_bucket ORDER BY recency_bucket;""",
"Buckets days_inactive_adj (days since last activity, adjusted to the snapshot and bounded at 120). Restricted to users with tenure of at least 31 days so brand-new users are not counted as 'recently active' by construction. Note: the Phase 3 headline 'inactive 90d proxy' (14.9%) uses the stricter base tenure >= 91 days (eligible_90d), so the >90 d bucket here (12.2%) is on a different base.",
"Recency is the earliest warning signal for disengagement. Flags are proxies, never confirmed churn.",
"4 rows: recency_bucket, users, share_pct, avg_trading_value_6m_inr.")

add("Q15", "Churn proxy: dormant for three months", "churn proxy",
"""SELECT 'All channels' AS acquisition_channel,
       COUNT(*) AS eligible_users, SUM(dormant_3m_monthly) AS dormant_users,
       ROUND(100.0 * AVG(dormant_3m_monthly), 2) AS dormant_3m_pct
FROM users WHERE dormant_3m_monthly IS NOT NULL      -- registered <= Jul-2026
UNION ALL
SELECT acquisition_channel, COUNT(*), SUM(dormant_3m_monthly), ROUND(100.0 * AVG(dormant_3m_monthly), 2)
FROM users WHERE dormant_3m_monthly IS NOT NULL
GROUP BY acquisition_channel
ORDER BY dormant_3m_pct DESC;""",
"dormant_3m = no active month in Aug-Oct 2026 (monthly source), defined only for users registered by Jul-2026 who had a full 3-month window. It is a churn PROXY: dormant users may return.",
"Sizes the win-back pool and shows which channels bring users who disengage fastest.",
"8 rows: acquisition_channel, eligible_users, dormant_users, dormant_3m_pct.")

add("Q16", "Repeat trading behaviour", "repeat trading",
"""WITH base AS (
    SELECT acquisition_channel, trade_months
    FROM users WHERE months_observed >= 4          -- at least 4 months of observable history
), traders AS (SELECT * FROM base WHERE trade_months >= 1)
SELECT 'All channels' AS acquisition_channel,
       (SELECT COUNT(*) FROM base)                                             AS users_observed_4m_plus,
       COUNT(*)                                                                AS ever_traded_users,
       ROUND(100.0 * AVG(trade_months >= 2), 1)                               AS repeat_pct_of_traders,
       ROUND(100.0 * AVG(trade_months >= 3), 1)                               AS repeat3_pct_of_traders
FROM traders
UNION ALL
SELECT t.acquisition_channel,
       (SELECT COUNT(*) FROM base b WHERE b.acquisition_channel = t.acquisition_channel),
       COUNT(*), ROUND(100.0 * AVG(t.trade_months >= 2), 1), ROUND(100.0 * AVG(t.trade_months >= 3), 1)
FROM traders t GROUP BY t.acquisition_channel
ORDER BY repeat_pct_of_traders DESC;""",
"trade_months counts calendar months in which the user placed at least one trade (monthly source). Repeat trader = trading in 2+ months. Base is users with >= 4 observed months so recent joiners do not understate repetition.",
"Repeat trading is the habit-formation signal that matters most for lifetime value; this shows which channels bring habitual traders.",
"8 rows: acquisition_channel, users_observed_4m_plus, ever_traded_users, repeat_pct_of_traders, repeat3_pct_of_traders.")

add("Q17", "Customer segmentation (journey segments)", "customer segmentation",
"""SELECT s.journey_segment,
       COUNT(*)                                             AS users,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)   AS share_pct,
       ROUND(AVG(u.tenure_days), 0)                         AS avg_tenure_days,
       ROUND(AVG(u.trading_value_6m_inr), 0)                AS avg_trading_value_6m_inr,
       ROUND(1.0 * SUM(u.ticket_count) / COUNT(*), 2)       AS tickets_per_user
FROM v_journey_segment s JOIN users u USING (user_id)
GROUP BY s.journey_segment ORDER BY s.journey_segment;""",
"Uses view v_journey_segment, which implements the Phase 3 rule: onboarding users still within the historical max stage lag are 'in-flight'; those beyond it are 'stalled' at their furthest stage; traders are split by recency and by trading months in the last 6.",
"Gives the Customer Operations team a rule-based action list per segment (nudge, KYC help, bank-link help, deposit prompt, activation, win-back).",
"10 rows: journey_segment, users, share_pct, avg_tenure_days, avg_trading_value_6m_inr, tickets_per_user.")

add("Q18", "Support ticket categories", "support ticket categories",
"""SELECT category,
       COUNT(*)                                             AS tickets,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)   AS share_pct,
       COUNT(DISTINCT user_id)                              AS users_affected,
       SUM(priority = 'High')                               AS high_priority,
       SUM(status = 'Escalated')                            AS escalated,
       SUM(is_unresolved)                                   AS unresolved
FROM support_tickets GROUP BY category ORDER BY tickets DESC;""",
"Ticket volume and severity mix per category; users_affected counts distinct users to separate widespread issues from repeat contactors.",
"Identifies the biggest contact drivers - the targets for self-service content, product fixes and staffing.",
"7 rows: category, tickets, share_pct, users_affected, high_priority, escalated, unresolved.")

add("Q19", "Average and median resolution time", "average resolution time",
"""WITH r AS (
    SELECT category, resolution_time_hours AS h,
           ROW_NUMBER() OVER (PARTITION BY category ORDER BY resolution_time_hours) AS rn,
           COUNT(*)     OVER (PARTITION BY category)                                AS n
    FROM support_tickets WHERE resolution_time_hours IS NOT NULL
), med AS (
    SELECT category, AVG(h) AS median_h FROM r WHERE rn IN ((n + 1) / 2, (n + 2) / 2) GROUP BY category
)
SELECT t.category,
       COUNT(t.resolution_time_hours)             AS resolved_tickets,
       ROUND(AVG(t.resolution_time_hours), 1)     AS mean_hours,
       ROUND(m.median_h, 1)                       AS median_hours,
       ROUND(MAX(t.resolution_time_hours), 1)     AS max_hours
FROM support_tickets t JOIN med m USING (category)
GROUP BY t.category
UNION ALL
SELECT 'ALL CATEGORIES', COUNT(resolution_time_hours), ROUND(AVG(resolution_time_hours), 1),
       (SELECT ROUND(AVG(h), 1) FROM (SELECT resolution_time_hours AS h,
              ROW_NUMBER() OVER (ORDER BY resolution_time_hours) rn, COUNT(*) OVER () n
              FROM support_tickets WHERE resolution_time_hours IS NOT NULL) WHERE rn IN ((n+1)/2, (n+2)/2)),
       ROUND(MAX(resolution_time_hours), 1)
FROM support_tickets
ORDER BY median_hours DESC;""",
"SQLite has no MEDIAN, so the median is the average of the middle one or two ROW_NUMBER positions. Only resolved tickets carry a resolution time; the mean is shown beside the median because resolution time is right-skewed.",
"Median is the typical customer wait; the gap to the mean reveals a long tail of slow cases to investigate.",
"8 rows (7 categories + ALL): category, resolved_tickets, mean_hours, median_hours, max_hours.")

add("Q20", "CSAT by category", "CSAT",
"""SELECT category,
       COUNT(csat_score)                                                  AS rated_tickets,
       ROUND(AVG(csat_score), 2)                                          AS avg_csat,
       ROUND(100.0 * SUM(csat_score >= 4) / COUNT(csat_score), 1)         AS satisfied_pct_4_5,
       ROUND(100.0 * SUM(csat_score <= 2) / COUNT(csat_score), 1)         AS dissatisfied_pct_1_2
FROM support_tickets WHERE csat_score IS NOT NULL
GROUP BY category
UNION ALL
SELECT 'ALL CATEGORIES', COUNT(csat_score), ROUND(AVG(csat_score), 3),
       ROUND(100.0 * SUM(csat_score >= 4) / COUNT(csat_score), 1),
       ROUND(100.0 * SUM(csat_score <= 2) / COUNT(csat_score), 1)
FROM support_tickets WHERE csat_score IS NOT NULL
ORDER BY avg_csat;""",
"CSAT exists only for resolved tickets (6,243 of 7,614). Reports the mean score plus top-box (4-5) and bottom-box (1-2) shares, which are more actionable than a mean alone.",
"Locates categories where service quality is weakest, to prioritise coaching and process fixes.",
"8 rows: category, rated_tickets, avg_csat, satisfied_pct_4_5, dissatisfied_pct_1_2.")

add("Q21", "Campaign performance ranking", "campaign performance ranking",
"""WITH c AS (
    SELECT k.campaign_id, k.campaign_name, k.channel, k.campaign_spend_inr, k.is_paid,
           COUNT(*) AS registered,
           SUM(u.funnel_mature) AS mature_n,
           SUM(CASE WHEN u.funnel_mature = 1 THEN u.trade_asof END) AS mature_traders,
           AVG(u.m3_retained) AS m3
    FROM users u JOIN campaigns k ON k.campaign_id = u.acquisition_campaign_id
    GROUP BY k.campaign_id
)
SELECT campaign_id, campaign_name, channel,
       ROUND(100.0 * mature_traders / mature_n, 1)                                   AS first_trade_pct,
       ROUND(100.0 * m3, 1)                                                          AS m3_retention_pct,
       CASE WHEN is_paid = 1 THEN ROUND(1.0 * campaign_spend_inr / registered / (1.0 * mature_traders / mature_n), 0) END AS cost_per_first_trader_inr,
       RANK() OVER (ORDER BY 1.0 * mature_traders / mature_n DESC)                   AS rank_first_trade,
       RANK() OVER (ORDER BY m3 DESC)                                                AS rank_m3,
       CASE WHEN is_paid = 1 THEN RANK() OVER (PARTITION BY is_paid ORDER BY campaign_spend_inr * 1.0 / registered / (1.0 * mature_traders / mature_n)) END AS rank_cost_efficiency_paid
FROM c ORDER BY rank_first_trade;""",
"Ranks campaigns on three independent measures with RANK(): first-trade rate, 3-month retention and (paid only) cost per first trader. Keeping measures separate avoids hiding trade-offs inside one blended score.",
"Gives marketing a defensible shortlist: scale campaigns that rank high on both cost and quality; question those cheap but low-activation.",
"10 rows: campaign_id, campaign_name, channel, first_trade_pct, m3_retention_pct, cost_per_first_trader_inr, rank_first_trade, rank_m3, rank_cost_efficiency_paid.")

add("Q22", "Customer acquisition by month and channel", "customer acquisition by month",
"""SELECT registration_month,
       COUNT(*) AS total,
       SUM(acquisition_channel = 'Paid Search')  AS paid_search,
       SUM(acquisition_channel = 'Paid Social')  AS paid_social,
       SUM(acquisition_channel = 'Organic')      AS organic,
       SUM(acquisition_channel = 'Referral')     AS referral,
       SUM(acquisition_channel = 'Affiliate')    AS affiliate,
       SUM(acquisition_channel = 'Partnerships') AS partnerships,
       SUM(acquisition_channel = 'CRM')          AS crm,
       SUM(trade_asof)                           AS became_traders_asof,
       ROUND(100.0 * SUM(trade_asof) / COUNT(*), 1) AS trader_rate_pct_asof
FROM users GROUP BY registration_month ORDER BY registration_month;""",
"Conditional SUM(condition) pivots channels into columns by registration month; became_traders_asof shows acquired customers who activated by the snapshot (older cohorts have had longer to convert, so the rate falls for recent months by construction).",
"Combines channel mix with activation in one month-by-month view for the weekly growth review.",
"12 rows: registration_month, total, one column per channel, became_traders_asof, trader_rate_pct_asof.")

add("Q23", "High-potential customers (funded, not yet trading, high deposit)", "high-potential customers",
"""WITH funded AS (
    SELECT user_id, acquisition_channel, city, device_type, first_deposit_amount_asof_inr AS first_deposit_inr,
           deposit_date_asof, tenure_days,
           NTILE(4) OVER (ORDER BY first_deposit_amount_asof_inr) AS deposit_quartile
    FROM users
    WHERE deposit_asof = 1 AND trade_asof = 0
)
SELECT user_id, acquisition_channel, city, device_type, first_deposit_inr, deposit_date_asof,
       CAST(julianday('2026-10-31') - julianday(deposit_date_asof) AS INTEGER) AS days_since_deposit
FROM funded
WHERE deposit_quartile = 4                                  -- top 25% of idle deposits
ORDER BY first_deposit_inr DESC
LIMIT 50;""",
"Among users who funded but never traded, NTILE(4) ranks first-deposit size into quartiles; the top quartile is the highest-value idle capital. Returns the top 50 as an outreach list (full list: remove LIMIT).",
"Highest-intent, highest-value users to prioritise for a human or in-app activation nudge - the cheapest conversion opportunity.",
"<=50 rows: user_id, acquisition_channel, city, device_type, first_deposit_inr, deposit_date_asof, days_since_deposit.")

add("Q24", "Deposited but inactive users", "deposited but inactive users",
"""SELECT acquisition_channel,
       COUNT(*)                                                         AS funded_never_traded,
       ROUND(AVG(first_deposit_amount_asof_inr), 0)                     AS avg_first_deposit_inr,
       SUM(first_deposit_amount_asof_inr)                               AS idle_first_deposits_inr,
       ROUND(AVG(julianday('2026-10-31') - julianday(deposit_date_asof)), 0) AS avg_days_idle,
       SUM(julianday('2026-10-31') - julianday(deposit_date_asof) > 14) AS idle_over_14d
FROM users
WHERE deposit_asof = 1 AND trade_asof = 0
GROUP BY acquisition_channel ORDER BY funded_never_traded DESC;""",
"Filters to funded users without a first trade; julianday arithmetic measures how long the first deposit has been sitting idle against the 2026-10-31 snapshot.",
"Quantifies the activation opportunity per channel and how stale it is; >14 days idle is beyond the historical deposit-to-trade lag, i.e. stalled rather than in-flight.",
"7 rows: acquisition_channel, funded_never_traded, avg_first_deposit_inr, idle_first_deposits_inr, avg_days_idle, idle_over_14d.")

add("Q25", "KYC-pending customers (ageing)", "KYC-pending customers",
"""SELECT CASE WHEN age_d <= 11 THEN '0-11 d (in-flight)'
            WHEN age_d <= 30 THEN '12-30 d'
            WHEN age_d <= 90 THEN '31-90 d'
            ELSE '>90 d' END                       AS pending_age_bucket,
       COUNT(*)                                    AS kyc_pending_users,
       SUM(has_ticket)                             AS users_with_kyc_ticket,
       ROUND(100.0 * SUM(has_ticket) / COUNT(*), 1) AS pct_with_kyc_ticket
FROM (
    SELECT u.user_id,
           CAST(julianday('2026-10-31') - julianday(u.registration_date) AS INTEGER) AS age_d,
           EXISTS (SELECT 1 FROM support_tickets t WHERE t.user_id = u.user_id AND t.category = 'KYC & verification') AS has_ticket
    FROM users u WHERE u.kyc_asof = 0
)
GROUP BY pending_age_bucket ORDER BY pending_age_bucket;""",
"Users with no KYC event by the snapshot, aged from registration date. 11 days is the maximum historical KYC lag in mature data, so older pending users are stalled. A correlated EXISTS flags whether they contacted support about KYC.",
"Defines the KYC rescue queue: stalled users with a ticket need a service fix; those without need proactive outreach.",
"4 rows: pending_age_bucket, kyc_pending_users, users_with_kyc_ticket, pct_with_kyc_ticket.")

add("Q26", "Customers with repeated support tickets", "customers with repeated support tickets",
"""WITH per_user AS (
    SELECT user_id, COUNT(*) AS tickets, COUNT(DISTINCT category) AS categories,
           SUM(is_unresolved) AS unresolved, ROUND(AVG(csat_score), 2) AS avg_csat
    FROM support_tickets GROUP BY user_id HAVING COUNT(*) >= 3
)
SELECT p.tickets, COUNT(*) AS users, SUM(p.unresolved) AS unresolved_tickets,
       ROUND(AVG(p.categories), 1) AS avg_distinct_categories, ROUND(AVG(p.avg_csat), 2) AS avg_csat,
       ROUND(100.0 * AVG(u.dormant_3m_monthly), 1) AS dormant_3m_pct
FROM per_user p JOIN users u USING (user_id)
GROUP BY p.tickets ORDER BY p.tickets;""",
"HAVING COUNT(*) >= 3 isolates repeat contactors, then groups by ticket count. Compares their CSAT and dormancy with the overall rates. Association only - repeat contact does not prove support caused disengagement.",
"Shows the size of the repeat-contact problem; these users are candidates for proactive case ownership.",
"Rows per ticket count (3..7): tickets, users, unresolved_tickets, avg_distinct_categories, avg_csat, dormant_3m_pct.")

add("Q27", "Channel-wise customer quality scorecard", "channel-wise customer quality",
"""SELECT acquisition_channel,
       COUNT(*) AS registrations,
       ROUND(100.0 * SUM(CASE WHEN funnel_mature = 1 THEN trade_asof END) / SUM(funnel_mature), 1) AS first_trade_pct,
       ROUND(100.0 * AVG(m3_retained), 1)                                  AS m3_retention_pct,
       ROUND(100.0 * AVG(dormant_3m_monthly), 1)                           AS dormant_3m_pct,
       ROUND(AVG(CASE WHEN trade_asof = 1 THEN trading_value_6m_inr END), 0) AS avg_6m_trading_value_traders_inr,
       ROUND(AVG(CASE WHEN deposit_asof = 1 THEN first_deposit_amount_asof_inr END), 0) AS avg_first_deposit_inr,
       ROUND(1000.0 * SUM(ticket_count) / COUNT(*), 0)                     AS tickets_per_1000_users
FROM users GROUP BY acquisition_channel ORDER BY first_trade_pct DESC;""",
"One row per channel combining activation, retention, dormancy, value and support load, each on its proper eligible base (mature for funnel, non-NULL for retention).",
"Moves the channel conversation from volume to quality. Differences between channels are often statistically small; check significance (Phase 3) before reallocating spend.",
"7 rows: acquisition_channel, registrations, first_trade_pct, m3_retention_pct, dormant_3m_pct, avg_6m_trading_value_traders_inr, avg_first_deposit_inr, tickets_per_1000_users.")

add("Q28", "Customer lifetime activity by registration cohort", "customer lifetime activity",
"""SELECT registration_month AS cohort,
       COUNT(*)                                          AS users,
       ROUND(AVG(months_observed), 1)                    AS avg_months_observed,
       ROUND(AVG(active_months), 2)                      AS avg_active_months,
       ROUND(AVG(trade_months), 2)                       AS avg_trade_months,
       ROUND(AVG(total_trades), 1)                       AS avg_lifetime_trades,
       ROUND(AVG(total_trading_value_inr), 0)            AS avg_lifetime_trading_value_inr,
       ROUND(AVG(total_deposit_value_inr), 0)            AS avg_lifetime_deposits_inr,
       ROUND(AVG(activity_ratio), 3)                     AS avg_activity_ratio
FROM users GROUP BY registration_month ORDER BY registration_month;""",
"Per-cohort averages of lifetime counters from the monthly source (months active, months traded, trades, value). Older cohorts have longer exposure, so compare activity_ratio (active months / observed months) rather than totals.",
"Summarises accumulated customer value by vintage; the basis for any later lifetime-value estimate (no revenue is inferred here).",
"12 rows: cohort, users, avg_months_observed, avg_active_months, avg_trade_months, avg_lifetime_trades, avg_lifetime_trading_value_inr, avg_lifetime_deposits_inr, avg_activity_ratio.")

add("Q29", "Monthly trading volume", "monthly trading volume",
"""SELECT activity_month,
       SUM(traded_in_month)                               AS trading_users,
       SUM(trade_count)                                   AS trades,
       ROUND(SUM(trading_value_inr) / 1e6, 2)             AS trading_value_inr_mn,
       ROUND(SUM(deposit_value_inr) / 1e6, 2)             AS deposits_inr_mn,
       ROUND(SUM(withdrawal_value_inr) / 1e6, 2)          AS withdrawals_inr_mn,
       ROUND(SUM(net_flow_inr) / 1e6, 2)                  AS net_flow_inr_mn,
       ROUND(1.0 * SUM(trade_count) / NULLIF(SUM(traded_in_month), 0), 1) AS trades_per_trading_user
FROM monthly_activity GROUP BY activity_month ORDER BY activity_month;""",
"Sums activity measures by calendar month. Values are synthetic INR amounts; they describe customer activity, not platform revenue (no fee or revenue is modelled).",
"Tracks engagement depth and fund flows; rising trading users with falling trades per user would signal a broadening but shallower base.",
"12 rows: activity_month, trading_users, trades, trading_value_inr_mn, deposits_inr_mn, withdrawals_inr_mn, net_flow_inr_mn, trades_per_trading_user.")

add("Q30", "Operational bottleneck analysis (stage losses + related support load)", "operational bottleneck analysis",
"""WITH f AS (
    SELECT COUNT(*) AS reg, SUM(kyc_asof) AS kyc, SUM(bank_asof) AS bank, SUM(deposit_asof) AS dep, SUM(trade_asof) AS trd,
           SUM(CASE WHEN trade_asof = 1 AND active_30d_adj = 1 THEN 1 ELSE 0 END) AS act30
    FROM users WHERE funnel_mature = 1
), stages AS (
    SELECT 1 AS step, 'KYC Completed' AS stage, reg AS at_risk, reg - kyc AS lost, 'kyc' AS tkt_stage FROM f UNION ALL
    SELECT 2, 'Bank Linked',   kyc,  kyc - bank, 'bank'    FROM f UNION ALL
    SELECT 3, 'First Deposit', bank, bank - dep, 'deposit' FROM f UNION ALL
    SELECT 4, 'First Trade',   dep,  dep - trd,  'trade'   FROM f UNION ALL
    SELECT 5, 'Active (30d)',  trd,  trd - act30, NULL     FROM f
), tk AS (
    SELECT related_funnel_stage AS tkt_stage, COUNT(*) AS tickets,
           SUM(stage_pending_at_ticket = 1) AS tickets_while_pending,
           ROUND(AVG(resolution_time_hours), 1) AS avg_resolution_h
    FROM support_tickets WHERE related_funnel_stage IS NOT NULL GROUP BY related_funnel_stage
)
SELECT s.step, s.stage, s.at_risk, s.lost,
       ROUND(100.0 * s.lost / s.at_risk, 1)                         AS drop_rate_pct,
       ROUND(100.0 * s.lost / SUM(s.lost) OVER (), 1)               AS share_of_all_losses_pct,
       RANK() OVER (ORDER BY s.lost DESC)                           AS rank_by_users_lost,
       tk.tickets, tk.tickets_while_pending, tk.avg_resolution_h
FROM stages s LEFT JOIN tk USING (tkt_stage)
ORDER BY s.step;""",
"Combines funnel losses per stage (mature cohort, five loss points including the post-activation Active (30d) lapse) with support tickets tagged to that stage. Ranking by absolute users lost - not drop rate - shows where the biggest volume leaks are. Ticket counts cover all users (not only mature), so read them as contact load, not a causal measure.",
"A single operations view: where users are lost and how much support demand sits on the same step. KYC ranks first on volume, making it the priority for process and content fixes.",
"5 rows: step, stage, at_risk, lost, drop_rate_pct, share_of_all_losses_pct, rank_by_users_lost, tickets, tickets_while_pending, avg_resolution_h (ticket columns NULL for the Active (30d) stage).")

add("Q31", "Time-to-first-trade by channel (median via window)", "time to convert",
"""WITH t AS (
    SELECT acquisition_channel AS ch, days_reg_to_trade AS d,
           ROW_NUMBER() OVER (PARTITION BY acquisition_channel ORDER BY days_reg_to_trade) rn,
           COUNT(*)     OVER (PARTITION BY acquisition_channel) n
    FROM users WHERE trade_asof = 1 AND days_reg_to_trade IS NOT NULL
)
SELECT ch AS acquisition_channel, MAX(n) AS traders,
       ROUND(AVG(d), 1) AS mean_days,
       ROUND(AVG(CASE WHEN rn IN ((n + 1) / 2, (n + 2) / 2) THEN d END), 1) AS median_days,
       MAX(d) AS max_days
FROM t GROUP BY ch ORDER BY median_days;""",
"Median via ROW_NUMBER (SQLite has no MEDIAN). Uses only users who have traded, so values describe speed of activation among converters.",
"If channels differ little in time-to-trade, speed is a product/process property rather than a channel effect - supporting funnel fixes over channel fixes.",
"7 rows: acquisition_channel, traders, mean_days, median_days, max_days.")

add("Q32", "Support ticket backlog ageing", "backlog",
"""SELECT backlog_age_bucket, priority,
       SUM(status = 'Open')       AS open_tickets,
       SUM(status = 'Escalated')  AS escalated_tickets,
       COUNT(*)                   AS unresolved_total
FROM support_tickets
WHERE is_unresolved = 1
GROUP BY backlog_age_bucket, priority
ORDER BY CASE backlog_age_bucket WHEN '0-30d' THEN 1 WHEN '31-90d' THEN 2 WHEN '91-180d' THEN 3 ELSE 4 END,
         CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END;""",
"Unresolved = Open + Escalated. Grouped by ticket age bucket and priority, with a CASE in ORDER BY to sort buckets chronologically rather than alphabetically.",
"Shows how stale the backlog is and whether high-priority tickets are ageing - the SLA-risk list for the support lead.",
"Up to 12 rows: backlog_age_bucket, priority, open_tickets, escalated_tickets, unresolved_total.")

add("Q33", "Support exposure vs dormancy (descriptive)", "support impact",
"""SELECT CASE WHEN ticket_count = 0 THEN '0 tickets'
            WHEN unresolved_ticket_count > 0 THEN 'Has unresolved ticket'
            ELSE 'Tickets all resolved' END                       AS support_status,
       COUNT(*)                                                    AS eligible_users,
       ROUND(100.0 * AVG(dormant_3m_monthly), 1)                   AS dormant_3m_pct,
       ROUND(100.0 * AVG(m3_retained), 1)                          AS m3_retention_pct
FROM users WHERE dormant_3m_monthly IS NOT NULL
GROUP BY support_status ORDER BY dormant_3m_pct DESC;""",
"Descriptive comparison of dormancy and M3 retention across support status. It does not adjust for cohort age or channel mix, so it is a screening query; Phase 3 used a cohort-adjusted test for the formal claim.",
"Tests whether unresolved tickets deserve a retention-risk flag in operations dashboards.",
"3 rows: support_status, eligible_users, dormant_3m_pct, m3_retention_pct.")

add("Q34", "Source reconciliation: users table vs monthly activity", "data quality / reconciliation",
"""WITH m AS (
    SELECT user_id, MAX(traded_in_month) AS traded_ever_monthly, MAX(active_in_month) AS active_ever_monthly
    FROM monthly_activity GROUP BY user_id
)
SELECT SUM(u.trade_asof = 1 AND m.traded_ever_monthly = 1)      AS trade_both_sources,
       SUM(u.trade_asof = 1 AND m.traded_ever_monthly = 0)      AS trade_users_only,
       SUM(u.trade_asof = 0 AND m.traded_ever_monthly = 1)      AS trade_monthly_only,
       SUM(u.trade_asof = 0 AND m.traded_ever_monthly = 0)      AS trade_neither,
       ROUND(100.0 * SUM((u.trade_asof = 1) <> (m.traded_ever_monthly = 1)) / COUNT(*), 1) AS trade_source_conflict_pct,
       ROUND(100.0 * SUM(u.trade_asof = 1) / COUNT(*), 1)       AS users_table_trader_pct,
       ROUND(100.0 * SUM(m.traded_ever_monthly = 1) / COUNT(*), 1) AS monthly_table_trader_pct
FROM users u JOIN m USING (user_id);""",
"Compares the two sources on 'has ever traded'. Many users are classified differently in the two synthetic sources (a known property carried from Phase 2). This is why funnel metrics use users and retention/MAU use monthly_activity, and why mixed-source results are only indicative.",
"Makes the source-of-truth rule auditable and warns analysts not to mix tables when computing a single rate.",
"1 row: counts for each agreement/conflict combination plus conflict % and each source's trader %.")
