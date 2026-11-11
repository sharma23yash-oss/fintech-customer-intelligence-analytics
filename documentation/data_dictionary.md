# Data Dictionary — Cleaned Analytics Tables

> **All data are synthetic** (fictional Indian online brokerage; not Futu/moomoo, Groww, Zerodha or any real firm). Observation window 2025-11-01 → 2026-10-31; snapshot 2026-10-31.

**Conventions:** snake_case names · dates ISO `yyyy-mm-dd`, months `yyyy-mm` · booleans stored as `0/1` · amounts in INR · NULL = not applicable / not yet observable (never a stand-in zero) · `flag_*` columns mark issues, they never delete rows · `*_asof` columns only count events on/before the snapshot.

## Relationships

```
Cleaned_Campaigns 1──* Cleaned_Users 1──* Cleaned_Monthly_Activity
                                 1──* Cleaned_Support_Tickets
                                 1──1 Customer_Segments
Cleaned_Campaigns 1──1 Campaign_Performance
Customer_Cohorts, Customer_Funnel = pre-aggregates (channel / campaign / month keys)
```

## Cleaned_Users

*Grain:* 1 row per customer · *Keys:* user_id (PK); acquisition_campaign_id -> Cleaned_Campaigns · *Rows:* 10,000 · *Columns:* 80

