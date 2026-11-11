# 05 · Python analytics

Reusable analysis package, a one-command pipeline and five executed notebooks. **All data are synthetic.**

## Layout

| Path | Content |
|---|---|
| [`fintech_analytics/`](fintech_analytics/) | Package: `config` (all paths), `loading`, `cleaning`, `eda`, `funnel`, `campaign`, `cohort`, `segmentation`, `support`, `kpi_report` |
| [`notebooks/`](notebooks/) | `01` loading, cleaning, EDA · `02` funnel and campaign · `03` cohort retention and segmentation · `04` support operations · `05` automated KPI report (all executed, outputs saved) |
| [`pipeline/run_pipeline.py`](pipeline/run_pipeline.py) | One command: load → validate → EDA → funnel → campaign → cohort → segmentation → support → KPI report |
| [`pipeline/10_phase3_analysis.py`](pipeline/10_phase3_analysis.py), `11_…`, `12_…` | The business-analytics modules that write `../03_business_analytics/*` and the Phase 3 charts |
| [`pipeline/verify_phase4.py`](pipeline/verify_phase4.py) | Cross-checks Python vs SQL vs Excel KPIs (71/71 match) |
| [`pipeline/build_notebooks.py`](pipeline/build_notebooks.py) | Regenerates the notebooks from source cells |
| [`outputs/`](outputs/) | `KPI_Report.md`, `kpi_values.csv/json`, `kpi_verification_vs_phase3.csv`, `tables/` |

Charts are written to [`../assets/charts/`](../assets/charts/) (`python_*.png` from the pipeline, `phase3_*.png` from the business analytics).

## Run

```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements.txt            # from the repository root

python3 05_python/pipeline/run_pipeline.py           # add --skip-kmeans for a faster run
python3 05_python/pipeline/verify_phase4.py          # optional: reconcile to SQL/Excel
jupyter nbconvert --to notebook --execute --inplace 05_python/notebooks/01_data_loading_cleaning_eda.ipynb
```

No path is hard-coded: `fintech_analytics/config.py` derives everything from the repository root, so the project runs from any clone location.

## Notes

* The raw data are never modified. Cleaning reads `data/raw/` and writes `data/cleaned/`.
* The pipeline was tested on Linux with two library combinations (see the comments in [`../requirements.txt`](../requirements.txt)). It has **not** been run on macOS.
* The early-warning model (logistic regression) reaches AUC 0.57: it is reported as weak and is not used for decisions.
