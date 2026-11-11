"""fintech_analytics - modular analytics package for the SYNTHETIC fintech growth project (Phase 4).
All data are synthetic; no real company data. Snapshot date: 2026-10-31."""
from . import config, loading, cleaning, eda, funnel, campaign, cohort, segmentation, support, kpi_report  # noqa: F401
__version__ = "1.0.0"
