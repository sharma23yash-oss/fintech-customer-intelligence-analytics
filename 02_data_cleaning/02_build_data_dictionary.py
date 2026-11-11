"""Builds the full data dictionary for the 8 cleaned tables from the CSVs + hand-written descriptions."""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data"; CLEAN = ROOT / "data" / "cleaned"; DER = CLEAN / "derived"
S, D = "Source", "Derived"   # origin labels

U = {  # Cleaned_Users: column -> (origin, description)
 "user_id": (S, "Unique synthetic customer ID. PRIMARY KEY."),
 "registration_date": (S, "Date the customer registered (ISO yyyy-mm-dd)."),
 "registration_month": (S, "Registration month, yyyy-mm. Cohort key."),
 "acquisition_campaign_id": (S, "Last-touch attributed campaign. FOREIGN KEY -> Cleaned_Campaigns.campaign_id."),
 "acquisition_channel": (S, "Acquisition channel of the attributed campaign."),
 "source_platform": (S, "Platform / source of the attributed campaign."),
 "city": (S, "City bucket; 'Other' = 9.2% of users, not analysable geographically."),
 "age_group": (S, "Age band: 18-24, 25-34, 35-44, 45-54, 55+."),
 "device_type": (S, "Android, iOS or Web."),
 "risk_profile": (S, "Self-declared risk profile: Conservative, Moderate, Aggressive."),
 "kyc_completed": (S, "1 if KYC completed (eventual completion flag - may include events after the snapshot; prefer kyc_asof)."),
 "kyc_completion_date": (S, "KYC completion date (may be after 2026-10-31 for 116 users)."),
 "bank_account_linked": (S, "1 if bank linked (eventual flag; prefer bank_asof)."),
 "bank_link_date": (S, "Bank-link date (196 post-snapshot dates)."),
 "first_deposit_made": (S, "1 if first deposit made (eventual flag; prefer deposit_asof)."),
 "first_deposit_date": (S, "First deposit date (274 post-snapshot dates)."),
 "first_deposit_amount_inr": (D, "First deposit amount in INR. NULL (not 0) when no deposit was made."),
 "first_trade_made": (S, "1 if first trade made (eventual flag; prefer trade_asof)."),
 "first_trade_date": (S, "First trade date (280 post-snapshot dates)."),
 "first_trade_segment": (S, "Product of first trade: Equity, Mutual Funds, ETF, Derivatives."),
 "active_30d": (S, "Supplied flag: active in the last 30 days at snapshot. Always 0 for users with tenure <= 30 days (not eligible)."),
 "last_active_date": (S, "Supplied last activity date. Unreliable: lower-bounded at 2026-07-03 and contradicts Monthly_Activity (see flag_last_active_conflict)."),
 "days_inactive_as_of_snapshot": (S, "Snapshot (2026-10-31) minus last_active_date, in days. Max 120."),
 "churned_30d_proxy": (S, "Supplied: days_inactive > 30. An INACTIVITY PROXY, not churn."),
 "churned_90d_proxy": (S, "Supplied: days_inactive > 90. Bounded by the 120-day maximum; under-states long-run inactivity."),
 "tenure_days": (D, "Snapshot minus registration_date, days."),
 "kyc_date_asof": (D, "kyc_completion_date if on/before snapshot, else NULL."),
 "kyc_asof": (D, "1 if KYC completed on/before snapshot. USE THIS for funnel metrics."),
 "bank_date_asof": (D, "bank_link_date if on/before snapshot, else NULL."),
 "bank_asof": (D, "1 if bank linked on/before snapshot."),
 "deposit_date_asof": (D, "first_deposit_date if on/before snapshot, else NULL."),
 "deposit_asof": (D, "1 if first deposit on/before snapshot."),
 "trade_date_asof": (D, "first_trade_date if on/before snapshot, else NULL."),
 "trade_asof": (D, "1 if first trade on/before snapshot."),
 "first_deposit_amount_asof_inr": (D, "first_deposit_amount_inr where deposit_asof = 1, else NULL."),
 "cohort_maturity": (D, "'mature' if registered before 2026-10; 'immature_oct26' otherwise."),
 "funnel_mature": (D, "1 for mature cohorts (Nov-2025..Sep-2026, n=9,116). Funnel rates use these users only."),
 "eligible_30d": (D, "1 if tenure_days >= 31, i.e. '>30 days inactive' is observable."),
 "eligible_90d": (D, "1 if tenure_days >= 91."),
 "furthest_stage_asof": (D, "Furthest funnel stage reached on/before snapshot: Registered / KYC Completed / Bank Linked / Funded / Traded."),
 "days_reg_to_kyc": (D, "Days from registration to KYC (as-of dates; NULL if not reached)."),
 "days_kyc_to_bank": (D, "Days from KYC to bank link."),
 "days_bank_to_deposit": (D, "Days from bank link to first deposit."),
 "days_deposit_to_trade": (D, "Days from first deposit to first trade."),
 "days_reg_to_trade": (D, "Days from registration to first trade."),
 "last_event_date_asof": (D, "Latest funnel event date on/before snapshot."),
 "last_active_date_adj": (D, "max(last_active_date, last_event_date_asof). Corrects 733 users whose last activity pre-dated their own funnel event."),
 "days_inactive_adj": (D, "Snapshot minus last_active_date_adj."),
 "inactive_30d_adj": (D, "1 if days_inactive_adj > 30. NULL when not eligible_30d. Inactivity proxy, not churn."),
 "inactive_90d_adj": (D, "1 if days_inactive_adj > 90. NULL when not eligible_90d. Bounded proxy."),
 "active_30d_adj": (D, "1 if days_inactive_adj <= 30. NULL when not eligible_30d."),
 "recency_status_30d": (D, "not_yet_eligible / active_last_30d / inactive_30d_proxy."),
 "recency_status_90d": (D, "not_yet_eligible / active_last_90d / inactive_90d_proxy."),
 "months_observed": (D, "Number of Monthly_Activity rows for the user."),
 "active_months": (D, "Months with active_in_month = 1."),
 "trade_months": (D, "Months with at least one trade."),
 "total_trades": (D, "Sum of monthly trade_count."),
 "total_trading_value_inr": (D, "Sum of monthly trading value, INR."),
 "total_deposit_value_inr": (D, "Sum of monthly deposits, INR."),
 "total_withdrawal_value_inr": (D, "Sum of monthly withdrawals, INR."),
 "trade_months_6m": (D, "Months with a trade in the last 6 calendar months (May-Oct 2026)."),
 "trading_value_6m_inr": (D, "Trading value in May-Oct 2026, INR."),
 "active_months_6m": (D, "Active months in May-Oct 2026."),
 "activity_ratio": (D, "active_months / months_observed."),
 "months_since_last_active_monthly": (D, "Oct-2026 minus last active calendar month. NULL if never active."),
 "never_active_monthly": (D, "1 if no active month in Monthly_Activity (n=337). Not necessarily churn - never engaged."),
 "dormant_3m_monthly": (D, "1 if no active month in Aug-Oct 2026. NULL if registered after Jul-2026 (not eligible)."),
 "m1_retained": (D, "1 if active in the calendar month after registration month. NULL if not observable (registered Oct-2026)."),
 "m3_retained": (D, "1 if active 3 calendar months after registration month. NULL if registered after Jul-2026."),
 "m6_retained": (D, "1 if active 6 calendar months after registration month. NULL if registered after Apr-2026."),
 "ticket_count": (D, "Support tickets raised (lifetime)."),
 "unresolved_ticket_count": (D, "Tickets with status Open or Escalated."),
 "flag_future_dated_event_raw": (D, "1 if any raw funnel event is dated after the snapshot (n=388)."),
 "flag_last_active_conflict": (D, "1 if last_active_date month differs from last active month in Monthly_Activity (n=6,336)."),
 "flag_last_active_before_event": (D, "1 if raw last_active_date pre-dates the user's own funnel event (n=733; corrected in last_active_date_adj)."),
 "flag_trade_conflict": (D, "1 if first_trade_made disagrees with trades in Monthly_Activity."),
 "flag_deposit_conflict": (D, "1 if first_deposit_made disagrees with deposits in Monthly_Activity."),
 "flag_activity_conflict": (D, "1 if any of trade / deposit / last-active conflicts apply."),
 "flag_deposit_outlier_iqr": (D, "1 if first deposit > Tukey fence (Rs 22,944). Retained - legitimate right tail."),
 "flag_deposit_outlier_log": (D, "1 if first deposit > Tukey fence on log scale (Rs 62,936)."),
}
CAMP = {
 "campaign_id": (S, "PRIMARY KEY."), "campaign_name": (S, "Campaign name."), "channel": (S, "Acquisition channel."), "source_platform": (S, "Source platform."),
 "campaign_spend_inr": (S, "Lump-sum illustrative spend over the whole window; no monthly breakdown."),
 "channel_group": (D, "Analyst grouping: Paid Media / Partner & Affiliate / Owned & Lifecycle / Organic."),
 "is_paid": (D, "1 if recorded spend > 0."), "spend_basis": (D, "recorded_spend or no_recorded_spend."),
}
MON = {
 "user_id": (S, "FOREIGN KEY -> Cleaned_Users.user_id. Part of composite PK."), "activity_month": (S, "yyyy-mm. Part of composite PK."),
 "months_since_registration": (S, "Calendar months since registration month (0 = partial registration month)."),
 "active_in_month": (S, "1 if at least one activity in the month."), "trade_count": (S, "Trades in the month."),
 "trading_value_inr": (S, "Monthly traded value, INR (synthetic)."), "deposit_value_inr": (S, "Deposits in the month, INR."), "withdrawal_value_inr": (S, "Withdrawals in the month, INR."),
 "activity_month_start": (D, "First day of activity_month (for Power BI date axis)."), "registration_month": (D, "Registration month of the user (cohort)."),
 "traded_in_month": (D, "trade_count > 0."), "deposited_in_month": (D, "deposit_value_inr > 0."), "withdrew_in_month": (D, "withdrawal_value_inr > 0."),
 "net_flow_inr": (D, "Deposits minus withdrawals."), "avg_trade_value_inr": (D, "trading_value / trade_count; NULL if no trades."),
 "is_registration_month": (D, "1 if months_since_registration = 0."),
 "flag_trade_without_first_trade_flag": (D, "Trades in a month for a user whose first_trade_made = 0 (n=5,640)."),
 "flag_trade_before_first_trade_month": (D, "Trades in a month earlier than the first-trade month (n=2,242)."),
 "flag_deposit_without_first_deposit_flag": (D, "Deposit for a user with first_deposit_made = 0 (n=2,613)."),
 "flag_deposit_before_first_deposit_month": (D, "Deposit earlier than first-deposit month (n=361)."),
 "flag_withdrawal_without_deposit_flag": (D, "Withdrawal for a user with first_deposit_made = 0 (n=1,818)."),
 "cum_deposit_inr": (D, "Running total of deposits per user."), "cum_withdrawal_inr": (D, "Running total of withdrawals per user."),
 "flag_cum_withdrawal_exceeds_deposits": (D, "1 if cumulative withdrawals exceed cumulative deposits (informational; do not use for balances)."),
 "flag_active_after_last_active_month": (D, "Active row after the month of the user's last_active_date (n=3,180)."),
 "flag_trading_value_outlier_iqr": (D, "Trading value above Tukey fence (Rs 30,365). Retained."),
 "flag_trading_value_outlier_log": (D, "Trading value above log-scale Tukey fence (Rs 105,451). Retained."),
 "flag_avg_trade_size_outlier": (D, "Average trade size above log-scale fence (Rs 35,759). Retained."),
}
TIX = {
 "ticket_id": (S, "PRIMARY KEY."), "user_id": (S, "FOREIGN KEY -> Cleaned_Users.user_id."), "created_date": (S, "Ticket creation date."),
 "category": (S, "KYC & verification, Bank linking, Deposits & withdrawals, Trading & orders, App navigation, Account access, Fees & charges."),
 "priority": (S, "Low / Medium / High. Does not change resolution time or escalation rate in this data."),
 "status": (S, "Resolved / Open / Escalated."), "resolution_time_hours": (S, "Hours to resolve; NULL unless Resolved (survivorship: averages are resolved-only)."),
 "csat_score": (S, "1-5; NULL unless Resolved."), "created_month": (S, "yyyy-mm."),
 "is_resolved": (D, "status = Resolved."), "is_unresolved": (D, "status in (Open, Escalated)."),
 "ticket_age_days": (D, "Snapshot minus created_date."), "backlog_age_bucket": (D, "Age bucket for unresolved tickets: 0-30d, 31-90d, 91-180d, >180d."),
 "csat_band": (D, "Low (1-2) / Neutral (3) / High (4-5)."), "days_since_registration": (D, "created_date minus registration_date."),
 "related_funnel_stage": (D, "kyc / bank / deposit / trade for the four funnel-related categories; NULL otherwise."),
 "stage_pending_at_ticket": (D, "1 if the related funnel event had not happened when the ticket was created (or never happened); 0 if already done; NULL for non-funnel categories. Hypothesis support only."),
 "flag_resolution_outlier": (D, "Resolution time above Tukey fence (27.85 h)."),
}
FUN = {
 "cut_type": (D, "Dimension of the cut: Overall, acquisition_channel, acquisition_campaign_id, device_type, age_group, city, risk_profile, registration_month."),
 "cut_value": (D, "Value of the cut."), "scope": (D, "mature_cohorts (Nov-25..Sep-26) or asof_snapshot_all_users (registration_month cut)."),
 "stage_order": (D, "1..6."), "stage_name": (D, "Registered, KYC Completed, Bank Linked, First Deposit, First Trade, Active (30d). 'App Visit' is NOT available in the data."),
 "users_registered": (D, "Users in the cut/scope."), "users_reached": (D, "Users reaching the stage on/before snapshot. Stage 6 = first-trade users with active_30d_adj = 1; NULL for the Oct-2026 cohort (not eligible)."),
 "conv_from_previous": (D, "users_reached / users_reached at previous stage."), "conv_from_registration": (D, "users_reached / users_registered."),
 "dropoff_from_previous": (D, "1 - conv_from_previous."), "median_days_from_previous": (D, "Median days from previous stage among those reaching it."), "p75_days_from_previous": (D, "75th percentile of the same."),
}
COH = {
 "registration_month": (D, "Cohort month. Composite PK with channel and months_since_registration."), "acquisition_channel": (D, "Channel."),
 "months_since_registration": (D, "0..11."), "cohort_users": (D, "Users in cohort x channel."),
 "active_users": (D, "Users active in that month. NULL if not yet observable."), "trading_users": (D, "Users with >= 1 trade."), "trades": (D, "Total trades."),
 "trading_value_inr": (D, "Total trading value."), "deposit_value_inr": (D, "Total deposits."), "withdrawal_value_inr": (D, "Total withdrawals."),
 "users_observed": (D, "Users with a row in the month."), "observable": (D, "1 if the cohort has reached that month by 2026-10."),
 "retention_rate": (D, "active_users / cohort_users. NULL (not zero) when not yet eligible. Sum counts, then divide, when aggregating."),
 "trading_rate": (D, "trading_users / cohort_users."), "cohort_status": (D, "observed / not_yet_eligible."),
}
CP = {
 "campaign_id": (S, "PK / FK."), "registered_users": (D, "Users attributed (all cohorts)."),
 "kyc_asof": (D, "KYC completed on/before snapshot (all users)."), "bank_asof": (D, "Bank linked as-of."), "deposit_asof": (D, "Deposited as-of."), "trade_asof": (D, "First traded as-of."),
 "mature_users": (D, "Registered before Oct-2026."), "kyc_rate_mature": (D, "Share of mature users who completed KYC."), "bank_rate_mature": (D, "..bank-linked."),
 "deposit_rate_mature": (D, "..deposited."), "first_trade_rate_mature": (D, "..traded."), "median_first_deposit_inr": (D, "Median first deposit (as-of)."),
 "eligible_30d_users": (D, "Users with tenure >= 31 d."), "active_30d_rate": (D, "Share active in last 30 d (adjusted)."), "inactive_30d_proxy_rate": (D, "1 - active_30d_rate."),
 "m1_retention": (D, "Month-1 retention (monthly source), observable cohorts only."), "m3_retention": (D, "Month-3 retention."), "dormant_3m_rate": (D, "Share with no activity Aug-Oct 2026 (registered <= Jul)."),
 "avg_activity_ratio": (D, "Mean active months / months observed."), "tickets": (D, "Tickets from attributed users."), "customer_months": (D, "User-months of exposure."),
 "share_of_registrations": (D, "Campaign registrations / all."), "share_of_spend": (D, "Campaign spend / all spend."),
 "cac_inr": (D, "Spend / registered users. NULL for zero-spend campaigns (not 'free')."),
 "cost_per_kyc_asof_inr": (D, "Spend / KYC completions on-snapshot. Penalises campaigns with many Oct-2026 registrations (still maturing)."),
 "cost_per_first_trade_asof_inr": (D, "Spend / first traders on-snapshot (same caveat)."),
 "cost_per_first_trade_at_maturity_inr": (D, "CAC / mature first-trade rate = expected cost per eventual first trader. Preferred comparison metric."),
 "cost_per_kyc_at_maturity_inr": (D, "CAC / mature KYC rate."), "cost_per_active_30d_user_inr": (D, "CAC / active_30d_rate."),
 "tickets_per_1000_customer_months": (D, "tickets / customer_months x 1000."), "cac_note": (D, "Explains NULL CAC for organic."),
}
SEG = {
 "user_id": (S, "PK / FK -> Cleaned_Users."), "tenure_days": (D, "Days since registration."), "furthest_stage_asof": (D, "See Cleaned_Users."),
 "r_score": (D, "Recency 1-5 from months since last active month (0 -> 5, 1 -> 4, 2 -> 3, 3-4 -> 2, >=5 or never -> 1). NULL if tenure < 60 d."),
 "f_score": (D, "Frequency 1-5 = 1 + months with a trade in last 6 months (capped at 4). NULL if tenure < 60 d."),
 "m_score": (D, "Monetary 1-5: 1 = no trading value in last 6 months; 2-5 = quartile of positive trading value. NULL if tenure < 60 d."),
 "rfm_segment": (D, "Champions (R>=4,F>=4) / Loyal (R>=3,F>=3) / Promising-Light (R>=4,F<=2) / At Risk (R 2-3,F>=3) / Hibernating (R<=2,F<=2) / Needs Attention / Too new."),
 "flag_needs_support": (D, "1 if >= 1 unresolved ticket or >= 3 tickets."),
 "flag_support_stuck_at_funnel_stage": (D, "1 if the user raised a funnel-related ticket while that stage was still pending."),
 "lifecycle_segment": (D, "Exclusive rule-based segment, priority order: 1 New/Onboarding (tenure<60d); 2 Frequent Trader (>=4 trading months in last 6); 3 High-Potential (first deposit >= p75 Rs 11,352, recently active); 4 Never Traded (no trade in either source); 5 Dormant (no activity Aug-Oct); 6 Core Active."),
 "months_since_last_active_monthly": (D, "See Cleaned_Users."),
}
GEN = {"trade_asof": "see Cleaned_Users", "deposit_asof": "see Cleaned_Users"}

