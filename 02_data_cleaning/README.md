# 02 · Data cleaning and validation

Turns the raw synthetic CSV and workbook into analysis-ready tables **without modifying the originals**. **All data are synthetic.**

| File | Role |
|---|---|
| [`01_phase2_clean_validate_transform.py`](01_phase2_clean_validate_transform.py) | Reads `../data/raw/`, applies documented fixes, validates, writes `../data/cleaned/Cleaned_*.csv` and derived tables to `../data/cleaned/derived/` |
| [`cleaning_log.csv`](cleaning_log.csv) | Every cleaning decision: issue, action taken, records affected and rationale (including steps that changed 0 rows) |
| [`validation/`](validation/) | Validation checks, data-quality scorecard, row-level exceptions, relationship checks, summary-sheet reconciliation, retention validation |
| [`02_build_data_dictionary.py`](02_build_data_dictionary.py) | Writes [`../data/data_dictionary.csv`](../data/data_dictionary.csv) and [`../documentation/data_dictionary.md`](../documentation/data_dictionary.md) |
| [`03_build_dq_report.py`](03_build_dq_report.py) | Writes [`../documentation/data_quality_report.md`](../documentation/data_quality_report.md) |

The executable, narrated version of the cleaning logic is notebook [`01_data_loading_cleaning_eda.ipynb`](../05_python/notebooks/01_data_loading_cleaning_eda.ipynb) in `05_python/notebooks/`, which uses the same functions from `05_python/fintech_analytics/cleaning.py`.

## Run

```bash
python3 02_data_cleaning/01_phase2_clean_validate_transform.py
python3 02_data_cleaning/02_build_data_dictionary.py
python3 02_data_cleaning/03_build_dq_report.py
```

Re-running reproduces the committed cleaned files byte for byte.

## Principles

* Raw files are read-only inputs. Each change is logged; nothing is silently dropped.
* Quality problems that cannot be fixed (for example, activity-log entries that conflict with funnel dates) are **flagged, not corrected**, and carried into the limitations.
* Derived tables (funnel, cohorts, segments, campaign performance) live in `data/cleaned/derived/`.
