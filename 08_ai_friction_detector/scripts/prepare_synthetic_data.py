"""Create the slim synthetic input CSVs shipped with the prototype.

Source: the cleaned synthetic tables produced in Phases 1-2 (../data/cleaned).
Only the columns the engine needs are kept. Nothing is modified or imputed.
Usage (from 08_ai_friction_detector/): python scripts/prepare_synthetic_data.py [path_to_data_cleaned]
"""
import sys
from pathlib import Path
import pandas as pd

SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "data" / "cleaned"
DST = Path(__file__).resolve().parents[1] / "data" / "synthetic"
DST.mkdir(parents=True, exist_ok=True)

USER_COLS = [
    "user_id", "registration_date", "registration_month", "acquisition_campaign_id",
    "acquisition_channel", "source_platform", "city", "age_group", "device_type", "risk_profile",
    "kyc_date_asof", "bank_date_asof", "deposit_date_asof", "trade_date_asof",
    "first_deposit_amount_asof_inr", "last_active_date_adj", "total_trades",
    "total_trading_value_inr", "total_deposit_value_inr", "trading_value_6m_inr",
    "trade_months_6m", "active_months_6m", "activity_ratio",
    "flag_trade_conflict", "flag_deposit_conflict", "flag_last_active_conflict", "flag_activity_conflict",
]
TICKET_COLS = ["ticket_id", "user_id", "created_date", "category", "priority", "status",
               "resolution_time_hours", "csat_score"]
ACT_COLS = ["user_id", "activity_month", "active_in_month", "trade_count", "trading_value_inr",
            "deposit_value_inr", "withdrawal_value_inr"]

pd.read_csv(SRC / "Cleaned_Users.csv")[USER_COLS].to_csv(DST / "users.csv", index=False)
pd.read_csv(SRC / "Cleaned_Support_Tickets.csv")[TICKET_COLS].to_csv(DST / "tickets.csv", index=False)
pd.read_csv(SRC / "Cleaned_Monthly_Activity.csv")[ACT_COLS].to_csv(DST / "monthly_activity.csv", index=False)
(DST / "README.txt").write_text(
    "ALL FILES HERE ARE SYNTHETIC. Fictional Indian retail brokerage, 10,000 users, "
    "Nov 2025 - Oct 2026, snapshot 2026-10-31. No real customer data.\n")
print("wrote slim synthetic CSVs to", DST)