TABLES = {"Cleaned_Users": U, "Cleaned_Campaigns": CAMP, "Cleaned_Monthly_Activity": MON, "Cleaned_Support_Tickets": TIX,
          "Customer_Funnel": FUN, "Customer_Cohorts": COH, "Campaign_Performance": {**CAMP, **CP}, "Customer_Segments": {**U, **SEG}}
KEYS = {"Cleaned_Users": "user_id (PK); acquisition_campaign_id -> Cleaned_Campaigns", "Cleaned_Campaigns": "campaign_id (PK)",
        "Cleaned_Monthly_Activity": "(user_id, activity_month) (PK); user_id -> Cleaned_Users", "Cleaned_Support_Tickets": "ticket_id (PK); user_id -> Cleaned_Users",
        "Customer_Funnel": "(cut_type, cut_value, stage_order)", "Customer_Cohorts": "(registration_month, acquisition_channel, months_since_registration)",
        "Campaign_Performance": "campaign_id (PK, FK -> Cleaned_Campaigns)", "Customer_Segments": "user_id (PK, FK -> Cleaned_Users)"}
GRAIN = {"Cleaned_Users": "1 row per customer", "Cleaned_Campaigns": "1 row per campaign", "Cleaned_Monthly_Activity": "1 row per customer x calendar month",
         "Cleaned_Support_Tickets": "1 row per ticket", "Customer_Funnel": "1 row per cut x stage", "Customer_Cohorts": "1 row per cohort x channel x month index (full grid incl. not-yet-eligible cells)",
         "Campaign_Performance": "1 row per campaign", "Customer_Segments": "1 row per customer"}