| Column | Type | Origin | Null % | Description |
|---|---|---|---|---|
| `user_id` | str | Source | 0.0 | Unique synthetic customer ID. PRIMARY KEY. |
| `registration_date` | str | Source | 0.0 | Date the customer registered (ISO yyyy-mm-dd). |
| `registration_month` | str | Source | 0.0 | Registration month, yyyy-mm. Cohort key. |
| `acquisition_campaign_id` | str | Source | 0.0 | Last-touch attributed campaign. FOREIGN KEY -> Cleaned_Campaigns.campaign_id. |
| `acquisition_channel` | str | Source | 0.0 | Acquisition channel of the attributed campaign. |
| `source_platform` | str | Source | 0.0 | Platform / source of the attributed campaign. |
| `city` | str | Source | 0.0 | City bucket; 'Other' = 9.2% of users, not analysable geographically. |
| `age_group` | str | Source | 0.0 | Age band: 18-24, 25-34, 35-44, 45-54, 55+. |
| `device_type` | str | Source | 0.0 | Android, iOS or Web. |
| `risk_profile` | str | Source | 0.0 | Self-declared risk profile: Conservative, Moderate, Aggressive. |
| `kyc_completed` | int64 | Source | 0.0 | 1 if KYC completed (eventual completion flag - may include events after the snapshot; prefer kyc_asof). |
| `kyc_completion_date` | str | Source | 29.2 | KYC completion date (may be after 2026-10-31 for 116 users). |
| `bank_account_linked` | int64 | Source | 0.0 | 1 if bank linked (eventual flag; prefer bank_asof). |
| `bank_link_date` | str | Source | 37.7 | Bank-link date (196 post-snapshot dates). |
| `first_deposit_made` | int64 | Source | 0.0 | 1 if first deposit made (eventual flag; prefer deposit_asof). |
| `first_deposit_date` | str | Source | 52.1 | First deposit date (274 post-snapshot dates). |
| `first_deposit_amount_inr` | float64 | Derived | 52.1 | First deposit amount in INR. NULL (not 0) when no deposit was made. |
| `first_trade_made` | int64 | Source | 0.0 | 1 if first trade made (eventual flag; prefer trade_asof). |
| `first_trade_date` | str | Source | 61.8 | First trade date (280 post-snapshot dates). |
| `first_trade_segment` | str | Source | 61.8 | Product of first trade: Equity, Mutual Funds, ETF, Derivatives. |
| `active_30d` | int64 | Source | 0.0 | Supplied flag: active in the last 30 days at snapshot. Always 0 for users with tenure <= 30 days (not eligible). |
| `last_active_date` | str | Source | 0.0 | Supplied last activity date. Unreliable: lower-bounded at 2026-07-03 and contradicts Monthly_Activity (see flag_last_active_conflict). |
| `days_inactive_as_of_snapshot` | int64 | Source | 0.0 | Snapshot (2026-10-31) minus last_active_date, in days. Max 120. |
| `churned_30d_proxy` | int64 | Source | 0.0 | Supplied: days_inactive > 30. An INACTIVITY PROXY, not churn. |
| `churned_90d_proxy` | int64 | Source | 0.0 | Supplied: days_inactive > 90. Bounded by the 120-day maximum; under-states long-run inactivity. |
| `tenure_days` | int64 | Derived | 0.0 | Snapshot minus registration_date, days. |
| `kyc_date_asof` | str | Derived | 30.4 | kyc_completion_date if on/before snapshot, else NULL. |
| `kyc_asof` | int64 | Derived | 0.0 | 1 if KYC completed on/before snapshot. USE THIS for funnel metrics. |
| `bank_date_asof` | str | Derived | 39.7 | bank_link_date if on/before snapshot, else NULL. |
| `bank_asof` | int64 | Derived | 0.0 | 1 if bank linked on/before snapshot. |
| `deposit_date_asof` | str | Derived | 54.9 | first_deposit_date if on/before snapshot, else NULL. |
| `deposit_asof` | int64 | Derived | 0.0 | 1 if first deposit on/before snapshot. |
| `trade_date_asof` | str | Derived | 64.6 | first_trade_date if on/before snapshot, else NULL. |
| `trade_asof` | int64 | Derived | 0.0 | 1 if first trade on/before snapshot. |
| `first_deposit_amount_asof_inr` | float64 | Derived | 54.9 | first_deposit_amount_inr where deposit_asof = 1, else NULL. |
| `cohort_maturity` | str | Derived | 0.0 | 'mature' if registered before 2026-10; 'immature_oct26' otherwise. |
| `funnel_mature` | int64 | Derived | 0.0 | 1 for mature cohorts (Nov-2025..Sep-2026, n=9,116). Funnel rates use these users only. |
| `eligible_30d` | int64 | Derived | 0.0 | 1 if tenure_days >= 31, i.e. '>30 days inactive' is observable. |
| `eligible_90d` | int64 | Derived | 0.0 | 1 if tenure_days >= 91. |
| `furthest_stage_asof` | str | Derived | 0.0 | Furthest funnel stage reached on/before snapshot: Registered / KYC Completed / Bank Linked / Funded / Traded. |
| `days_reg_to_kyc` | float64 | Derived | 30.4 | Days from registration to KYC (as-of dates; NULL if not reached). |
| `days_kyc_to_bank` | float64 | Derived | 39.7 | Days from KYC to bank link. |
| `days_bank_to_deposit` | float64 | Derived | 54.9 | Days from bank link to first deposit. |
| `days_deposit_to_trade` | float64 | Derived | 64.6 | Days from first deposit to first trade. |
| `days_reg_to_trade` | float64 | Derived | 64.6 | Days from registration to first trade. |
| `last_event_date_asof` | str | Derived | 30.4 | Latest funnel event date on/before snapshot. |
| `last_active_date_adj` | str | Derived | 0.0 | max(last_active_date, last_event_date_asof). Corrects 733 users whose last activity pre-dated their own funnel event. |
| `days_inactive_adj` | int64 | Derived | 0.0 | Snapshot minus last_active_date_adj. |
| `inactive_30d_adj` | float64 | Derived | 8.8 | 1 if days_inactive_adj > 30. NULL when not eligible_30d. Inactivity proxy, not churn. |
| `inactive_90d_adj` | float64 | Derived | 25.3 | 1 if days_inactive_adj > 90. NULL when not eligible_90d. Bounded proxy. |
| `active_30d_adj` | float64 | Derived | 8.8 | 1 if days_inactive_adj <= 30. NULL when not eligible_30d. |
| `recency_status_30d` | str | Derived | 0.0 | not_yet_eligible / active_last_30d / inactive_30d_proxy. |
| `recency_status_90d` | str | Derived | 0.0 | not_yet_eligible / active_last_90d / inactive_90d_proxy. |
| `months_observed` | int64 | Derived | 0.0 | Number of Monthly_Activity rows for the user. |
| `active_months` | int64 | Derived | 0.0 | Months with active_in_month = 1. |
| `trade_months` | int64 | Derived | 0.0 | Months with at least one trade. |
| `total_trades` | int64 | Derived | 0.0 | Sum of monthly trade_count. |
| `total_trading_value_inr` | float64 | Derived | 0.0 | Sum of monthly trading value, INR. |
| `total_deposit_value_inr` | float64 | Derived | 0.0 | Sum of monthly deposits, INR. |
| `total_withdrawal_value_inr` | float64 | Derived | 0.0 | Sum of monthly withdrawals, INR. |
| `trade_months_6m` | int64 | Derived | 0.0 | Months with a trade in the last 6 calendar months (May-Oct 2026). |
| `trading_value_6m_inr` | float64 | Derived | 0.0 | Trading value in May-Oct 2026, INR. |
| `active_months_6m` | int64 | Derived | 0.0 | Active months in May-Oct 2026. |
| `activity_ratio` | float64 | Derived | 0.0 | active_months / months_observed. |
| `months_since_last_active_monthly` | float64 | Derived | 3.4 | Oct-2026 minus last active calendar month. NULL if never active. |
| `never_active_monthly` | int64 | Derived | 0.0 | 1 if no active month in Monthly_Activity (n=337). Not necessarily churn - never engaged. |
| `dormant_3m_monthly` | float64 | Derived | 25.7 | 1 if no active month in Aug-Oct 2026. NULL if registered after Jul-2026 (not eligible). |
| `m1_retained` | float64 | Derived | 8.8 | 1 if active in the calendar month after registration month. NULL if not observable (registered Oct-2026). |
| `m3_retained` | float64 | Derived | 25.7 | 1 if active 3 calendar months after registration month. NULL if registered after Jul-2026. |
| `m6_retained` | float64 | Derived | 50.4 | 1 if active 6 calendar months after registration month. NULL if registered after Apr-2026. |
| `ticket_count` | int64 | Derived | 0.0 | Support tickets raised (lifetime). |
| `unresolved_ticket_count` | int64 | Derived | 0.0 | Tickets with status Open or Escalated. |
| `flag_future_dated_event_raw` | int64 | Derived | 0.0 | 1 if any raw funnel event is dated after the snapshot (n=388). |
| `flag_last_active_conflict` | int64 | Derived | 0.0 | 1 if last_active_date month differs from last active month in Monthly_Activity (n=6,336). |
| `flag_last_active_before_event` | int64 | Derived | 0.0 | 1 if raw last_active_date pre-dates the user's own funnel event (n=733; corrected in last_active_date_adj). |
| `flag_trade_conflict` | int64 | Derived | 0.0 | 1 if first_trade_made disagrees with trades in Monthly_Activity. |
| `flag_deposit_conflict` | int64 | Derived | 0.0 | 1 if first_deposit_made disagrees with deposits in Monthly_Activity. |
| `flag_activity_conflict` | int64 | Derived | 0.0 | 1 if any of trade / deposit / last-active conflicts apply. |
| `flag_deposit_outlier_iqr` | int64 | Derived | 0.0 | 1 if first deposit > Tukey fence (Rs 22,944). Retained - legitimate right tail. |
| `flag_deposit_outlier_log` | int64 | Derived | 0.0 | 1 if first deposit > Tukey fence on log scale (Rs 62,936). |

