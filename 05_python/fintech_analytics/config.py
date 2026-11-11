"""Project paths and analytical constants (single place to change them)."""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]          # repository root (fintech_analytics/ -> 05_python/ -> root)
RAW_DIR = ROOT / "data" / "raw"
DATA_CLEAN = ROOT / "data" / "cleaned"
DATA_DERIVED = DATA_CLEAN / "derived"               # tables derived from the cleaned data in the cleaning step
DB_PATH = ROOT / "04_sql" / "fintech_analytics.db"  # SQLite file is git-ignored; rebuild with 04_sql/build_database.py
OUT_DIR = ROOT / "05_python" / "outputs"
CHARTS_DIR = ROOT / "assets" / "charts"
BA_DIR = ROOT / "03_business_analytics"
STRATEGY_DIR = ROOT / "07_growth_strategy"

# Phase 3 result tables are stored next to the business question they answer (m1..m8 prefix -> folder).
_P3_DIRS = {"m1": BA_DIR / "acquisition", "m2": BA_DIR / "funnel", "m3": BA_DIR / "retention_churn",
            "m4": BA_DIR / "segmentation", "m5": BA_DIR / "campaign_performance", "m6": BA_DIR / "customer_support",
            "m7": STRATEGY_DIR / "phase3_experiments", "m8": STRATEGY_DIR / "phase3_findings"}


def p3_path(name):
    """Location of a Phase 3 output file by file name (m1_*.csv -> acquisition/, results.json -> summary/ ...)."""
    d = _P3_DIRS.get(str(name)[:2], BA_DIR / "summary")
    return d / name


def clean_path(name):
    """Cleaned_* tables live in data/cleaned; tables derived from them live in data/cleaned/derived."""
    return (DATA_CLEAN if str(name).startswith("Cleaned_") else DATA_DERIVED) / name


class _Mapper:
    """Drop-in for a directory Path: `M / "file"` resolves through a mapping function (keeps script bodies unchanged)."""
    def __init__(self, fn, dirs): self._fn, self._dirs = fn, dirs
    def __truediv__(self, name): return self._fn(name)
    def mkdir(self, *a, **k):
        for d in self._dirs: Path(d).mkdir(parents=True, exist_ok=True)
    def glob(self, pat):
        for d in self._dirs: yield from Path(d).glob(pat)


P3_TABLES = _Mapper(p3_path, [*_P3_DIRS.values(), BA_DIR / "summary"])
CLEAN_TABLES = _Mapper(clean_path, [DATA_CLEAN, DATA_DERIVED])
PHASE3_RESULTS = p3_path("results.json")

SNAPSHOT = pd.Timestamp("2026-10-31")               # all *_asof columns use events on/before this date
MATURE_CUTOFF_MONTH = "2026-10"                      # registered before this month = mature cohort (n = 9,116)
SEED = 42
STAGES = ["Registered", "KYC Completed", "Bank Linked", "First Deposit", "First Trade", "Active (30d)"]
STAGE_ORDER = {"Registered": 0, "KYC Completed": 1, "Bank Linked": 2, "Funded": 3, "Traded": 4}
CHANNEL_ORDER = ["Organic", "Referral", "CRM", "Paid Search", "Paid Social", "Affiliate", "Partnerships"]
DATE_COLS_USERS = ["registration_date", "kyc_date_asof", "bank_date_asof", "deposit_date_asof", "trade_date_asof"]
# Max historical stage lag in days (mature data): a user pending LONGER than this is 'stalled', not 'in-flight'
MAX_LAG = {"Registered": 11, "KYC Completed": 7, "Bank Linked": 14, "Funded": 11}