rows = []
for t, desc in TABLES.items():
    df = pd.read_csv((CLEAN if t.startswith("Cleaned_") else DER) / f"{t}.csv")
    for c in df.columns:
        o, d = desc.get(c, (None, None))
        if d is None: raise SystemExit(f"Missing description: {t}.{c}")
        rows.append(dict(table=t, column=c, dtype=str(df[c].dtype), origin=o, non_null=int(df[c].notna().sum()), null_pct=round(df[c].isna().mean() * 100, 1), description=d))
dd = pd.DataFrame(rows); dd.to_csv(OUT / "data_dictionary.csv", index=False)

md = ["# Data Dictionary — Cleaned Analytics Tables", "",
      "> **All data are synthetic** (fictional Indian online brokerage; not Futu/moomoo, Groww, Zerodha or any real firm). Observation window 2025-11-01 → 2026-10-31; snapshot 2026-10-31.", "",
      "**Conventions:** snake_case names · dates ISO `yyyy-mm-dd`, months `yyyy-mm` · booleans stored as `0/1` · amounts in INR · NULL = not applicable / not yet observable (never a stand-in zero) · `flag_*` columns mark issues, they never delete rows · `*_asof` columns only count events on/before the snapshot.", "",
      "## Relationships", "", "```", "Cleaned_Campaigns 1──* Cleaned_Users 1──* Cleaned_Monthly_Activity", "                                 1──* Cleaned_Support_Tickets", "                                 1──1 Customer_Segments", "Cleaned_Campaigns 1──1 Campaign_Performance",
      "Customer_Cohorts, Customer_Funnel = pre-aggregates (channel / campaign / month keys)", "```", ""]
for t in TABLES:
    sub = dd[dd.table == t]
    md += [f"## {t}", "", f"*Grain:* {GRAIN[t]} · *Keys:* {KEYS[t]} · *Rows:* {len(pd.read_csv((CLEAN if t.startswith('Cleaned_') else DER) / f'{t}.csv')):,} · *Columns:* {len(sub)}", "",
           "| Column | Type | Origin | Null % | Description |", "|---|---|---|---|---|"]
    md += [f"| `{r.column}` | {r.dtype} | {r.origin} | {r.null_pct} | {r.description} |" for r in sub.itertuples()]
    md.append("")
(ROOT / "documentation" / "data_dictionary.md").write_text("\n".join(md))
print("dictionary rows", len(dd))