## Cleaned_Campaigns

*Grain:* 1 row per campaign · *Keys:* campaign_id (PK) · *Rows:* 10 · *Columns:* 8

| Column | Type | Origin | Null % | Description |
|---|---|---|---|---|
| `campaign_id` | str | Source | 0.0 | PRIMARY KEY. |
| `campaign_name` | str | Source | 0.0 | Campaign name. |
| `channel` | str | Source | 0.0 | Acquisition channel. |
| `source_platform` | str | Source | 0.0 | Source platform. |
| `campaign_spend_inr` | int64 | Source | 0.0 | Lump-sum illustrative spend over the whole window; no monthly breakdown. |
| `channel_group` | str | Derived | 0.0 | Analyst grouping: Paid Media / Partner & Affiliate / Owned & Lifecycle / Organic. |
| `is_paid` | int64 | Derived | 0.0 | 1 if recorded spend > 0. |
| `spend_basis` | str | Derived | 0.0 | recorded_spend or no_recorded_spend. |

## Cleaned_Monthly_Activity

*Grain:* 1 row per customer x calendar month · *Keys:* (user_id, activity_month) (PK); user_id -> Cleaned_Users · *Rows:* 64,645 · *Columns:* 28

| Column | Type | Origin | Null % | Description |
|---|---|---|---|---|
| `user_id` | str | Source | 0.0 | FOREIGN KEY -> Cleaned_Users.user_id. Part of composite PK. |
| `activity_month` | str | Source | 0.0 | yyyy-mm. Part of composite PK. |
| `months_since_registration` | int64 | Source | 0.0 | Calendar months since registration month (0 = partial registration month). |
| `active_in_month` | int64 | Source | 0.0 | 1 if at least one activity in the month. |
| `trade_count` | int64 | Source | 0.0 | Trades in the month. |
| `trading_value_inr` | float64 | Source | 0.0 | Monthly traded value, INR (synthetic). |
| `deposit_value_inr` | float64 | Source | 0.0 | Deposits in the month, INR. |
| `withdrawal_value_inr` | float64 | Source | 0.0 | Withdrawals in the month, INR. |
| `activity_month_start` | str | Derived | 0.0 | First day of activity_month (for Power BI date axis). |
| `registration_month` | str | Derived | 0.0 | Registration month of the user (cohort). |
| `traded_in_month` | int64 | Derived | 0.0 | trade_count > 0. |
| `deposited_in_month` | int64 | Derived | 0.0 | deposit_value_inr > 0. |
| `withdrew_in_month` | int64 | Derived | 0.0 | withdrawal_value_inr > 0. |
| `net_flow_inr` | float64 | Derived | 0.0 | Deposits minus withdrawals. |
| `avg_trade_value_inr` | float64 | Derived | 69.5 | trading_value / trade_count; NULL if no trades. |
| `is_registration_month` | int64 | Derived | 0.0 | 1 if months_since_registration = 0. |
| `flag_trade_without_first_trade_flag` | int64 | Derived | 0.0 | Trades in a month for a user whose first_trade_made = 0 (n=5,640). |
| `flag_trade_before_first_trade_month` | int64 | Derived | 0.0 | Trades in a month earlier than the first-trade month (n=2,242). |
| `flag_deposit_without_first_deposit_flag` | int64 | Derived | 0.0 | Deposit for a user with first_deposit_made = 0 (n=2,613). |
| `flag_deposit_before_first_deposit_month` | int64 | Derived | 0.0 | Deposit earlier than first-deposit month (n=361). |
| `flag_withdrawal_without_deposit_flag` | int64 | Derived | 0.0 | Withdrawal for a user with first_deposit_made = 0 (n=1,818). |
| `cum_deposit_inr` | float64 | Derived | 0.0 | Running total of deposits per user. |
| `cum_withdrawal_inr` | float64 | Derived | 0.0 | Running total of withdrawals per user. |
| `flag_cum_withdrawal_exceeds_deposits` | int64 | Derived | 0.0 | 1 if cumulative withdrawals exceed cumulative deposits (informational; do not use for balances). |
| `flag_active_after_last_active_month` | int64 | Derived | 0.0 | Active row after the month of the user's last_active_date (n=3,180). |
| `flag_trading_value_outlier_iqr` | int64 | Derived | 0.0 | Trading value above Tukey fence (Rs 30,365). Retained. |
| `flag_trading_value_outlier_log` | int64 | Derived | 0.0 | Trading value above log-scale Tukey fence (Rs 105,451). Retained. |
| `flag_avg_trade_size_outlier` | int64 | Derived | 0.0 | Average trade size above log-scale fence (Rs 35,759). Retained. |

## Cleaned_Support_Tickets

*Grain:* 1 row per ticket · *Keys:* ticket_id (PK); user_id -> Cleaned_Users · *Rows:* 7,614 · *Columns:* 18

| Column | Type | Origin | Null % | Description |
|---|---|---|---|---|
| `ticket_id` | str | Source | 0.0 | PRIMARY KEY. |
| `user_id` | str | Source | 0.0 | FOREIGN KEY -> Cleaned_Users.user_id. |
| `created_date` | str | Source | 0.0 | Ticket creation date. |
| `category` | str | Source | 0.0 | KYC & verification, Bank linking, Deposits & withdrawals, Trading & orders, App navigation, Account access, Fees & charges. |
| `priority` | str | Source | 0.0 | Low / Medium / High. Does not change resolution time or escalation rate in this data. |
| `status` | str | Source | 0.0 | Resolved / Open / Escalated. |
| `resolution_time_hours` | float64 | Source | 18.0 | Hours to resolve; NULL unless Resolved (survivorship: averages are resolved-only). |
| `csat_score` | float64 | Source | 18.0 | 1-5; NULL unless Resolved. |
| `created_month` | str | Source | 0.0 | yyyy-mm. |
| `is_resolved` | int64 | Derived | 0.0 | status = Resolved. |
| `is_unresolved` | int64 | Derived | 0.0 | status in (Open, Escalated). |
| `ticket_age_days` | int64 | Derived | 0.0 | Snapshot minus created_date. |
| `backlog_age_bucket` | str | Derived | 0.0 | Age bucket for unresolved tickets: 0-30d, 31-90d, 91-180d, >180d. |
| `csat_band` | str | Derived | 18.0 | Low (1-2) / Neutral (3) / High (4-5). |
| `days_since_registration` | int64 | Derived | 0.0 | created_date minus registration_date. |
| `related_funnel_stage` | str | Derived | 28.0 | kyc / bank / deposit / trade for the four funnel-related categories; NULL otherwise. |
| `stage_pending_at_ticket` | float64 | Derived | 28.0 | 1 if the related funnel event had not happened when the ticket was created (or never happened); 0 if already done; NULL for non-funnel categories. Hypothesis support only. |
| `flag_resolution_outlier` | float64 | Derived | 18.0 | Resolution time above Tukey fence (27.85 h). |

## Customer_Funnel

*Grain:* 1 row per cut x stage · *Keys:* (cut_type, cut_value, stage_order) · *Rows:* 312 · *Columns:* 12

| Column | Type | Origin | Null % | Description |
|---|---|---|---|---|
| `cut_type` | str | Derived | 0.0 | Dimension of the cut: Overall, acquisition_channel, acquisition_campaign_id, device_type, age_group, city, risk_profile, registration_month. |
| `cut_value` | str | Derived | 0.0 | Value of the cut. |
| `scope` | str | Derived | 0.0 | mature_cohorts (Nov-25..Sep-26) or asof_snapshot_all_users (registration_month cut). |
| `stage_order` | int64 | Derived | 0.0 | 1..6. |
| `stage_name` | str | Derived | 0.0 | Registered, KYC Completed, Bank Linked, First Deposit, First Trade, Active (30d). 'App Visit' is NOT available in the data. |
| `users_registered` | int64 | Derived | 0.0 | Users in the cut/scope. |
| `users_reached` | float64 | Derived | 0.3 | Users reaching the stage on/before snapshot. Stage 6 = first-trade users with active_30d_adj = 1; NULL for the Oct-2026 cohort (not eligible). |
| `conv_from_previous` | float64 | Derived | 0.3 | users_reached / users_reached at previous stage. |
| `conv_from_registration` | float64 | Derived | 0.3 | users_reached / users_registered. |
| `dropoff_from_previous` | float64 | Derived | 0.3 | 1 - conv_from_previous. |
| `median_days_from_previous` | float64 | Derived | 33.3 | Median days from previous stage among those reaching it. |
| `p75_days_from_previous` | float64 | Derived | 33.3 | 75th percentile of the same. |

## Customer_Cohorts

*Grain:* 1 row per cohort x channel x month index (full grid incl. not-yet-eligible cells) · *Keys:* (registration_month, acquisition_channel, months_since_registration) · *Rows:* 1,008 · *Columns:* 15

| Column | Type | Origin | Null % | Description |
|---|---|---|---|---|
| `registration_month` | str | Derived | 0.0 | Cohort month. Composite PK with channel and months_since_registration. |
| `acquisition_channel` | str | Derived | 0.0 | Channel. |
| `months_since_registration` | int64 | Derived | 0.0 | 0..11. |
| `cohort_users` | int64 | Derived | 0.0 | Users in cohort x channel. |
| `active_users` | float64 | Derived | 45.8 | Users active in that month. NULL if not yet observable. |
| `trading_users` | float64 | Derived | 45.8 | Users with >= 1 trade. |
| `trades` | float64 | Derived | 45.8 | Total trades. |
| `trading_value_inr` | float64 | Derived | 45.8 | Total trading value. |
| `deposit_value_inr` | float64 | Derived | 45.8 | Total deposits. |
| `withdrawal_value_inr` | float64 | Derived | 45.8 | Total withdrawals. |
| `users_observed` | float64 | Derived | 45.8 | Users with a row in the month. |
| `observable` | int64 | Derived | 0.0 | 1 if the cohort has reached that month by 2026-10. |
| `retention_rate` | float64 | Derived | 45.8 | active_users / cohort_users. NULL (not zero) when not yet eligible. Sum counts, then divide, when aggregating. |
| `trading_rate` | float64 | Derived | 45.8 | trading_users / cohort_users. |
| `cohort_status` | str | Derived | 0.0 | observed / not_yet_eligible. |

## Campaign_Performance

*Grain:* 1 row per campaign · *Keys:* campaign_id (PK, FK -> Cleaned_Campaigns) · *Rows:* 10 · *Columns:* 38

| Column | Type | Origin | Null % | Description |
|---|---|---|---|---|
| `campaign_id` | str | Source | 0.0 | PK / FK. |
| `campaign_name` | str | Source | 0.0 | Campaign name. |
| `channel` | str | Source | 0.0 | Acquisition channel. |
| `source_platform` | str | Source | 0.0 | Source platform. |
| `campaign_spend_inr` | int64 | Source | 0.0 | Lump-sum illustrative spend over the whole window; no monthly breakdown. |
| `channel_group` | str | Derived | 0.0 | Analyst grouping: Paid Media / Partner & Affiliate / Owned & Lifecycle / Organic. |
| `is_paid` | int64 | Derived | 0.0 | 1 if recorded spend > 0. |
| `spend_basis` | str | Derived | 0.0 | recorded_spend or no_recorded_spend. |
| `registered_users` | int64 | Derived | 0.0 | Users attributed (all cohorts). |
| `kyc_asof` | int64 | Derived | 0.0 | KYC completed on/before snapshot (all users). |
| `bank_asof` | int64 | Derived | 0.0 | Bank linked as-of. |
| `deposit_asof` | int64 | Derived | 0.0 | Deposited as-of. |
| `trade_asof` | int64 | Derived | 0.0 | First traded as-of. |
| `mature_users` | int64 | Derived | 0.0 | Registered before Oct-2026. |
| `kyc_rate_mature` | float64 | Derived | 0.0 | Share of mature users who completed KYC. |
| `bank_rate_mature` | float64 | Derived | 0.0 | ..bank-linked. |
| `deposit_rate_mature` | float64 | Derived | 0.0 | ..deposited. |
| `first_trade_rate_mature` | float64 | Derived | 0.0 | ..traded. |
| `median_first_deposit_inr` | float64 | Derived | 0.0 | Median first deposit (as-of). |
| `eligible_30d_users` | int64 | Derived | 0.0 | Users with tenure >= 31 d. |
| `active_30d_rate` | float64 | Derived | 0.0 | Share active in last 30 d (adjusted). |
| `inactive_30d_proxy_rate` | float64 | Derived | 0.0 | 1 - active_30d_rate. |
| `m1_retention` | float64 | Derived | 0.0 | Month-1 retention (monthly source), observable cohorts only. |
| `m3_retention` | float64 | Derived | 0.0 | Month-3 retention. |
| `dormant_3m_rate` | float64 | Derived | 0.0 | Share with no activity Aug-Oct 2026 (registered <= Jul). |
| `avg_activity_ratio` | float64 | Derived | 0.0 | Mean active months / months observed. |
| `tickets` | int64 | Derived | 0.0 | Tickets from attributed users. |
| `customer_months` | int64 | Derived | 0.0 | User-months of exposure. |
| `share_of_registrations` | float64 | Derived | 0.0 | Campaign registrations / all. |
| `share_of_spend` | float64 | Derived | 0.0 | Campaign spend / all spend. |
| `cac_inr` | float64 | Derived | 20.0 | Spend / registered users. NULL for zero-spend campaigns (not 'free'). |
| `cost_per_kyc_asof_inr` | float64 | Derived | 20.0 | Spend / KYC completions on-snapshot. Penalises campaigns with many Oct-2026 registrations (still maturing). |
| `cost_per_first_trade_asof_inr` | float64 | Derived | 20.0 | Spend / first traders on-snapshot (same caveat). |
| `cost_per_first_trade_at_maturity_inr` | float64 | Derived | 20.0 | CAC / mature first-trade rate = expected cost per eventual first trader. Preferred comparison metric. |
| `cost_per_kyc_at_maturity_inr` | float64 | Derived | 20.0 | CAC / mature KYC rate. |
| `cost_per_active_30d_user_inr` | float64 | Derived | 20.0 | CAC / active_30d_rate. |
| `tickets_per_1000_customer_months` | float64 | Derived | 0.0 | tickets / customer_months x 1000. |
| `cac_note` | str | Derived | 0.0 | Explains NULL CAC for organic. |

## Customer_Segments

*Grain:* 1 row per customer · *Keys:* user_id (PK, FK -> Cleaned_Users) · *Rows:* 10,000 · *Columns:* 32

| Column | Type | Origin | Null % | Description |
|---|---|---|---|---|
| `user_id` | str | Source | 0.0 | PK / FK -> Cleaned_Users. |
| `acquisition_channel` | str | Source | 0.0 | Acquisition channel of the attributed campaign. |
| `age_group` | str | Source | 0.0 | Age band: 18-24, 25-34, 35-44, 45-54, 55+. |
| `city` | str | Source | 0.0 | City bucket; 'Other' = 9.2% of users, not analysable geographically. |
| `device_type` | str | Source | 0.0 | Android, iOS or Web. |
| `risk_profile` | str | Source | 0.0 | Self-declared risk profile: Conservative, Moderate, Aggressive. |
| `tenure_days` | int64 | Derived | 0.0 | Days since registration. |
| `furthest_stage_asof` | str | Derived | 0.0 | See Cleaned_Users. |
| `trade_asof` | int64 | Derived | 0.0 | 1 if first trade on/before snapshot. |
| `deposit_asof` | int64 | Derived | 0.0 | 1 if first deposit on/before snapshot. |
| `first_deposit_amount_asof_inr` | float64 | Derived | 54.9 | first_deposit_amount_inr where deposit_asof = 1, else NULL. |
| `never_active_monthly` | int64 | Derived | 0.0 | 1 if no active month in Monthly_Activity (n=337). Not necessarily churn - never engaged. |
| `trade_months_6m` | int64 | Derived | 0.0 | Months with a trade in the last 6 calendar months (May-Oct 2026). |
| `trading_value_6m_inr` | float64 | Derived | 0.0 | Trading value in May-Oct 2026, INR. |
| `active_months_6m` | int64 | Derived | 0.0 | Active months in May-Oct 2026. |
| `total_trades` | int64 | Derived | 0.0 | Sum of monthly trade_count. |
| `total_trading_value_inr` | float64 | Derived | 0.0 | Sum of monthly trading value, INR. |
| `activity_ratio` | float64 | Derived | 0.0 | active_months / months_observed. |
| `dormant_3m_monthly` | float64 | Derived | 25.7 | 1 if no active month in Aug-Oct 2026. NULL if registered after Jul-2026 (not eligible). |
| `ticket_count` | int64 | Derived | 0.0 | Support tickets raised (lifetime). |
| `unresolved_ticket_count` | int64 | Derived | 0.0 | Tickets with status Open or Escalated. |
| `flag_trade_conflict` | int64 | Derived | 0.0 | 1 if first_trade_made disagrees with trades in Monthly_Activity. |
| `flag_deposit_conflict` | int64 | Derived | 0.0 | 1 if first_deposit_made disagrees with deposits in Monthly_Activity. |
| `flag_activity_conflict` | int64 | Derived | 0.0 | 1 if any of trade / deposit / last-active conflicts apply. |
| `r_score` | float64 | Derived | 16.9 | Recency 1-5 from months since last active month (0 -> 5, 1 -> 4, 2 -> 3, 3-4 -> 2, >=5 or never -> 1). NULL if tenure < 60 d. |
| `f_score` | float64 | Derived | 16.9 | Frequency 1-5 = 1 + months with a trade in last 6 months (capped at 4). NULL if tenure < 60 d. |
| `m_score` | float64 | Derived | 16.9 | Monetary 1-5: 1 = no trading value in last 6 months; 2-5 = quartile of positive trading value. NULL if tenure < 60 d. |
| `rfm_segment` | str | Derived | 0.0 | Champions (R>=4,F>=4) / Loyal (R>=3,F>=3) / Promising-Light (R>=4,F<=2) / At Risk (R 2-3,F>=3) / Hibernating (R<=2,F<=2) / Needs Attention / Too new. |
| `flag_needs_support` | int64 | Derived | 0.0 | 1 if >= 1 unresolved ticket or >= 3 tickets. |
| `flag_support_stuck_at_funnel_stage` | int64 | Derived | 0.0 | 1 if the user raised a funnel-related ticket while that stage was still pending. |
| `lifecycle_segment` | str | Derived | 0.0 | Exclusive rule-based segment, priority order: 1 New/Onboarding (tenure<60d); 2 Frequent Trader (>=4 trading months in last 6); 3 High-Potential (first deposit >= p75 Rs 11,352, recently active); 4 Never Traded (no trade in either source); 5 Dormant (no activity Aug-Oct); 6 Core Active. |
| `months_since_last_active_monthly` | float64 | Derived | 3.4 | See Cleaned_Users. |
